import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ConnectionState,
  ControlAction,
  SessionSnapshot,
  ServerEnvelope,
  UiPayload,
  UiState,
} from "../types";

function wsBaseUrl(): string {
  const envUrl = import.meta.env.VITE_WS_URL as string | undefined;
  if (envUrl) {
    return envUrl.replace(/\/$/, "");
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

function mergeSession(
  prev: SessionSnapshot,
  payload: UiPayload | null,
  action: string | null,
): SessionSnapshot {
  if (!payload) {
    return prev;
  }
  const searchChanged =
    payload.search_query != null && payload.search_query !== prev.search_query;
  const isShowProducts = action === "show_products";

  return {
    cart: payload.cart?.length ? payload.cart : prev.cart,
    delivery_info: payload.delivery_info && (
      payload.delivery_info.city ||
      payload.delivery_info.date ||
      payload.delivery_info.validated
    )
      ? { ...prev.delivery_info, ...payload.delivery_info }
      : prev.delivery_info,
    checkout_info: payload.checkout_info?.recipient || payload.checkout_info?.gift_message
      ? { ...prev.checkout_info, ...payload.checkout_info }
      : prev.checkout_info,
    products: isShowProducts
      ? (payload.products ?? [])
      : searchChanged
        ? (payload.products ?? [])
        : payload.products?.length
          ? payload.products
          : prev.products,
    search_query:
      isShowProducts && payload.search_query != null
        ? payload.search_query
        : payload.search_query ?? prev.search_query,
    selected_product: isShowProducts
      ? payload.selected_product
      : searchChanged
        ? payload.selected_product
        : payload.selected_product ?? prev.selected_product,
  };
}

const EMPTY_SESSION: SessionSnapshot = {
  cart: [],
  delivery_info: {},
  checkout_info: {},
  products: [],
};

export interface UseLiveAgentOptions {
  sessionId: string;
  onInboundAudio: (base64: string) => void;
  onConnected?: () => void;
  onControl?: (action: ControlAction) => void;
}

export interface UseLiveAgentResult {
  connectionState: ConnectionState;
  uiState: UiState;
  session: SessionSnapshot;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
  sendBinary: (data: ArrayBuffer) => void;
  sendControl: (payload: Record<string, unknown>) => void;
}

export function useLiveAgent(options: UseLiveAgentOptions): UseLiveAgentResult {
  const { sessionId, onInboundAudio, onConnected, onControl } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const onInboundAudioRef = useRef(onInboundAudio);
  const onConnectedRef = useRef(onConnected);
  const onControlRef = useRef(onControl);

  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [uiState, setUiState] = useState<UiState>({ action: null, payload: null });
  const [session, setSession] = useState<SessionSnapshot>(EMPTY_SESSION);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    onInboundAudioRef.current = onInboundAudio;
    onConnectedRef.current = onConnected;
    onControlRef.current = onControl;
  }, [onInboundAudio, onConnected, onControl]);

  const sendBinary = useCallback((data: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  const sendControl = useCallback((payload: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnectionState("disconnected");
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setError(null);
    setConnectionState("connecting");

    const url = `${wsBaseUrl()}/ws/stream/${sessionId}`;
    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState("connected");
      onConnectedRef.current?.();
    };

    ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data !== "string") {
        return;
      }

      try {
        const envelope = JSON.parse(event.data) as ServerEnvelope;
        if (envelope.type === "audio") {
          onInboundAudioRef.current(envelope.data);
        } else if (envelope.type === "ui") {
          const payload = envelope.payload as UiPayload;
          setUiState({ action: envelope.action, payload });
          setSession((prev) => mergeSession(prev, payload, envelope.action));
        } else if (envelope.type === "control") {
          if (envelope.action === "error" && envelope.message) {
            setError(envelope.message);
            setConnectionState("error");
          }
          onControlRef.current?.(envelope.action);
        }
      } catch {
        // ignore malformed frames
      }
    };

    ws.onerror = () => {
      setConnectionState("error");
      setError("WebSocket connection failed");
    };

    ws.onclose = () => {
      wsRef.current = null;
      setConnectionState("disconnected");
    };
  }, [sessionId]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connectionState,
    uiState,
    session,
    error,
    connect,
    disconnect,
    sendBinary,
    sendControl,
  };
}
