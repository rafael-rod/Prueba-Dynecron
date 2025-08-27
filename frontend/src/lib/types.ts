export interface SearchResult {
  text: string;
  document_name: string;
  score: number;
  page_number?: number;
  text_position?: {
    start_pos: number;
    end_pos: number;
  };
}

export interface Citation {
  document_name: string;
  content_hex: string;
  page_number?: number;
  text_position?: {
    start_pos: number;
    end_pos: number;
  };
}

export interface QAResponse {
  answer: string;
  citations: Citation[];
}

export interface Message {
  sender: 'user' | 'bot';
  text: string;
  results?: SearchResult[];
  qaResponse?: QAResponse;
}

export interface Chat {
  id: number;
  title: string;
  created_at: string;
  session_id: string;
}

export interface ChatMessage {
  id: number;
  chat_id: number;
  sender: 'user' | 'bot';
  text: string;
  payload_json?: any;
  created_at: string;
}