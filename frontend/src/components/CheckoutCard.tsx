import type { CheckoutInfo, CheckoutPayload } from "../types";

interface CheckoutCardProps {
  payload: CheckoutPayload;
  inline?: boolean;
  stale?: boolean;
  onRequestNewLink?: () => void;
}

function formatExpiry(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export function CheckoutCard({
  payload,
  inline = false,
  stale = false,
  onRequestNewLink,
}: CheckoutCardProps) {
  const { checkout_url, order_ref, summary, expires_at, checkout_info, cart } = payload;
  const info = checkout_info as CheckoutInfo | undefined;
  const isStale = stale || payload.checkout_stale === true;

  return (
    <section
      className={`w-full overflow-hidden ${
        inline
          ? "rounded-2xl rounded-bl-sm border border-[#402970]/15 bg-white shadow-[0_4px_16px_rgba(64,41,112,0.1)]"
          : "mx-auto max-w-lg rounded-2xl border border-[#402970]/20 bg-white shadow-xl"
      }`}
    >
      <div className="border-b border-[#402970]/10 bg-[#F0EEFA] px-5 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-[#402970]">Ready to pay</p>
        <h2 className="mt-0.5 text-lg font-bold text-[#222222]">Your Kapruka checkout</h2>
      </div>

      <div className="space-y-3 p-5">
        {isStale ? (
          <div className="rounded-xl border border-[#6f5d00]/30 bg-[#fff8e0] px-4 py-3 text-sm text-[#6f5d00]">
            <p className="font-semibold">Cart changed — this link may be outdated</p>
            <p className="mt-1 text-xs text-[#494550]">
              Your cart has been updated since this link was created. Generate a new link before paying.
            </p>
            {onRequestNewLink ? (
              <button
                type="button"
                onClick={onRequestNewLink}
                className="mt-3 rounded-lg bg-[#FBD614] px-4 py-2 text-xs font-semibold text-[#222222] hover:bg-[#fdd818]"
              >
                Get new payment link
              </button>
            ) : null}
          </div>
        ) : null}

        {cart && cart.length > 0 ? (
          <ul className="space-y-1.5 text-sm text-[#494550]">
            {cart.map((item) => (
              <li key={item.product_id} className="flex justify-between gap-2">
                <span className="truncate">{item.name} × {item.quantity}</span>
                <span className="shrink-0 font-medium text-[#222222]">
                  LKR {(item.price * item.quantity).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        ) : null}

        {summary ? (
          <div className="rounded-xl border border-[#402970]/8 bg-[#fcf9f8] p-3 text-sm">
            {summary.items_total != null ? (
              <div className="flex justify-between text-[#494550]">
                <span>Items</span>
                <span>LKR {summary.items_total.toLocaleString()}</span>
              </div>
            ) : null}
            {summary.delivery_fee != null ? (
              <div className="mt-1 flex justify-between text-[#494550]">
                <span>Delivery</span>
                <span>LKR {summary.delivery_fee.toLocaleString()}</span>
              </div>
            ) : null}
            {summary.grand_total != null ? (
              <div className="mt-2 flex justify-between border-t border-[#402970]/8 pt-2 text-base font-bold text-[#402970]">
                <span>Total</span>
                <span>{summary.currency ?? "LKR"} {summary.grand_total.toLocaleString()}</span>
              </div>
            ) : null}
          </div>
        ) : null}

        {info?.recipient?.name || info?.gift_message ? (
          <div className="rounded-xl border border-[#402970]/8 bg-[#F0EEFA]/50 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-[#402970]">Gift details</p>
            {info.recipient?.name ? (
              <p className="mt-1.5 text-sm text-[#222222]">
                To: {info.recipient.name}
                {info.recipient.phone ? ` · ${info.recipient.phone}` : ""}
              </p>
            ) : null}
            {info.recipient?.address ? (
              <p className="text-xs text-[#494550]">{info.recipient.address}</p>
            ) : null}
            {info.sender?.name ? (
              <p className="mt-1 text-xs text-[#494550]">From: {info.sender.name}</p>
            ) : null}
            {info.gift_message ? (
              <blockquote className="mt-2 border-l-2 border-[#402970]/30 pl-3 text-sm italic text-[#494550]">
                &ldquo;{info.gift_message}&rdquo;
              </blockquote>
            ) : null}
          </div>
        ) : null}

        {order_ref ? (
          <p className="text-xs text-[#494550]/70">
            Checkout ref: <span className="font-mono text-[#222222]">{order_ref}</span>
          </p>
        ) : null}

        {expires_at ? (
          <p className="text-xs text-[#6f5d00]">Pay before {formatExpiry(expires_at)}</p>
        ) : null}

        {checkout_url ? (
          <a
            href={checkout_url}
            target="_blank"
            rel="noreferrer"
            className={`inline-flex w-full items-center justify-center rounded-xl px-4 py-3 text-center text-sm font-semibold shadow-sm ${
              isStale
                ? "pointer-events-none bg-[#eae7e7] text-[#494550]/60"
                : "bg-[#FBD614] text-[#222222] hover:bg-[#fdd818]"
            }`}
            aria-disabled={isStale}
          >
            {isStale ? "Link outdated — get a new one" : "Open secure checkout →"}
          </a>
        ) : (
          <p className="text-sm text-[#6f5d00]">Checkout link not available yet.</p>
        )}

        <p className="text-[11px] leading-relaxed text-[#494550]/70">
          After paying, your Kapruka order number arrives by email. Say
          {" "}
          <span className="font-medium text-[#402970]">&ldquo;track my order&rdquo;</span>
          {" "}with that number any time to see delivery progress.
        </p>
      </div>
    </section>
  );
}
