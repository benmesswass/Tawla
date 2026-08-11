"use client";

import { useCallback, useEffect, useState } from "react";
import { Cairo } from "next/font/google";
import { api, wsUrl, ApiError, MenuItem, Order, OrderStatus, Restaurant, Table } from "@/lib/api";
import { toLocalizedMessage } from "@/lib/errors";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { useLocale } from "@/lib/i18n/useLocale";
import SplitBill from "@/components/SplitBill";

const cairo = Cairo({ subsets: ["arabic", "latin"], weight: ["400", "600", "700"] });

type CartLine = { item: MenuItem; quantity: number; note: string; shared: boolean };

type StepStatus = Exclude<OrderStatus, "cancelled">;

const STEP_STATUSES: StepStatus[] = [
  "pending_confirmation",
  "confirmed",
  "sent_to_kitchen",
  "in_preparation",
  "ready",
  "served",
];

function lastOrderStorageKey(qrToken: string): string {
  return `resto-qr-menu:last-order:${qrToken}`;
}

export default function MenuPage({ params }: { params: { qrToken: string } }) {
  const { qrToken } = params;
  const { t, locale, toggleLocale } = useLocale();

  const [table, setTable] = useState<Table | null>(null);
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [cart, setCart] = useState<Record<number, CartLine>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [trackedOrder, setTrackedOrder] = useState<Order | null>(null);
  const [tipInput, setTipInput] = useState("");
  const [paying, setPaying] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [preOrderForIftar, setPreOrderForIftar] = useState(false);

  function formatTime(iso: string): string {
    return new Date(iso).toLocaleTimeString(locale === "ar" ? "ar-TN" : "fr-FR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  const load = useCallback(() => {
    setLoadError(null);
    setTable(null);
    api
      .getTableByToken(qrToken)
      .then(async (t) => {
        setTable(t);
        const [rest, items] = await Promise.all([api.getRestaurant(t.restaurant_id), api.getMenu(t.restaurant_id)]);
        setRestaurant(rest);
        setMenu(items);

        // Si le client a déjà une commande en cours pour cette table (ex:
        // téléphone rafraîchi pendant que le plat était en préparation), on
        // reprend le suivi au lieu de lui montrer à nouveau tout le menu.
        const savedId = sessionStorage.getItem(lastOrderStorageKey(qrToken));
        if (savedId) {
          try {
            const order = await api.getOrder(Number(savedId));
            if (order.status !== "served" && order.status !== "cancelled") {
              setTrackedOrder(order);
            } else {
              sessionStorage.removeItem(lastOrderStorageKey(qrToken));
            }
          } catch {
            sessionStorage.removeItem(lastOrderStorageKey(qrToken));
          }
        }
      })
      .catch((e) => setLoadError(toLocalizedMessage(e, locale)));
  }, [qrToken, locale]);

  useEffect(() => {
    load();
  }, [load]);

  // Suivi temps réel de la commande après validation — jusqu'ici le client
  // n'avait plus aucune nouvelle après "commande envoyée" (audit PO 2026-08-10).
  const orderWsUrl =
    trackedOrder && restaurant ? wsUrl(`/ws/order/${restaurant.id}/${trackedOrder.id}`) : null;
  useReconnectingSocket(orderWsUrl, (msg) => {
    if (msg.event === "order.status_changed" && trackedOrder && msg.order_id === trackedOrder.id) {
      setTrackedOrder((prev) => (prev ? { ...prev, status: msg.status } : prev));
      if (msg.status === "served" || msg.status === "cancelled") {
        sessionStorage.removeItem(lastOrderStorageKey(qrToken));
      }
    }
    // Le serveur vient d'encaisser un paiement en espèces demandé depuis
    // cette même page — inutile de faire deviner au client s'il doit
    // rafraîchir pour le voir.
    if (msg.event === "order.payment_confirmed" && trackedOrder && msg.order_id === trackedOrder.id) {
      setTrackedOrder((prev) => (prev ? { ...prev, payment_status: "paid" } : prev));
    }
    // Dès qu'un serveur est affecté (prise en charge ou confirmation), le
    // client sait qui s'occupe de sa table sans avoir à demander.
    if (msg.event === "order.staff_assigned" && trackedOrder && msg.order_id === trackedOrder.id) {
      setTrackedOrder((prev) => (prev ? { ...prev, taken_by_staff_name: msg.staff_name } : prev));
    }
  });

  async function payByCard() {
    if (!trackedOrder) return;
    setPaying(true);
    setPaymentError(null);
    const tip = Number(tipInput.replace(",", ".")) || 0;
    try {
      const updated = await api.payByCard(trackedOrder.id, tip);
      setTrackedOrder(updated);
    } catch (e) {
      setPaymentError(toLocalizedMessage(e, locale));
    } finally {
      setPaying(false);
    }
  }

  async function payByCash() {
    if (!trackedOrder) return;
    setPaying(true);
    setPaymentError(null);
    try {
      const updated = await api.requestCashPayment(trackedOrder.id);
      setTrackedOrder(updated);
    } catch (e) {
      setPaymentError(toLocalizedMessage(e, locale));
    } finally {
      setPaying(false);
    }
  }

  function addToCart(item: MenuItem) {
    setCart((prev) => {
      const existing = prev[item.id];
      return {
        ...prev,
        [item.id]: {
          item,
          quantity: (existing?.quantity ?? 0) + 1,
          note: existing?.note ?? "",
          shared: existing?.shared ?? false,
        },
      };
    });
  }

  function removeFromCart(itemId: number) {
    setCart((prev) => {
      const next = { ...prev };
      if (next[itemId] && next[itemId].quantity > 1) {
        next[itemId] = { ...next[itemId], quantity: next[itemId].quantity - 1 };
      } else {
        delete next[itemId];
      }
      return next;
    });
  }

  function setNote(itemId: number, note: string) {
    setCart((prev) => (prev[itemId] ? { ...prev, [itemId]: { ...prev[itemId], note } } : prev));
  }

  function setShared(itemId: number, shared: boolean) {
    setCart((prev) => (prev[itemId] ? { ...prev, [itemId]: { ...prev[itemId], shared } } : prev));
  }

  const cartLines = Object.values(cart);
  const total = cartLines.reduce((sum, l) => sum + l.item.price * l.quantity, 0);

  async function validateOrder() {
    if (!table || cartLines.length === 0) return;
    setSending(true);
    setOrderError(null);
    try {
      const order = await api.createOrder({
        restaurant_id: table.restaurant_id,
        table_id: table.id,
        items: cartLines.map((l) => ({
          menu_item_id: l.item.id,
          quantity: l.quantity,
          notes: l.note || null,
          is_shared: l.shared,
        })),
        scheduled_for: preOrderForIftar && restaurant?.iftar_time ? restaurant.iftar_time : null,
      });
      sessionStorage.setItem(lastOrderStorageKey(qrToken), String(order.id));
      setTrackedOrder(order);
      setCart({});
      setPreOrderForIftar(false);
    } catch (e) {
      // Un article devenu indisponible pendant que le client avait le panier
      // ouvert ne doit plus faire disparaître tout l'écran (bug critique
      // corrigé suite à l'audit) : on retire juste cet article et le client
      // peut valider le reste.
      if (e instanceof ApiError && (e.code === "ITEM_UNAVAILABLE" || e.code === "ITEM_NOT_FOUND")) {
        const staleId = e.context.menu_item_id as number | undefined;
        if (staleId) {
          setCart((prev) => {
            const next = { ...prev };
            delete next[staleId];
            return next;
          });
        }
        api.getMenu(table.restaurant_id).then(setMenu).catch(() => {});
      }
      setOrderError(toLocalizedMessage(e, locale));
    } finally {
      setSending(false);
    }
  }

  function orderAgain() {
    setTrackedOrder(null);
    sessionStorage.removeItem(lastOrderStorageKey(qrToken));
  }

  const dir = t.dir;
  const wrapperClassName = locale === "ar" ? cairo.className : undefined;

  if (loadError) {
    return (
      <div dir={dir} className={`p-6 max-w-md mx-auto text-center ${wrapperClassName ?? ""}`}>
        <p className="text-red-600 mb-4">{loadError}</p>
        <button onClick={load} className="bg-neutral-900 text-white px-4 py-2 rounded-lg">
          {t.retry}
        </button>
      </div>
    );
  }
  if (!table || !restaurant) {
    return (
      <div dir={dir} className={`p-6 ${wrapperClassName ?? ""}`}>
        {t.loadingMenu}
      </div>
    );
  }

  if (trackedOrder) {
    const currentStepIndex = STEP_STATUSES.indexOf(trackedOrder.status as StepStatus);
    const cancelled = trackedOrder.status === "cancelled";
    return (
      <div dir={dir} className={`p-6 max-w-md mx-auto ${wrapperClassName ?? ""}`}>
        <h1 className="text-xl font-semibold text-center">
          {cancelled ? t.orderCancelledTitle : t.orderSentTitle}
        </h1>
        <p className="mt-2 text-neutral-600 text-center">{t.orderSubtitle(table.label, trackedOrder.id)}</p>

        {!cancelled && trackedOrder.scheduled_for && (
          <p className="mt-4 text-sm text-center bg-indigo-50 text-indigo-800 border border-indigo-200 rounded-lg py-2 px-3">
            {t.preorderBadge(formatTime(trackedOrder.scheduled_for))}
          </p>
        )}

        {!cancelled && trackedOrder.taken_by_staff_name && (
          <p className="mt-4 text-sm text-center bg-amber-50 text-amber-800 border border-amber-200 rounded-lg py-2 px-3">
            {t.dedicatedServer(trackedOrder.taken_by_staff_name)}
          </p>
        )}

        {!cancelled && (
          <ol className="mt-8 space-y-4">
            {STEP_STATUSES.map((status, i) => {
              const done = i <= currentStepIndex;
              return (
                <li key={status} className="flex items-center gap-3">
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 ${
                      done ? "bg-amber-600 text-white" : "bg-neutral-200 text-neutral-500"
                    }`}
                  >
                    {done ? "✓" : i + 1}
                  </span>
                  <span className={done ? "font-medium text-neutral-900" : "text-neutral-400"}>
                    {t.steps[status]}
                  </span>
                </li>
              );
            })}
          </ol>
        )}

        <div className="mt-8 border-t pt-4">
          <p className="text-sm font-medium mb-2">{t.orderDetailsTitle}</p>
          <ul className="text-sm text-neutral-600 space-y-1">
            {trackedOrder.items.map((it) => (
              <li key={it.id}>
                {it.quantity}× {it.menu_item_name}
                {it.is_shared && <span className="text-amber-700"> · {t.sharedTag}</span>}
                {it.notes && <span className="text-neutral-400"> — {it.notes}</span>}
              </li>
            ))}
          </ul>
          <div className="flex justify-between font-medium mt-2 pt-2 border-t">
            <span>{t.total}</span>
            <span>
              {trackedOrder.total_amount.toFixed(2)} {t.currency}
            </span>
          </div>
        </div>

        {!cancelled && (
          <div className="mt-6 border-t pt-4">
            <p className="text-sm font-medium mb-3">{t.paymentTitle}</p>

            {trackedOrder.payment_status === "paid" && (
              <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                {t.paidMessage(trackedOrder.payment_method === "card" ? "card" : "cash", trackedOrder.tip_amount)}
              </p>
            )}

            {trackedOrder.payment_status === "pending" && (
              <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                {t.cashPendingMessage(trackedOrder.total_amount)}
              </p>
            )}

            {trackedOrder.payment_status === "unpaid" && (
              <div className="space-y-3">
                {paymentError && (
                  <div className="text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">
                    {paymentError}
                  </div>
                )}
                <SplitBill order={trackedOrder} t={t} />
                <div>
                  <label htmlFor="tip" className="text-sm text-neutral-500">
                    {t.tipLabel}
                  </label>
                  <input
                    id="tip"
                    type="text"
                    inputMode="decimal"
                    value={tipInput}
                    onChange={(e) => setTipInput(e.target.value)}
                    placeholder={t.tipPlaceholder}
                    className="mt-1 w-full text-sm border rounded-lg px-3 py-1.5"
                  />
                </div>
                <button
                  onClick={payByCard}
                  disabled={paying}
                  className="w-full bg-neutral-900 text-white rounded-lg py-2.5 disabled:opacity-50"
                >
                  {t.payByCard}
                </button>
                <button
                  onClick={payByCash}
                  disabled={paying}
                  className="w-full border border-neutral-300 rounded-lg py-2.5 disabled:opacity-50"
                >
                  {t.payByCash}
                </button>
              </div>
            )}
          </div>
        )}

        <button onClick={orderAgain} className="mt-8 w-full border border-neutral-300 rounded-lg py-2.5">
          {t.orderAgain}
        </button>
      </div>
    );
  }

  const availableItems = menu.filter((m) => m.is_available);
  const categories = Array.from(new Set(availableItems.map((m) => m.category)));

  return (
    <div dir={dir} className={`pb-32 ${wrapperClassName ?? ""}`}>
      <header className="bg-amber-700 text-white px-4 py-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{restaurant.name}</h1>
          <p className="text-amber-100 text-sm">{table.label}</p>
        </div>
        <button
          onClick={toggleLocale}
          className="shrink-0 text-sm border border-amber-300 rounded-lg px-3 py-1.5 text-amber-50"
        >
          {t.localeSwitchLabel}
        </button>
      </header>

      {restaurant.ramadan_mode_enabled && restaurant.iftar_time && (
        <div className="bg-indigo-950 text-indigo-100 px-4 py-3 text-sm text-center">
          {t.ramadanBanner(formatTime(restaurant.iftar_time))}
        </div>
      )}

      <div className="p-4 max-w-md mx-auto">
        {orderError && (
          <div className="mb-4 text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3 flex justify-between items-start gap-2">
            <span>{orderError}</span>
            <button onClick={() => setOrderError(null)} aria-label={t.closeErrorAria} className="text-red-500">
              ✕
            </button>
          </div>
        )}

        {categories.map((category) => (
          <section key={category} className="mb-6">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-amber-700 mb-2">{category}</h2>
            {availableItems
              .filter((m) => m.category === category)
              .map((item) => (
                <div key={item.id} className="border-b py-3">
                  <div className="flex justify-between items-center">
                    <div className="pe-3">
                      <div className="font-medium">
                        {item.name}
                        {item.spice_level > 0 && <span className="ms-1">{"🌶️".repeat(item.spice_level)}</span>}
                        {!item.is_halal && (
                          <span className="ms-1 text-xs font-normal text-red-600 border border-red-200 rounded px-1 align-middle">
                            {t.notHalalBadge}
                          </span>
                        )}
                      </div>
                      {item.description && <div className="text-sm text-neutral-500">{item.description}</div>}
                      {item.allergens && (
                        <div className="text-xs text-neutral-400 mt-0.5">{t.allergensLabel(item.allergens)}</div>
                      )}
                      <div className="text-sm text-neutral-500 mt-0.5">
                        {item.price.toFixed(2)} {t.currency}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {item.image_url && (
                        <img
                          src={item.image_url}
                          alt={item.name}
                          className="w-12 h-12 rounded-lg object-cover hidden sm:block"
                        />
                      )}
                      {cart[item.id] && (
                        <>
                          <button
                            onClick={() => removeFromCart(item.id)}
                            aria-label={t.removeFromCartAria(item.name)}
                            className="w-8 h-8 rounded-full border"
                          >
                            -
                          </button>
                          <span>{cart[item.id].quantity}</span>
                        </>
                      )}
                      <button
                        onClick={() => addToCart(item)}
                        aria-label={t.addToCartAria(item.name)}
                        className="w-8 h-8 rounded-full bg-neutral-900 text-white"
                      >
                        +
                      </button>
                    </div>
                  </div>
                  {cart[item.id] && (
                    <>
                      <input
                        type="text"
                        value={cart[item.id].note}
                        onChange={(e) => setNote(item.id, e.target.value)}
                        placeholder={t.notePlaceholder}
                        className="mt-2 w-full text-sm border rounded-lg px-3 py-1.5"
                      />
                      <label className="mt-2 flex items-center gap-2 text-sm text-neutral-600">
                        <input
                          type="checkbox"
                          checked={cart[item.id].shared}
                          onChange={(e) => setShared(item.id, e.target.checked)}
                        />
                        {t.sharedCheckboxLabel}
                      </label>
                    </>
                  )}
                </div>
              ))}
          </section>
        ))}

        {cartLines.length > 0 && (
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4">
            <div className="max-w-md mx-auto">
              {restaurant.ramadan_mode_enabled && restaurant.iftar_time && (
                <label className="flex items-center gap-2 text-sm text-indigo-900 mb-3">
                  <input
                    type="checkbox"
                    checked={preOrderForIftar}
                    onChange={(e) => setPreOrderForIftar(e.target.checked)}
                  />
                  {t.preorderCheckboxLabel(formatTime(restaurant.iftar_time))}
                </label>
              )}
              <div className="flex justify-between items-center">
                <span className="font-medium">
                  {total.toFixed(2)} {t.currency}
                </span>
                <button
                  onClick={validateOrder}
                  disabled={sending}
                  className="bg-neutral-900 text-white px-4 py-2 rounded-lg"
                >
                  {sending ? t.sending : t.validateOrder}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
