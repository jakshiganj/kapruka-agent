import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Translator } from "../i18n";
import type { ChatMessage, VoicePhase } from "../types";
import { CategoryChips } from "./CategoryChips";
import { CategoryPicker } from "./CategoryPicker";
import { CheckoutCard } from "./CheckoutCard";
import { CheckoutForm } from "./CheckoutForm";
import { DeliveryBanner } from "./DeliveryBanner";
import { DeliveryEstimator } from "./DeliveryEstimator";
import { MicButton } from "./MicButton";
import { OrderTrackingCard } from "./OrderTrackingCard";
import { ProductCarousel } from "./ProductCarousel";
import { VoiceIndicator } from "./VoiceIndicator";

interface ChatPanelProps {
  t: Translator;
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
  onViewProduct?: (product: import("../types").Product) => void;
  onOpenCart?: () => void;
  checkoutStale?: boolean;
  onRequestNewLink?: () => void;
  onSelectCategory?: (category: string, subcategory?: string) => void;
  onSubmitCheckout?: (data: import("../types").CheckoutFormData) => void;
  pendingAddId?: string | null;
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
        } hover:opacity-80 transition-opacity`}
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
        className={`max-w-[92%] px-3.5 py-2.5 text-[13px] leading-relaxed sm:max-w-[85%] sm:px-4 sm:py-3 sm:text-sm md:max-w-[42rem] md:text-base ${
          isUser
            ? `rounded-2xl rounded-br-sm bg-[#F0EEFA] text-[#222222] shadow-[0_1px_3px_rgba(64,41,112,0.06)] ${
                isStreaming ? "border border-dashed border-[#402970]/25 opacity-90" : ""
              }`
            : `rounded-2xl rounded-bl-sm bg-gradient-to-br from-[#402970] to-[#4e3485] text-white shadow-[0_2px_12px_rgba(64,41,112,0.15)] ${
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
  onViewProduct,
  onOpenCart,
  checkoutStale,
  onSend,
  onRequestNewLink,
  onSelectCategory,
  onSubmitCheckout,
  checkoutSubmitting,
  pendingAddId,
}: {
  message: ChatMessage;
  selectedProductId?: string;
  onSelectProduct?: (product: import("../types").Product) => void;
  onViewProduct?: (product: import("../types").Product) => void;
  onOpenCart?: () => void;
  checkoutStale?: boolean;
  onSend?: (text: string) => void;
  onRequestNewLink?: () => void;
  onSelectCategory?: (category: string, subcategory?: string) => void;
  onSubmitCheckout?: (data: import("../types").CheckoutFormData) => void;
  checkoutSubmitting?: boolean;
  pendingAddId?: string | null;
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
            pendingId={pendingAddId ?? undefined}
            error={message.searchError}
            onSelect={onSelectProduct}
            onViewDetails={onViewProduct}
          />
        ) : null}
        {message.kind === "checkout" && message.checkoutPayload ? (
          <CheckoutCard
            inline
            payload={message.checkoutPayload}
            stale={checkoutStale}
            onRequestNewLink={onRequestNewLink}
          />
        ) : null}
        {message.kind === "checkout_form" && message.checkoutForm && onSubmitCheckout ? (
          <CheckoutForm
            payload={message.checkoutForm}
            onSubmit={onSubmitCheckout}
            submitting={checkoutSubmitting}
          />
        ) : null}
        {message.kind === "delivery" && message.delivery ? (
          <DeliveryBanner inline delivery={message.delivery} />
        ) : null}
        {message.kind === "order_tracking" && message.orderTracking ? (
          <OrderTrackingCard payload={message.orderTracking} />
        ) : null}
        {message.kind === "categories" ? (
          <CategoryPicker
            compact
            categories={message.categories ?? []}
            onSelectCategory={onSelectCategory}
          />
        ) : null}
        {message.kind === "branch_prompt" ? (
          <div className="rounded-2xl rounded-bl-sm border border-[#402970]/15 bg-[#F0EEFA] px-4 py-4 text-sm text-[#222222]">
            <p className="font-medium">You already have a payment link open.</p>
            <p className="mt-1 text-[#494550]">
              Should I add this to that order, or start a new gift?
            </p>
            {onSend ? (
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onSend("Add to this order")}
                  className="rounded-full bg-[#402970] px-4 py-2 text-xs font-semibold text-white hover:bg-[#2a1059]"
                >
                  Add to this order
                </button>
                <button
                  type="button"
                  onClick={() => onSend("Start a new gift")}
                  className="rounded-full border border-[#402970]/20 bg-white px-4 py-2 text-xs font-semibold text-[#402970] hover:bg-[#402970]/5"
                >
                  New gift
                </button>
              </div>
            ) : null}
          </div>
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

interface RenderMessageOptions {
  selectedProductId?: string;
  onSelectProduct?: (product: import("../types").Product) => void;
  onViewProduct?: (product: import("../types").Product) => void;
  onOpenCart?: () => void;
  checkoutStale?: boolean;
  onSend?: (text: string) => void;
  onRequestNewLink?: () => void;
  onSelectCategory?: (category: string, subcategory?: string) => void;
  onSubmitCheckout?: (data: import("../types").CheckoutFormData) => void;
  checkoutSubmitting?: boolean;
  pendingAddId?: string | null;
}

function renderMessage(message: ChatMessage, options: RenderMessageOptions) {
  if (message.kind === "text") {
    return <MessageBubble message={message} />;
  }
  const {
    selectedProductId,
    onSelectProduct,
    onViewProduct,
    onOpenCart,
    checkoutStale,
    onSend,
    onRequestNewLink,
    onSelectCategory,
    onSubmitCheckout,
    checkoutSubmitting,
    pendingAddId,
  } = options;
  return (
    <RichMessageBlock
      message={message}
      selectedProductId={selectedProductId}
      onSelectProduct={onSelectProduct}
      onViewProduct={onViewProduct}
      onOpenCart={onOpenCart}
      checkoutStale={checkoutStale}
      onSend={onSend}
      onRequestNewLink={onRequestNewLink}
      onSubmitCheckout={onSubmitCheckout}
      onSelectCategory={onSelectCategory}
      checkoutSubmitting={checkoutSubmitting}
      pendingAddId={pendingAddId}
    />
  );
}

export function ChatPanel({
  t,
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
  onViewProduct,
  onOpenCart,
  checkoutStale,
  onRequestNewLink,
  onSelectCategory,
  onSubmitCheckout,
  pendingAddId,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [atBottom, setAtBottom] = useState(true);

  const showEmptyState = messages.length === 0;
  const lastCheckoutFormId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i]?.kind === "checkout_form") {
        return messages[i]?.id;
      }
    }
    return undefined;
  }, [messages]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior });
    }
  }, []);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setAtBottom(distanceFromBottom < 80);
  }, []);

  useEffect(() => {
    if (atBottom) {
      scrollToBottom();
    }
  }, [messages, processing, atBottom, scrollToBottom]);

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

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="scrollbar-hide overscroll-contain flex-1 overflow-y-auto px-3 pb-4 sm:scrollbar-thin sm:px-4 md:px-6"
      >
        {showEmptyState ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="flex min-h-full flex-col items-center justify-center px-4 py-8 text-center sm:py-12"
          >
            {connected ? (
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.1, duration: 0.4 }}
                className="mb-6"
              >
                <VoiceIndicator
                  phase={voicePhase}
                  level={voiceLevel}
                  connected={connected}
                  micEnabled={micActive}
                />
              </motion.div>
            ) : (
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.1, duration: 0.4 }}
                className="mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-[#402970] to-[#5a3d8a] text-xl font-bold text-white shadow-[0_8px_24px_rgba(64,41,112,0.25)] sm:h-16 sm:w-16 sm:text-2xl"
              >
                K
              </motion.div>
            )}
            <motion.h2
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="text-lg font-bold tracking-tight text-[#222222] sm:text-xl md:text-2xl"
            >
              {connected ? t("welcome.connectedTitle") : t("welcome.disconnectedTitle")}
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mt-2 max-w-sm text-xs leading-relaxed text-[#494550] sm:text-sm md:text-base"
            >
              {connected
                ? t("welcome.connectedSubtitle")
                : t("welcome.disconnectedSubtitle")}
            </motion.p>
            {!connected ? (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.25 }}
                className="mt-3 text-xs text-[#402970]/70"
              >
                ආයුබෝවන් · Vanakkam · Welcome
              </motion.p>
            ) : null}

            {connected ? (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="mt-8 flex w-full justify-center"
              >
                <div className="flex flex-col items-center gap-4">
                  <CategoryChips onSelect={(hint) => onSend(hint)} disabled={processing} />
                  <DeliveryEstimator />
                </div>
              </motion.div>
            ) : (
              <motion.button
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                type="button"
                onClick={onConnect}
                disabled={connecting}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="mt-8 rounded-full bg-gradient-to-r from-[#402970] to-[#5a3d8a] px-8 py-3.5 text-sm font-semibold text-white shadow-[0_4px_20px_rgba(64,41,112,0.3)] transition-all hover:shadow-[0_6px_24px_rgba(64,41,112,0.4)] disabled:opacity-60"
              >
                {connecting ? t("welcome.connecting") : t("welcome.cta")}
              </motion.button>
            )}
          </motion.div>
        ) : (
          <div className="mx-auto w-full max-w-5xl space-y-4 py-4 sm:space-y-6 sm:py-6">
            <AnimatePresence initial={false}>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  layout
                  initial={{ opacity: 0, scale: 0.95, y: 15 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: -15 }}
                  transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                >
                  {renderMessage(message, {
                    selectedProductId,
                    onSelectProduct,
                    onViewProduct,
                    onOpenCart,
                    checkoutStale,
                    onSend,
                    onRequestNewLink,
                    onSelectCategory,
                    onSubmitCheckout,
                    checkoutSubmitting:
                      processing && message.kind === "checkout_form" && message.id === lastCheckoutFormId,
                    pendingAddId,
                  })}
                </motion.div>
              ))}
            </AnimatePresence>

            {processing ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-[#402970]/8 px-3 py-2.5 text-xs text-[#402970] sm:px-4 sm:py-3 sm:text-sm">
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
                  {t("chat.searching")}
                </div>
              </motion.div>
            ) : null}
          </div>
        )}
      </div>

      <AnimatePresence>
        {!showEmptyState && !atBottom ? (
          <motion.button
            type="button"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={() => scrollToBottom()}
            aria-label="Scroll to latest"
            className="absolute bottom-24 left-1/2 z-20 flex h-10 w-10 -translate-x-1/2 items-center justify-center rounded-full bg-gradient-to-br from-[#402970] to-[#5a3d8a] text-white shadow-[0_4px_20px_rgba(64,41,112,0.35)] transition-all hover:shadow-[0_6px_24px_rgba(64,41,112,0.45)] sm:h-9 sm:w-9"
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden>
              <path
                d="M12 5v14m0 0l-6-6m6 6l6-6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </motion.button>
        ) : null}
      </AnimatePresence>

      <div
        className="shrink-0 border-t border-[#402970]/6 bg-white/85 px-3 py-2.5 backdrop-blur-xl sm:px-4 sm:py-3 md:px-6"
        style={{ paddingBottom: "max(0.625rem, env(safe-area-inset-bottom))" }}
      >
        {error ? (
          <p className="mb-2 text-center text-[11px] text-[#ba1a1a] sm:text-xs">{error}</p>
        ) : null}
        <form
          onSubmit={handleSubmit}
          className="mx-auto flex w-full max-w-5xl items-center gap-2 sm:gap-2.5"
        >
          <div className="min-w-0 flex-1">
            <input
              ref={inputRef}
              type="text"
              disabled={!connected || processing}
              placeholder={connected ? t("input.connected") : t("input.disconnected")}
              className="w-full rounded-full border border-[#402970]/10 bg-[#F0EEFA]/40 px-4 py-3 text-sm text-[#222222] placeholder:text-[#494550]/40 shadow-[inset_0_1px_3px_rgba(64,41,112,0.04)] transition-all focus:border-[#402970]/25 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#402970]/10 focus:shadow-[0_0_0_4px_rgba(64,41,112,0.04)] disabled:opacity-50 sm:px-5 sm:py-3.5 md:text-base"
            />
          </div>
          <button
            type="submit"
            disabled={!connected || processing}
            aria-label={t("input.send")}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-[#402970] to-[#5a3d8a] text-white shadow-[0_2px_8px_rgba(64,41,112,0.2)] transition-all hover:shadow-[0_4px_16px_rgba(64,41,112,0.3)] disabled:cursor-not-allowed disabled:opacity-40 sm:h-12 sm:w-12"
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden>
              <path d="M6 12l6-6 6 6M12 6v14" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <MicButton
            phase={voicePhase}
            level={voiceLevel}
            connected={connected}
            active={micActive}
            disabled={processing}
            onToggle={onMicToggle}
            compact
          />
        </form>
      </div>
    </div>
  );
}
