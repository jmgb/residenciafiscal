import { ChatView } from '@/components/chat/ChatView';
import { SPAIN_ROUTE } from '@/data/countryRoutes';
import { chatEngine, chatEngineMode } from '@/lib/chat-engine';

export function SpainPage() {
  return (
    <ChatView
      engine={chatEngine}
      isStub={chatEngineMode === 'stub'}
      canonicalPath='/españa'
      country={SPAIN_ROUTE}
    />
  );
}
