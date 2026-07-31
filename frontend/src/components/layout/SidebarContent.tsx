import {
  BookOpen,
  Compass,
  Globe2,
  Mail,
  MessageSquarePlus,
  Shield,
  Trash2,
  Users,
} from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import {
  COUNTRY_ROUTES,
  getJurisdictionLabel,
  getJurisdictionRoute,
  SPAIN_ROUTE,
} from '@/data/countryRoutes';
import { CONTACT_EMAIL } from '@/lib/contribution';
import { Button } from '@/shared/components/ui/button';
import { cn } from '@/shared/lib/utils';
import { useConversations } from '@/stores/useConversations';

export interface SidebarContentProps {
  /** Modo rail: solo iconos. Nunca se activa en el drawer móvil. */
  collapsed?: boolean;
  /** El drawer lo usa para cerrarse al navegar. */
  onNavigate?: () => void;
}

export function SidebarBrand({ collapsed = false, onNavigate }: SidebarContentProps) {
  const location = useLocation();
  const jurisdictionLabel = getJurisdictionLabel(getJurisdictionRoute(location.pathname));

  return (
    <div
      className={cn(
        'flex shrink-0 items-center gap-3 border-b border-sidebar-border py-4',
        collapsed ? 'justify-center px-2' : 'px-4'
      )}
    >
      <Link
        to={SPAIN_ROUTE.path}
        onClick={onNavigate}
        aria-label='Ir al inicio'
        className='flex shrink-0 items-center rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        <img src='/favicon.svg' alt='' className='h-9 w-9' />
      </Link>
      {!collapsed && (
        <div className='min-w-0'>
          <div className='truncate font-heading text-sm font-semibold'>Residencia Fiscal</div>
          <div className='truncate text-xs text-muted-foreground'>{jurisdictionLabel}</div>
        </div>
      )}
    </div>
  );
}

export function SidebarNavigation({ collapsed = false, onNavigate }: SidebarContentProps) {
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const conversations = useConversations((state) => state.conversations);
  const deleteConversation = useConversations((state) => state.deleteConversation);
  const [showAllCountries, setShowAllCountries] = useState(false);

  // La conversación se crea de forma perezosa en `ChatView` con el primer
  // mensaje, así que «Nueva consulta» solo navega a la raíz.
  const handleNew = () => {
    onNavigate?.();
    navigate('/consulta');
  };

  const handleDelete = (id: string) => {
    if (!window.confirm('¿Borrar esta conversación? Esta acción no se puede deshacer.')) return;
    deleteConversation(id);
    if (id === conversationId) navigate('/');
  };

  const location = useLocation();

  return (
    <>
      <nav
        aria-label='Conversaciones'
        className={cn('flex flex-col gap-1', collapsed ? 'px-2' : 'px-3')}
      >
        <Button
          type='button'
          onClick={handleNew}
          className={cn('mb-2 w-full', collapsed && 'px-0')}
          aria-label='Nueva consulta'
          title='Nueva consulta'
        >
          <MessageSquarePlus className='h-4 w-4 shrink-0' aria-hidden='true' />
          {!collapsed && <span>Nueva consulta</span>}
        </Button>

        {!collapsed && conversations.length === 0 && (
          <p className='px-2 py-4 text-xs text-muted-foreground'>
            Todavía no has hecho ninguna consulta.
          </p>
        )}

        {!collapsed &&
          conversations.map((conversation) => {
            const isActive = conversation.id === conversationId;
            return (
              <div
                key={conversation.id}
                className={cn(
                  'group flex items-center gap-1 rounded-lg pr-1 transition-colors',
                  isActive
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'hover:bg-sidebar-accent/60'
                )}
              >
                <Link
                  to={`/c/${conversation.id}`}
                  onClick={onNavigate}
                  aria-current={isActive ? 'page' : undefined}
                  className='min-w-0 flex-1 truncate rounded-lg px-2 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring'
                  title={conversation.title}
                >
                  {conversation.title}
                </Link>
                <button
                  type='button'
                  onClick={() => handleDelete(conversation.id)}
                  aria-label={`Borrar conversación: ${conversation.title}`}
                  className='shrink-0 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100'
                >
                  <Trash2 className='h-3.5 w-3.5' aria-hidden='true' />
                </button>
              </div>
            );
          })}
      </nav>

      <nav
        aria-label='Países'
        className={cn('mt-6 flex flex-col gap-1', collapsed ? 'px-2' : 'px-3')}
      >
        {collapsed ? (
          <Link
            to={SPAIN_ROUTE.path}
            onClick={onNavigate}
            aria-label='Países'
            title='Países'
            className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
          >
            <Globe2 className='h-4 w-4' aria-hidden='true' />
          </Link>
        ) : (
          <>
            <h2 className='flex items-center gap-2 px-2 pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground'>
              <Globe2 className='h-3.5 w-3.5' aria-hidden='true' />
              Países
            </h2>
            {(showAllCountries ? COUNTRY_ROUTES : COUNTRY_ROUTES.slice(0, 3)).map((country) => {
              const isActive = getJurisdictionRoute(location.pathname)?.path === country.path;
              return (
                <Link
                  key={country.path}
                  to={country.path}
                  onClick={onNavigate}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'truncate rounded-lg px-2 py-1.5 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-sidebar-ring',
                    isActive
                      ? 'bg-sidebar-accent font-semibold text-sidebar-accent-foreground'
                      : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
                  )}
                >
                  {country.name}
                </Link>
              );
            })}
            {!showAllCountries && (
              <button
                type='button'
                onClick={() => setShowAllCountries(true)}
                className='rounded-lg px-2 py-1.5 text-left text-sm font-medium text-muted-foreground outline-none transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
              >
                Mostrar más
              </button>
            )}
          </>
        )}
      </nav>
    </>
  );
}

