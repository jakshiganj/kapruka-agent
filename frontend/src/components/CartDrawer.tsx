import type { CartItem, CheckoutCartSnapshot, DeliveryInfo } from "../types";

interface CartDrawerProps {
  open: boolean;
  cart: CartItem[];
  delivery?: DeliveryInfo;
  checkoutStale?: boolean;
  checkoutSnapshot?: CheckoutCartSnapshot;
  onClose: () => void;
  onRequestNewLink?: () => void;
}

function lineTotal(item: CartItem): number {
  return item.price * item.quantity;
}

function cartDiffersFromSnapshot(
  cart: CartItem[],
  snapshot?: CheckoutCartSnapshot,
): boolean {
  if (!snapshot?.lines?.length) {
    return false;
  }
  const live = cart
    .map((item) => `${item.product_id}:${item.quantity}`)
    .sort()
    .join("|");
  const frozen = snapshot.lines
    .map((line) => `${line.product_id}:${line.quantity}`)
    .sort()
    .join("|");
  return live !== frozen;
}

export function CartDrawer({
  open,
  cart,
  delivery,
  checkoutStale = false,
  checkoutSnapshot,
  onClose,
  onRequestNewLink,
}: CartDrawerProps) {
  const subtotal = cart.reduce((sum, item) => sum + lineTotal(item), 0);
  const deliveryFee =
    delivery?.validated === "true" && delivery.delivery_rate
      ? Number(delivery.delivery_rate)
      : 0;
  const total = subtotal + (Number.isFinite(deliveryFee) ? deliveryFee : 0);
  const showStaleWarning =
    checkoutStale || cartDiffersFromSnapshot(cart, checkoutSnapshot);

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden={!open}
      />
      <aside
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-white/10 bg-slate-950/95 shadow-2xl backdrop-blur transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        aria-hidden={!open}
      >
        <header className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Gift cart</h2>
            <p className="text-xs text-slate-400">{cart.length} item{cart.length !== 1 ? "s" : ""}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-1 text-sm text-slate-400 hover:bg-white/5 hover:text-white"
          >
            Close
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {cart.length === 0 ? (
            <p className="text-slate-400">Your cart is empty. Browse Kapruka picks and tap one to add it.</p>
          ) : (
            <ul className="space-y-3">
              {cart.map((item) => (
                <li
                  key={item.product_id}
                  className="flex gap-3 rounded-xl border border-white/10 bg-white/5 p-3"
                >
                  <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-2xl">
                    {item.perishable_flag ? "🎂" : "🎁"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-white">{item.name}</p>
                    <p className="mt-0.5 text-xs text-slate-400">
                      Qty {item.quantity}
                      {item.perishable_flag ? " · Fresh item" : ""}
                    </p>
                    <p className="mt-1 font-semibold text-emerald-300">
                      LKR {lineTotal(item).toLocaleString()}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <footer className="space-y-2 border-t border-white/10 px-5 py-4">
          {showStaleWarning ? (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              Cart changed since your last payment link. Say checkout for a fresh link.
              {onRequestNewLink ? (
                <button
                  type="button"
                  onClick={onRequestNewLink}
                  className="mt-2 block font-semibold text-amber-100 underline underline-offset-2"
                >
                  Get new payment link
                </button>
              ) : null}
            </div>
          ) : null}
          <div className="flex justify-between text-sm text-slate-400">
            <span>Items</span>
            <span>LKR {subtotal.toLocaleString()}</span>
          </div>
          {deliveryFee > 0 ? (
            <div className="flex justify-between text-sm text-slate-400">
              <span>Delivery to {delivery?.city}</span>
              <span>LKR {deliveryFee.toLocaleString()}</span>
            </div>
          ) : null}
          <div className="flex items-center justify-between border-t border-white/10 pt-3 text-white">
            <span className="font-medium">Estimated total</span>
            <span className="text-xl font-bold text-emerald-300">LKR {total.toLocaleString()}</span>
          </div>
        </footer>
      </aside>
    </>
  );
}
