"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, MenuItem, Restaurant } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";

const CATEGORIES = ["Entrées", "Plats", "Desserts", "Boissons", "Ftour", "Autre"];

// Convertit un ISO UTC en valeur pour <input type="datetime-local"> (heure
// locale du navigateur) et inversement — sans lib externe.
function isoToLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function localInputToIso(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}

type Draft = { name: string; category: string; price: string; description: string; image_url: string };

function itemToDraft(item: MenuItem): Draft {
  return {
    name: item.name,
    category: item.category,
    price: String(item.price),
    description: item.description ?? "",
    image_url: item.image_url ?? "",
  };
}

const EMPTY_DRAFT: Draft = { name: "", category: "Plats", price: "", description: "", image_url: "" };

export default function DashboardPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["manager"]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [newItem, setNewItem] = useState<Draft>(EMPTY_DRAFT);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [ramadanEnabled, setRamadanEnabled] = useState(false);
  const [iftarInput, setIftarInput] = useState("");
  const [savingRamadan, setSavingRamadan] = useState(false);

  const restaurantId = staff?.restaurant_id ?? null;

  const load = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const [menu, rest] = await Promise.all([api.getMenu(restaurantId), api.getRestaurant(restaurantId)]);
      setItems(menu);
      setDrafts(Object.fromEntries(menu.map((m) => [m.id, itemToDraft(m)])));
      setRestaurant(rest);
      setRamadanEnabled(rest.ramadan_mode_enabled);
      setIftarInput(isoToLocalInput(rest.iftar_time));
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  useEffect(() => {
    if (restaurantId) load();
  }, [restaurantId, load]);

  async function saveRamadanMode(nextEnabled: boolean) {
    if (!restaurantId) return;
    setError(null);
    setSavingRamadan(true);
    try {
      const updated = await api.setRamadanMode(restaurantId, nextEnabled, localInputToIso(iftarInput));
      setRestaurant(updated);
      setRamadanEnabled(updated.ramadan_mode_enabled);
      flash(nextEnabled ? "Mode Ramadan activé." : "Mode Ramadan désactivé.");
    } catch (e) {
      setError(toFrenchMessage(e));
    } finally {
      setSavingRamadan(false);
    }
  }

  function logout() {
    clearToken();
    router.push("/login");
  }

  function flash(text: string) {
    setMessage(text);
    setTimeout(() => setMessage(null), 2500);
  }

  async function saveItem(item: MenuItem) {
    setError(null);
    const draft = drafts[item.id];
    const price = Number(draft.price);
    if (!draft.name.trim() || Number.isNaN(price) || price < 0) {
      setError("Nom et prix (positif) sont obligatoires.");
      return;
    }
    try {
      await api.updateMenuItem(item.id, {
        name: draft.name.trim(),
        category: draft.category,
        price,
        description: draft.description.trim() || null,
        image_url: draft.image_url.trim() || null,
      });
      flash(`« ${draft.name} » enregistré.`);
      await load();
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function toggleAvailability(item: MenuItem) {
    setError(null);
    try {
      await api.setMenuItemAvailability(item.id, !item.is_available);
      await load();
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function removeItem(item: MenuItem) {
    if (!confirm(`Supprimer « ${item.name} » du menu ?`)) return;
    setError(null);
    try {
      await api.deleteMenuItem(item.id);
      flash(`« ${item.name} » supprimé.`);
      await load();
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function addItem() {
    setError(null);
    if (!restaurantId) return;
    const price = Number(newItem.price);
    if (!newItem.name.trim() || Number.isNaN(price) || price < 0) {
      setError("Nom et prix (positif) sont obligatoires pour ajouter un article.");
      return;
    }
    try {
      await api.createMenuItem({
        restaurant_id: restaurantId,
        name: newItem.name.trim(),
        category: newItem.category,
        price,
        description: newItem.description.trim() || null,
        image_url: newItem.image_url.trim() || null,
      });
      flash(`« ${newItem.name} » ajouté au menu.`);
      setNewItem(EMPTY_DRAFT);
      await load();
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  if (staffLoading || !staff) return null;

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h1 className="text-lg font-semibold">Dashboard resto — gérer le menu</h1>
        <div className="flex items-center gap-4 text-sm">
          <Link href="/dashboard/stats" className="underline">
            Suivi de l&apos;activité
          </Link>
          <button onClick={logout} className="text-neutral-500 underline">
            Se déconnecter
          </button>
        </div>
      </div>
      <p className="text-sm text-neutral-500 mb-4">
        Modifier un article, basculer une rupture de stock, ou en ajouter un nouveau — sans passer par Swagger.
      </p>

      {restaurant && (
        <div className="border rounded-lg p-3 mb-4 bg-amber-50 border-amber-200">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <label className="flex items-center gap-2 font-medium text-amber-900">
              <input
                type="checkbox"
                checked={ramadanEnabled}
                onChange={(e) => {
                  setRamadanEnabled(e.target.checked);
                  saveRamadanMode(e.target.checked);
                }}
              />
              🌙 Mode Ramadan
            </label>
            {ramadanEnabled && (
              <div className="flex items-center gap-2 text-sm">
                <label htmlFor="iftar-time" className="text-amber-800">
                  Heure de l&apos;iftar aujourd&apos;hui
                </label>
                <input
                  id="iftar-time"
                  type="datetime-local"
                  value={iftarInput}
                  onChange={(e) => setIftarInput(e.target.value)}
                  onBlur={() => saveRamadanMode(true)}
                  disabled={savingRamadan}
                  className="border rounded px-2 py-1"
                />
              </div>
            )}
          </div>
          <p className="text-xs text-amber-700 mt-2">
            Une fois activé, les clients peuvent pré-commander pour l&apos;iftar depuis le menu. Pensez à mettre à
            jour l&apos;heure chaque jour (elle varie). Astuce : classez vos plats de rupture du jeûne dans la
            catégorie « Ftour » pour qu&apos;ils ressortent bien sur le menu client.
          </p>
        </div>
      )}

      {error && (
        <div className="mb-4 text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">{error}</div>
      )}
      {message && (
        <div className="mb-4 text-sm bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg p-3">
          {message}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const draft = drafts[item.id] ?? itemToDraft(item);
          return (
            <div key={item.id} className={`border rounded-lg p-3 ${!item.is_available ? "bg-neutral-50" : ""}`}>
              <div className="grid grid-cols-1 sm:grid-cols-[2fr_1fr_1fr] gap-2">
                <input
                  value={draft.name}
                  onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, name: e.target.value } }))}
                  className="border rounded px-2 py-1"
                  placeholder="Nom"
                />
                <select
                  value={draft.category}
                  onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, category: e.target.value } }))}
                  className="border rounded px-2 py-1"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                <input
                  value={draft.price}
                  onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, price: e.target.value } }))}
                  className="border rounded px-2 py-1"
                  placeholder="Prix (DT)"
                  inputMode="decimal"
                />
              </div>
              <input
                value={draft.description}
                onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, description: e.target.value } }))}
                className="border rounded px-2 py-1 w-full mt-2"
                placeholder="Description (facultatif)"
              />
              <input
                value={draft.image_url}
                onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, image_url: e.target.value } }))}
                className="border rounded px-2 py-1 w-full mt-2"
                placeholder="URL de la photo (facultatif)"
              />
              <div className="flex items-center justify-between mt-3">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={item.is_available} onChange={() => toggleAvailability(item)} />
                  {item.is_available ? "Disponible" : "Rupture de stock"}
                </label>
                <div className="flex gap-2">
                  <button onClick={() => saveItem(item)} className="bg-neutral-900 text-white text-sm px-3 py-1.5 rounded-lg">
                    Enregistrer
                  </button>
                  <button
                    onClick={() => removeItem(item)}
                    className="text-red-600 border border-red-200 text-sm px-3 py-1.5 rounded-lg"
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            </div>
          );
        })}
        {items.length === 0 && <p className="text-neutral-500">Aucun article pour l&apos;instant.</p>}
      </div>

      <h2 className="text-base font-semibold mt-8 mb-3">Ajouter un article</h2>
      <div className="border rounded-lg p-3">
        <div className="grid grid-cols-1 sm:grid-cols-[2fr_1fr_1fr] gap-2">
          <input
            value={newItem.name}
            onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
            className="border rounded px-2 py-1"
            placeholder="Nom"
          />
          <select
            value={newItem.category}
            onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
            className="border rounded px-2 py-1"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <input
            value={newItem.price}
            onChange={(e) => setNewItem({ ...newItem, price: e.target.value })}
            className="border rounded px-2 py-1"
            placeholder="Prix (DT)"
            inputMode="decimal"
          />
        </div>
        <input
          value={newItem.description}
          onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
          className="border rounded px-2 py-1 w-full mt-2"
          placeholder="Description (facultatif)"
        />
        <input
          value={newItem.image_url}
          onChange={(e) => setNewItem({ ...newItem, image_url: e.target.value })}
          className="border rounded px-2 py-1 w-full mt-2"
          placeholder="URL de la photo (facultatif)"
        />
        <button onClick={addItem} className="mt-3 bg-amber-700 text-white text-sm px-4 py-2 rounded-lg">
          Ajouter au menu
        </button>
      </div>
    </div>
  );
}
