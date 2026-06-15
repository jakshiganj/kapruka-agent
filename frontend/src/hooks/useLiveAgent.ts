import { useCallback, useEffect, useRef, useState } from "react";
import { enrichCategories, getCategoryLabel } from "../data/categoryCatalog";
import type {
  ChatMessage,
  ChatRole,
  CheckoutPayload,
  ConnectionState,
  ControlAction,
  DeliveryInfo,
  KaprukaCategory,
  Product,
  SessionSnapshot,
  ServerEnvelope,
  ShowProductsPayload,
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
  const isShowCategories = action === "show_categories";
  const isUpdateCart = action === "update_cart";

  return {
    cart: isUpdateCart && Array.isArray(payload.cart)
      ? payload.cart
      : payload.cart?.length
        ? payload.cart
        : prev.cart,
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
    categories:
      isShowCategories && payload.categories?.length
        ? payload.categories
        : payload.categories?.length
          ? payload.categories
          : prev.categories,
    search_query:
      isShowProducts && payload.search_query != null
        ? payload.search_query
        : payload.search_query ?? prev.search_query,
    selected_product: isShowProducts
      ? payload.selected_product
      : searchChanged
        ? payload.selected_product
        : payload.selected_product ?? prev.selected_product,
    order_phase: payload.order_phase ?? prev.order_phase,
    checkout_stale:
      action === "show_checkout"
        ? false
        : payload.checkout_stale === true
          ? true
          : payload.checkout_stale === false
            ? false
            : prev.checkout_stale,
    checkout_cart_snapshot: payload.checkout_cart_snapshot ?? prev.checkout_cart_snapshot,
    checkout_url: (payload as CheckoutPayload).checkout_url ?? prev.checkout_url,
  };
}

const EMPTY_SESSION: SessionSnapshot = {
  cart: [],
  delivery_info: {},
  checkout_info: {},
  products: [],
  categories: [],
};

async function fetchCategories(): Promise<KaprukaCategory[]> {
  const response = await fetch("/api/categories?depth=2&featured=true");
  if (!response.ok) {
    throw new Error(`Categories request failed (${response.status})`);
  }
  const data = (await response.json()) as { categories?: KaprukaCategory[] };
  const raw = data.categories ?? [];
  return enrichCategories(raw);
}

function createMessageId(): string {
  return crypto.randomUUID();
}

function extractCheckoutPayload(payload: UiPayload | null): CheckoutPayload | null {
  const record = payload as CheckoutPayload | null;
  if (!record?.checkout_url) {
    return null;
  }
  return record;
}

function mergeStreamingChunk(prev: string, chunk: string): string {
  if (!prev) {
    return chunk;
  }
  if (chunk.startsWith(prev)) {
    return chunk;
  }
  if (prev.startsWith(chunk)) {
    return prev;
  }
  const needsSpace = !prev.endsWith(" ") && !chunk.startsWith(" ");
  return needsSpace ? `${prev} ${chunk}` : `${prev}${chunk}`;
}

function finalizeStreamingMessages(
  messages: ChatMessage[],
  role?: ChatRole,
): ChatMessage[] {
  return messages.map((message) => {
    if (message.kind !== "text" || message.status !== "streaming") {
      return message;
    }
    if (role && message.role !== role) {
      return message;
    }
    return { ...message, status: "final" };
  });
}

function findLastTextIndex(messages: ChatMessage[], role: ChatRole): number {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i];
    if (msg?.kind === "text" && msg.role === role) {
      return i;
    }
  }
  return -1;
}

function shouldStartNewTranscriptBubble(
  messages: ChatMessage[],
  role: ChatRole,
): boolean {
  if (messages.length === 0) {
    return true;
  }
  const last = messages[messages.length - 1];
  if (!last || last.kind !== "text") {
    return true;
  }
  return last.role !== role;
}

function updateTextMessage(
  messages: ChatMessage[],
  index: number,
  content: string,
  status: ChatMessage["status"],
): ChatMessage[] {
  const existing = messages[index];
  if (!existing) {
    return messages;
  }
  const updated: ChatMessage = {
    ...existing,
    content,
    status,
  };
  return [...messages.slice(0, index), updated, ...messages.slice(index + 1)];
}

function findLastStreamingTextIndex(messages: ChatMessage[], role: ChatRole): number {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i];
    if (msg?.kind === "text" && msg.role === role && msg.status === "streaming") {
      return i;
    }
  }
  return -1;
}

function normalizeSearchQuery(query: string | undefined): string {
  return (query ?? "").trim().toLowerCase().replace(/\s+/g, " ");
}

