import { BookOpen, MessageSquarePlus, Scale, Trash2 } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
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
  return (
    <div
      className={cn(
        'flex shrink-0 items-center gap-3 border-b border-sidebar-border py-4',
        collapsed ? 'justify-center px-2' : 'px-4'
      )}
    >
      <Link
        to='/'
        onClick={onNavigate}
        aria-label='Ir al inicio'
        className='flex shrink-0 items-center rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        <span className='flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground'>
          <Scale className='h-5 w-5' aria-hidden='true' />
        </span>
      </Link>
      {!collapsed && (
        <div className='min-w-0'>
          <div className='truncate font-heading text-sm font-semibold'>Residencia Fiscal</div>
          <div className='truncate text-xs text-muted-foreground'>Art. 9 LIRPF</div>
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

  // La conversación se crea de forma perezosa en `ChatView` con el primer
  // mensaje, así que «Nueva consulta» solo navega a la raíz.
  const handleNew = () => {
    onNavigate?.();
    navigate('/');
  };

  const handleDelete = (id: string) => {
    deleteConversation(id);
    if (id === conversationId) navigate('/');
  };

  return (
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
  );
}

export function SidebarFooter({ collapsed = false, onNavigate }: SidebarContentProps) {
  if (collapsed) {
    return (
      <div className='shrink-0 border-t border-sidebar-border px-2 py-3'>
        <Link
          to='/metodologia'
          onClick={onNavigate}
          aria-label='Metodología'
          title='Metodología'
          className='flex justify-center rounded-lg p-2 text-muted-foreground outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring'
        >
          <BookOpen className='h-4 w-4' aria-hidden='true' />
        </Link>
      </div>
    );
  }

  return (
    <div className='shrink-0 border-t border-sidebar-border px-3 py-3 text-xs'>
      <Link
        to='/metodologia'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Metodología
      </Link>
      <Link
        to='/metodologia#corpus'
        onClick={onNavigate}
        className='block rounded px-2 py-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring'
      >
        Corpus analizado
      </Link>
    </div>
  );
}
