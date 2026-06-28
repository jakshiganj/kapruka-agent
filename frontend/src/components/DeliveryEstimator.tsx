import { useState } from "react";

interface DeliveryEstimate {
  city?: string;
  date?: string;
  available?: boolean | null;
  rate?: number | string | null;
  reason?: string;
  next_available_date?: string;
  perishable_warning?: string;
  error?: string;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function DeliveryEstimator() {
  const [city, setCity] = useState("");
  const [date, setDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DeliveryEstimate | null>(null);

  const check = async () => {
    if (!city.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const params = new URLSearchParams({ city: city.trim() });
      if (date) params.set("date", date);
      const res = await fetch(`/api/delivery-estimate?${params.toString()}`);
      const data = (await res.json()) as DeliveryEstimate;
      setResult(data);
    } catch {
      setResult({ error: "Couldn't reach the delivery service. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const available = result?.available;

  return (
    <div className="w-full max-w-lg rounded-2xl border border-[#402970]/10 bg-white p-3.5 text-left shadow-[0_2px_12px_rgba(64,41,112,0.05)] sm:p-4">
      <p className="text-sm font-semibold text-[#222222]">Check delivery before you shop</p>
      <p className="mt-0.5 text-xs text-[#494550]">
        See if Kapruka delivers to your city on a given date.
      </p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void check();
          }}
          placeholder="City (e.g. Colombo 07)"
          className="min-w-0 flex-1 rounded-lg border border-[#402970]/10 bg-[#F0EEFA]/40 px-3 py-2 text-sm text-[#222222] placeholder:text-[#494550]/40 transition-all focus:border-[#402970]/25 focus:bg-white focus:outline-none"
        />
        <input
          type="date"
          value={date}
          min={todayIso()}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-lg border border-[#402970]/12 bg-[#F0EEFA]/40 px-3 py-2 text-sm text-[#222222] focus:border-[#402970]/30 focus:bg-white focus:outline-none"
        />
        <button
          type="button"
          onClick={() => void check()}
          disabled={loading || !city.trim()}
          className="rounded-lg bg-gradient-to-r from-[#402970] to-[#5a3d8a] px-4 py-2 text-sm font-semibold text-white transition-all hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Checking…" : "Check"}
        </button>
      </div>

      {result ? (
        <div className="mt-3 text-sm">
          {result.error ? (
            <p className="text-[#ba1a1a]">{result.error}</p>
          ) : available ? (
            <div className="rounded-lg border border-[#402970]/10 bg-[#F0EEFA]/50 px-3 py-2">
              <p className="font-medium text-[#402970]">
                Delivers to {result.city}
                {result.rate != null ? ` · LKR ${Number(result.rate).toLocaleString()}` : ""}
              </p>
              {result.perishable_warning ? (
                <p className="mt-1 text-xs text-[#6f5d00]">{result.perishable_warning}</p>
              ) : null}
            </div>
          ) : (
            <div className="rounded-lg border border-[#6f5d00]/20 bg-[#fff8e0] px-3 py-2 text-[#6f5d00]">
              <p>{result.reason ?? `Delivery to ${result.city} isn't available on that date.`}</p>
              {result.next_available_date ? (
                <p className="mt-1 text-xs">Next available: {result.next_available_date}</p>
              ) : null}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
