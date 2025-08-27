# Backend - RAG System API

Este directorio contiene el backend de la aplicación RAG (Retrieval-Augmented Generation) organizado en módulos para mejor mantenibilidad y escalabilidad.

## Estructura de Archivos

### `main.py`
- **Propósito**: Punto de entrada principal de la aplicación FastAPI
- **Contenido**: Configuración de la app, middleware CORS, y todos los endpoints de la API
- **Responsabilidades**: 
  - Definir rutas y endpoints
  - Manejar requests/responses HTTP
  - Coordinar entre diferentes módulos

### `config.py`
- **Propósito**: Configuración centralizada de la aplicación
- **Contenido**: Variables de entorno, configuración de API keys, constantes
- **Funciones principales**:
  - `get_google_api_key()`: Obtiene la API key de Google
  - `set_google_api_key()`: Configura la API key de Google
  - Constantes de configuración (CHUNK_SIZE, TOP_K_RESULTS, etc.)

### `models.py`
- **Propósito**: Modelos Pydantic para validación de datos
- **Contenido**: Clases para requests y responses de la API
- **Modelos**:
  - `AskQuestionRequest`
  - `ConfigureApiKeyRequest`
  - `DocumentFragment`
  - `AskQuestionResponse`

### `database.py`
- **Propósito**: Operaciones de base de datos SQLite
- **Contenido**: Funciones para manejar chats y mensajes
- **Funciones principales**:
  - `initialize_database()`: Crear tablas
  - `list_chats()`, `create_chat()`, `delete_chat()`
  - `list_messages()`, `add_message()`

### `document_processor.py`
- **Propósito**: Procesamiento de documentos PDF y TXT
- **Contenido**: Extracción de texto y chunking
- **Funciones principales**:
  - `extract_text_from_pdf()`: Extraer texto de PDFs
  - `extract_text_from_txt()`: Extraer texto de archivos TXT
  - `chunk_text()`: Dividir texto en chunks
  - `process_document()`: Procesar documento completo

### `search_engine.py`
- **Propósito**: Motor de búsqueda con indexación TF-IDF
- **Contenido**: Indexación y búsqueda semántica
- **Funciones principales**:
  - `build_index()`: Construir índices TF-IDF
  - `search_query()`: Buscar fragmentos relevantes

### `gemini_service.py`
- **Propósito**: Integración con Google Gemini AI
- **Contenido**: Configuración y generación de respuestas
- **Funciones principales**:
  - `configure_gemini()`: Configurar API de Gemini
  - `generate_answer()`: Generar respuestas usando RAG

### `session_manager.py`
- **Propósito**: Gestión de sesiones y persistencia
- **Contenido**: Almacenamiento y recuperación de datos de sesión
- **Funciones principales**:
  - `create_session()`: Crear nueva sesión
  - `get_session()`: Obtener datos de sesión
  - `save_session()`: Guardar sesión en archivo
  - `load_session()`: Cargar sesión desde archivo

## Flujo de Trabajo

1. **Inicialización**: `main.py` importa y configura todos los módulos
2. **Ingesta**: `document_processor.py` procesa archivos → `search_engine.py` indexa → `session_manager.py` guarda
3. **Búsqueda**: `search_engine.py` busca fragmentos relevantes
4. **Generación**: `gemini_service.py` genera respuestas usando RAG
5. **Persistencia**: `database.py` maneja chats y mensajes

## Ventajas de esta Estructura

- **Separación de responsabilidades**: Cada módulo tiene una función específica
- **Mantenibilidad**: Cambios en un módulo no afectan otros
- **Testabilidad**: Cada módulo puede ser testeado independientemente
- **Escalabilidad**: Fácil agregar nuevas funcionalidades
- **Reutilización**: Módulos pueden ser reutilizados en otros proyectos

## Dependencias

Las dependencias están definidas en `requirements.txt` en el directorio raíz del backend.
