import { useCallback, useEffect, useRef, useState } from "react";
import type { VoicePhase } from "../types";

const TARGET_SAMPLE_RATE = 16000;
const OUTPUT_SAMPLE_RATE = 24000;
const SPEECH_THRESHOLD = 0.012;
const SILENCE_THRESHOLD = 0.007;
const SILENCE_FRAMES_REQUIRED = 10;

function floatTo16BitPCM(input: Float32Array): ArrayBuffer {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, input[i] ?? 0));
    output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output.buffer;
}

function downsampleBuffer(
  buffer: Float32Array,
  inputRate: number,
  outputRate: number,
): Float32Array {
  if (outputRate === inputRate) {
    return buffer;
  }
  const ratio = inputRate / outputRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offset = 0;
  for (let i = 0; i < newLength; i += 1) {
    const nextOffset = Math.round((i + 1) * ratio);
    let sum = 0;
    let count = 0;
    for (let j = offset; j < nextOffset && j < buffer.length; j += 1) {
      sum += buffer[j] ?? 0;
      count += 1;
    }
    result[i] = count > 0 ? sum / count : 0;
    offset = nextOffset;
  }
  return result;
}

function base64ToBytes(base64: string): Uint8Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function int16ToFloat32(bytes: Uint8Array): Float32Array {
  const int16 = new Int16Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 2);
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i += 1) {
    float32[i] = int16[i] / 0x8000;
  }
  return float32;
}

export interface UseAudioSessionOptions {
  onPcmChunk?: (chunk: ArrayBuffer) => void;
  onPhaseChange?: (phase: VoicePhase) => void;
  onActivityStart?: () => void;
  onActivityEnd?: () => void;
}

export interface UseAudioSessionResult {
  isCapturing: boolean;
  level: number;
  voicePhase: VoicePhase;
  startCapture: () => Promise<void>;
  stopCapture: () => void;
  playPcmBase64: (base64: string, sampleRate?: number) => Promise<void>;
  resetPlaybackQueue: () => void;
  pauseMicUpload: () => void;
  resumeMicUpload: () => void;
  setVoicePhase: (phase: VoicePhase) => void;
}

