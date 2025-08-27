# main.py
import os
import io
import json
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pickle
import uuid

# Dependencias para procesamiento de texto y PDF
import pypdf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- Dependencia para Gemini ---
import google.generativeai as genai

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

# --- Configuración de la API Key de Gemini ---
def get_google_api_key():
    """Get Google API key from environment variable or config file."""
    # First try environment variable
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        return api_key
    
    # If not in environment, try to read from a local config file
    config_file = os.path.join(os.path.dirname(__file__), "api_config.txt")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                api_key = f.read().strip()
                if api_key and api_key != "your_google_api_key_here":
                    return api_key
        except Exception:
            pass
    
    return None

def set_google_api_key(api_key: str):
    """Set Google API key in a local config file."""
    try:
        config_file = os.path.join(os.path.dirname(__file__), "api_config.txt")
        with open(config_file, "w") as f:
            f.write(api_key)
        return True
    except Exception:
        return False

# --- Configuración de la App FastAPI ---
app = FastAPI(
    title="RAG System API with Gemini",
    description="API para un sistema de Retrieval-Augmented Generation con FastAPI y Gemini.",
    version="1.1.0"
)

# --- Configuración de la API Key de Gemini ---
# Carga la API Key desde una variable de entorno o archivo de configuración
try:
    api_key = get_google_api_key()
    if not api_key:
        raise ValueError("La API Key de Google no está configurada. Por favor, configura GOOGLE_API_KEY en las variables de entorno o usa el endpoint /configure_api_key")
    genai.configure(api_key=api_key)
    print("✅ API Key de Google configurada exitosamente")
except ValueError as e:
    print(f"⚠️  Error de configuración de Gemini: {e}")
    print("💡 La aplicación puede iniciarse, pero el endpoint /ask fallará si no hay clave.")
    print("💡 Usa el endpoint /configure_api_key para configurar tu API key")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Almacenamiento por sesión ---
# Cada sesión mantiene su propio índice/documentos para persistencia por chat
SESSIONS: Dict[str, Dict[str, Any]] = {}

import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize tables
with db_connect() as conn:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            session_id TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            payload_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()

# Helper serializers

def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}

# REST: Chats
@app.get("/chats")
def list_chats():
    with db_connect() as conn:
        rows = conn.execute("SELECT id, title, created_at, session_id FROM chats ORDER BY id DESC").fetchall()
        return [row_to_dict(r) for r in rows]

@app.post("/chats")
def create_chat(title: str = Body(...), session_id: str = Body(...)):
    created_at = datetime.utcnow().isoformat()
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO chats(title, created_at, session_id) VALUES(?,?,?)", (title, created_at, session_id))
        chat_id = cur.lastrowid
        conn.commit()
        return {"id": chat_id, "title": title, "created_at": created_at, "session_id": session_id}

@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int):
    with db_connect() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))
        conn.commit()
    return {"status": "deleted"}

# REST: Messages
@app.get("/chats/{chat_id}/messages")
def list_messages(chat_id: int):
    with db_connect() as conn:
        rows = conn.execute("SELECT id, chat_id, sender, text, payload_json, created_at FROM messages WHERE chat_id=? ORDER BY id ASC", (chat_id,)).fetchall()
        return [row_to_dict(r) for r in rows]

@app.post("/chats/{chat_id}/messages")
def add_message(chat_id: int, sender: str = Body(...), text: str = Body(...), payload_json: Dict[str, Any] | None = Body(default=None)):
    created_at = datetime.utcnow().isoformat()
    payload_str = json.dumps(payload_json) if payload_json is not None else None
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO messages(chat_id, sender, text, payload_json, created_at) VALUES(?,?,?,?,?)", (chat_id, sender, text, payload_str, created_at))
        msg_id = cur.lastrowid
        conn.commit()
        return {"id": msg_id, "chat_id": chat_id, "sender": sender, "text": text, "payload_json": payload_json, "created_at": created_at}


