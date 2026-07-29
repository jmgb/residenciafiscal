import { Menu } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/shared/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from '@/shared/components/ui/sheet';
import { SidebarBrand, SidebarFooter, SidebarNavigation } from './SidebarContent';

const SHEET_CONTENT_ID = 'mobile-navigation';

/**
 * Drawer de navegación por debajo de `lg`. Reutiliza exactamente las mismas
 * piezas que el sidebar desktop, siempre en modo expandido.
 */
export function MobileNavigation() {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          type='button'
          variant='ghost'
          size='icon'
          className='lg:hidden'
          aria-label='Abrir menú de navegación'
          aria-controls={SHEET_CONTENT_ID}
        >
          <Menu className='h-5 w-5' aria-hidden='true' />
        </Button>
      </SheetTrigger>

      <SheetContent
        id={SHEET_CONTENT_ID}
        side='left'
        className='flex w-[min(20rem,88vw)] flex-col gap-0 border-sidebar-border bg-sidebar p-0 text-sidebar-foreground sm:max-w-none'
      >
        <div className='sr-only'>
          <SheetTitle>Navegación</SheetTitle>
          <SheetDescription>Menú de navegación de la aplicación</SheetDescription>
        </div>

        <SidebarBrand onNavigate={close} />
        <div className='min-h-0 flex-1 overflow-y-auto py-4'>
          <SidebarNavigation onNavigate={close} />
        </div>
        <SidebarFooter onNavigate={close} />
      </SheetContent>
    </Sheet>
  );
}
