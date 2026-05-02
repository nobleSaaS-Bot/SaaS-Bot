const DEFAULT_CURRENCY = "USD";

export function formatCurrency(
  amount: number | string,
  currency: string = DEFAULT_CURRENCY,
  locale: string = "en-US"
): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return `${currency} 0.00`;

  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  } catch {
    return `${currency} ${num.toFixed(2)}`;
  }
}

export function formatCompactCurrency(amount: number, currency: string = DEFAULT_CURRENCY): string {
  if (amount >= 1_000_000) return `${currency} ${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `${currency} ${(amount / 1_000).toFixed(1)}K`;
  return formatCurrency(amount, currency);
}
