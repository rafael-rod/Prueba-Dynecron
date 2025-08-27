import io
import pypdf
from typing import List, Dict, Any, Tuple
from config import CHUNK_SIZE, CHUNK_OVERLAP

def extract_text_from_pdf(file_stream: io.BytesIO) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract text from PDF file with page information"""
    try:
        pdf_reader = pypdf.PdfReader(file_stream)
        text = ""
        page_info = []
        current_pos = 0
        
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                page_info.append({
                    'page_number': page_num + 1,
                    'start_pos': current_pos,
                    'end_pos': current_pos + len(page_text),
                    'text': page_text
                })
                text += page_text + "\n"
                current_pos += len(page_text) + 1  # +1 for newline
        return text, page_info
    except Exception as e:
        print(f"Error extrayendo texto del PDF: {e}")
        return "", []

def extract_text_from_txt(file_stream: io.BytesIO) -> str:
    """Extract text from TXT file"""
    try:
        return file_stream.read().decode('utf-8')
    except Exception as e:
        print(f"Error extrayendo texto del TXT: {e}")
        return ""

def chunk_text(text: str, page_info: List[Dict[str, Any]], chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict[str, Any]]:
    """Split text into chunks with page information"""
    if not text:
        return []

    chunks = []

    for page in page_info:
        page_text = page['text']
        page_number = page['page_number']

        start = 0
        while start < len(page_text):
            end = start + chunk_size
            chunk_text = page_text[start:end]

            chunks.append({
                'text': chunk_text,
                'start_pos': start,
                'end_pos': min(end, len(page_text)),
                'page_number': page_number
            })

            start += chunk_size - overlap

    return chunks

def process_document(file_content_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Process a document and return its structured data"""
    file_stream = io.BytesIO(file_content_bytes)
    
    if filename.lower().endswith('.pdf'):
        text, page_info = extract_text_from_pdf(file_stream)
    elif filename.lower().endswith('.txt'):
        text = extract_text_from_txt(file_stream)
        page_info = [{'page_number': 1, 'start_pos': 0, 'end_pos': len(text), 'text': text}]
    else:
        return None
    
    if not text.strip():
        return None
    
    chunks = chunk_text(text, page_info)
    
    return {
        "name": filename,
        "chunks": [{
            "text": chunk['text'], 
            "document_name": filename, 
            "page_number": chunk['page_number'], 
            "start_pos": chunk['start_pos'], 
            "end_pos": chunk['end_pos']
        } for chunk in chunks],
        "content": file_content_bytes.hex()
    }
