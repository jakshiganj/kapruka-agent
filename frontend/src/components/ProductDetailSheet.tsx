import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import type { Product } from "../types";

interface ProductVariant {
  name?: string;
  label?: string;
  price?: { amount?: number | null; currency?: string } | number;
}

interface ProductDetail {
  id?: string;
  name?: string;
  summary?: string;
  description?: string;
  price?: { amount?: number | null; currency?: string };
  in_stock?: boolean;
  image_url?: string | null;
  images?: string[];
  url?: string;
  variants?: ProductVariant[];
  shipping?: string;
  shipping_info?: string;
}

interface ProductDetailSheetProps {
  product: Product;
  onClose: () => void;
  onAddToCart: (product: Product) => void;
}

function formatAmount(
  price: { amount?: number | null; currency?: string } | number | undefined,
): string | null {
  if (price == null) {
    return null;
  }
  if (typeof price === "number") {
    return `LKR ${price.toLocaleString()}`;
  }
  if (price.amount == null) {
    return null;
  }
  return `${price.currency ?? "LKR"} ${price.amount.toLocaleString()}`;
}

export function ProductDetailSheet({ product, onClose, onAddToCart }: ProductDetailSheetProps) {
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/product/${encodeURIComponent(product.id)}`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: { product?: ProductDetail; error?: string }) => {
        if (cancelled) return;
        if (data.error || !data.product) {
          setError(data.error ?? "Could not load product details.");
        } else {
          setDetail(data.product);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Could not load product details right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [product.id]);

  const name = detail?.name ?? product.name;
  const summary = detail?.description ?? detail?.summary ?? product.summary;
  const priceText = formatAmount(detail?.price) ?? formatAmount(product.price);
  const inStock = detail?.in_stock ?? product.in_stock;
  const heroImage = detail?.images?.[0] ?? detail?.image_url ?? product.image_url;
  const gallery = detail?.images?.slice(0, 4) ?? (heroImage ? [heroImage] : []);
  const variants = detail?.variants ?? [];
  const shipping = detail?.shipping ?? detail?.shipping_info;
  const productUrl = detail?.url ?? product.url;

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-end justify-center bg-[#1b1c1c]/40 backdrop-blur-sm sm:items-center"
        onClick={onClose}
      >
        <motion.div
          initial={{ y: 40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 40, opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          onClick={(e) => e.stopPropagation()}
          className="scrollbar-thin max-h-[95vh] w-full max-w-lg overflow-y-auto rounded-t-3xl bg-[#fcf9f8] shadow-2xl sm:max-h-[88vh] sm:rounded-3xl"
          style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
          role="dialog"
          aria-label={name}
        >
          <div className="relative">
            <div className="aspect-[4/3] w-full overflow-hidden bg-[#F0EEFA]">
              {heroImage ? (
                <img src={heroImage} alt={name} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center text-5xl">🎁</div>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="absolute right-3 top-3 flex h-10 w-10 items-center justify-center rounded-full bg-white/90 text-[#402970] shadow-lg backdrop-blur-sm transition-all hover:bg-white hover:shadow-xl sm:right-4 sm:top-4 sm:h-9 sm:w-9"
            >
              ✕
            </button>
          </div>

          <div className="space-y-4 p-4 sm:p-5">
            {gallery.length > 1 ? (
              <div className="flex gap-2 overflow-x-auto">
                {gallery.map((img, i) => (
                  <img
                    key={`${img}-${i}`}
                    src={img}
                    alt={`${name} ${i + 1}`}
                    className="h-14 w-14 shrink-0 rounded-lg object-cover sm:h-16 sm:w-16"
                    loading="lazy"
                  />
                ))}
              </div>
            ) : null}

            <div>
              <h2 className="text-xl font-bold text-[#222222]">{name}</h2>
              <div className="mt-1.5 flex items-center gap-2">
                {priceText ? (
                  <span className="text-base font-bold text-[#402970] sm:text-lg">{priceText}</span>
                ) : null}
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                    inStock
                      ? "bg-[#402970]/10 text-[#402970]"
                      : "bg-[#ba1a1a]/10 text-[#ba1a1a]"
                  }`}
                >
                  {inStock ? "In stock" : "Out of stock"}
                </span>
              </div>
            </div>

            {loading ? (
              <div className="space-y-2">
                <div className="h-3 w-full animate-pulse rounded bg-[#402970]/10" />
                <div className="h-3 w-4/5 animate-pulse rounded bg-[#402970]/10" />
                <div className="h-3 w-2/3 animate-pulse rounded bg-[#402970]/10" />
              </div>
            ) : null}

            {error ? <p className="text-sm text-[#ba1a1a]">{error}</p> : null}

            {summary ? (
              <p className="text-sm leading-relaxed text-[#494550]">{summary}</p>
            ) : null}

            {variants.length > 0 ? (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[#402970]/70">
                  Options
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {variants.map((variant, i) => (
                    <span
                      key={`${variant.name ?? variant.label ?? "variant"}-${i}`}
                      className="rounded-full border border-[#402970]/15 bg-white px-3 py-1 text-xs text-[#402970]"
                    >
                      {variant.label ?? variant.name ?? "Option"}
                      {formatAmount(variant.price) ? ` · ${formatAmount(variant.price)}` : ""}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            {shipping ? (
              <p className="rounded-xl border border-[#402970]/8 bg-[#F0EEFA]/50 p-3 text-xs text-[#494550]">
                {shipping}
              </p>
            ) : null}

            <div className="flex flex-col gap-2 pt-1 sm:flex-row sm:items-center sm:gap-3">
              <button
                type="button"
                disabled={!inStock}
                onClick={() => {
                  onAddToCart(product);
                  onClose();
                }}
                className="w-full rounded-xl bg-gradient-to-r from-[#402970] to-[#5a3d8a] px-4 py-3.5 text-sm font-semibold text-white shadow-[0_4px_16px_rgba(64,41,112,0.2)] transition-all hover:shadow-[0_6px_20px_rgba(64,41,112,0.3)] disabled:cursor-not-allowed disabled:opacity-50 sm:flex-1 sm:py-3"
              >
                Add to cart
              </button>
              {productUrl ? (
                <a
                  href={productUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full rounded-xl border border-[#402970]/15 px-4 py-3 text-center text-sm font-medium text-[#402970] transition-colors hover:bg-[#F0EEFA] sm:w-auto sm:py-3"
                >
                  Kapruka →
                </a>
              ) : null}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </>
  );
}
