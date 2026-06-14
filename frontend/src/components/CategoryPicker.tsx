import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import { getCategoryLabel } from "../data/categoryCatalog";
import type { KaprukaCategory } from "../types";

interface CategoryPickerProps {
  categories: KaprukaCategory[];
  onSelectCategory?: (category: string, subcategory?: string) => void;
  disabled?: boolean;
  loading?: boolean;
  compact?: boolean;
}

function normalizeSearch(value: string): string {
  return value.trim().toLowerCase();
}

function matchesSearch(text: string, query: string): boolean {
  return normalizeSearch(text).includes(query);
}

function filterCategories(
  categories: KaprukaCategory[],
  query: string,
): KaprukaCategory[] {
  if (!query) {
    return categories;
  }
  const normalized = normalizeSearch(query);
  return categories
    .map((parent) => {
      const parentLabel = parent.label ?? getCategoryLabel(parent.name);
      const parentMatch =
        matchesSearch(parent.name, normalized) || matchesSearch(parentLabel, normalized);
      const matchingChildren = (parent.children ?? []).filter((child) => {
        const childLabel = child.label ?? getCategoryLabel(child.name);
        return (
          matchesSearch(child.name, normalized) || matchesSearch(childLabel, normalized)
        );
      });
      if (parentMatch) {
        return parent;
      }
      if (matchingChildren.length > 0) {
        return { ...parent, children: matchingChildren };
      }
      return null;
    })
    .filter((cat): cat is KaprukaCategory => cat !== null);
}

function CategorySkeleton({ compact }: { compact?: boolean }) {
  const count = compact ? 10 : 15;
  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="flex flex-col items-center gap-2">
          <div
            className={`animate-pulse rounded-full bg-[#402970]/10 ${
              compact ? "h-12 w-12" : "h-14 w-14"
            }`}
          />
          <div className="h-3 w-12 animate-pulse rounded bg-[#402970]/8" />
        </div>
      ))}
    </div>
  );
}

export function CategoryPicker({
  categories,
  onSelectCategory,
  disabled = false,
  loading = false,
  compact = false,
}: CategoryPickerProps) {
  const [search, setSearch] = useState("");
  const [expandedParent, setExpandedParent] = useState<string | null>(null);
  const [brokenIcons, setBrokenIcons] = useState<Set<string>>(() => new Set());

  const filtered = useMemo(
    () => filterCategories(categories, search),
    [categories, search],
  );

  const expandedCategory = filtered.find((cat) => cat.name === expandedParent);

  const handleParentTap = (category: KaprukaCategory) => {
    if (disabled || !onSelectCategory) {
      return;
    }
    const children = category.children ?? [];
    if (children.length > 0) {
      setExpandedParent((prev) => (prev === category.name ? null : category.name));
      return;
    }
    onSelectCategory(category.name);
  };

  const handleSubcategoryTap = (parent: KaprukaCategory, subcategory: KaprukaCategory) => {
    if (disabled || !onSelectCategory) {
      return;
    }
    onSelectCategory(parent.name, subcategory.name);
  };

  return (
    <div
      className={`w-full rounded-2xl border border-[#402970]/12 bg-white ${
        compact ? "px-3 py-3" : "px-4 py-4 shadow-[0_2px_12px_rgba(64,41,112,0.06)]"
      }`}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-[#222222]">Browse Kapruka</p>
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search categories…"
          disabled={disabled || loading}
          className="w-36 rounded-full border border-[#402970]/12 bg-[#F0EEFA]/60 px-3 py-1.5 text-xs text-[#222222] placeholder:text-[#494550]/50 focus:border-[#402970]/30 focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#402970]/10 disabled:opacity-50 sm:w-44"
        />
      </div>

      {loading ? (
        <CategorySkeleton compact={compact} />
      ) : filtered.length === 0 ? (
        <p className="py-6 text-center text-sm text-[#494550]">
          No categories match &ldquo;{search}&rdquo;
        </p>
      ) : (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
          {filtered.map((category) => {
            const label = category.label ?? getCategoryLabel(category.name);
            const isExpanded = expandedParent === category.name;
            const iconSize = compact ? "h-12 w-12 text-xl" : "h-14 w-14 text-2xl";
            const showEmoji = !category.iconUrl || brokenIcons.has(category.name);

            return (
              <motion.button
                key={category.name}
                type="button"
                disabled={disabled || !onSelectCategory}
                onClick={() => handleParentTap(category)}
                whileHover={disabled ? undefined : { scale: 1.03 }}
                whileTap={disabled ? undefined : { scale: 0.97 }}
                className={`group flex flex-col items-center gap-1.5 rounded-xl p-1 transition-colors ${
                  disabled ? "cursor-default opacity-70" : "cursor-pointer hover:bg-[#F0EEFA]/50"
                }`}
              >
                <div
                  className={`flex items-center justify-center rounded-full bg-[#F0EEFA] shadow-[inset_0_0_0_1px_rgba(64,41,112,0.08)] transition-all ${iconSize} ${
                    isExpanded
                      ? "ring-2 ring-[#402970] ring-offset-2"
                      : "group-hover:ring-2 group-hover:ring-[#402970]/30 group-hover:ring-offset-1"
                  }`}
                >
                  {showEmoji ? (
                    <span aria-hidden>{category.emoji ?? "🎁"}</span>
                  ) : (
                    <img
                      src={category.iconUrl}
                      alt=""
                      className="h-full w-full rounded-full object-cover"
                      onError={() =>
                        setBrokenIcons((prev) => new Set(prev).add(category.name))
                      }
                    />
                  )}
                </div>
                <span className="w-full truncate px-0.5 text-center text-[11px] font-medium leading-tight text-[#222222]">
                  {label}
                </span>
              </motion.button>
            );
          })}
        </div>
      )}

      <AnimatePresence>
        {expandedCategory && (expandedCategory.children?.length ?? 0) > 0 ? (
          <motion.div
            key={expandedCategory.name}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-3 border-t border-[#402970]/10 pt-3">
              <p className="mb-2 text-xs font-semibold text-[#402970]">
                {expandedCategory.label ?? getCategoryLabel(expandedCategory.name)}
              </p>
              <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
                {expandedCategory.children?.map((child) => (
                  <button
                    key={child.name}
                    type="button"
                    disabled={disabled || !onSelectCategory}
                    onClick={() => handleSubcategoryTap(expandedCategory, child)}
                    className="shrink-0 rounded-full border border-[#402970]/20 bg-white px-3 py-1.5 text-xs font-medium text-[#402970] transition-colors hover:border-[#402970]/40 hover:bg-[#F0EEFA] disabled:opacity-50"
                  >
                    {child.label ?? getCategoryLabel(child.name)}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
