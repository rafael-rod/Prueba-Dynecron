'use client';

import { useState, useEffect, useRef } from 'react';
import { Message, SearchResult, QAResponse, Citation, Chat, ChatMessage } from '@/lib/types';
import { PdfViewer } from './PdfViewer';
import { useRouter } from 'next/navigation';


type ChatMode = 'search' | 'qa';

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<ChatMode>('qa');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [indexedFiles, setIndexedFiles] = useState<string[]>([]);
  const [activePdf, setActivePdf] = useState<{fileHex: string, pageNumber?: number, textPosition?: {start_pos: number, end_pos: number}} | null>(null);
  const [showFilesPopup, setShowFilesPopup] = useState(false);
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [showRightPane, setShowRightPane] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const currentChat = chats.find(c => c.id === activeChatId) || null;
  const currentSessionId = currentChat?.session_id;
  const hasSession = Boolean(currentSessionId);

  const loadChats = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/chats');
      const data: Chat[] = await res.json();
      setChats(data);
      if (data.length > 0 && activeChatId == null) {
        setActiveChatId(data[0].id);
      }
    } catch (e) {
      console.error('Error cargando chats', e);
    }
  };

  const loadMessages = async (chatId: number) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/chats/${chatId}/messages`);
      const data: ChatMessage[] = await res.json();
      const uiMsgs: Message[] = data.map(m => {
        const payload = m.payload_json || {};
        if (payload.results || payload.qaResponse) {
          return { sender: m.sender, text: m.text, ...(payload.results ? { results: payload.results } : {}), ...(payload.qaResponse ? { qaResponse: payload.qaResponse } : {}) } as Message;
        }
        return { sender: m.sender, text: m.text } as Message;
      });
      setMessages(uiMsgs.length ? uiMsgs : [{ sender: 'bot', text: '¡Hola! Puedes empezar a preguntar.' }]);
    } catch (e) {
      console.error('Error cargando mensajes', e);
    }
  };

  useEffect(() => {
    const files = localStorage.getItem('indexedFiles');
    if (files) setIndexedFiles(JSON.parse(files));
    loadChats();
  }, []);

  useEffect(() => {
    if (activeChatId != null) loadMessages(activeChatId);
  }, [activeChatId]);

  // Cargar nombres de archivos indexados para el chat activo desde el backend
  useEffect(() => {
    const fetchIndexed = async () => {
      if (!currentSessionId) {
        setIndexedFiles([]);
        return;
      }
      try {
        const res = await fetch(`http://127.0.0.1:8000/status?session_id=${encodeURIComponent(currentSessionId)}`);
        if (!res.ok) throw new Error('No se pudo obtener el estado de la sesión');
        const data = await res.json();
        if (Array.isArray(data.indexed_documents)) {
          setIndexedFiles(data.indexed_documents);
          // Persistimos de forma opcional para fallback rápido
          localStorage.setItem('indexedFiles', JSON.stringify(data.indexed_documents));
        } else {
          setIndexedFiles([]);
        }
      } catch (e) {
        console.error('Error cargando archivos indexados', e);
      }
    };
    fetchIndexed();
  }, [currentSessionId]);

  // Refrescar lista al abrir el popup
  useEffect(() => {
    const refreshOnOpen = async () => {
      if (showFilesPopup && currentSessionId) {
        try {
          const res = await fetch(`http://127.0.0.1:8000/status?session_id=${encodeURIComponent(currentSessionId)}`);
          if (res.ok) {
            const data = await res.json();
            if (Array.isArray(data.indexed_documents)) {
              setIndexedFiles(data.indexed_documents);
            }
          }
        } catch (e) {
          console.error('Error refrescando archivos indexados', e);
        }
      }
    };
    refreshOnOpen();
  }, [showFilesPopup, currentSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const appendMessage = async (msg: Message) => {
    setMessages(prev => [...prev, msg]);
    if (activeChatId == null) return;
    try {
      const payload = (msg.results || msg.qaResponse) ? { results: msg.results, qaResponse: msg.qaResponse } : null;
      await fetch(`http://127.0.0.1:8000/chats/${activeChatId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender: msg.sender, text: msg.text, payload_json: payload })
      });
    } catch (e) {
      console.error('No se pudo persistir el mensaje', e);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    if (!hasSession) {
      setError('Esta conversación no tiene documentos. Ve a Inicio para crear un nuevo chat.');
      return;
    }

    const userMessage: Message = { sender: 'user', text: input };
    await appendMessage(userMessage);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      let response;
      if (mode === 'search') {
        const url = `http://127.0.0.1:8000/search?q=${encodeURIComponent(input)}&session_id=${encodeURIComponent(currentSessionId!)}`;
        response = await fetch(url);
        if (!response.ok) throw new Error('Error en la búsqueda.');
        const data: SearchResult[] = await response.json();
        const botMsg: Message = { sender: 'bot', text: `Resultados de búsqueda para "${input}":`, results: data };
        await appendMessage(botMsg);
      } else {
        response = await fetch('http://127.0.0.1:8000/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: input, session_id: currentSessionId }),
        });
        if (!response.ok) throw new Error('Error al obtener la respuesta.');
        const data: QAResponse = await response.json();
        const botMsg: Message = { sender: 'bot', text: data.answer, qaResponse: data };
        await appendMessage(botMsg);
      }
    } catch (err: any) {
      setError(err.message);
      const botErr: Message = { sender: 'bot', text: `Lo siento, ocurrió un error: ${err.message}` };
      await appendMessage(botErr);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCitationClick = (citation: Citation) => {
    setActivePdf({
      fileHex: citation.content_hex,
      pageNumber: citation.page_number,
      textPosition: citation.text_position
    });
    setShowRightPane(true);
  };

  const handleSearchResultClick = (result: SearchResult) => {
    if (!hasSession) {
      setError('No hay sesión de documentos para abrir el PDF. Crea un nuevo chat desde Inicio.');
      return;
    }
    const url = `http://127.0.0.1:8000/get_document/${encodeURIComponent(result.document_name)}?session_id=${encodeURIComponent(currentSessionId!)}`;
    fetch(url)
      .then(response => response.json())
      .then(data => {
        setActivePdf({
          fileHex: data.content_hex,
          pageNumber: result.page_number,
          textPosition: result.text_position
        });
        setShowRightPane(true);
      })
      .catch(error => {
        console.error('Error obteniendo documento:', error);
        setError('No se pudo abrir el documento para este resultado.');
      });
  };

  const deriveTitle = (msgs: Message[], fallback: string) => {
    const firstUser = msgs.find(m => m.sender === 'user');
    return firstUser ? (firstUser.text.length > 40 ? firstUser.text.slice(0, 40) + '…' : firstUser.text) : fallback;
  };

  const createSession = () => {
    router.push('/')
  };

  const deleteChat = async (chatId: number) => {
    try {
      await fetch(`http://127.0.0.1:8000/chats/${chatId}`, { method: 'DELETE' });
      await loadChats();
      if (activeChatId === chatId) {
        const remaining = chats.filter(c => c.id !== chatId);
        setActiveChatId(remaining[0]?.id ?? null);
        setMessages(remaining[0] ? messages : [{ sender: 'bot', text: 'Selecciona o crea un chat para comenzar.' }]);
      }
    } catch (e) {
      console.error('Error eliminando chat', e);
    }
  };

  const selectChat = (id: number) => {
    setActiveChatId(id);
  };

  const gridClasses = activePdf ? 'md:grid-cols-[260px_minmax(0,1fr)_minmax(0,420px)]' : 'md:grid-cols-[260px_minmax(0,1fr)]';
  return (
    <div className={`grid grid-cols-1 ${gridClasses} gap-4 md:gap-6 h-[calc(100vh-4rem)]`}>
      {/* Sidebar izquierda: Historial */}
      <aside className="hidden md:flex flex-col card p-3 overflow-hidden">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold">Historial</h2>
          <button className="btn btn-primary h-8 px-2 text-xs" onClick={createSession}>Nuevo</button>
        </div>
        <div className="overflow-y-auto space-y-1">
          {chats.map(c => (
            <div key={c.id} className={`group flex items-center justify-between gap-2 p-2 rounded-md cursor-pointer border ${activeChatId===c.id?'border-[--color-primary] bg-[--color-muted]':'border-[--color-border]'}`} onClick={() => selectChat(c.id)}>
              <div className="min-w-0">
                <p className="truncate text-xs">{c.title}</p>
                <p className="text-[10px] text-gray-500">{new Date(c.created_at).toLocaleDateString()}</p>
              </div>
              <button className="text-red-500 opacity-0 group-hover:opacity-100 text-xs" onClick={(e)=>{e.stopPropagation(); deleteChat(c.id);}}>&times;</button>
            </div>
          ))}
        </div>
      </aside>

      {/* Columna de Chat */}
      <div className="flex-1 flex flex-col card overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-[--color-border]">
          <div className="flex justify-between items-center">
            <h1 className="text-base md:text-lg font-semibold">Panel de Chat</h1>
            <div className="flex items-center gap-1 bg-[--color-muted] p-1 rounded-lg border border-[--color-border]">
              <button aria-pressed={mode==='qa'} disabled={!hasSession} onClick={() => setMode('qa')} className={`px-3 py-1 rounded-md text-xs font-medium border ${mode === 'qa' ? 'bg-[--color-primary] text-[--color-primary-foreground] border-[--color-primary]' : 'border-transparent'} ${!hasSession ? 'opacity-50 cursor-not-allowed' : ''}`}>Q&A</button>
              <button aria-pressed={mode==='search'} disabled={!hasSession} onClick={() => setMode('search')} className={`px-3 py-1 rounded-md text-xs font-medium border ${mode === 'search' ? 'bg-[--color-primary] text-[--color-primary-foreground] border-[--color-primary]' : 'border-transparent'} ${!hasSession ? 'opacity-50 cursor-not-allowed' : ''}`}>Búsqueda</button>
            </div>
          </div>
          {!hasSession && (
            <div className="mt-2 text-xs text-yellow-400">Esta conversación no tiene documentos. Ve a Inicio para crear un nuevo chat.</div>
          )}
          <div className="mt-2 text-xs text-gray-400">
            <button className="chip text-xs" onClick={()=>setShowFilesPopup(true)}>Archivos indexados ({indexedFiles.length})</button>
          </div>
        </div>

        {/* Mensajes */}
        <div className="flex-grow p-4 md:p-6 overflow-y-auto">
          <div className="space-y-4 md:space-y-6">
            {messages.map((msg, index) => (
              <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-lg p-4 rounded-xl ${msg.sender === 'user' ? 'bg-[--color-primary] text-[--color-primary-foreground]' : 'bg-[--color-muted] border border-[--color-border]'}`}>
                  <p className="whitespace-pre-wrap text-sm md:text-base">{msg.text}</p>
                  {msg.results && (
                    <div className="mt-4 space-y-3">
                      {msg.results.length > 0 ? msg.results.map((res, i) => (
                        <div 
                          key={i} 
                          className="bg-[--color-card] p-3 rounded-lg border border-[--color-border] cursor-pointer hover:border-[--color-primary] transition-colors"
                          onClick={() => handleSearchResultClick(res)}
                        >
                          <p className="text-sm text-gray-700 dark:text-gray-200 italic">"{res.text}"</p>
                          <p className="text-xs text-right mt-2 text-[--color-primary]">
                            Fuente: {res.document_name} (Relevancia: {res.score})
                            {res.page_number && ` - Página ${res.page_number}`}
                          </p>
                        </div>
                      )) : <p className="text-sm text-gray-500 dark:text-gray-400">No se encontraron resultados.</p>}
                    </div>
                  )}
                  {msg.qaResponse && msg.qaResponse.citations.length > 0 && (
                     <div className="mt-4 border-t border-[--color-border] pt-3">
                        <h3 className="text-sm font-semibold mb-2">Fuentes:</h3>
                        <div className="flex flex-wrap gap-2">
                           {msg.qaResponse.citations.map((cit, i) => (
                              <button
                                key={i}
                                onClick={() => handleCitationClick(cit)}
                                className="chip text-xs hover:border-[--color-primary]"
                              >
                                 {cit.document_name}
                              </button>
                           ))}
                        </div>
                     </div>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="max-w-lg p-4 rounded-xl bg-[--color-muted] border border-[--color-border]">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-[--color-primary] rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-[--color-primary] rounded-full animate-pulse delay-75"></div>
                    <div className="w-2 h-2 bg-[--color-primary] rounded-full animate-pulse delay-150"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="p-4 border-t border-[--color-border]">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={hasSession ? (mode === 'qa' ? 'Haz una pregunta...' : 'Busca un término...') : 'Crea un nuevo chat en Inicio para comenzar'}
              className="w-full input focus:outline-none focus:ring-2 focus:ring-[--color-ring]"
              disabled={!hasSession}
            />
            <button type="submit" disabled={isLoading || !hasSession} className="btn btn-primary disabled:bg_gray-400 disabled:cursor-not-allowed">
              Enviar
            </button>
          </form>
        </div>
      </div>

      {/* Pane derecha: Visor PDF */}
      {activePdf && (
        <div className="card overflow-hidden">
          <div className="relative h-full">
            <button className="absolute top-2 right-2 chip text-xs" onClick={()=>{ setActivePdf(null); setShowRightPane(false); }}>Cerrar</button>
            <PdfViewer fileHex={activePdf.fileHex} pageNumber={activePdf.pageNumber} textPosition={activePdf.textPosition} onClose={() => { setActivePdf(null); setShowRightPane(false); }} />
          </div>
        </div>
      )}

      {/* Popup de archivos indexados */}
      {showFilesPopup && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" onClick={()=>setShowFilesPopup(false)}>
          <div className="card w-full max-w-lg p-4" onClick={(e)=>e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold">Archivos indexados</h3>
              <button className="chip text-xs" onClick={()=>setShowFilesPopup(false)}>Cerrar</button>
            </div>
            {indexedFiles.length ? (
              <ul className="space-y-2 max-h-80 overflow-y-auto">
                {indexedFiles.map((f,i)=> (
                  <li key={i} className="text-xs bg-[--color-muted] border border-[--color-border] p-2 rounded-md">{f}</li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-500">No hay archivos cargados.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}