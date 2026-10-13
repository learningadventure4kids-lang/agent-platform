export interface ProductCardData {
  name: string;
  price?: string;
  description?: string;
}

/** Presentational only for now -- /api/chat returns plain text today. Wiring
 * this to real structured data just needs the backend to attach a
 * `products: ProductCardData[]` field to ChatResponse when a search tool
 * runs, and this component rendered per item in AriaChatWidget. */
export function ProductCard({ product, accent }: { product: ProductCardData; accent: string }) {
  return (
    <div className="w-56 shrink-0 rounded-xl border border-white/10 bg-white/5 p-3">
      <p className="text-sm font-medium text-parchment">{product.name}</p>
      {product.price && (
        <p className="mt-0.5 text-sm font-semibold" style={{ color: accent }}>
          {product.price}
        </p>
      )}
      {product.description && <p className="mt-1 text-xs text-dust-light">{product.description}</p>}
    </div>
  );
}
