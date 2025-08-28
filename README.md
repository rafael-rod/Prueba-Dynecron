# Sistema RAG con FastAPI y Next.js

Este proyecto implementa un sistema de Retrieval-Augmented Generation (RAG) que permite a los usuarios subir documentos (.txt y .pdf), indexarlos y posteriormente interactuar con ellos mediante un chat inteligente. El sistema está dividido en dos partes principales:

- **Backend:** API desarrollada con [FastAPI](backend/main.py) que procesa documentos, construye índices TF-IDF, gestiona sesiones y genera respuestas con integración a Google Gemini.
- **Frontend:** Aplicación web desarrollada con [Next.js](frontend/src/app/page.tsx) que ofrece una interfaz de usuario moderna para el chat y la visualización de documentos.

## Tecnologías Utilizadas

- **Python** y [FastAPI](backend/main.py) para el backend.
- **Next.js** y React con Typescript para el frontend.
- **Docker & Docker Compose** para la contenedorización y despliegue.
- **Scikit-learn** para el procesamiento e indexación de textos.
- **PDF.js (react-pdf)** para la visualización de documentos en el navegador.
- Manejo de persistencia en archivos: índices guardados en formato `.pkl`.
- Validaciones robustas de archivos en el frontend ([FileUploader](frontend/src/app/components/FileUploader.tsx)).

## Estructura del Proyecto

La estructura está organizada de la siguiente manera:

- **backend/**
  - `main.py`: Punto de entrada de la API con todos los endpoints ([detalles aquí](backend/main.py)).
  - `config.py`: Configuración de variables, API Key y constantes como `CHUNK_SIZE` y `SIMILARITY_THRESHOLD` ([ver config](backend/config.py)).
  - `database.py`: Operaciones de persistencia en SQLite para chats y mensajes ([ver database](backend/database.py)).
  - `document_processor.py`: Extracción y chunking de documentos (.pdf y .txt) ([ver document_processor](backend/document_processor.py)).
  - `search_engine.py`: Construcción de índices TF-IDF y búsqueda de fragmentos relevantes ([ver search_engine](backend/search_engine.py)).
  - `gemini_service.py`: Integración con el servicio de Google Gemini para generar respuestas ([ver gemini_service](backend/gemini_service.py)).
  - `session_manager.py`: Gestión de sesiones y persistencia en archivos `.pkl` ([ver session_manager](backend/session_manager.py)).
  - Otros archivos y configuraciones de entorno.

- **frontend/**
  - `src/app/`: Contiene las páginas y componentes principales de la aplicación.
    - `layout.tsx`: Define el layout global y la configuración del tema ([ver layout](frontend/src/app/layout.tsx)).
    - `page.tsx`: Página inicial que invita al usuario a subir documentos ([ver page](frontend/src/app/page.tsx)).
    - `chat/`: Módulo para la interfaz del chat y visualización dinámica de documentos ([ver ChatInterface en frontend/src/app/components/ChatInterface.tsx]).
  - `src/lib/types.ts`: Modelos TypeScript para manejar la estructura de datos del chat y resultados ([ver types](frontend/src/lib/types.ts)).
  - Configuración de Next.js y ESLint en los archivos `next.config.ts`, `tsconfig.json` y `eslint.config.mjs`.

## Decisiones Técnicas y Funcionalidades

- **Arquitectura Modular:** Se decidió separar claramente el procesamiento de documentos, la gestión de índices y la generación de respuestas para facilitar el mantenimiento y pruebas unitarias.
- **Persistencia del Índice:** Los índices se guardan en archivos `.pkl` para garantizar la persistencia de datos entre reinicios y facilitar una rápida recuperación de la sesión.
- **Validaciones Robustas:** El frontend implementa validaciones estrictas en el componente [FileUploader](frontend/src/app/components/FileUploader.tsx) para asegurar que solo se acepten archivos `.txt` y `.pdf`, y que se suban entre 3 y 10 archivos.
- **Citas Clicables:** Las respuestas del sistema incluyen citas clicables que enlazan directamente al contenido original del documento, lo cual facilita la verificación y profundización de la información proporcionada.
- **Integración con Gemini:** Se utiliza la API de Google Gemini para la generación de respuestas, complementada con una robusta capa de búsqueda que utiliza similitud de coseno entre índices de palabras y caracteres.

## Cómo Ejecutarlo

1. **Generar API Key de Google:**

   Antes de proceder con Docker, es necesario que generes una API Key en [Google AI Studio](https://aistudio.google.com/app/apikey) y configures la variable de entorno o el archivo de configuración correspondiente para que el backend pueda acceder a ella (crear
   un archivo .env en la carpeta backend y añadir la API key, ejemplo: GOOGLE_API_KEY=tu_api_key_aqui)

2. **Ejecutar con Docker Compose:**

   - Construir y levantar los contenedores:
     ```bash
     docker compose up
     ```
   - Acceder al frontend en: [http://localhost:3000](http://localhost:3000)
   - Acceder a la API del backend en: [http://localhost:8000](http://localhost:8000)

## Demo

Aquí se incluirá un gif demostrativo del funcionamiento del sistema:

![Demo](./Dynecron_New_GIF.gif)

## Tiempo Invertido
Invertí un total de 8 horas aproximadamente en este proyecto.

## Nota
La visualización de documentos (al abrir las citas) solo funciona con archivos .pdf por el momento, no con .txt, ya que el
visor es exclusivo de pdf. En próximas actualizaciones se añadirá soporte para .txt.

## Referencias y Citas

- Consulta document_processor.py para ver cómo se extrae y se divide el texto de los documentos.
- Revisa search_engine.py para entender la lógica del indexado y búsqueda utilizando TF-IDF.
- La configuración de la API de Google se realiza en config.py.


## Conclusión

Este sistema RAG permite una integración fluida entre la ingesta, indexación y consulta de documentos, ofreciendo respuestas precisas y citas verificables. La separación modular del backend y la intuitiva interfaz del frontend aseguran una experiencia de usuario robusta y escalable.

¡Disfruta navegando y consultando tus documentos!
