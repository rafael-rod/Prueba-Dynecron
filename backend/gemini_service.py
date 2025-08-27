import google.generativeai as genai
from typing import List, Dict, Any
from models import DocumentFragment, AskQuestionResponse
from config import get_google_api_key
from search_engine import search_query

def configure_gemini():
    """Configure Gemini API"""
    api_key = get_google_api_key()
    if not api_key:
        raise ValueError("La API Key de Google no está configurada. Por favor, configura GOOGLE_API_KEY en las variables de entorno o usa el endpoint /configure_api_key")
    genai.configure(api_key=api_key)
    print("✅ API Key de Google configurada exitosamente")

def generate_answer(question: str, db: Dict[str, Any]) -> AskQuestionResponse:
    """Generate answer using Gemini with RAG approach"""
    if not get_google_api_key():
        raise ValueError("La API Key de Google no está configurada en el servidor.")

    # 1. Recuperación (Retrieval)
    relevant_fragments = search_query(question, db)
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

        PREGUNTA: {question}

        RESPUESTA:
        """
        
        response = model.generate_content(prompt)
        answer = response.text

    except Exception as e:
        print(f"Error al llamar a la API de Gemini: {e}")
        raise ValueError("Error al generar la respuesta con el modelo de lenguaje.")
    
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
