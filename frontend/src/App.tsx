import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CartDrawer } from "./components/CartDrawer";
import { ChatPanel } from "./components/ChatPanel";
import { LanguageToggle } from "./components/LanguageToggle";
import { OrderProgress } from "./components/OrderProgress";
import { ProductDetailSheet } from "./components/ProductDetailSheet";
import { useAudioSession } from "./hooks/useAudioSession";
import { useLiveAgent } from "./hooks/useLiveAgent";
import { getTranslator, type Language } from "./i18n";
import type { CheckoutFormData, Product } from "./types";

const SESSION_STORAGE_KEY = "kapruka_session_id";
const SESSION_ID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function getOrCreateSessionId(): string {
  try {
    const stored = localStorage.getItem(SESSION_STORAGE_KEY);
    if (stored && SESSION_ID_RE.test(stored)) {
      return stored;
    }
  } catch {
    // localStorage blocked (private mode, etc.)
  }
  const id = crypto.randomUUID();
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, id);
  } catch {
    // persist best-effort only
  }
  return id;
}

export default function App() {
  const sessionId = useMemo(() => getOrCreateSessionId(), []);
  const [cartOpen, setCartOpen] = useState(false);
  const [micActive, setMicActive] = useState(false);
  const [language, setLanguage] = useState<Language>("en");
  const [detailProduct, setDetailProduct] = useState<Product | undefined>();
  const [intentionalDisconnect, setIntentionalDisconnect] = useState(false);
  const t = useMemo(() => getTranslator(language), [language]);
  const [selectedProductId, setSelectedProductId] = useState<string | undefined>();
  const sendBinaryRef = useRef<(data: ArrayBuffer) => void>(() => {});
  const sendControlRef = useRef<(payload: Record<string, unknown>) => void>(() => {});
  const pendingMicRef = useRef(false);
  const micActiveRef = useRef(false);

  const audio = useAudioSession({
    onPcmChunk: (chunk) => sendBinaryRef.current(chunk),
  });

  const live = useLiveAgent({
    sessionId,
    onInboundAudio: (base64) => {
      void audio.playPcmBase64(base64);
    },
    onControl: (action) => {
      if (action === "processing") {
        audio.setVoicePhase("processing");
      } else if (action === "mic_pause") {
        audio.pauseMicUpload();
      } else if (action === "mic_resume") {
        audio.resumeMicUpload();
      } else if (action === "live_ready" && pendingMicRef.current) {
        pendingMicRef.current = false;
        setMicActive(true);
        micActiveRef.current = true;
      } else if (action === "live_error") {
        pendingMicRef.current = false;
        setMicActive(false);
        micActiveRef.current = false;
        void audio.stopCapture();
      }
    },
  });

  useEffect(() => {
    sendBinaryRef.current = live.sendBinary;
    sendControlRef.current = live.sendControl;
  }, [live.sendBinary, live.sendControl]);

  const handleConnect = useCallback(() => {
    setIntentionalDisconnect(false);
    live.connect();
  }, [live]);

  const handleDisconnect = useCallback(() => {
    if (micActiveRef.current) {
      live.sendVoiceControl("voice_stop");
    }
    void audio.stopCapture();
    setMicActive(false);
    micActiveRef.current = false;
    pendingMicRef.current = false;
    setIntentionalDisconnect(true);
    live.disconnect();
  }, [audio, live]);

  const handleToggleMic = useCallback(async () => {
    if (live.connectionState !== "connected") {
      return;
    }

    if (!micActiveRef.current && !pendingMicRef.current) {
      try {
        await audio.startCapture();
        if (live.liveReady) {
          setMicActive(true);
          micActiveRef.current = true;
        } else {
          pendingMicRef.current = true;
        }
        live.sendVoiceControl("voice_start");
      } catch {
        pendingMicRef.current = false;
        live.sendVoiceControl("voice_stop");
        setMicActive(false);
        micActiveRef.current = false;
      }
      return;
    }

    pendingMicRef.current = false;
    live.sendVoiceControl("voice_stop");
    await audio.stopCapture();
    setMicActive(false);
    micActiveRef.current = false;
  }, [audio, live]);

  const { session } = live;
  const cart = session.cart;
  const selectedId = selectedProductId ?? session.selected_product?.id;

  const handleSelectProduct = useCallback((product: Product) => {
    setSelectedProductId(product.id);
    sendControlRef.current({
      type: "select_product",
      product_id: product.id,
      product,
    });
  }, []);

  const handleViewProduct = useCallback((product: Product) => {
    setDetailProduct(product);
  }, []);

  const handleSelectCategory = useCallback(
    (category: string, subcategory?: string) => {
      live.sendSelectCategory(category, subcategory);
    },
    [live],
  );

  useEffect(() => {
    if (live.uiState.action === "update_cart" && cart.length > 0) {
      setCartOpen(true);
    }
  }, [live.uiState.action, cart.length]);

  useEffect(() => {
    if (live.uiState.action === "show_products") {
      setSelectedProductId(undefined);
    }
  }, [live.uiState.action, live.uiState.payload]);

  const connected = live.connectionState === "connected";
  const itemCount = cart.reduce((n, i) => n + i.quantity, 0);
  const shoppingStarted =
    connected && (session.products.length > 0 || cart.length > 0);
  const showReconnect =
    !connected &&
    live.connectionState !== "connecting" &&
    !intentionalDisconnect &&
    live.messages.length > 0;

  const handleRequestNewLink = useCallback(() => {
    live.sendTextMessage("Please checkout");
  }, [live]);

  const handleUpdateCartItem = useCallback(
    (productId: string, op: "increment" | "decrement" | "remove") => {
      sendControlRef.current({ type: "update_cart_item", product_id: productId, op });
    },
    [],
  );

  const handleLanguageChange = useCallback((next: Language) => {
    setLanguage(next);
    sendControlRef.current({ type: "set_language", language: next });
  }, []);

  const handleSubmitCheckout = useCallback((data: CheckoutFormData) => {
    sendControlRef.current({ type: "submit_checkout", ...data });
  }, []);

  const handleProceedToCheckout = useCallback(() => {
    setCartOpen(false);
    live.sendTextMessage("checkout");
  }, [live]);

  return (
    <div className="flex h-full flex-col bg-[#fcf9f8]">
      <header
        className="sticky top-0 z-30 border-b border-[#402970]/8 bg-white/90 px-4 py-3 backdrop-blur-md md:px-6"
        style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}
      >
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#402970] text-lg font-bold text-white shadow-[0_2px_8px_rgba(64,41,112,0.2)]">
              K
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#402970]/70">
                {t("header.tagline")}
              </p>
              <h1 className="text-base font-semibold text-[#222222] md:text-lg">
                {t("header.title")}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <LanguageToggle language={language} onChange={handleLanguageChange} />
            {connected ? (
              <button
                type="button"
                onClick={() => setCartOpen(true)}
                className="relative rounded-full border border-[#402970]/12 bg-[#F0EEFA] px-4 py-2 text-sm font-medium text-[#402970] transition-colors hover:bg-[#402970]/8"
              >
                🛒 {t("header.cart")}{itemCount > 0 ? ` · ${itemCount}` : ""}
              </button>
            ) : null}
            {connected ? (
              <button
                type="button"
                onClick={handleDisconnect}
                className="rounded-full border border-[#ba1a1a]/20 bg-[#ffdad6]/50 px-4 py-2 text-sm font-medium text-[#ba1a1a] hover:bg-[#ffdad6]"
              >
                {t("header.end")}
              </button>
            ) : null}
          </div>
        </div>
      </header>

      {shoppingStarted ? (
        <div className="sticky top-[57px] z-20 border-b border-[#402970]/8 bg-[#fcf9f8]/90 px-4 py-2 backdrop-blur-md md:top-[65px] md:px-6">
          <div className="mx-auto flex max-w-5xl justify-center">
            <OrderProgress session={session} action={live.uiState.action} />
          </div>
        </div>
      ) : null}

      {showReconnect ? (
        <div className="border-b border-[#6f5d00]/20 bg-[#fff8e0] px-4 py-2 md:px-6">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
            <p className="text-sm text-[#6f5d00]">Connection lost. Your cart is safe.</p>
            <button
              type="button"
              onClick={handleConnect}
              className="shrink-0 rounded-full bg-[#402970] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#2a1059]"
            >
              Reconnect
            </button>
          </div>
        </div>
      ) : null}

      <ChatPanel
        t={t}
        messages={live.messages}
        connected={connected}
        processing={live.processing}
        error={live.error}
        voicePhase={audio.voicePhase}
        voiceLevel={audio.level}
        micActive={micActive}
        onSend={live.sendTextMessage}
        onMicToggle={() => void handleToggleMic()}
        onConnect={handleConnect}
        connecting={live.connectionState === "connecting"}
        selectedProductId={selectedId}
        onSelectProduct={connected ? handleSelectProduct : undefined}
        onViewProduct={connected ? handleViewProduct : undefined}
        onOpenCart={() => setCartOpen(true)}
        checkoutStale={session.checkout_stale}
        onRequestNewLink={handleRequestNewLink}
        onSelectCategory={handleSelectCategory}
        onSubmitCheckout={connected ? handleSubmitCheckout : undefined}
      />

      <CartDrawer
        t={t}
        open={cartOpen}
        cart={cart}
        delivery={session.delivery_info}
        checkoutStale={session.checkout_stale}
        checkoutSnapshot={session.checkout_cart_snapshot}
        onClose={() => setCartOpen(false)}
        onRequestNewLink={handleRequestNewLink}
        onUpdateItem={connected ? handleUpdateCartItem : undefined}
        onProceedCheckout={connected ? handleProceedToCheckout : undefined}
      />

      {detailProduct ? (
        <ProductDetailSheet
          product={detailProduct}
          onClose={() => setDetailProduct(undefined)}
          onAddToCart={handleSelectProduct}
        />
      ) : null}
    </div>
  );
}