def build_index(db: Dict[str, Any]):
    all_chunks = [chunk['text'] for doc in db['documents'] for chunk in doc['chunks']]
    if not all_chunks:
        db['word_vectorizer'] = None
        db['char_vectorizer'] = None
        db['word_index'] = None
        db['char_index'] = None
        return

    # Lista simple de stopwords en español (compacta para no añadir dependencias)
    spanish_stopwords = {
        'de','la','que','el','en','y','a','los','del','se','las','por','un','para','con','no','una','su','al','lo','como','más','pero','sus','le','ya','o','este','sí','porque','esta','entre','cuando','muy','sin','sobre','también','me','hasta','hay','donde','quien','desde','todo','nos','durante','todos','uno','les','ni','contra','otros','ese','eso','ante','ellos','e','esto','mí','antes','algunos','qué','unos','yo','otro','otras','otra','él','tanto','esa','estos','mucho','quienes','nada','muchos','cual','poco','ella','estar','estas','algunas','algo','nosotros','mi','mis','tú','te','ti','tu','tus','ellas','nosotras','vosotros','vosotras','os','mío','mía','míos','mías','tuyo','tuya','tuyos','tuyas','suyo','suya','suyos','suyas','nuestro','nuestra','nuestros','nuestras','vuestro','vuestra','vuestros','vuestras','esos','esas','estoy','estás','está','estamos','estáis','están','esté','estés','estemos','estéis','estén','estaré','estarás','estará','estaremos','estaréis','estarán','estaba','estabas','estábamos','estabais','estaban','estuve','estuviste','estuvo','estuvimos','estuvisteis','estuvieron','estuviera','estuvieras','estuviéramos','estuvierais','estuvieran','estuviese','estuvieses','estuviésemos','estuvieseis','estuviesen','estando','estado','estada','estados','estadas','estad','he','has','ha','hemos','habéis','han','haya','hayas','hayamos','hayáis','hayan','habré','habrás','habrá','habremos','habréis','habrán','había','habías','habíamos','habíais','habían','hube','hubiste','hubo','hubimos','hubisteis','hubieron','hubiera','hubieras','hubiéramos','hubierais','hubieran','hubiese','hubieses','hubiésemos','hubieseis','hubiesen','habiendo','habido','habida','habidos','habidas','soy','eres','es','somos','sois','son','sea','seas','seamos','seáis','sean','seré','serás','será','seremos','seréis','serán','era','eras','éramos','erais','eran','fui','fuiste','fue','fuimos','fuisteis','fueron','fuera','fueras','fuéramos','fuerais','fueran','fuese','fueses','fuésemos','fueseis','fuesen','siendo','sido','tengo','tienes','tiene','tenemos','tenéis','tienen','tenga','tengas','tengamos','tengáis','tengan','tendré','tendrás','tendrá','tendremos','tendréis','tendrán','tenía','tenías','teníamos','teníais','tenían','tuve','tuviste','tuvo','tuvimos','tuvisteis','tuvieron','tuviera','tuvieras','tuviéramos','tuvierais','tuvieran','tuviese','tuvieses','tuviésemos','tuvieseis','tuviesen','teniendo','tenido','tenida','tenidos','tenidas'
    }
    combined_stopwords = list(spanish_stopwords.union(ENGLISH_STOP_WORDS))

    # Vectorizador de palabras con lematización simple por acentos y n-gramas 1-2
    word_vectorizer = TfidfVectorizer(
        stop_words=combined_stopwords,
        ngram_range=(1, 2),
        strip_accents='unicode',
        lowercase=True
    )
    word_index = word_vectorizer.fit_transform(all_chunks)

    # Vectorizador de caracteres para captar variaciones morfológicas y errores (char_wb)
    char_vectorizer = TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(3, 5),
        strip_accents='unicode',
        lowercase=True
    )
    char_index = char_vectorizer.fit_transform(all_chunks)

    db['word_vectorizer'] = word_vectorizer
    db['char_vectorizer'] = char_vectorizer
    db['word_index'] = word_index
    db['char_index'] = char_index
    print("Índice TF-IDF (palabras+caracteres) construido exitosamente.")


def session_path(session_id: str) -> str:
    return os.path.join(os.path.dirname(__file__), f"document_store_{session_id}.pkl")


def save_session(session_id: str):
    db = SESSIONS.get(session_id)
    if not db:
        return
    try:
        with open(session_path(session_id), 'wb') as f:
            pickle.dump(db, f)
    except Exception as e:
        print(f"Error guardando sesión {session_id}: {e}")


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    if session_id in SESSIONS:
        return SESSIONS[session_id]
    path = session_path(session_id)
    if os.path.exists(path):
        try:
            with open(path, 'rb') as f:
                SESSIONS[session_id] = pickle.load(f)
                return SESSIONS[session_id]
        except Exception as e:
            print(f"Error cargando sesión {session_id}: {e}")
            return None
    return None

# --- Modelos Pydantic ---
class AskQuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class ConfigureApiKeyRequest(BaseModel):
    api_key: str

class DocumentFragment(BaseModel):
    text: str
    document_name: str
    score: float
    page_number: int = None
    text_position: dict = None

class AskQuestionResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]

# --- Funciones Auxiliares ---
def extract_text_from_pdf(file_stream: io.BytesIO) -> tuple[str, list]:
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
    try:
        return file_stream.read().decode('utf-8')
    except Exception as e:
        print(f"Error extrayendo texto del TXT: {e}")
        return ""

