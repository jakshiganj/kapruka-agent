import type { KaprukaCategory } from "../types";

export interface CategoryMeta {
  mcpName: string;
  label: string;
  emoji: string;
  featured: boolean;
  sortOrder: number;
}

/** Curated gift categories — mirrors backend FEATURED_CATALOG for client-side enrichment. */
export const CATEGORY_CATALOG: CategoryMeta[] = [
  { mcpName: "cakes", label: "Cake Shop", emoji: "🎂", featured: true, sortOrder: 1 },
  { mcpName: "combopack", label: "Combo Gift Packs", emoji: "🎁", featured: true, sortOrder: 2 },
  { mcpName: "Chocolates", label: "Chocolates", emoji: "🍫", featured: true, sortOrder: 3 },
  { mcpName: "Clothing", label: "Clothing", emoji: "👕", featured: true, sortOrder: 4 },
  { mcpName: "Electronic", label: "Electronics", emoji: "📱", featured: true, sortOrder: 5 },
  { mcpName: "flowers", label: "Flower Shop", emoji: "💐", featured: true, sortOrder: 6 },
  { mcpName: "Food", label: "Food & Restaurants", emoji: "🍽️", featured: true, sortOrder: 7 },
  { mcpName: "Fruits", label: "Fruit Baskets", emoji: "🍎", featured: true, sortOrder: 8 },
  { mcpName: "Vegetables", label: "Veg Baskets", emoji: "🥬", featured: true, sortOrder: 9 },
  { mcpName: "Giftcert", label: "Gift Vouchers", emoji: "🎟️", featured: true, sortOrder: 10 },
  { mcpName: "Giftset", label: "Gift Sets", emoji: "🧺", featured: true, sortOrder: 11 },
  { mcpName: "Grocery", label: "Grocery", emoji: "🛒", featured: true, sortOrder: 12 },
  { mcpName: "GreetingCards", label: "Greeting Cards", emoji: "💌", featured: true, sortOrder: 13 },
  { mcpName: "Jewellery", label: "Jewelry & Watches", emoji: "💎", featured: true, sortOrder: 14 },
  { mcpName: "Personalized Gifts", label: "Personalized Gifts", emoji: "✨", featured: true, sortOrder: 15 },
  { mcpName: "Perfumes", label: "Perfumes", emoji: "🌸", featured: true, sortOrder: 16 },
  { mcpName: "Fashion", label: "Fashion & Shoes", emoji: "👗", featured: true, sortOrder: 17 },
  { mcpName: "Cosmetics", label: "Cosmetics", emoji: "💄", featured: true, sortOrder: 18 },
  { mcpName: "Books", label: "Books", emoji: "📚", featured: true, sortOrder: 19 },
  { mcpName: "Toys", label: "Toys", emoji: "🧸", featured: true, sortOrder: 20 },
  { mcpName: "baby", label: "Baby Gifts", emoji: "👶", featured: true, sortOrder: 21 },
  { mcpName: "birthday", label: "Birthday", emoji: "🎉", featured: true, sortOrder: 22 },
  { mcpName: "anniversary", label: "Anniversary", emoji: "💍", featured: true, sortOrder: 23 },
  { mcpName: "valentine", label: "Valentine", emoji: "❤️", featured: true, sortOrder: 24 },
  { mcpName: "mothersday", label: "Mother's Day", emoji: "🌷", featured: true, sortOrder: 25 },
  { mcpName: "fathersday", label: "Father's Day", emoji: "👔", featured: true, sortOrder: 26 },
  { mcpName: "Christmas", label: "Christmas", emoji: "🎄", featured: true, sortOrder: 27 },
  { mcpName: "newyear", label: "New Year", emoji: "🎆", featured: true, sortOrder: 28 },
  { mcpName: "Tea", label: "Tea & Beverages", emoji: "🍵", featured: true, sortOrder: 29 },
  { mcpName: "Health", label: "Health & Wellness", emoji: "💊", featured: true, sortOrder: 30 },
  { mcpName: "Home", label: "Home & Living", emoji: "🏠", featured: true, sortOrder: 31 },
  { mcpName: "Sports", label: "Sports", emoji: "⚽", featured: true, sortOrder: 32 },
  { mcpName: "Stationery", label: "Stationery", emoji: "✏️", featured: true, sortOrder: 33 },
  { mcpName: "plants", label: "Plants", emoji: "🪴", featured: true, sortOrder: 34 },
  { mcpName: "Pet", label: "Pet Gifts", emoji: "🐾", featured: true, sortOrder: 35 },
  { mcpName: "wesak", label: "Wesak", emoji: "🪷", featured: true, sortOrder: 36 },
  { mcpName: "deepawali", label: "Deepawali", emoji: "🪔", featured: true, sortOrder: 37 },
  { mcpName: "Musical Instruments", label: "Music", emoji: "🎵", featured: true, sortOrder: 38 },
  { mcpName: "Art", label: "Art & Crafts", emoji: "🎨", featured: true, sortOrder: 39 },
];

export const ICON_EMOJI: Record<string, string> = Object.fromEntries(
  CATEGORY_CATALOG.map((entry) => [entry.mcpName, entry.emoji]),
);

export const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  CATEGORY_CATALOG.map((entry) => [entry.mcpName, entry.label]),
);

const catalogByName = new Map(CATEGORY_CATALOG.map((entry) => [entry.mcpName, entry]));

function titleCase(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getCategoryLabel(name: string, fallback?: string): string {
  return CATEGORY_LABELS[name] ?? fallback ?? titleCase(name);
}

export function getCategoryEmoji(name: string): string {
  return ICON_EMOJI[name] ?? "🎁";
}

export function enrichCategory(category: KaprukaCategory): KaprukaCategory {
  const meta = catalogByName.get(category.name);
  return {
    ...category,
    label: category.label ?? meta?.label ?? getCategoryLabel(category.name),
    emoji: category.emoji ?? meta?.emoji ?? getCategoryEmoji(category.name),
    children: category.children?.map(enrichCategory),
  };
}

export function enrichCategories(categories: KaprukaCategory[]): KaprukaCategory[] {
  return categories.map(enrichCategory);
}

export function featuredCategories(categories: KaprukaCategory[]): KaprukaCategory[] {
  const featuredNames = new Set(
    CATEGORY_CATALOG.filter((entry) => entry.featured).map((entry) => entry.mcpName),
  );
  const enriched = enrichCategories(categories);
  const filtered = enriched.filter((cat) => featuredNames.has(cat.name));
  return filtered.sort((a, b) => {
    const orderA = catalogByName.get(a.name)?.sortOrder ?? 999;
    const orderB = catalogByName.get(b.name)?.sortOrder ?? 999;
    return orderA - orderB;
  });
}
