/**
 * Lightweight className merger — combines conditional class names.
 * Avoids pulling in clsx/tailwind-merge to keep the bundle light.
 * For complex merge conflicts use tailwind-merge if needed later.
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}