function findLastProductsMessage(messages: ChatMessage[]): ChatMessage | undefined {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i]?.kind === "products") {
      return messages[i];
    }
  }
  return undefined;
}

function deliveryFingerprint(delivery: DeliveryInfo | undefined): string {
  if (!delivery) {
    return "";
  }
  return [
    delivery.city ?? "",
    delivery.date ?? "",
    delivery.validated ?? "",
    delivery.delivery_rate ?? "",
  ].join("|");
}

function findLastDeliveryMessage(messages: ChatMessage[]): ChatMessage | undefined {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i]?.kind === "delivery") {
      return messages[i];
    }
  }
  return undefined;
}

function checkoutFingerprint(payload: CheckoutPayload | undefined): string {
  if (!payload?.checkout_url) {
    return "";
  }
  return [payload.checkout_url, payload.order_ref ?? ""].join("|");
}

function findLastCheckoutMessage(messages: ChatMessage[]): ChatMessage | undefined {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i]?.kind === "checkout") {
      return messages[i];
    }
  }
  return undefined;
}

function buildRichMessages(
  action: string,
  payload: UiPayload,
  prevCartLength: number,
  prevMessages: ChatMessage[],
  sessionProducts: Product[] = [],
  sessionSearchQuery?: string,
  sessionCategories: KaprukaCategory[] = [],
): ChatMessage[] {
  const messages: ChatMessage[] = [];
  const payloadProducts = payload.products ?? [];
  const searchQuery = payload.search_query ?? sessionSearchQuery;
  const products =
    payloadProducts.length > 0
      ? payloadProducts
      : action === "show_products"
        ? sessionProducts
        : payloadProducts;
  const lastProducts = findLastProductsMessage(prevMessages);
  const searchChanged =
    !!searchQuery &&
    normalizeSearchQuery(searchQuery) !== normalizeSearchQuery(lastProducts?.searchQuery);

  const shouldShowProducts =
    action === "show_products" || (products.length > 0 && searchChanged);

  if (shouldShowProducts) {
    const showPayload = payload as ShowProductsPayload;
    messages.push({
      id: createMessageId(),
      role: "assistant",
      kind: "products",
      products: [...products],
      searchQuery,
      searchError: showPayload.error,
    });
  }

  if (action === "show_order_tracking") {
    const trackingPayload = payload as unknown as {
      order_number?: string;
      tracking?: Record<string, unknown>;
    };
    if (trackingPayload.order_number) {
      messages.push({
        id: createMessageId(),
        role: "assistant",
        kind: "order_tracking",
        orderTracking: {
          order_number: trackingPayload.order_number,
          tracking: trackingPayload.tracking ?? {},
        },
      });
    }
  }

  if (action === "show_categories") {
    const categories = payload.categories?.length
      ? payload.categories
      : sessionCategories;
    if (categories.length > 0) {
      messages.push({
        id: createMessageId(),
        role: "assistant",
        kind: "categories",
        categories: [...categories],
      });
    }
  }

  if (action === "show_checkout") {
    const checkout = payload as CheckoutPayload;
    const lastCheckout = findLastCheckoutMessage(prevMessages);
    const checkoutChanged =
      checkoutFingerprint(checkout) !== checkoutFingerprint(lastCheckout?.checkoutPayload);
    if (checkout.checkout_url && checkoutChanged) {
      messages.push({
        id: createMessageId(),
        role: "assistant",
        kind: "checkout",
        checkoutPayload: checkout,
      });
    }
  }

  if (action === "update_cart") {
    const cart = payload.cart ?? [];
    if (payload.order_phase === "branch_pending") {
      const hasBranchPrompt = prevMessages.some((msg) => msg.kind === "branch_prompt");
      if (!hasBranchPrompt) {
        messages.push({
          id: createMessageId(),
          role: "assistant",
          kind: "branch_prompt",
        });
      }
    } else if (cart.length > prevCartLength && cart.length > 0) {
      messages.push({
        id: createMessageId(),
        role: "assistant",
        kind: "cart_notice",
        cartItemName: cart[cart.length - 1]?.name,
      });
    }
  }

  const delivery = payload.delivery_info;
  const lastDelivery = findLastDeliveryMessage(prevMessages);
  const deliveryChanged =
    deliveryFingerprint(delivery) !== deliveryFingerprint(lastDelivery?.delivery);

  if ((delivery?.city || delivery?.date) && deliveryChanged) {
    messages.push({
      id: createMessageId(),
      role: "assistant",
      kind: "delivery",
      delivery,
    });
  }

  return messages;
}

