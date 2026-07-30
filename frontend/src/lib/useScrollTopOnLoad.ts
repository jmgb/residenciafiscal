import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router';
import { prefersReducedMotion } from '@/lib/motion';

/**
 * Devuelve el `ref` para el contenedor de scroll de una página y, al montarla,
 * lo desplaza suavemente hasta arriba.
 *
 * Cada página posee su propio contenedor `overflow-y-auto` (el documento no
 * scrollea), y el navegador puede restaurar en él una posición previa al
 * recargar; este hook garantiza que la página siempre se vea desde arriba al
 * cargar. Si la URL trae un ancla (`#seccion`), no hace nada: el destino lo
 * decide el efecto de anclas de la página, no este hook.
 */
export function useScrollTopOnLoad<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const { hash } = useLocation();
  // Solo importa el hash del montaje: un cambio de hash posterior no debe
  // re-disparar el scroll a arriba.
  const initialHashRef = useRef(hash);

  useEffect(() => {
    if (initialHashRef.current) return;
    const el = ref.current;
    if (!el) return;
    // Un frame de margen para que la restauración de scroll del navegador,
    // si la hay, ocurra antes y el usuario vea el desplazamiento hasta arriba.
    const frame = requestAnimationFrame(() => {
      // jsdom no implementa `scrollTo` en elementos; en el navegador siempre existe.
      if (typeof el.scrollTo === 'function') {
        el.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
      } else {
        el.scrollTop = 0;
      }
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  return ref;
}
