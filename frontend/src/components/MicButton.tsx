import { motion } from "framer-motion";
import type { VoicePhase } from "../types";

interface MicButtonProps {
  phase: VoicePhase;
  level: number;
  connected: boolean;
  active: boolean;
  disabled?: boolean;
  onToggle: () => void;
  compact?: boolean;
}

export function MicButton({
  phase,
  level,
  connected,
  active,
  disabled = false,
  onToggle,
  compact = false,
}: MicButtonProps) {
  const pulseScale = phase === "processing" ? 1.12 : 1 + Math.min(level * 10, 0.5);
  const isListening = active && phase === "listening";
  const isSpeaking = phase === "speaking";
  const isProcessing = phase === "processing";

  const label = isSpeaking
    ? "Speaking"
    : isProcessing
      ? "Searching"
      : isListening
        ? "Listening"
        : active
          ? "Tap to mute"
          : connected
            ? "Tap to speak"
            : "Offline";

  /* ── Compact mode: clean inline button matching the send button ── */
  if (compact) {
    const compactBg = active
      ? isSpeaking
        ? "bg-[#FBD614] text-[#222222]"
        : isProcessing
          ? "bg-[#FBD614]/80 text-[#222222]"
          : "bg-[#402970] text-white"
      : connected
        ? "bg-[#402970]/10 text-[#402970] hover:bg-[#402970]/20"
        : "bg-[#e5e2e1] text-[#494550]";

    return (
      <motion.button
        type="button"
        disabled={disabled || !connected}
        aria-label={label}
        aria-pressed={active}
        onClick={() => {
          if (!disabled && connected) onToggle();
        }}
        whileTap={connected && !disabled ? { scale: 0.92 } : undefined}
        className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition-all sm:h-12 sm:w-12 ${compactBg} ${
          disabled || !connected
            ? "cursor-not-allowed opacity-40"
            : "cursor-pointer"
        } ${active ? "shadow-[0_0_0_3px_rgba(64,41,112,0.15)]" : ""}`}
      >
        {/* Subtle pulse ring when active */}
        {active ? (
          <motion.span
            className="absolute inset-0 rounded-full bg-[#402970]/15"
            animate={{ scale: [1, 1.15, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        ) : null}
        <svg viewBox="0 0 24 24" fill="currentColor" className="relative z-10 h-5 w-5" aria-hidden>
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5-3c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-2.08c3.39-.49 6-3.39 6-6.92h-2z" />
        </svg>
      </motion.button>
    );
  }

  /* ── Full mode: used in empty state / voice hero ── */
  const ringClass = isSpeaking
    ? "bg-[#FBD614]"
    : isProcessing
      ? "bg-[#FBD614]/70"
      : isListening
        ? "bg-[#402970]"
        : connected
          ? "bg-[#402970]/40"
          : "bg-[#e5e2e1]";

  return (
    <div className="flex flex-col items-center gap-1">
      <motion.button
        type="button"
        disabled={disabled || !connected}
        aria-label={label}
        aria-pressed={active}
        onClick={() => {
          if (!disabled && connected) onToggle();
        }}
        whileTap={connected && !disabled ? { scale: 0.94 } : undefined}
        className={`relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full transition-shadow ${
          disabled || !connected
            ? "cursor-not-allowed opacity-50"
            : active
              ? "cursor-pointer shadow-[0_0_0_4px_rgba(64,41,112,0.15),0_8px_24px_rgba(64,41,112,0.25)]"
              : "cursor-pointer shadow-[0_4px_16px_rgba(64,41,112,0.2)] hover:shadow-[0_6px_20px_rgba(64,41,112,0.28)]"
        }`}
      >
        <motion.span
          className={`absolute inset-0 rounded-full ${ringClass} opacity-25 blur-md`}
          animate={{ scale: active ? pulseScale : 1 }}
          transition={{ duration: 0.1 }}
        />
        <motion.span
          className={`absolute inset-1 rounded-full border-2 ${
            active ? "border-[#402970]/30" : "border-[#402970]/15"
          } ${ringClass} opacity-20`}
          animate={{ scale: active ? Math.min(pulseScale, 1.15) : 1 }}
          transition={{ duration: 0.1 }}
        />
        <span
          className={`relative z-10 flex h-14 w-14 items-center justify-center rounded-full transition-colors ${
            active
              ? "bg-[#402970] text-white"
              : connected
                ? "bg-[#402970] text-white"
                : "bg-[#e5e2e1] text-[#494550]"
          }`}
        >
          <svg viewBox="0 0 24 24" fill="currentColor" className="h-6 w-6" aria-hidden>
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5-3c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-2.08c3.39-.49 6-3.39 6-6.92h-2z" />
          </svg>
        </span>
      </motion.button>
      <span className="text-[10px] font-medium tracking-wide text-[#494550]/80">{label}</span>
    </div>
  );
}
