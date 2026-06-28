import { motion } from "framer-motion";
import { useState } from "react";
import type { Product } from "../types";

function ProductImage({ src, alt }: { src: string; alt: string }) {
  const [loaded, setLoaded] = useState(false);
  return (
    <>
      {!loaded ? (
        <div className="absolute inset-0 animate-pulse bg-[#402970]/8" />
      ) : null}
      <img
        src={src}
        alt={alt}
        onLoad={() => setLoaded(true)}
        className={`h-full w-full object-cover transition-opacity duration-300 ${
          loaded ? "opacity-100" : "opacity-0"
        }`}
        loading="lazy"
      />
    </>
  );
}

interface ProductCarouselProps {
  products: Product[];
  searchQuery?: string;
  selectedId?: string;
  pendingId?: string;
  error?: string;
  onSelect?: (product: Product) => void;
  onViewDetails?: (product: Product) => void;
  inline?: boolean;
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
  pendingId,
  error,
  onSelect,
  onViewDetails,
  inline = false,
}: ProductCarouselProps) {
  if (error) {
    return (
      <div
        className={`text-sm text-[#ba1a1a] ${
          inline
            ? "rounded-2xl rounded-bl-sm border border-[#ba1a1a]/20 bg-[#ffdad6] px-4 py-3"
            : "rounded-2xl border border-[#ba1a1a]/30 bg-[#ffdad6] p-6 text-center"
        }`}
      >
        {error}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div
        className={`text-[#494550] ${
          inline
            ? "rounded-2xl rounded-bl-sm border border-[#402970]/10 bg-[#F0EEFA] px-4 py-4"
            : "rounded-2xl border border-[#402970]/10 bg-[#F0EEFA] p-6 text-center"
        }`}
      >
        <p className="text-2xl">🎁</p>
        <p className="mt-2 text-sm">Tell Kapru what you&apos;d like to send — cake, flowers, hampers…</p>
        {searchQuery ? (
          <p className="mt-1 text-xs text-[#494550]/70">No results for &ldquo;{searchQuery}&rdquo;</p>
        ) : null}
      </div>
    );
  }

  return (
    <section className="w-full">
      {inline ? (
      <div className="mb-2 flex items-center justify-between gap-2 sm:mb-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-[#402970]/70 sm:text-xs">Kapruka picks</p>
            {searchQuery ? (
              <p className="text-[10px] text-[#494550] sm:text-xs">Results for &ldquo;{searchQuery}&rdquo;</p>
            ) : null}
          </div>
          <span className="rounded-full bg-[#402970]/8 px-2 py-0.5 text-[9px] font-medium text-[#402970] sm:px-2.5 sm:text-[10px]">
            {products.length} gifts
          </span>
        </div>
      ) : (
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-[#222222]">Kapruka picks</h2>
            {searchQuery ? (
              <p className="text-sm text-[#494550]">Results for &ldquo;{searchQuery}&rdquo;</p>
            ) : null}
            {onSelect ? (
              <p className="mt-1 text-xs text-[#402970]">Tap a gift to add it to your cart</p>
            ) : null}
          </div>
          <span className="rounded-full bg-[#402970]/8 px-3 py-1 text-xs text-[#402970]">
            {products.length} gifts
          </span>
        </div>
      )}

      <div className="relative">
      <div className="scrollbar-hide flex gap-2.5 overflow-x-auto pb-1 snap-x snap-mandatory sm:gap-3 sm:scrollbar-thin">
        {products.map((product, index) => {
          const selected = product.id === selectedId;
          const pending = product.id === pendingId;
          return (
            <motion.article
              key={product.id}
              initial={inline ? { opacity: 0, x: 12 } : false}
              animate={inline ? { opacity: 1, x: 0 } : false}
              transition={{ delay: index * 0.05, duration: 0.3 }}
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
              className={`snap-start shrink-0 w-52 overflow-hidden rounded-2xl border transition-all sm:w-64 ${
                inline ? "shadow-[0_4px_16px_rgba(64,41,112,0.08)]" : "shadow-xl"
              } ${
                selected
                  ? "border-[#402970]/40 bg-white ring-2 ring-[#402970]/20"
                  : "border-[#402970]/8 bg-white hover:border-[#402970]/15"
              } ${onSelect ? "cursor-pointer active:scale-[0.98] sm:hover:scale-[1.02]" : ""}`}
            >
              <div className="relative aspect-[4/3] bg-[#f0eded]">
                {product.image_url ? (
                  <ProductImage src={product.image_url} alt={product.name} />
                ) : (
                  <div className="flex h-full items-center justify-center text-4xl">🎂</div>
                )}
                {pending ? (
                  <span className="absolute left-2 top-2 rounded-full bg-gradient-to-r from-[#402970] to-[#5a3d8a] px-2 py-0.5 text-[9px] font-bold text-white sm:left-3 sm:top-3 sm:text-[10px]">
                    Adding…
                  </span>
                ) : selected ? (
                  <span className="absolute left-2 top-2 rounded-full bg-[#FBD614] px-2 py-0.5 text-[9px] font-bold text-[#222222] shadow-sm sm:left-3 sm:top-3 sm:text-[10px]">
                    Selected
                  </span>
                ) : null}
                {!product.in_stock ? (
                  <span className="absolute right-3 top-3 rounded-full bg-[#ba1a1a] px-2 py-0.5 text-[10px] font-bold text-white">
                    Out of stock
                  </span>
                ) : null}
              </div>
              <div className="space-y-1 p-2.5 sm:space-y-1.5 sm:p-3">
                <h3 className="line-clamp-2 text-xs font-medium text-[#222222] sm:text-sm">{product.name}</h3>
                {product.summary ? (
                  <p className="line-clamp-2 text-[10px] leading-relaxed text-[#494550] sm:text-xs">{product.summary}</p>
                ) : null}
                <p className="text-sm font-bold text-[#402970] sm:text-base">{formatPrice(product)}</p>
                <div className="flex items-center gap-2 pt-0.5 sm:gap-3">
                  {onViewDetails ? (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewDetails(product);
                      }}
                      className="text-xs font-medium text-[#402970] underline-offset-2 hover:underline"
                    >
                      Details
                    </button>
                  ) : null}
                  {product.url ? (
                    <a
                      href={product.url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-xs text-[#402970]/80 hover:text-[#402970]"
                    >
                      View on Kapruka →
                    </a>
                  ) : null}
                </div>
              </div>
            </motion.article>
          );
        })}
        </div>
      </div>
      {inline && onSelect ? (
        <p className="mt-1.5 text-[9px] text-[#494550]/60 sm:mt-2 sm:text-[10px]">Tap a gift to add it to your cart</p>
      ) : null}
    </section>
  );
}
