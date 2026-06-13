import type { CheckoutInfo, CheckoutPayload } from "../types";

interface CheckoutCardProps {
  payload: CheckoutPayload;
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

export function CheckoutCard({ payload }: CheckoutCardProps) {
  const { checkout_url, order_ref, summary, expires_at, checkout_info, cart } = payload;
  const info = checkout_info as CheckoutInfo | undefined;

  return (
    <section className="mx-auto w-full max-w-lg overflow-hidden rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-950/60 to-slate-900/80 shadow-2xl">
      <div className="border-b border-emerald-500/20 bg-emerald-500/10 px-6 py-4">
        <p className="text-xs uppercase tracking-widest text-emerald-300">Ready to pay</p>
        <h2 className="mt-1 text-2xl font-bold text-white">Your Kapruka checkout</h2>
      </div>

      <div className="space-y-4 p-6">
        {cart && cart.length > 0 ? (
          <ul className="space-y-2 text-sm text-slate-300">
            {cart.map((item) => (
              <li key={item.product_id} className="flex justify-between gap-2">
                <span className="truncate">{item.name} × {item.quantity}</span>
                <span className="shrink-0 text-white">
                  LKR {(item.price * item.quantity).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        ) : null}

        {summary ? (
          <div className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm">
            {summary.items_total != null ? (
              <div className="flex justify-between text-slate-400">
                <span>Items</span>
                <span>LKR {summary.items_total.toLocaleString()}</span>
              </div>
            ) : null}
            {summary.delivery_fee != null ? (
              <div className="mt-1 flex justify-between text-slate-400">
                <span>Delivery</span>
                <span>LKR {summary.delivery_fee.toLocaleString()}</span>
              </div>
            ) : null}
            {summary.grand_total != null ? (
              <div className="mt-3 flex justify-between border-t border-white/10 pt-3 text-lg font-bold text-emerald-300">
                <span>Total</span>
                <span>{summary.currency ?? "LKR"} {summary.grand_total.toLocaleString()}</span>
              </div>
            ) : null}
          </div>
        ) : null}

        {info?.recipient?.name || info?.gift_message ? (
          <div className="rounded-xl border border-pink-500/20 bg-pink-950/20 p-4">
            <p className="text-xs uppercase tracking-wider text-pink-300">Gift details</p>
            {info.recipient?.name ? (
              <p className="mt-2 text-sm text-white">
                To: {info.recipient.name}
                {info.recipient.phone ? ` · ${info.recipient.phone}` : ""}
              </p>
            ) : null}
            {info.recipient?.address ? (
              <p className="text-xs text-slate-400">{info.recipient.address}</p>
            ) : null}
            {info.sender?.name ? (
              <p className="mt-1 text-xs text-slate-400">From: {info.sender.name}</p>
            ) : null}
            {info.gift_message ? (
              <blockquote className="mt-3 border-l-2 border-pink-400/50 pl-3 text-sm italic text-pink-100">
                &ldquo;{info.gift_message}&rdquo;
              </blockquote>
            ) : null}
          </div>
        ) : null}

        {order_ref ? (
          <p className="text-xs text-slate-500">
            Checkout ref: <span className="font-mono text-slate-300">{order_ref}</span>
            <span className="block mt-1">Final order number arrives by email after payment.</span>
          </p>
        ) : null}

        {expires_at ? (
          <p className="text-xs text-amber-200/80">Pay before {formatExpiry(expires_at)}</p>
        ) : null}

        {checkout_url ? (
          <a
            href={checkout_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex w-full items-center justify-center rounded-xl bg-emerald-500 px-4 py-3.5 text-center font-semibold text-slate-950 shadow-lg shadow-emerald-500/20 hover:bg-emerald-400"
          >
            Open secure checkout →
          </a>
        ) : (
          <p className="text-sm text-amber-300">Checkout link not available yet.</p>
        )}
      </div>
    </section>
  );
}
