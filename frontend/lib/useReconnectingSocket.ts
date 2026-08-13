"use client";

import { useEffect, useRef, useState } from "react";

export type SocketStatus = "connecting" | "connected" | "disconnected" | "unauthorized";

// Code applicatif renvoyé par le backend quand le canal refuse le jeton (voir
// notifications/dependencies.py). Distinct d'une coupure réseau : réessayer
// n'y changera jamais rien.
const WS_UNAUTHORIZED = 4401;

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
 */
export function useReconnectingSocket(url: string | null, onMessage: (data: any) => void): SocketStatus {
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!url) return;

    let attempt = 0;
    let closedByUs = false;
    let ws: WebSocket;
    let retryTimer: ReturnType<typeof setTimeout>;

    function connect() {
      setStatus("connecting");
      ws = new WebSocket(url as string);

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
        const delay = Math.min(1000 * 2 ** attempt, 15000);
        attempt += 1;
        retryTimer = setTimeout(connect, delay);
      };
      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      closedByUs = true;
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, [url]);

  return status;
}