export function SidebarFooter({ collapsed = false, onNavigate }: SidebarContentProps) {
  if (collapsed) {
    return (
      <div className='shrink-0 border-t border-sidebar-border px-2 py-3'>
        <Link
          to='/manifiesto'
          onClick={onNavigate}
          aria-label='Manifiesto'
          title='Manifiesto'
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <Compass className='h-4 w-4' aria-hidden='true' />
        </Link>
        <Link
          to='/metodologia'
          onClick={onNavigate}
          aria-label='Metodología'
          title='Metodología'
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <BookOpen className='h-4 w-4' aria-hidden='true' />
        </Link>
        <Link
          to='/colaborar'
          onClick={onNavigate}
          aria-label='Colaborar'
          title='Colaborar'
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <Users className='h-4 w-4' aria-hidden='true' />
        </Link>
        <Link
          to='/privacidad'
          onClick={onNavigate}
          aria-label='Privacidad'
          title='Privacidad'
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <Shield className='h-4 w-4' aria-hidden='true' />
        </Link>
        <a
          href={`mailto:${CONTACT_EMAIL}`}
          onClick={onNavigate}
          aria-label={CONTACT_EMAIL}
          title={CONTACT_EMAIL}
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <Mail className='h-4 w-4' aria-hidden='true' />
        </a>
      </div>
    );
  }

  return (
    <div className='shrink-0 border-t border-sidebar-border px-3 py-3 text-xs'>
      <Link
        to='/manifiesto'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Manifiesto
      </Link>
      <Link
        to='/metodologia'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Metodología
      </Link>
      <Link
        to='/espana/fuentes'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Corpus de España
      </Link>
      <Link
        to='/colaborar'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Colaborar
      </Link>
      <Link
        to='/privacidad'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Privacidad
      </Link>
      <a
        href={`mailto:${CONTACT_EMAIL}`}
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        {CONTACT_EMAIL}
      </a>
    </div>
  );
}
