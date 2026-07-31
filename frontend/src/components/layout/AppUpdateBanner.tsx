/**
 * Aviso de que hay una versión nueva publicada.
 *
 * Solo se pinta cuando recargar destruiría algo —una respuesta llegando, una
 * pregunta a medio escribir—; si no hay nada en curso, el guardián recarga en
 * silencio y este componente no llega a renderizar nada.
 */
import { RefreshCw } from 'lucide-react';
import { hasWorkInProgress } from '@/lib/app-activity';
import { useAppVersionGuard } from '@/lib/useAppVersionGuard';
import { Button } from '@/shared/components/ui/button';

interface AppUpdateBannerProps {
  checkVersion?: () => Promise<boolean>;
  isBusy?: () => boolean;
  reload?: () => void;
}

export function AppUpdateBanner({
  checkVersion,
  isBusy = hasWorkInProgress,
  reload,
}: AppUpdateBannerProps = {}) {
  const { updateAvailable, applyUpdate } = useAppVersionGuard({ isBusy, checkVersion, reload });

  if (!updateAvailable) return null;

  return (
    <div
      role='status'
      aria-live='polite'
      className='flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-primary-200 bg-primary-50 px-4 py-2 text-sm text-primary-900'
    >
      <span>Hay una versión nueva de la web. Actualiza para verla.</span>
      <Button type='button' variant='outline' size='sm' onClick={applyUpdate}>
        <RefreshCw className='h-4 w-4' aria-hidden='true' />
        Actualizar
      </Button>
    </div>
  );
}
