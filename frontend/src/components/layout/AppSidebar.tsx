import { cn } from '@/shared/lib/utils';
import { SidebarBrand, SidebarFooter, SidebarNavigation } from './SidebarContent';

export interface AppSidebarProps {
  collapsed: boolean;
  /** `id` del landmark, enlazado desde el toggle mediante `aria-controls`. */
  id?: string;
  className?: string;
}

export function AppSidebar({ collapsed, id, className }: AppSidebarProps) {
  return (
    <aside
      id={id}
      data-collapsed={collapsed}
      className={cn(
        'flex h-full shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground',
        'transition-[width] duration-200 motion-reduce:transition-none',
        collapsed ? 'w-16' : 'w-64',
        className
      )}
    >
      <SidebarBrand collapsed={collapsed} />
      <div className='min-h-0 flex-1 overflow-y-auto py-4'>
        <SidebarNavigation collapsed={collapsed} />
      </div>
      <SidebarFooter collapsed={collapsed} />
    </aside>
  );
}