export interface UseLiveAgentOptions {
  sessionId: string;
  onInboundAudio?: (base64: string) => void;
  onConnected?: () => void;
  onControl?: (action: ControlAction) => void;
}

export interface UseLiveAgentResult {
  connectionState: ConnectionState;
  uiState: UiState;
  session: SessionSnapshot;
  checkoutPayload: CheckoutPayload | null;
  messages: ChatMessage[];
  processing: boolean;
  liveReady: boolean;
  categoriesLoading: boolean;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
  sendBinary: (data: ArrayBuffer) => void;
  sendControl: (payload: Record<string, unknown>) => void;
  sendTextMessage: (text: string) => void;
  sendSelectCategory: (category: string, subcategory?: string) => void;
  sendVoiceControl: (action: "voice_start" | "voice_stop") => void;
}

export function useLiveAgent(options: UseLiveAgentOptions): UseLiveAgentResult {
  const { sessionId, onInboundAudio, onConnected, onControl } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const onInboundAudioRef = useRef(onInboundAudio);
  const onConnectedRef = useRef(onConnected);
  const onControlRef = useRef(onControl);
  const sessionRef = useRef<SessionSnapshot>(EMPTY_SESSION);

  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [uiState, setUiState] = useState<UiState>({ action: null, payload: null });
  const [session, setSession] = useState<SessionSnapshot>(EMPTY_SESSION);
  const [checkoutPayload, setCheckoutPayload] = useState<CheckoutPayload | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [processing, setProcessing] = useState(false);
  const [liveReady, setLiveReady] = useState(false);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  const upsertTranscript = useCallback((role: ChatRole, content: string, final: boolean) => {
    setMessages((prev) => {
      const streamingIdx = findLastStreamingTextIndex(prev, role);

      if (streamingIdx >= 0) {
        const existing = prev[streamingIdx];
        const merged = mergeStreamingChunk(existing.content ?? "", content);
        return updateTextMessage(prev, streamingIdx, merged, final ? "final" : "streaming");
      }

      if (!shouldStartNewTranscriptBubble(prev, role)) {
        const lastIdx = findLastTextIndex(prev, role);
        if (lastIdx >= 0) {
          const existing = prev[lastIdx];
          const merged = mergeStreamingChunk(existing?.content ?? "", content);
          return updateTextMessage(prev, lastIdx, merged, final ? "final" : "streaming");
        }
      }

      return [
        ...prev,
        {
          id: createMessageId(),
          role,
          kind: "text",
          content,
          status: final ? "final" : "streaming",
        },
      ];
    });
  }, []);

  const finalizeOrAppendText = useCallback((role: ChatRole, content: string) => {
    setMessages((prev) => {
      const finalized = finalizeStreamingMessages(prev, role);

      // Only suppress a TRULY consecutive duplicate (e.g. voice transcript echo
      // immediately followed by the same text). If the user has spoken since,
      // always show the reply even when its text repeats — otherwise the agent
      // looks unresponsive when it gives the same guidance twice.
      const last = finalized[finalized.length - 1];
      if (
        last &&
        last.kind === "text" &&
        last.role === role &&
        last.status === "final" &&
        last.content === content
      ) {
        return finalized;
      }

      return [
        ...finalized,
        {
          id: createMessageId(),
          role,
          kind: "text",
          content,
          status: "final",
        },
      ];
    });
  }, []);

  const appendUserText = useCallback((content: string) => {
    setMessages((prev) => [
      ...finalizeStreamingMessages(prev, "user"),
      {
        id: createMessageId(),
        role: "user",
        kind: "text",
        content,
        status: "final",
      },
    ]);
  }, []);

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

  const sendTextMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || wsRef.current?.readyState !== WebSocket.OPEN) {
        return;
      }
      appendUserText(trimmed);
      sendControl({ type: "text_message", text: trimmed });
    },
    [appendUserText, sendControl],
  );

  const sendVoiceControl = useCallback(
    (action: "voice_start" | "voice_stop") => {
      sendControl({ type: action });
      if (action === "voice_stop") {
        setLiveReady(false);
      }
    },
    [sendControl],
  );

  const sendSelectCategory = useCallback(
    (category: string, subcategory?: string) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        return;
      }
      const label = subcategory
        ? getCategoryLabel(subcategory)
        : getCategoryLabel(category);
      appendUserText(`Browsing ${label}`);
      sendControl({
        type: "select_category",
        category,
        ...(subcategory ? { subcategory } : {}),
      });
    },
    [appendUserText, sendControl],
  );

  const loadCategories = useCallback(async () => {
    setCategoriesLoading(true);
    try {
      const categories = await fetchCategories();
      sessionRef.current = { ...sessionRef.current, categories };
      setSession((prev) => ({ ...prev, categories }));
    } catch {
      // Categories API may be unavailable before backend ships; picker stays empty.
    } finally {
      setCategoriesLoading(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnectionState("disconnected");
    setProcessing(false);
    setLiveReady(false);
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
          onInboundAudioRef.current?.(envelope.data);
        } else if (envelope.type === "transcript") {
          upsertTranscript(envelope.role, envelope.content, envelope.final ?? false);
        } else if (envelope.type === "text") {
          finalizeOrAppendText(envelope.role, envelope.content);
        } else if (envelope.type === "ui") {
          void (async () => {
            let payload = envelope.payload as UiPayload;
            if (envelope.action === "show_categories" && !payload.categories?.length) {
              await loadCategories();
              payload = { ...payload, categories: sessionRef.current.categories };
            }
            const prevCartLength = sessionRef.current.cart.length;
            const merged = mergeSession(sessionRef.current, payload, envelope.action);
            sessionRef.current = merged;
            setUiState({ action: envelope.action, payload });
            setSession(merged);
            setMessages((msgPrev) => {
            if (envelope.action === "show_checkout_form") {
                const fp = payload as unknown as {
                  checkout_info?: import("../types").CheckoutInfo;
                  delivery_info?: DeliveryInfo;
                  cart?: import("../types").CartItem[];
                  ready?: boolean;
                };
                const formData = {
                  checkout_info: fp.checkout_info,
                  delivery_info: fp.delivery_info,
                  cart: fp.cart,
                  ready: fp.ready,
                };
                const delivery = fp.delivery_info;
                const lastDelivery = findLastDeliveryMessage(msgPrev);
                const deliveryChanged =
                  deliveryFingerprint(delivery) !== deliveryFingerprint(lastDelivery?.delivery);
                const withDelivery =
                  delivery &&
                  deliveryChanged &&
                  (delivery.city || delivery.date)
                    ? [
                        ...msgPrev,
                        {
                          id: createMessageId(),
                          role: "assistant" as const,
                          kind: "delivery" as const,
                          delivery,
                        },
                      ]
                    : msgPrev;
                // Refresh the existing form in place (voice hydration) or add one.
                if (withDelivery.some((m) => m.kind === "checkout_form")) {
                  return withDelivery.map((m) =>
                    m.kind === "checkout_form" ? { ...m, checkoutForm: formData } : m,
                  );
                }
                return [
                  ...withDelivery,
                  {
                    id: createMessageId(),
                    role: "assistant",
                    kind: "checkout_form",
                    checkoutForm: formData,
                  },
                ];
              }
              const richMessages = buildRichMessages(
                envelope.action,
                payload,
                prevCartLength,
                msgPrev,
                merged.products,
                merged.search_query,
                merged.categories,
              );
              return richMessages.length > 0 ? [...msgPrev, ...richMessages] : msgPrev;
            });
            const checkout = extractCheckoutPayload(payload);
            if (checkout) {
              setCheckoutPayload((prev) => ({
                ...prev,
                ...checkout,
                cart: checkout.cart?.length ? checkout.cart : prev?.cart,
                delivery_info: checkout.delivery_info ?? prev?.delivery_info,
                checkout_info: checkout.checkout_info ?? prev?.checkout_info,
              }));
            }
          })();
        } else if (envelope.type === "control") {
          if (envelope.action === "processing") {
            setProcessing(true);
            setMessages((prev) => finalizeStreamingMessages(prev));
          } else if (envelope.action === "mic_resume") {
            setProcessing(false);
            setMessages((prev) => finalizeStreamingMessages(prev));
          } else if (envelope.action === "session_ready") {
            setProcessing(false);
          } else if (envelope.action === "live_ready") {
            setLiveReady(true);
            setError(null);
          } else if (envelope.action === "live_error") {
            setLiveReady(false);
            if (envelope.message) {
              setError(envelope.message);
            }
          } else if (envelope.action === "error" && envelope.message) {
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
      setProcessing(false);
      setLiveReady(false);
    };
  }, [finalizeOrAppendText, loadCategories, sessionId, upsertTranscript]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connectionState,
    uiState,
    session,
    checkoutPayload,
    messages,
    processing,
    liveReady,
    categoriesLoading,
    error,
    connect,
    disconnect,
    sendBinary,
    sendControl,
    sendTextMessage,
    sendSelectCategory,
    sendVoiceControl,
  };
}
