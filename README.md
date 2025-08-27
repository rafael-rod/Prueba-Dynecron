# Sistema RAG con FastAPI y Next.js

Este proyecto implementa un sistema de Retrieval-Augmented Generation (RAG) con FastAPI en el backend y Next.js en el frontend.

## Ejecutar con Docker

### Prerrequisitos
- Docker Desktop (incluye Docker Compose)
  - Descarga desde: https://www.docker.com/products/docker-desktop/
  - Instala y reinicia tu computadora
  - Asegúrate de que Docker Desktop esté ejecutándose

### Instrucciones

1. Clona el repositorio
2. Navega al directorio del proyecto
3. Ejecuta el comando:

```bash
docker compose up
```

4. Abre tu navegador y ve a:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

### Detener los servicios

```bash
docker compose down
```

### Reconstruir las imágenes

```bash
docker compose up --build
```

## Estructura del Proyecto

- `backend/`: API FastAPI con endpoints para procesamiento de documentos y chat
- `frontend/`: Aplicación Next.js con interfaz de usuario
- `docker-compose.yml`: Configuración de Docker Compose
- `backend/Dockerfile`: Imagen Docker para el backend
- `frontend/Dockerfile`: Imagen Docker para el frontend
