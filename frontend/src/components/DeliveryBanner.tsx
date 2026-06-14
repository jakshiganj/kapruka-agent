import type { DeliveryInfo } from "../types";

interface DeliveryBannerProps {
  delivery: DeliveryInfo;
  inline?: boolean;
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

export function DeliveryBanner({ delivery, inline = false }: DeliveryBannerProps) {
  if (!delivery.city && !delivery.date) {
    return null;
  }

  const validated = delivery.validated === "true";
  const failed = delivery.validated === "false";

  const statusStyles = validated
    ? "border-[#402970]/15 bg-[#F0EEFA]"
    : failed
      ? "border-[#ba1a1a]/20 bg-[#ffdad6]"
      : "border-[#FBD614]/30 bg-[#fff8e0]";

  const badgeStyles = validated
    ? "bg-[#402970]/10 text-[#402970]"
    : failed
      ? "bg-[#ba1a1a]/10 text-[#ba1a1a]"
      : "bg-[#FBD614]/30 text-[#6f5d00]";

  return (
    <section
      className={`border p-4 ${
        inline ? "rounded-2xl rounded-bl-sm" : "rounded-2xl"
      } ${statusStyles}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-[#494550]">Delivery</p>
          <p className="mt-1 text-base font-semibold text-[#222222]">
            {delivery.city ?? "City pending"}
            {delivery.date ? ` · ${formatDate(delivery.date)}` : ""}
          </p>
          {validated && delivery.delivery_rate ? (
            <p className="mt-1 text-sm text-[#402970]">
              Flat rate LKR {Number(delivery.delivery_rate).toLocaleString()} · Confirmed
            </p>
          ) : failed ? (
            <p className="mt-1 text-sm text-[#ba1a1a]">Not available — try another date or city</p>
          ) : (
            <p className="mt-1 text-sm text-[#6f5d00]">Awaiting validation…</p>
          )}
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${badgeStyles}`}>
          {validated ? "✓ Validated" : failed ? "Unavailable" : "Pending"}
        </span>
      </div>
    </section>
  );
}
