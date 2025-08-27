import { ChatInterface } from '../components/ChatInterface';

// Configurar para que no se prerenderice
export const dynamic = 'force-dynamic';

export default function ChatPage() {
  return <ChatInterface />;
}