def chunk_text(text: str, page_info: list, chunk_size: int = 1000, overlap: int = 200) -> List[dict]:
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

# def chunk_text(text: str, page_info: list, chunk_size: int = 1000, overlap: int = 200) -> List[dict]:
#     if not text:
#         return []
#     chunks = []
#     start = 0
    
#     while start < len(text):
#         end = start + chunk_size
#         chunk_text = text[start:end]
        
#         # Encontrar en qué página está este chunk
#         page_number = 1
#         chunk_center = (start + end) // 2
#         for page in page_info:
#             if chunk_center >= page['start_pos'] and chunk_center < page['end_pos']:
#                 page_number = page['page_number']
#                 break
#         # for page in page_info:
#         #     if start >= page['start_pos'] and start < page['end_pos']:
#         #         page_number = page['page_number']
#         #         break
        
#         chunks.append({
#             'text': chunk_text,
#             'start_pos': start,
#             'end_pos': end,
#             'page_number': page_number
#         })
#         start += chunk_size - overlap
    
#     return chunks

# --- Endpoints de la API ---

@app.post("/ingest", summary="Ingesta y procesamiento de documentos")
async def ingest_files(files: List[UploadFile] = File(...), session_id: Optional[str] = Query(None)):
    if not (3 <= len(files) <= 10):
        raise HTTPException(status_code=400, detail="Por favor, sube entre 3 y 10 archivos.")
    if not session_id:
        session_id = uuid.uuid4().hex
    db = {"documents": [], "index": None, "vectorizer": None}
    processed_files = []
    for file in files:
        file_content_bytes = await file.read()
        file_stream = io.BytesIO(file_content_bytes)
        filename = file.filename
        if filename.lower().endswith('.pdf'):
            text, page_info = extract_text_from_pdf(file_stream)
        elif filename.lower().endswith('.txt'):
            text = extract_text_from_txt(file_stream)
            page_info = [{'page_number': 1, 'start_pos': 0, 'end_pos': len(text), 'text': text}]
        else:
            continue
        if not text.strip():
            continue
        chunks = chunk_text(text, page_info)
        document_data = {
            "name": filename,
            "chunks": [{"text": chunk['text'], "document_name": filename, "page_number": chunk['page_number'], "start_pos": chunk['start_pos'], "end_pos": chunk['end_pos']} for chunk in chunks],
            "content": file_content_bytes.hex()
        }
        db['documents'].append(document_data)
        processed_files.append({"filename": filename, "chunks_count": len(chunks)})
    if not db['documents']:
        raise HTTPException(status_code=400, detail="No se pudo procesar ningún archivo.")
    build_index(db)
    SESSIONS[session_id] = db
    save_session(session_id)
    return {"message": "Archivos procesados e indexados exitosamente.", "processed_files": processed_files, "session_id": session_id}


@app.get("/search", response_model=List[DocumentFragment], summary="Busca pasajes relevantes")
def search_query(q: str = Query(..., min_length=3), session_id: Optional[str] = Query(None)):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id es requerido")
    db = load_session(session_id)
    if not db or db.get('word_vectorizer') is None or db.get('char_vectorizer') is None:
        raise HTTPException(status_code=503, detail="El índice no está listo.")
    try:
        # Consulta en ambos espacios (palabras y caracteres)
        word_q = db['word_vectorizer'].transform([q])
        char_q = db['char_vectorizer'].transform([q])

        word_sim = cosine_similarity(word_q, db['word_index']).flatten()
        char_sim = cosine_similarity(char_q, db['char_index']).flatten()

        # Combinar con un promedio ponderado (más peso a palabras)
        similarities = 0.7 * word_sim + 0.3 * char_sim
        
        # Verificar si hay alguna similitud significativa
        max_similarity = np.max(similarities)
        if max_similarity < 0.1:  # Umbral más estricto
            return []  # Retorna lista vacía si no hay coincidencias significativas
        
        top_k = 5
        top_indices = similarities.argsort()[-top_k:][::-1]
        results = []
        all_chunks = [chunk for doc in db['documents'] for chunk in doc['chunks']]
        
        for i in top_indices:
            if similarities[i] > 0.1:  # Umbral más estricto para incluir resultados
                chunk = all_chunks[i]
                results.append(
                    DocumentFragment(
                        text=chunk['text'],
                        document_name=chunk['document_name'],
                        score=round(float(similarities[i]), 4),
                        page_number=chunk.get('page_number'),
                        text_position={
                            'start_pos': chunk.get('start_pos'),
                            'end_pos': chunk.get('end_pos')
                        }
                    )
                )
        return results
    except Exception as e:
        print(f"Error durante la búsqueda: {e}")
        raise HTTPException(status_code=500, detail="Ocurrió un error al procesar la búsqueda.")


