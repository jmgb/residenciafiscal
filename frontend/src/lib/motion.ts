/**
 * `true` si el usuario pidió reducir las animaciones: los desplazamientos
 * suaves pasan a ser instantáneos. El guard de `matchMedia` cubre jsdom,
 * donde puede no existir.
 */
export function prefersReducedMotion(): boolean {
  if (typeof window.matchMedia !== 'function') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
