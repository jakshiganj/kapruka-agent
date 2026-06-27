import type { VoicePhase } from "../types";

interface VoiceIndicatorProps {
  phase: VoicePhase;
  level: number;
  connected: boolean;
  micEnabled: boolean;
  reconnecting?: boolean;
}

export function VoiceIndicator({
  phase,
  level,
  connected,
  micEnabled,
  reconnecting = false,
}: VoiceIndicatorProps) {
  const pulseScale = phase === "processing" ? 1.1 : 1 + Math.min(level * 8, 0.6);
  const label =
    reconnecting
      ? "Reconnecting"
      : phase === "speaking"
      ? "Kapru speaking"
      : phase === "processing"
        ? "Searching Kapruka"
        : phase === "listening"
          ? "Listening"
          : connected && micEnabled
            ? "Ready"
            : connected
              ? "Chat mode"
              : "Offline";

  const ringColor =
    reconnecting
      ? "bg-[#FBD614]/60"
      : phase === "speaking"
      ? "bg-[#FBD614]"
      : phase === "processing"
        ? "bg-[#FBD614]/70"
        : phase === "listening"
          ? "bg-[#402970]"
          : connected && micEnabled
            ? "bg-[#402970]/50"
            : "bg-[#402970]/25";

  const subtitle =
    reconnecting
      ? "Restoring your session — your cart and checkout details are safe."
      : phase === "processing"
      ? "Finding gifts and checking delivery across Sri Lanka…"
      : connected && micEnabled
        ? "Speak in English, Sinhala, Tamil, or Tanglish — machan, cake ekak, flowers, hampers…"
        : connected
          ? "Type below or tap the mic to speak with Kapru."
          : "Connect to meet Kapru, your Kapruka gift assistant.";

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative flex h-28 w-28 items-center justify-center">
        <span
          className={`absolute inset-0 rounded-full ${ringColor} opacity-25 blur-lg transition-transform duration-100 ${
            phase === "processing" || reconnecting ? "animate-pulse" : ""
          }`}
          style={{ transform: `scale(${pulseScale})` }}
        />
        <span
          className={`absolute inset-3 rounded-full border-2 border-[#402970]/15 ${ringColor} opacity-60 transition-transform duration-100 ${
            phase === "listening" || phase === "processing" || reconnecting ? "animate-pulse" : ""
          }`}
          style={{ transform: `scale(${Math.min(pulseScale, 1.15)})` }}
        />
        <span className="relative z-10 text-center text-[10px] font-bold uppercase tracking-widest text-[#402970]">
          {label}
        </span>
      </div>
      <p className="max-w-md text-center text-sm leading-relaxed text-[#494550]">{subtitle}</p>
      {connected && phase === "idle" ? (
        <p className="text-xs font-medium text-[#402970]/70">ආයුබෝවන් · Vanakkam · Welcome</p>
      ) : null}
    </div>
  );
}
