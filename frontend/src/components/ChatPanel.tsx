import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef } from "react";
import type { ChatMessage, VoicePhase } from "../types";
import { CategoryChips } from "./CategoryChips";
import { CheckoutCard } from "./CheckoutCard";
import { DeliveryBanner } from "./DeliveryBanner";
import { MicButton } from "./MicButton";
import { ProductCarousel } from "./ProductCarousel";

interface ChatPanelProps {
  messages: ChatMessage[];
  connected: boolean;
  processing: boolean;
  error?: string | null;
  voicePhase: VoicePhase;
  voiceLevel: number;
  micActive: boolean;
  onSend: (text: string) => void;
  onMicToggle: () => void;
  onConnect?: () => void;
  connecting?: boolean;
  selectedProductId?: string;
  onSelectProduct?: (product: import("../types").Product) => void;
  onOpenCart?: () => void;
}

function linkifyContent(content: string, isUser: boolean) {
  const urlPattern = /(https?:\/\/[^\s]+)/g;
  const parts = content.split(urlPattern);
  if (parts.length === 1) {
    return content;
  }
  return parts.map((part, index) =>
    part.startsWith("http") ? (
      <a
        key={`${index}-${part}`}
        href={part}
        target="_blank"
        rel="noreferrer"
        className={`break-all underline underline-offset-2 ${
          isUser ? "decoration-[#402970]/40" : "decoration-white/40"
        }`}
      >
        {part}
      </a>
    ) : (
      <span key={`${index}-${part}`}>{part}</span>
    ),
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const isStreaming = message.status === "streaming";
  const displayContent = message.content?.trim() || (isStreaming ? "Listening…" : "");

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[85%] px-4 py-3 text-sm leading-relaxed md:text-base ${
          isUser
            ? `rounded-2xl rounded-br-sm bg-[#F0EEFA] text-[#222222] ${
                isStreaming ? "border border-dashed border-[#402970]/25 opacity-90" : ""
              }`
            : `rounded-2xl rounded-bl-sm bg-[#402970] text-white shadow-[0_2px_8px_rgba(64,41,112,0.12)] ${
                isStreaming ? "border border-dashed border-white/25 opacity-90" : ""
              }`
        }`}
      >
        <span className={isStreaming && !message.content?.trim() ? "italic opacity-70" : ""}>
          {linkifyContent(displayContent, isUser)}
        </span>
      </div>
    </motion.div>
  );
}

function RichMessageBlock({
  message,
  selectedProductId,
  onSelectProduct,
  onOpenCart,
}: {
  message: ChatMessage;
  selectedProductId?: string;
  onSelectProduct?: (product: import("../types").Product) => void;
  onOpenCart?: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="flex justify-start"
    >
      <div className="w-full max-w-full md:max-w-[92%]">
        {message.kind === "products" ? (
          <ProductCarousel
            inline
            products={message.products ?? []}
            searchQuery={message.searchQuery}
            selectedId={selectedProductId}
            error={message.searchError}
            onSelect={onSelectProduct}
          />
        ) : null}
        {message.kind === "checkout" && message.checkoutPayload ? (
          <CheckoutCard inline payload={message.checkoutPayload} />
        ) : null}
        {message.kind === "delivery" && message.delivery ? (
          <DeliveryBanner inline delivery={message.delivery} />
        ) : null}
        {message.kind === "cart_notice" ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl rounded-bl-sm border border-[#402970]/10 bg-[#F0EEFA] px-4 py-3 text-sm text-[#222222]">
            <span>
              Added {message.cartItemName} — browse more or tell Kapru your delivery city and date.
            </span>
            {onOpenCart ? (
              <button
                type="button"
                className="shrink-0 font-semibold text-[#402970] underline underline-offset-2"
                onClick={onOpenCart}
              >
                View cart
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </motion.div>
  );
}

function renderMessage(
  message: ChatMessage,
  selectedProductId?: string,
  onSelectProduct?: (product: import("../types").Product) => void,
  onOpenCart?: () => void,
) {
  if (message.kind === "text") {
    return <MessageBubble message={message} />;
  }
  return (
    <RichMessageBlock
      message={message}
      selectedProductId={selectedProductId}
      onSelectProduct={onSelectProduct}
      onOpenCart={onOpenCart}
    />
  );
}

export function ChatPanel({
  messages,
  connected,
  processing,
  error,
  voicePhase,
  voiceLevel,
  micActive,
  onSend,
  onMicToggle,
  onConnect,
  connecting = false,
  selectedProductId,
  onSelectProduct,
  onOpenCart,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const showEmptyState = messages.length === 0;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages, processing]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const value = inputRef.current?.value ?? "";
    const trimmed = value.trim();
    if (!trimmed || !connected || processing) {
      return;
    }
    onSend(trimmed);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const handleChipSelect = (hint: string) => {
    if (!connected) {
      onConnect?.();
      return;
    }
    onSend(hint);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        ref={scrollRef}
        className="scrollbar-thin flex-1 overflow-y-auto px-4 pb-4 md:px-6"
      >
        {showEmptyState ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="flex min-h-full flex-col items-center justify-center py-12 text-center"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.1, duration: 0.4 }}
              className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-[#402970] text-2xl font-bold text-white shadow-[0_8px_24px_rgba(64,41,112,0.25)]"
            >
              K
            </motion.div>
            <motion.h2
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="text-xl font-bold tracking-tight text-[#222222] md:text-2xl"
            >
              {connected ? "Hi, I'm Kapru" : "Welcome to Kapruka"}
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mt-2 max-w-sm text-sm leading-relaxed text-[#494550] md:text-base"
            >
              {connected
                ? "Your gift concierge for cakes, flowers, and hampers across Sri Lanka. Type or tap the mic to speak."
                : "Start a chat to browse gifts with your AI concierge — in English, Sinhala, Tamil, or Tanglish."}
            </motion.p>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.25 }}
              className="mt-3 text-xs text-[#402970]/70"
            >
              ආයුබෝවන් · Vanakkam · Welcome
            </motion.p>

            <div className="mt-10 w-full max-w-lg px-2">
              <CategoryChips onSelect={handleChipSelect} disabled={processing} />
            </div>

            {!connected ? (
              <motion.button
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                type="button"
                onClick={onConnect}
                disabled={connecting}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="mt-8 rounded-full bg-[#402970] px-8 py-3 text-sm font-semibold text-white shadow-[0_4px_16px_rgba(64,41,112,0.3)] hover:bg-[#2a1059] disabled:opacity-60"
              >
                {connecting ? "Connecting…" : "Start chatting with Kapru"}
              </motion.button>
            ) : null}
          </motion.div>
        ) : (
          <div className="mx-auto w-full max-w-[800px] space-y-6 py-6">
            <AnimatePresence initial={false}>
              {messages.map((message) => (
                <div key={message.id}>
                  {renderMessage(message, selectedProductId, onSelectProduct, onOpenCart)}
                </div>
              ))}
            </AnimatePresence>

            {processing ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-[#402970]/10 px-4 py-3 text-sm text-[#402970]">
                  <span className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <motion.span
                        key={i}
                        className="h-1.5 w-1.5 rounded-full bg-[#402970]"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                      />
                    ))}
                  </span>
                  Kapru is searching Kapruka…
                </div>
              </motion.div>
            ) : null}
          </div>
        )}
      </div>

      <div className="shrink-0 border-t border-[#402970]/8 bg-white/80 px-4 py-3 backdrop-blur-md md:px-6">
        {error ? (
          <p className="mb-2 text-center text-xs text-[#ba1a1a]">{error}</p>
        ) : null}
        <form
          onSubmit={handleSubmit}
          className="mx-auto flex w-full max-w-[800px] items-end gap-3"
        >
          <div className="min-w-0 flex-1">
            <input
              ref={inputRef}
              type="text"
              disabled={!connected || processing}
              placeholder={connected ? "Message Kapru…" : "Start chat to type"}
              className="w-full rounded-full border border-[#402970]/12 bg-[#F0EEFA]/50 px-5 py-3.5 text-sm text-[#222222] placeholder:text-[#494550]/50 shadow-inner focus:border-[#402970]/30 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#402970]/10 disabled:opacity-50 md:text-base"
            />
          </div>
          <MicButton
            phase={voicePhase}
            level={voiceLevel}
            connected={connected}
            active={micActive}
            disabled={processing}
            onToggle={onMicToggle}
          />
        </form>
      </div>
    </div>
  );
}
