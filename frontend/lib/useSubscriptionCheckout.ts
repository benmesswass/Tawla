"use client";

import { useEffect, useRef } from "react";
import { api, type Restaurant } from "@/lib/api";

/**
 * Paiement d'abonnement (palier Tawla payé par le restaurant, pas le
 * paiement d'une commande par le client) dans un nouvel onglet plutôt
 * qu'une redirection sur place (retour utilisateur, 2026-09-02) :
 * UpgradeModal, SubscriptionReminderModal et ActivationRequired restent
 * montés pendant que le manager règle sur Konnect/Stripe, au lieu de perdre
 * tout l'état du dashboard. Partagé entre les trois plutôt que dupliqué :
 * la manip pour que Safari ne bloque pas `window.open` après un `await`
 * (voir openPaymentTab) est facile à casser en la recopiant trois fois.
 *
 * Ni le webhook ni la page de retour (`?konnect=success` /
 * `?stripe_subscription=success`, dashboard/page.tsx) ne concernent CET
 * onglet-ci une fois qu'il ne quitte plus Tawla — ils atterrissent dans le
 * nouvel onglet. `onPaid` est donc rappelé ici à chaque retour sur cet
 * onglet tant qu'un paiement a été lancé ; `checkSubscriptionPayment` est
 * idempotent (tenants/service.py::settle_subscription_payment) — sans
 * risque à le rerappeler tant que rien n'est réglé côté fournisseur.
 */
export function useSubscriptionCheckout(
  restaurantId: number,
  onPaid: (restaurant: Restaurant) => void,
  onError: (error: unknown) => void
) {
  const awaitingReturn = useRef(false);

  useEffect(() => {
    function onVisibilityChange() {
      if (document.visibilityState !== "visible" || !awaitingReturn.current) return;
      api.checkSubscriptionPayment(restaurantId).then(onPaid).catch(onError);
    }
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [restaurantId, onPaid, onError]);

  /**
   * À appeler AVANT le premier `await` du gestionnaire de clic — après un
   * `await`, Safari ne relie plus `window.open` au geste utilisateur et le
   * bloque comme un popup.
   */
  function openPaymentTab(): Window | null {
    return window.open("", "_blank");
  }

  /**
   * `payUrl` reçu après l'appel réseau : redirige l'onglet ouvert par
   * `openPaymentTab` et arme le suivi du retour. Sans onglet (popup bloqué
   * malgré tout) : retombe sur le comportement historique, une redirection
   * sur place de cet onglet-ci.
   */
  function goToPayment(tab: Window | null, payUrl: string) {
    if (tab) {
      tab.location.href = payUrl;
      awaitingReturn.current = true;
    } else {
      window.location.href = payUrl;
    }
  }

  return { openPaymentTab, goToPayment };
}
