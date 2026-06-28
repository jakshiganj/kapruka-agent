import type { OrderStep, SessionSnapshot } from "../types";

const STEPS: { id: OrderStep; label: string }[] = [
  { id: "discover", label: "Discover" },
  { id: "cart", label: "Cart" },
  { id: "delivery", label: "Delivery" },
  { id: "checkout", label: "Checkout" },
];

function currentStep(session: SessionSnapshot, action: string | null): OrderStep {
  if (action === "show_checkout" || session.checkout_info?.recipient?.name) {
    return "checkout";
  }
  if (session.delivery_info?.validated === "true") {
    return "checkout";
  }
  if (session.delivery_info?.city && session.delivery_info?.date) {
    return "delivery";
  }
  if (session.cart.length > 0) {
    return "cart";
  }
  if (session.products.length > 0) {
    return "discover";
  }
  return "discover";
}

interface OrderProgressProps {
  session: SessionSnapshot;
  action: string | null;
}

export function OrderProgress({ session, action }: OrderProgressProps) {
  const active = currentStep(session, action);
  const activeIndex = STEPS.findIndex((s) => s.id === active);

  return (
    <nav
      aria-label="Order progress"
      className="flex flex-wrap items-center justify-center gap-1 sm:gap-1.5 md:gap-0"
    >
      {STEPS.map((step, index) => {
        const done = index < activeIndex;
        const current = index === activeIndex;
        return (
          <div key={step.id} className="flex items-center">
            <div
              className={`flex items-center gap-1.5 rounded-full px-2 py-1 text-[10px] font-medium transition-colors sm:gap-2 sm:px-3 sm:py-1.5 sm:text-xs ${
                current
                  ? "bg-[#402970]/10 text-[#402970] ring-1 ring-[#402970]/25"
                  : done
                    ? "text-[#402970]"
                    : "text-[#494550]/45"
              }`}
            >
              <span
                className={`flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold sm:h-5 sm:w-5 sm:text-[10px] ${
                  done
                    ? "bg-[#402970] text-white"
                    : current
                      ? "bg-[#FBD614] text-[#222222]"
                      : "bg-[#402970]/10 text-[#402970]/50"
                }`}
              >
                {done ? "✓" : index + 1}
              </span>
              {step.label}
            </div>
            {index < STEPS.length - 1 ? (
              <div
                className={`mx-1 hidden h-px w-6 md:block ${
                  done ? "bg-[#402970]/40" : "bg-[#402970]/12"
                }`}
              />
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}
