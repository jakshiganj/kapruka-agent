import type { VoicePhase } from "../types";

interface VoiceIndicatorProps {
  phase: VoicePhase;
  level: number;
  connected: boolean;
}

export function VoiceIndicator({ phase, level, connected }: VoiceIndicatorProps) {
  const pulseScale = phase === "processing" ? 1.1 : 1 + Math.min(level * 8, 0.6);
  const label =
    phase === "speaking"
      ? "Kapru speaking"
      : phase === "processing"
        ? "Searching Kapruka"
        : phase === "listening"
          ? "Listening"
          : connected
            ? "Ready"
            : "Offline";

  const ringColor =
    phase === "speaking"
      ? "bg-emerald-400/80"
      : phase === "processing"
        ? "bg-amber-400/80"
        : phase === "listening"
          ? "bg-sky-400/80"
          : "bg-slate-500/60";

  const subtitle =
    phase === "processing"
      ? "Finding gifts and checking delivery across Sri Lanka…"
      : connected
        ? "Speak in English, Sinhala, Tamil, or Tanglish — machan, cake ekak, flowers, hampers…"
        : "Connect to meet Kapru, your Kapruka gift assistant.";

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative flex h-28 w-28 items-center justify-center">
        <span
          className={`absolute inset-0 rounded-full ${ringColor} opacity-30 blur-lg transition-transform duration-100 ${
            phase === "processing" ? "animate-pulse" : ""
          }`}
          style={{ transform: `scale(${pulseScale})` }}
        />
        <span
          className={`absolute inset-3 rounded-full border-2 border-white/20 ${ringColor} transition-transform duration-100 ${
            phase === "listening" ? "animate-pulse" : phase === "processing" ? "animate-pulse" : ""
          }`}
          style={{ transform: `scale(${Math.min(pulseScale, 1.15)})` }}
        />
        <span className="relative z-10 text-center text-[10px] font-bold uppercase tracking-widest text-white/90">
          {label}
        </span>
      </div>
      <p className="max-w-md text-center text-sm leading-relaxed text-slate-400">{subtitle}</p>
      {connected && phase === "idle" ? (
        <p className="text-xs text-emerald-400/80">ආයුබෝවන් · Vanakkam · Welcome</p>
      ) : null}
    </div>
  );
}
