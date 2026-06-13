import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CartDrawer } from "./components/CartDrawer";
import { CheckoutCard } from "./components/CheckoutCard";
import { DeliveryBanner } from "./components/DeliveryBanner";
import { OrderProgress } from "./components/OrderProgress";
import { ProductCarousel } from "./components/ProductCarousel";
import { VoiceIndicator } from "./components/VoiceIndicator";
import { useAudioSession } from "./hooks/useAudioSession";
import { useLiveAgent } from "./hooks/useLiveAgent";
import type { CheckoutPayload, Product, ShowProductsPayload } from "./types";

function createSessionId(): string {
  return crypto.randomUUID();
}

export default function App() {
  const sessionId = useMemo(() => createSessionId(), []);
  const [cartOpen, setCartOpen] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState<string | undefined>();
  const sendBinaryRef = useRef<(data: ArrayBuffer) => void>(() => {});
  const sendControlRef = useRef<(payload: Record<string, unknown>) => void>(() => {});

  const audio = useAudioSession({
    onPcmChunk: (chunk) => sendBinaryRef.current(chunk),
  });

  const live = useLiveAgent({
    sessionId,
    onInboundAudio: (base64) => {
      void audio.playPcmBase64(base64);
    },
    onConnected: () => {
      void audio.startCapture();
    },
    onControl: (action) => {
      if (action === "processing") {
        audio.setVoicePhase("processing");
      } else if (action === "mic_pause") {
        audio.pauseMicUpload();
      } else {
        audio.resumeMicUpload();
      }
    },
  });

  useEffect(() => {
    sendBinaryRef.current = live.sendBinary;
    sendControlRef.current = live.sendControl;
  }, [live.sendBinary, live.sendControl]);

  const handleConnect = useCallback(() => {
    live.connect();
  }, [live]);

  const handleDisconnect = useCallback(() => {
    audio.stopCapture();
    live.disconnect();
  }, [audio, live]);

  const { session } = live;
  const products = session.products;
  const cart = session.cart;
  const searchQuery = session.search_query;
  const selectedId = selectedProductId ?? session.selected_product?.id;
  const payload = live.uiState.payload as ShowProductsPayload | null;
  const searchError = payload?.error;

  const handleSelectProduct = useCallback((product: Product) => {
    setSelectedProductId(product.id);
    sendControlRef.current({ type: "select_product", product_id: product.id });
  }, []);

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

  return (
    <div className="flex min-h-full flex-col bg-[radial-gradient(ellipse_at_top,_#0f172a_0%,_#070b14_50%,_#050810_100%)]">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/80 px-4 py-3 backdrop-blur md:px-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500 text-lg font-bold text-slate-950">
              K
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.25em] text-emerald-400">Kapruka Agent</p>
              <h1 className="text-base font-semibold text-white md:text-lg">Kapru · Gift Assistant</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {connected ? (
              <button
                type="button"
                onClick={() => setCartOpen(true)}
                className="relative rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white hover:bg-white/10"
              >
                🛒 Cart{itemCount > 0 ? ` · ${itemCount}` : ""}
              </button>
            ) : null}
            {connected ? (
              <button
                type="button"
                onClick={handleDisconnect}
                className="rounded-xl bg-red-500/20 px-4 py-2 text-sm font-medium text-red-200 hover:bg-red-500/30"
              >
                End
              </button>
            ) : (
              <button
                type="button"
                onClick={handleConnect}
                disabled={live.connectionState === "connecting"}
                className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-60"
              >
                {live.connectionState === "connecting" ? "Connecting…" : "Start voice"}
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 md:gap-8 md:px-8 md:py-8">
        <OrderProgress session={session} action={live.uiState.action} />

        <div className="flex flex-col items-center gap-6 rounded-3xl border border-white/10 bg-white/[0.03] px-6 py-8 shadow-inner">
          <VoiceIndicator phase={audio.voicePhase} level={audio.level} connected={connected} />
          {live.error ? <p className="text-sm text-red-300">{live.error}</p> : null}
        </div>

        {(session.delivery_info?.city || session.delivery_info?.date) ? (
          <DeliveryBanner delivery={session.delivery_info} />
        ) : null}

        {products.length > 0 || live.uiState.action === "show_products" ? (
          <ProductCarousel
            products={products}
            searchQuery={searchQuery}
            selectedId={selectedId}
            error={searchError}
            onSelect={connected ? handleSelectProduct : undefined}
          />
        ) : null}

        {live.uiState.action === "update_cart" && cart.length > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-sky-500/20 bg-sky-950/30 px-4 py-3 text-sm text-sky-100">
            <span>
              Added {cart[cart.length - 1]?.name} — browse more gifts or tell Kapru your delivery city and date to
              checkout.
            </span>
            <button type="button" className="font-medium underline" onClick={() => setCartOpen(true)}>
              View cart
            </button>
          </div>
        ) : null}

        {live.uiState.action === "show_checkout" && live.uiState.payload ? (
          <CheckoutCard payload={live.uiState.payload as CheckoutPayload} />
        ) : null}

        {!connected && products.length === 0 ? (
          <section className="grid gap-4 md:grid-cols-3">
            {[
              { emoji: "🎂", title: "Cakes & treats", hint: "Chocolate cake to Kadawatha" },
              { emoji: "💐", title: "Flowers & hampers", hint: "Also add flowers to cart" },
              { emoji: "🎁", title: "Gift messages", hint: "Wish amma a happy birthday" },
            ].map((tip) => (
              <div
                key={tip.title}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-center"
              >
                <p className="text-3xl">{tip.emoji}</p>
                <p className="mt-2 font-medium text-white">{tip.title}</p>
                <p className="mt-1 text-xs text-slate-500">&ldquo;{tip.hint}&rdquo;</p>
              </div>
            ))}
          </section>
        ) : null}
      </main>

      <CartDrawer
        open={cartOpen}
        cart={cart}
        delivery={session.delivery_info}
        onClose={() => setCartOpen(false)}
      />
    </div>
  );
}
