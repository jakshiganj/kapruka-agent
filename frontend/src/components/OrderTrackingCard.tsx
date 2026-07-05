import { motion } from "framer-motion";
import type { OrderTrackingEvent, OrderTrackingPayload } from "../types";

interface OrderTrackingCardProps {
  payload: OrderTrackingPayload;
}

function collectEvents(payload: OrderTrackingPayload): OrderTrackingEvent[] {
  const t = payload.tracking ?? {};
  const events =
    t.timeline ?? t.events ?? t.history ?? t.progress ?? [];
  return Array.isArray(events) ? events : [];
}

function eventLabel(event: OrderTrackingEvent): string {
  return (
    event.step ?? event.label ?? event.title ?? event.status ?? event.description ?? "Update"
  );
}

function eventTime(event: OrderTrackingEvent): string | undefined {
  const raw = event.timestamp ?? event.time ?? event.date;
  if (!raw) {
    return undefined;
  }
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return raw;
  }
  return parsed.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function OrderTrackingCard({ payload }: OrderTrackingCardProps) {
  const tracking = payload.tracking ?? {};
  const status = tracking.status ?? tracking.order_status ?? "In progress";
  const recipientName = tracking.recipient?.name;
  const items = Array.isArray(tracking.items) ? tracking.items : [];
  const events = collectEvents(payload);

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="w-full overflow-hidden rounded-2xl rounded-bl-sm border border-[#402970]/15 bg-white shadow-[0_4px_16px_rgba(64,41,112,0.1)]"
    >
      <div className="border-b border-[#402970]/10 bg-[#F0EEFA] px-4 py-2.5 sm:px-5 sm:py-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-[#402970]">
          Order tracking
        </p>
        <h2 className="mt-0.5 text-lg font-bold text-[#222222]">
          Order #{payload.order_number}
        </h2>
      </div>

      <div className="space-y-4 p-4 sm:p-5">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-[#402970]/10 px-3 py-1 text-xs font-semibold text-[#402970]">
            {status}
          </span>
          {recipientName ? (
            <span className="text-xs text-[#494550]">For {recipientName}</span>
          ) : null}
        </div>

        {(tracking.amount?.value || tracking.payment_method || tracking.recipient?.phone || tracking.recipient?.address || tracking.comments || tracking.greeting_message || tracking.special_instructions) && (
          <div className="rounded-lg bg-[#F9F8FD] p-3 text-sm text-[#494550] space-y-2">
            {tracking.amount?.value && (
              <div className="flex justify-between">
                <span className="font-medium">Total Amount:</span>
                <span>{tracking.amount.currency} {tracking.amount.value}</span>
              </div>
            )}
            {tracking.payment_method && (
              <div className="flex justify-between">
                <span className="font-medium">Payment Method:</span>
                <span>{tracking.payment_method}</span>
              </div>
            )}
            {tracking.recipient?.phone && (
              <div className="flex justify-between">
                <span className="font-medium">Phone:</span>
                <span dangerouslySetInnerHTML={{ __html: tracking.recipient.phone }} />
              </div>
            )}
            {tracking.recipient?.address && (
              <div className="flex justify-between gap-4">
                <span className="font-medium whitespace-nowrap">Address:</span>
                <span className="text-right truncate">{tracking.recipient.address}</span>
              </div>
            )}
            {tracking.recipient?.city && (
              <div className="flex justify-between">
                <span className="font-medium">City:</span>
                <span>{tracking.recipient.city}</span>
              </div>
            )}
            {tracking.comments && (
              <div className="flex flex-col gap-0.5">
                <span className="font-medium">Comments:</span>
                <span className="text-xs">{tracking.comments}</span>
              </div>
            )}
            {tracking.greeting_message && (
              <div className="flex flex-col gap-0.5">
                <span className="font-medium">Greeting Message:</span>
                <span className="text-xs italic">"{tracking.greeting_message}"</span>
              </div>
            )}
            {tracking.special_instructions && (
              <div className="flex flex-col gap-0.5">
                <span className="font-medium">Special Instructions:</span>
                <span className="text-xs">{tracking.special_instructions}</span>
              </div>
            )}
          </div>
        )}

        {items.length > 0 ? (
          <ul className="space-y-1 text-sm text-[#494550]">
            {items.map((item, index) => (
              <li key={`${item.name ?? "item"}-${index}`} className="flex justify-between gap-3">
                <span className="truncate">{item.name ?? "Item"}</span>
                {item.quantity ? <span>×{item.quantity}</span> : null}
              </li>
            ))}
          </ul>
        ) : null}

        {events.length > 0 ? (
          <ol className="relative space-y-4 border-l border-[#402970]/15 pl-5">
            {events.map((event, index) => {
              const isLatest = index === events.length - 1;
              const time = eventTime(event);
              return (
                <li key={`${eventLabel(event)}-${index}`} className="relative">
                  <span
                    className={`absolute -left-[1.45rem] top-1 flex h-3 w-3 items-center justify-center rounded-full ${
                      isLatest ? "bg-[#FBD614] ring-2 ring-[#402970]/20" : "bg-[#402970]"
                    }`}
                  />
                  <p className="text-sm font-medium text-[#222222]">{eventLabel(event)}</p>
                  {event.description && event.description !== eventLabel(event) ? (
                    <p className="mt-0.5 text-xs text-[#494550]">{event.description}</p>
                  ) : null}
                  {time ? <p className="mt-0.5 text-[11px] text-[#494550]/70">{time}</p> : null}
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="text-sm text-[#494550]">
            We're fetching the latest delivery updates for this order.
          </p>
        )}
      </div>
    </motion.section>
  );
}
