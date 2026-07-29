import { useCallback, useEffect, useState } from 'react';

/**
 * Preferencia de colapso del sidebar (solo desktop), persistida bajo una clave
 * versionada. Cualquier fallo de storage degrada a EXPANDIDO: nunca rompe el shell.
 */
export const SIDEBAR_COLLAPSED_STORAGE_KEY = 'rf.sidebar-collapsed.v1';

function readInitialCollapsed(): boolean {
  try {
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

export interface UseSidebarCollapsedResult {
  collapsed: boolean;
  toggle: () => void;
}

export function useSidebarCollapsed(): UseSidebarCollapsedResult {
  const [collapsed, setCollapsed] = useState<boolean>(readInitialCollapsed);

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(collapsed));
    } catch {
      // Persistir es best-effort.
    }
  }, [collapsed]);

  const toggle = useCallback(() => setCollapsed((prev) => !prev), []);

  return { collapsed, toggle };
}
