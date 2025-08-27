# main.py
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

# Importar módulos organizados
from config import get_google_api_key, set_google_api_key
from database import initialize_database, list_chats, create_chat, delete_chat, list_messages, add_message
from models import AskQuestionRequest, ConfigureApiKeyRequest, AskQuestionResponse
from document_processor import process_document
from search_engine import build_index, search_query
from gemini_service import configure_gemini, generate_answer
from session_manager import create_session, get_session, list_sessions

# --- Configuración de la App FastAPI ---
app = FastAPI(
    title="RAG System API with Gemini",
    description="API para un sistema de Retrieval-Augmented Generation con FastAPI y Gemini.",
    version="1.1.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Inicialización ---
# Initialize database
initialize_database()

# Configure Gemini
try:
    configure_gemini()
except ValueError as e:
    print(f"⚠️  Error de configuración de Gemini: {e}")
    print("💡 La aplicación puede iniciarse, pero el endpoint /ask fallará si no hay clave.")
    print("💡 Usa el endpoint /configure_api_key para configurar tu API key")

# --- Endpoints de la API ---

# Chat endpoints
@app.get("/chats")
def get_chats():
    return list_chats()

@app.post("/chats")
def post_chat(title: str = Body(...), session_id: str = Body(...)):
    return create_chat(title, session_id)

@app.delete("/chats/{chat_id}")
def delete_chat_endpoint(chat_id: int):
    return delete_chat(chat_id)

# Message endpoints
@app.get("/chats/{chat_id}/messages")
def get_messages(chat_id: int):
    return list_messages(chat_id)

@app.post("/chats/{chat_id}/messages")
def post_message(chat_id: int, sender: str = Body(...), text: str = Body(...), payload_json: dict = Body(default=None)):
    return add_message(chat_id, sender, text, payload_json)

# Document processing endpoint
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
        document_data = process_document(file_content_bytes, file.filename)
        
        if document_data:
            db['documents'].append(document_data)
            processed_files.append({
                "filename": file.filename, 
                "chunks_count": len(document_data['chunks'])
            })
    
    if not db['documents']:
        raise HTTPException(status_code=400, detail="No se pudo procesar ningún archivo.")
    
    build_index(db)
    create_session(session_id, db)
    
    return {
        "message": "Archivos procesados e indexados exitosamente.", 
        "processed_files": processed_files, 
        "session_id": session_id
    }

# Search endpoint
@app.get("/search", summary="Busca pasajes relevantes")
def search_endpoint(q: str = Query(..., min_length=3), session_id: Optional[str] = Query(None)):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id es requerido")
    
    db = get_session(session_id)
    if not db or db.get('word_vectorizer') is None or db.get('char_vectorizer') is None:
        raise HTTPException(status_code=503, detail="El índice no está listo.")
    
    try:
        results = search_query(q, db)
        return results
    except Exception as e:
        print(f"Error durante la búsqueda: {e}")
        raise HTTPException(status_code=500, detail="Ocurrió un error al procesar la búsqueda.")

# Question answering endpoint
@app.post("/ask", response_model=AskQuestionResponse, summary="Responde preguntas usando Gemini")
async def ask_question(request: AskQuestionRequest):
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id es requerido")
    
    db = get_session(request.session_id)
    if not db or db.get('word_vectorizer') is None or db.get('char_vectorizer') is None:
        raise HTTPException(status_code=503, detail="No hay documentos cargados.")
    
    if not get_google_api_key():
        raise HTTPException(status_code=500, detail="La API Key de Google no está configurada en el servidor.")

    try:
        return generate_answer(request.question, db)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Error al generar respuesta: {e}")
        raise HTTPException(status_code=500, detail="Error al generar la respuesta con el modelo de lenguaje.")

# API key configuration endpoint
@app.post("/configure_api_key", summary="Configura la API Key de Google")
async def configure_api_key_endpoint(request: ConfigureApiKeyRequest):
    """Endpoint para configurar la API Key de Google de forma segura"""
    try:
        if set_google_api_key(request.api_key):
            # Reconfigure Gemini with the new API key
            configure_gemini()
            return {"message": "API Key configurada exitosamente", "status": "success"}
        else:
            raise HTTPException(status_code=500, detail="No se pudo guardar la API Key")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al configurar la API Key: {str(e)}")

# Status endpoint
@app.get("/status", summary="Verifica el estado del servicio")
def get_status(session_id: Optional[str] = Query(None)):
    if session_id:
        db = get_session(session_id)
        return {
            "indexed_documents": [doc["name"] for doc in db["documents"]] if db else [],
            "is_index_ready": bool(db and db.get("word_index") is not None and db.get("char_index") is not None),
            "api_key_configured": get_google_api_key() is not None
        }
    return {
        "sessions": list_sessions(),
        "api_key_configured": get_google_api_key() is not None
    }

# Document retrieval endpoint
@app.get("/get_document/{document_name}", summary="Obtiene un documento por nombre")
def get_document(document_name: str, session_id: Optional[str] = Query(None)):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id es requerido")
    
    db = get_session(session_id)
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
