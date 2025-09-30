export function cn(...classes: Array<string | number | null | false | undefined>) {
  return classes.filter(Boolean).join(" ")
}

export function formatPercent(n: number) {
  const v = isFinite(n) ? Math.round(n) : 0
  return `${v}%`
}