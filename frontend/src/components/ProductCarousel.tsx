import type { Product } from "../types";

interface ProductCarouselProps {
  products: Product[];
  searchQuery?: string;
  selectedId?: string;
  error?: string;
  onSelect?: (product: Product) => void;
}

function formatPrice(product: Product): string {
  const amount = product.price?.amount;
  const currency = product.price?.currency ?? "LKR";
  if (amount == null) {
    return "Price on request";
  }
  return `${currency} ${amount.toLocaleString()}`;
}

export function ProductCarousel({
  products,
  searchQuery,
  selectedId,
  error,
  onSelect,
}: ProductCarouselProps) {
  if (error) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-950/20 p-8 text-center text-red-200">
        {error}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-slate-300">
        <p className="text-4xl">🎁</p>
        <p className="mt-3">Tell Kapru what you&apos;d like to send — cake, flowers, hampers…</p>
        {searchQuery ? (
          <p className="mt-2 text-sm text-slate-500">No results for &ldquo;{searchQuery}&rdquo;</p>
        ) : null}
      </div>
    );
  }

  return (
    <section className="w-full">
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-white">Kapruka picks</h2>
          {searchQuery ? (
            <p className="text-sm text-slate-400">Results for &ldquo;{searchQuery}&rdquo;</p>
          ) : null}
          {onSelect ? (
            <p className="mt-1 text-xs text-emerald-300/90">Tap a gift to add it to your cart</p>
          ) : null}
        </div>
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-300">
          {products.length} gifts
        </span>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory scrollbar-thin">
        {products.map((product) => {
          const selected = product.id === selectedId;
          return (
            <article
              key={product.id}
              role={onSelect ? "button" : undefined}
              tabIndex={onSelect ? 0 : undefined}
              onClick={onSelect ? () => onSelect(product) : undefined}
              onKeyDown={
                onSelect
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(product);
                      }
                    }
                  : undefined
              }
              className={`snap-start shrink-0 w-72 overflow-hidden rounded-2xl border shadow-xl transition-transform hover:scale-[1.02] ${
                selected
                  ? "border-emerald-400/50 bg-emerald-950/40 ring-2 ring-emerald-400/30"
                  : "border-white/10 bg-slate-900/80"
              } ${onSelect ? "cursor-pointer" : ""}`}
            >
              <div className="relative aspect-[4/3] bg-slate-800">
                {product.image_url ? (
                  <img
                    src={product.image_url}
                    alt={product.name}
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-4xl">🎂</div>
                )}
                {selected ? (
                  <span className="absolute left-3 top-3 rounded-full bg-emerald-500 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-950">
                    Selected
                  </span>
                ) : null}
                {!product.in_stock ? (
                  <span className="absolute right-3 top-3 rounded-full bg-red-500/80 px-2 py-0.5 text-[10px] font-bold text-white">
                    Out of stock
                  </span>
                ) : null}
              </div>
              <div className="space-y-2 p-4">
                <h3 className="line-clamp-2 font-medium text-white">{product.name}</h3>
                {product.summary ? (
                  <p className="line-clamp-2 text-xs leading-relaxed text-slate-400">{product.summary}</p>
                ) : null}
                <p className="text-xl font-bold text-emerald-300">{formatPrice(product)}</p>
                {product.url ? (
                  <a
                    href={product.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block text-xs text-sky-400 hover:text-sky-300"
                  >
                    View on Kapruka →
                  </a>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
