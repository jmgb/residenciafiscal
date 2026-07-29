import { Navigate, Route, Routes } from 'react-router-dom';
import { ChatView } from '@/components/chat/ChatView';
import { AppLayout } from '@/components/layout/AppLayout';
import { chatEngine, chatEngineMode } from '@/lib/chat-engine';
import { MetodologiaPage } from '@/pages/MetodologiaPage';

const isStub = chatEngineMode === 'stub';

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path='/' element={<ChatView engine={chatEngine} isStub={isStub} />} />
        <Route
          path='/c/:conversationId'
          element={<ChatView engine={chatEngine} isStub={isStub} />}
        />
        <Route path='/metodologia' element={<MetodologiaPage />} />
        <Route path='*' element={<Navigate to='/' replace />} />
      </Route>
    </Routes>
  );
}
