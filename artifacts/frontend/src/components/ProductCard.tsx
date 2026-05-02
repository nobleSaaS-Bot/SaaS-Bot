import { formatCurrency } from "@/utils/formatCurrency";

interface Product {
  id: string;
  name: string;
  description: string | null;
  price: number;
  stock_quantity: number;
  is_active: boolean;
  images: string[] | null;
}

interface ProductCardProps {
  product: Product;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}

export default function ProductCard({ product, onEdit, onDelete }: ProductCardProps) {
  return (
    <div className="rounded-xl border overflow-hidden group hover:shadow-md transition-shadow">
      <div className="aspect-[4/3] bg-muted relative overflow-hidden">
        {product.images?.[0] ? (
          <img
            src={product.images[0]}
            alt={product.name}
            className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-10 h-10 text-muted-foreground/40">
              <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        )}
        {!product.is_active && (
          <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-destructive text-destructive-foreground text-xs font-medium">
            Inactive
          </span>
        )}
      </div>

      <div className="p-3 space-y-1">
        <h3 className="font-medium text-sm truncate">{product.name}</h3>
        {product.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">{product.description}</p>
        )}
        <div className="flex items-center justify-between pt-1">
          <span className="font-semibold text-sm">{formatCurrency(product.price)}</span>
          <span className="text-xs text-muted-foreground">{product.stock_quantity} in stock</span>
        </div>
        <div className="flex gap-2 pt-1">
          {onEdit && (
            <button
              onClick={() => onEdit(product.id)}
              className="flex-1 py-1.5 rounded-lg border text-xs font-medium hover:bg-accent transition-colors"
            >
              Edit
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(product.id)}
              className="flex-1 py-1.5 rounded-lg border border-destructive/30 text-destructive text-xs font-medium hover:bg-destructive/10 transition-colors"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
