"use client";

import { useEffect, useRef, useState } from "react";

export type SocketStatus = "connecting" | "connected" | "disconnected" | "unauthorized";

// Code applicatif renvoyé par le backend quand le canal refuse le jeton (voir
// notifications/dependencies.py). Distinct d'une coupure réseau : réessayer
// n'y changera jamais rien.
const WS_UNAUTHORIZED = 4401;

export type SocketSend = (data: unknown) => boolean;

/**
 * Une URL qui doit être **refabriquée avant chaque tentative de connexion**
 * (ROADMAP_PRODUCTION.md §P2.4).
 *
 * Les canaux du personnel s'autorisent désormais par un billet à usage unique
 * de 30 secondes : une URL calculée une fois ne servirait qu'une fois, et la
 * première reconnexion échouerait — panne d'autant plus pénible qu'elle ne se
 * produirait qu'après une coupure réseau, c'est-à-dire précisément au moment
 * où l'écran doit revenir.
 *
 * `cle` est ce dont dépend la connexion (l'identifiant du canal), et **elle
 * seule** relance l'effet : `fabriquer` est une nouvelle fonction à chaque
 * rendu, la mettre en dépendance rebrancherait la socket en boucle.
 *
 * `fabriquer` rend `null` quand aucune session ne permettra jamais d'obtenir
 * l'URL (statut `unauthorized`, on s'arrête), et **lève** sur une panne
 * passagère (on réessaie avec le backoff).
 */
export type FabriqueUrl = { cle: string; fabriquer: () => Promise<string | null> };

/**
 * WebSocket avec reconnexion automatique (backoff exponentiel plafonné) et
 * statut exposé pour affichage — avant ce hook, une coupure réseau de
 * quelques secondes sur les écrans serveur/cuisine tuait le flux temps réel
 * silencieusement, sans aucune tentative de reconnexion (audit 2026-08-10).
 *
 * Depuis la Phase 12.2 les canaux staff et cuisine sont authentifiés : un
 * refus (session expirée, compte désactivé) arrête définitivement les
 * tentatives et remonte le statut `unauthorized`, au lieu de marteler un canal
 * auquel l'appelant n'aura jamais droit.
 *
 * `send` renvoie `false` sans lever d'exception quand la connexion n'est pas
 * ouverte — à l'appelant de décider du repli (ex. panier local le temps que
 * la table reconnecte), jamais à ce hook générique, aussi utilisé par les
 * canaux staff/cuisine qui n'envoient jamais rien.
 */
export function useReconnectingSocket(
  source: string | null | FabriqueUrl,
  onMessage: (data: any) => void
): { status: SocketStatus; send: SocketSend } {
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  // Gardée dans une ref et non en dépendance : voir `FabriqueUrl`.
  const sourceRef = useRef(source);
  sourceRef.current = source;
  const wsRef = useRef<WebSocket | null>(null);

  const cle = typeof source === "string" ? source : source?.cle ?? null;

  useEffect(() => {
    if (!cle) return;

    let attempt = 0;
    let closedByUs = false;
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout>;

    function reessayer() {
      const delay = Math.min(1000 * 2 ** attempt, 15000);
      attempt += 1;
      retryTimer = setTimeout(connect, delay);
    }

    async function connect() {
      if (closedByUs) return;
      setStatus("connecting");

      const courante = sourceRef.current;
      let url: string | null;
      try {
        url = typeof courante === "string" ? courante : await courante!.fabriquer();
      } catch {
        // Panne passagère (réseau coupé) : c'est exactement le cas que le
        // backoff existe pour absorber.
        setStatus("disconnected");
        reessayer();
        return;
      }
      // Le démontage a pu se produire pendant l'aller-retour du billet.
      if (closedByUs) return;
      if (!url) {
        setStatus("unauthorized");
        return;
      }

      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        attempt = 0;
        setStatus("connected");
      };
      ws.onmessage = (event) => {
        try {
          onMessageRef.current(JSON.parse(event.data));
        } catch {
          // message non-JSON, ignoré (ex: keep-alive)
        }
      };
      ws.onclose = (event) => {
        if (closedByUs) return;
        if (event.code === WS_UNAUTHORIZED) {
          setStatus("unauthorized");
          return;
        }
        setStatus("disconnected");
        reessayer();
      };
      ws.onerror = () => ws?.close();
    }

    connect();
    return () => {
      closedByUs = true;
      clearTimeout(retryTimer);
      ws?.close();
      wsRef.current = null;
    };
  }, [cle]);

  function send(data: unknown): boolean {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return false;
    wsRef.current.send(JSON.stringify(data));
    return true;
  }

  return { status, send };
}
