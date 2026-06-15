import type { Translator } from "../i18n";
import type { CartItem, CheckoutCartSnapshot, DeliveryInfo } from "../types";

export type CartItemOp = "increment" | "decrement" | "remove";

interface CartDrawerProps {
  t: Translator;
  open: boolean;
  cart: CartItem[];
  delivery?: DeliveryInfo;
  checkoutStale?: boolean;
  checkoutSnapshot?: CheckoutCartSnapshot;
  onClose: () => void;
  onRequestNewLink?: () => void;
  onUpdateItem?: (productId: string, op: CartItemOp) => void;
  onProceedCheckout?: () => void;
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

function QtyButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={!onClick}
      className="flex h-7 w-7 items-center justify-center rounded-full border border-[#402970]/15 bg-white text-[#402970] transition-colors hover:bg-[#F0EEFA] disabled:cursor-not-allowed disabled:opacity-40"
    >
      {children}
    </button>
  );
}

export function CartDrawer({
  t,
  open,
  cart,
  delivery,
  checkoutStale = false,
  checkoutSnapshot,
  onClose,
  onRequestNewLink,
  onUpdateItem,
  onProceedCheckout,
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
        className={`fixed inset-0 z-40 bg-[#1b1c1c]/40 backdrop-blur-sm transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden={!open}
      />
      <aside
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-[#402970]/10 bg-[#fcf9f8] shadow-2xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
        aria-hidden={!open}
      >
        <header className="flex items-center justify-between border-b border-[#402970]/10 bg-white px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-[#222222]">{t("cart.title")}</h2>
            <p className="text-xs text-[#494550]">
              {cart.length} item{cart.length !== 1 ? "s" : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-1 text-sm text-[#494550] hover:bg-[#F0EEFA] hover:text-[#402970]"
          >
            {t("cart.close")}
          </button>
        </header>

        <div className="scrollbar-thin flex-1 overflow-y-auto px-5 py-4">
          {cart.length === 0 ? (
            <div className="mt-10 text-center text-[#494550]">
              <p className="text-3xl">🎁</p>
              <p className="mt-3 text-sm">{t("cart.empty")}</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {cart.map((item) => (
                <li
                  key={item.product_id}
                  className="flex gap-3 rounded-2xl border border-[#402970]/10 bg-white p-3 shadow-[0_2px_8px_rgba(64,41,112,0.05)]"
                >
                  <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-[#F0EEFA]">
                    {item.image_url ? (
                      <img
                        src={item.image_url}
                        alt={item.name}
                        className="h-full w-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-2xl">
                        {item.perishable_flag ? "🎂" : "🎁"}
                      </div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-[#222222]">{item.name}</p>
                    {item.perishable_flag ? (
                      <p className="mt-0.5 text-[11px] text-[#6f5d00]">Fresh item</p>
                    ) : null}
                    <p className="mt-1 font-semibold text-[#402970]">
                      LKR {lineTotal(item).toLocaleString()}
                    </p>
                    <div className="mt-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <QtyButton
                          label={`Decrease ${item.name}`}
                          onClick={
                            onUpdateItem
                              ? () => onUpdateItem(item.product_id, "decrement")
                              : undefined
                          }
                        >
                          −
                        </QtyButton>
                        <span className="min-w-5 text-center text-sm font-semibold text-[#222222]">
                          {item.quantity}
                        </span>
                        <QtyButton
                          label={`Increase ${item.name}`}
                          onClick={
                            onUpdateItem
                              ? () => onUpdateItem(item.product_id, "increment")
                              : undefined
                          }
                        >
                          +
                        </QtyButton>
                      </div>
                      {onUpdateItem ? (
                        <button
                          type="button"
                          onClick={() => onUpdateItem(item.product_id, "remove")}
                          className="text-xs font-medium text-[#ba1a1a] hover:underline"
                        >
                          {t("cart.remove")}
                        </button>
                      ) : null}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <footer className="space-y-2 border-t border-[#402970]/10 bg-white px-5 py-4">
          {showStaleWarning ? (
            <div className="rounded-xl border border-[#6f5d00]/30 bg-[#fff8e0] px-3 py-2 text-xs text-[#6f5d00]">
              Cart changed since your last payment link. Say checkout for a fresh link.
              {onRequestNewLink ? (
                <button
                  type="button"
                  onClick={onRequestNewLink}
                  className="mt-2 block font-semibold text-[#402970] underline underline-offset-2"
                >
                  Get new payment link
                </button>
              ) : null}
            </div>
          ) : null}
          <div className="flex justify-between text-sm text-[#494550]">
            <span>{t("cart.items")}</span>
            <span>LKR {subtotal.toLocaleString()}</span>
          </div>
          {deliveryFee > 0 ? (
            <div className="flex justify-between text-sm text-[#494550]">
              <span>{t("cart.delivery")} {delivery?.city}</span>
              <span>LKR {deliveryFee.toLocaleString()}</span>
            </div>
          ) : null}
          <div className="flex items-center justify-between border-t border-[#402970]/10 pt-3 text-[#222222]">
            <span className="font-medium">{t("cart.total")}</span>
            <span className="text-xl font-bold text-[#402970]">LKR {total.toLocaleString()}</span>
          </div>
          {onProceedCheckout && cart.length > 0 ? (
            <button
              type="button"
              onClick={onProceedCheckout}
              className="mt-2 w-full rounded-xl bg-[#402970] px-4 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#2a1059]"
            >
              Proceed to checkout
            </button>
          ) : null}
        </footer>
      </aside>
    </>
  );
}