export function useAudioSession(options: UseAudioSessionOptions = {}): UseAudioSessionResult {
  const onPcmChunkRef = useRef(options.onPcmChunk);
  const onPhaseChangeRef = useRef(options.onPhaseChange);
  const onActivityStartRef = useRef(options.onActivityStart);
  const onActivityEndRef = useRef(options.onActivityEnd);

  useEffect(() => {
    onPcmChunkRef.current = options.onPcmChunk;
    onPhaseChangeRef.current = options.onPhaseChange;
    onActivityStartRef.current = options.onActivityStart;
    onActivityEndRef.current = options.onActivityEnd;
  }, [options.onPcmChunk, options.onPhaseChange, options.onActivityStart, options.onActivityEnd]);

  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const playbackTimeRef = useRef(0);
  const playbackCountRef = useRef(0);
  const micUploadEnabledRef = useRef(true);
  const micPausedByServerRef = useRef(false);
  const isCapturingRef = useRef(false);
  const silentSinkRef = useRef<GainNode | null>(null);
  const userSpeechActiveRef = useRef(false);
  const silenceFramesRef = useRef(0);

  const [isCapturing, setIsCapturing] = useState(false);
  const [level, setLevel] = useState(0);
  const [voicePhase, setVoicePhase] = useState<VoicePhase>("idle");

  const setPhase = useCallback((phase: VoicePhase) => {
    setVoicePhase(phase);
    onPhaseChangeRef.current?.(phase);
  }, []);

  const ensureContext = useCallback(async (): Promise<AudioContext> => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
      playbackTimeRef.current = audioContextRef.current.currentTime;
    }
    if (audioContextRef.current.state === "suspended") {
      await audioContextRef.current.resume();
    }
    return audioContextRef.current;
  }, []);

  const syncMicUploadState = useCallback(() => {
    micUploadEnabledRef.current =
      !micPausedByServerRef.current && playbackCountRef.current === 0;
  }, []);

  const pauseMicUpload = useCallback(() => {
    userSpeechActiveRef.current = false;
    silenceFramesRef.current = 0;
    micPausedByServerRef.current = true;
    syncMicUploadState();
  }, [syncMicUploadState]);

  const resumeMicUpload = useCallback(() => {
    micPausedByServerRef.current = false;
    userSpeechActiveRef.current = false;
    silenceFramesRef.current = 0;
    syncMicUploadState();
    if (playbackCountRef.current === 0) {
      setPhase("listening");
    }
  }, [syncMicUploadState, setPhase]);

  const stopCapture = useCallback(() => {
    if (userSpeechActiveRef.current) {
      userSpeechActiveRef.current = false;
      silenceFramesRef.current = 0;
      onActivityEndRef.current?.();
    }
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    silentSinkRef.current?.disconnect();
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    processorRef.current = null;
    sourceRef.current = null;
    silentSinkRef.current = null;
    mediaStreamRef.current = null;
    playbackCountRef.current = 0;
    micPausedByServerRef.current = false;
    micUploadEnabledRef.current = true;
    userSpeechActiveRef.current = false;
    silenceFramesRef.current = 0;
    isCapturingRef.current = false;
    setIsCapturing(false);
    setLevel(0);
    setPhase("idle");
  }, [setPhase]);

  const startCapture = useCallback(async () => {
    if (isCapturingRef.current) {
      return;
    }
    const ctx = await ensureContext();
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    const source = ctx.createMediaStreamSource(stream);
    const processor = ctx.createScriptProcessor(4096, 1, 1);

    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      let sum = 0;
      for (let i = 0; i < input.length; i += 1) {
        sum += Math.abs(input[i] ?? 0);
      }
      const avg = sum / input.length;
      setLevel(avg);

      const canDetectSpeech =
        micUploadEnabledRef.current && playbackCountRef.current === 0;

      if (canDetectSpeech) {
        if (!userSpeechActiveRef.current && avg >= SPEECH_THRESHOLD) {
          userSpeechActiveRef.current = true;
          silenceFramesRef.current = 0;
          onActivityStartRef.current?.();
        } else if (userSpeechActiveRef.current) {
          if (avg < SILENCE_THRESHOLD) {
            silenceFramesRef.current += 1;
            if (silenceFramesRef.current >= SILENCE_FRAMES_REQUIRED) {
              userSpeechActiveRef.current = false;
              silenceFramesRef.current = 0;
              onActivityEndRef.current?.();
            }
          } else {
            silenceFramesRef.current = 0;
          }
        }
      } else if (userSpeechActiveRef.current) {
        userSpeechActiveRef.current = false;
        silenceFramesRef.current = 0;
        onActivityEndRef.current?.();
      }

      if (!micUploadEnabledRef.current || playbackCountRef.current > 0) {
        return;
      }

      const downsampled = downsampleBuffer(input, ctx.sampleRate, TARGET_SAMPLE_RATE);
      onPcmChunkRef.current?.(floatTo16BitPCM(downsampled));
    };

    const silentSink = ctx.createGain();
    silentSink.gain.value = 0;

    source.connect(processor);
    processor.connect(silentSink);
    silentSink.connect(ctx.destination);

    mediaStreamRef.current = stream;
    sourceRef.current = source;
    processorRef.current = processor;
    silentSinkRef.current = silentSink;
    isCapturingRef.current = true;
    setIsCapturing(true);
    setPhase("listening");
  }, [ensureContext, setPhase]);

  const playPcmBase64 = useCallback(
    async (base64: string, sampleRate = OUTPUT_SAMPLE_RATE) => {
      const ctx = await ensureContext();

      const bytes = base64ToBytes(base64);
      const float32 = int16ToFloat32(bytes);
      const buffer = ctx.createBuffer(1, float32.length, sampleRate);
      buffer.copyToChannel(float32, 0);

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);

      playbackCountRef.current += 1;
      syncMicUploadState();
      setPhase("speaking");

      const startAt = Math.max(ctx.currentTime, playbackTimeRef.current);
      source.start(startAt);
      playbackTimeRef.current = startAt + buffer.duration;

      source.onended = () => {
        playbackCountRef.current = Math.max(0, playbackCountRef.current - 1);
        syncMicUploadState();
        if (
          playbackCountRef.current === 0 &&
          ctx.currentTime >= playbackTimeRef.current - 0.05
        ) {
          setPhase(isCapturingRef.current ? "listening" : "idle");
        }
      };
    },
    [ensureContext, setPhase, syncMicUploadState],
  );

  const resetPlaybackQueue = useCallback(() => {
    if (audioContextRef.current) {
      playbackTimeRef.current = audioContextRef.current.currentTime;
    }
    playbackCountRef.current = 0;
  }, []);

  useEffect(() => {
    return () => {
      stopCapture();
      void audioContextRef.current?.close();
      audioContextRef.current = null;
    };
  }, [stopCapture]);

  return {
    isCapturing,
    level,
    voicePhase,
    startCapture,
    stopCapture,
    playPcmBase64,
    resetPlaybackQueue,
    pauseMicUpload,
    resumeMicUpload,
    setVoicePhase: setPhase,
  };
}
