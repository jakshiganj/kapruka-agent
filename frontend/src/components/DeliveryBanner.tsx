import type { DeliveryInfo } from "../types";

interface DeliveryBannerProps {
  delivery: DeliveryInfo;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso + "T12:00:00").toLocaleDateString(undefined, {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export function DeliveryBanner({ delivery }: DeliveryBannerProps) {
  if (!delivery.city && !delivery.date) {
    return null;
  }

  const validated = delivery.validated === "true";
  const failed = delivery.validated === "false";

  return (
    <section
      className={`rounded-2xl border p-4 md:p-5 ${
        validated
          ? "border-emerald-500/30 bg-emerald-950/30"
          : failed
            ? "border-red-500/30 bg-red-950/20"
            : "border-amber-500/30 bg-amber-950/20"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-400">Delivery</p>
          <p className="mt-1 text-lg font-semibold text-white">
            {delivery.city ?? "City pending"}
            {delivery.date ? ` · ${formatDate(delivery.date)}` : ""}
          </p>
          {validated && delivery.delivery_rate ? (
            <p className="mt-1 text-sm text-emerald-200">
              Flat rate LKR {Number(delivery.delivery_rate).toLocaleString()} · Confirmed
            </p>
          ) : failed ? (
            <p className="mt-1 text-sm text-red-200">Not available — try another date or city</p>
          ) : (
            <p className="mt-1 text-sm text-amber-200">Awaiting validation…</p>
          )}
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            validated
              ? "bg-emerald-500/20 text-emerald-200"
              : failed
                ? "bg-red-500/20 text-red-200"
                : "bg-amber-500/20 text-amber-200"
          }`}
        >
          {validated ? "✓ Validated" : failed ? "Unavailable" : "Pending"}
        </span>
      </div>
    </section>
  );
}