@app.post("/ask", response_model=AskQuestionResponse, summary="Responde preguntas usando Gemini")
async def ask_question(request: AskQuestionRequest):
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id es requerido")
    db = load_session(request.session_id)
    if not db or db.get('word_vectorizer') is None or db.get('char_vectorizer') is None:
        raise HTTPException(status_code=503, detail="No hay documentos cargados.")
    
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(status_code=500, detail="La API Key de Google no está configurada en el servidor.")

    # 1. Recuperación (Retrieval)
    relevant_fragments = search_query(request.question, request.session_id)
    if not relevant_fragments:
        return AskQuestionResponse(
            answer="No encontré coincidencias significativas para tu consulta en los documentos cargados. Por favor, intenta con términos más específicos o reformula tu pregunta.",
            citations=[]
        )

    # 2. Aumentación (Augmentation)
    context = "\n\n---\n\n".join([f"Fuente: {frag.document_name}\nContenido: {frag.text}" for frag in relevant_fragments])
    
    # 3. Generación (Generation) con Gemini
    try:
        model = genai.GenerativeModel('gemini-2.5-flash') # Usamos un modelo rápido y eficiente
        
        prompt = f"""
        Eres un asistente experto en analizar documentos. Basándote EXCLUSIVAMENTE en el siguiente contexto, responde la pregunta del usuario de forma breve y concisa (3-4 líneas).
        Cita tus fuentes usando el formato [Fuente: nombre_del_documento.pdf]. Puedes usar múltiples citas si es necesario.
        También eres un asistente bilingüe, por lo que debes responder en español y en inglés, depende de la pregunta del usuario. Si la pregunta es en español, responde en español, si la pregunta es en inglés, responde en inglés.
        
        IMPORTANTE: Solo responde si encuentras información RELEVANTE y DIRECTA en el contexto. Si la información no está presente o es muy vaga, NO CITES NADA y responde exactamente: "No encuentro información específica sobre esto en los documentos cargados."

        CONTEXTO:
        {context}

        PREGUNTA: {request.question}

        RESPUESTA:
        """
        
        response = model.generate_content(prompt)
        answer = response.text

    except Exception as e:
        print(f"Error al llamar a la API de Gemini: {e}")
        raise HTTPException(status_code=500, detail="Error al generar la respuesta con el modelo de lenguaje.")
    
    # Extraemos las citas para que el frontend pueda mostrarlas
    citations = []
    seen_docs = set()
    for frag in relevant_fragments:
        if frag.document_name not in seen_docs:
            doc_content = next((doc['content'] for doc in db['documents'] if doc['name'] == frag.document_name), None)
            if doc_content:
                citations.append({
                    "document_name": frag.document_name, 
                    "content_hex": doc_content,
                    "page_number": frag.page_number,
                    "text_position": frag.text_position
                })
                seen_docs.add(frag.document_name)

    return AskQuestionResponse(answer=answer, citations=citations[:3])


@app.post("/configure_api_key", summary="Configura la API Key de Google")
async def configure_api_key(request: ConfigureApiKeyRequest):
    """Endpoint para configurar la API Key de Google de forma segura"""
    try:
        if set_google_api_key(request.api_key):
            # Reconfigure Gemini with the new API key
            genai.configure(api_key=request.api_key)
            return {"message": "API Key configurada exitosamente", "status": "success"}
        else:
            raise HTTPException(status_code=500, detail="No se pudo guardar la API Key")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al configurar la API Key: {str(e)}")


@app.get("/status", summary="Verifica el estado del servicio")
def get_status(session_id: Optional[str] = Query(None)):
    if session_id:
        db = load_session(session_id)
        return {
            "indexed_documents": [doc["name"] for doc in db["documents"]] if db else [],
            "is_index_ready": bool(db and db.get("word_index") is not None and db.get("char_index") is not None),
            "api_key_configured": get_google_api_key() is not None
        }
    return {
        "sessions": list(SESSIONS.keys()),
        "api_key_configured": get_google_api_key() is not None
    }


@app.get("/get_document/{document_name}", summary="Obtiene un documento por nombre")
def get_document(document_name: str, session_id: Optional[str] = Query(None)):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id es requerido")
    db = load_session(session_id)
    if not db:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    document = next((doc for doc in db["documents"] if doc["name"] == document_name), None)
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return {
        "name": document["name"],
        "content_hex": document["content"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
