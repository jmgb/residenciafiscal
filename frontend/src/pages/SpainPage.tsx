import { ChatView } from '@/components/chat/ChatView';
import { chatEngine, chatEngineMode } from '@/lib/chat-engine';

export function SpainPage() {
  return (
    <ChatView engine={chatEngine} isStub={chatEngineMode === 'stub'} canonicalPath='/españa' />
  );
}
