import { motion } from "framer-motion";

export interface CategorySuggestion {
  emoji: string;
  title: string;
  hint: string;
}

export const DEFAULT_CATEGORIES: CategorySuggestion[] = [
  { emoji: "🎂", title: "Cakes & treats", hint: "Machan, chocolate cake ekak ඕනේ" },
  { emoji: "💐", title: "Flowers", hint: "Birthday flowers for amma" },
  { emoji: "🎁", title: "Gift under 5000", hint: "Show me gifts under Rs. 5,000" },
  { emoji: "📦", title: "Track my order", hint: "Track my order" },
];

interface CategoryChipsProps {
  categories?: CategorySuggestion[];
  onSelect?: (hint: string) => void;
  disabled?: boolean;
  layout?: "grid" | "row";
}

export function CategoryChips({
  categories = DEFAULT_CATEGORIES,
  onSelect,
  disabled = false,
  layout = "grid",
}: CategoryChipsProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.08 } },
      }}
      className={
        layout === "grid"
          ? "grid w-full max-w-lg gap-3 sm:grid-cols-2"
          : "flex flex-wrap justify-center gap-2"
      }
    >
      {categories.map((cat) => (
        <motion.button
          key={cat.title}
          type="button"
          disabled={disabled || !onSelect}
          onClick={() => onSelect?.(cat.hint)}
          variants={{
            hidden: { opacity: 0, y: 12 },
            visible: { opacity: 1, y: 0 },
          }}
          whileHover={disabled ? undefined : { scale: 1.02 }}
          whileTap={disabled ? undefined : { scale: 0.98 }}
          className={`group rounded-2xl border border-[#402970]/12 bg-white px-3.5 py-3.5 text-left shadow-[0_2px_12px_rgba(64,41,112,0.05)] transition-all sm:px-4 sm:py-4 ${
            layout === "row" ? "min-w-[140px] flex-1" : ""
          } ${disabled ? "cursor-default opacity-70" : "cursor-pointer hover:border-[#402970]/25 hover:bg-[#F0EEFA]/60 hover:shadow-[0_4px_16px_rgba(64,41,112,0.08)] active:scale-[0.98]"}`}
        >
          <span className="text-xl sm:text-2xl">{cat.emoji}</span>
          <p className="mt-1.5 text-xs font-semibold text-[#222222] sm:mt-2 sm:text-sm">{cat.title}</p>
          <p className="mt-1 text-xs leading-relaxed text-[#222222]/60 group-hover:text-[#222222]/80">
            &ldquo;{cat.hint}&rdquo;
          </p>
        </motion.button>
      ))}
    </motion.div>
  );
}
