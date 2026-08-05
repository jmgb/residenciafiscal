import type { Components } from 'react-markdown';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const remarkPlugins = [remarkGfm];

function safeMarkdownHref(href: string | undefined): string {
  if (!href) return '#';
  if (href.startsWith('https://') || href.startsWith('http://') || href.startsWith('mailto:')) {
    return href;
  }
  return '#';
}

const markdownComponents: Components = {
  p: ({ children }) => (
    <p className='my-2 text-sm leading-relaxed first:mt-0 last:mb-0'>{children}</p>
  ),
  strong: ({ children }) => <strong className='font-semibold'>{children}</strong>,
  em: ({ children }) => <em className='italic'>{children}</em>,
  a: ({ children, href }) => (
    <a
      href={safeMarkdownHref(href)}
      target='_blank'
      rel='noopener noreferrer'
      className='text-primary underline underline-offset-2 hover:text-primary-500'
    >
      {children}
    </a>
  ),
  ul: ({ children }) => (
    <ul className='my-2 list-disc space-y-1 pl-5 text-sm leading-relaxed'>{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className='my-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed'>{children}</ol>
  ),
  li: ({ children }) => <li className='pl-0.5 text-sm leading-relaxed'>{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className='my-2 border-l-4 border-accent-500 bg-accent px-3 py-2 text-sm text-accent-foreground'>
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className='my-2 overflow-x-auto'>
      <table className='min-w-full border-collapse text-left text-xs'>{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className='bg-muted'>{children}</thead>,
  th: ({ children }) => (
    <th className='border border-border px-2 py-1 font-semibold text-foreground'>{children}</th>
  ),
  td: ({ children }) => <td className='border border-border px-2 py-1 align-top'>{children}</td>,
  code: ({ children }) => (
    <code className='rounded bg-muted px-1 py-0.5 text-[0.8125em]'>{children}</code>
  ),
};

/** Elimina HTML embebido de las respuestas del asistente antes de renderizar. */
function normalizeAssistantMarkdown(content: string): string {
  return content
    .replace(/<\s*(script|style)\b[\s\S]*?<\s*\/\s*\1\s*>/gi, '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/?[a-z][^>]*>/gi, '')
    .replace(/&nbsp;/gi, ' ');
}

interface ChatMessageContentProps {
  content: string;
  isUser: boolean;
}

export function ChatMessageContent({ content, isUser }: ChatMessageContentProps) {
  if (isUser) {
    return (
      <p className='whitespace-pre-wrap break-words text-sm leading-relaxed text-background'>
        {content}
      </p>
    );
  }

  return (
    <div className='break-words text-sm leading-relaxed text-foreground'>
      <ReactMarkdown remarkPlugins={remarkPlugins} components={markdownComponents}>
        {normalizeAssistantMarkdown(content)}
      </ReactMarkdown>
    </div>
  );
}
