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
      className="flex flex-wrap items-center justify-center gap-2 md:gap-0"
    >
      {STEPS.map((step, index) => {
        const done = index < activeIndex;
        const current = index === activeIndex;
        return (
          <div key={step.id} className="flex items-center">
            <div
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                current
                  ? "bg-emerald-500/20 text-emerald-200 ring-1 ring-emerald-400/40"
                  : done
                    ? "bg-white/10 text-white"
                    : "text-slate-500"
              }`}
            >
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${
                  done ? "bg-emerald-500 text-slate-950" : current ? "bg-emerald-400 text-slate-950" : "bg-slate-800"
                }`}
              >
                {done ? "✓" : index + 1}
              </span>
              {step.label}
            </div>
            {index < STEPS.length - 1 ? (
              <div className={`mx-1 hidden h-px w-6 md:block ${done ? "bg-emerald-500/50" : "bg-white/10"}`} />
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}
