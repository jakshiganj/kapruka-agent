import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CartDrawer } from "./components/CartDrawer";
import { ChatPanel } from "./components/ChatPanel";
import { useAudioSession } from "./hooks/useAudioSession";
import { useLiveAgent } from "./hooks/useLiveAgent";
import type { Product } from "./types";

function createSessionId(): string {
  return crypto.randomUUID();
}

export default function App() {
  const sessionId = useMemo(() => createSessionId(), []);
  const [cartOpen, setCartOpen] = useState(false);
  const [micActive, setMicActive] = useState(false);
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
    <div className="flex h-full flex-col bg-[#fcf9f8]">
      <header className="sticky top-0 z-30 border-b border-[#402970]/8 bg-white/90 px-4 py-3 backdrop-blur-md md:px-6">
        <div className="mx-auto flex max-w-[800px] items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#402970] text-lg font-bold text-white shadow-[0_2px_8px_rgba(64,41,112,0.2)]">
              K
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#402970]/70">
                Kapruka
              </p>
              <h1 className="text-base font-semibold text-[#222222] md:text-lg">Kapru · Gift Assistant</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {connected ? (
              <button
                type="button"
                onClick={() => setCartOpen(true)}
                className="relative rounded-full border border-[#402970]/12 bg-[#F0EEFA] px-4 py-2 text-sm font-medium text-[#402970] transition-colors hover:bg-[#402970]/8"
              >
                🛒 Cart{itemCount > 0 ? ` · ${itemCount}` : ""}
              </button>
            ) : null}
            {connected ? (
              <button
                type="button"
                onClick={handleDisconnect}
                className="rounded-full border border-[#ba1a1a]/20 bg-[#ffdad6]/50 px-4 py-2 text-sm font-medium text-[#ba1a1a] hover:bg-[#ffdad6]"
              >
                End
              </button>
            ) : null}
          </div>
        </div>
      </header>

      <ChatPanel
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
        onOpenCart={() => setCartOpen(true)}
      />

      <CartDrawer
        open={cartOpen}
        cart={cart}
        delivery={session.delivery_info}
        onClose={() => setCartOpen(false)}
      />
    </div>
  );
}
