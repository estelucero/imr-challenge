# imr-challenge

Este documento explica como levantar los servicios del challenge, la estructura general del proyecto y las API keys necesarias para el backend.

## Estructura del proyecto

```text
imr-challenge/
|- backend/
|  |- app/
|  |  |- agents/          # Agentes de IA
|  |  |- models/          # Modelos de datos y requests
|  |  |- prompts/         # Prompts del sistema
|  |  |- services/        # Servicios de negocio
|  |  `- main.py          # Punto de entrada de la API
|  |- .env                # Variables de entorno del backend
|  |- Dockerfile
|  `- requirements.txt
|- frontend/
|  |- app/                # Rutas de Next.js
|  |- components/         # Componentes de UI
|  |- hooks/              # Hooks de React
|  |- lib/                # Utilidades
|  |- Dockerfile
|  `- package.json
|- compose.yml            # Orquestacion de frontend y backend
`- README.md
```

## Configuracion del backend

Crear o completar el archivo `backend/.env` con las siguientes API keys:

```env
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
```

Ambas claves son necesarias para el funcionamiento correcto del backend.

## Levantar los servicios

Con Docker y Docker Compose instalados, ejecutar el siguiente comando desde la raiz del proyecto:

```bash
docker compose up --build
```

Una vez iniciados los contenedores, los servicios estaran disponibles en:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

Para detener los servicios, ejecutar:

```bash
docker compose down
```
