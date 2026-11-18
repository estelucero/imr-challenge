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

## Agentes

- **Clarifier**: revisa la conversación, solicita aclaraciones cuando son necesarias y prepara un resumen del proceso para el analista.
- **Process Analyst**: transforma el resumen en un grafo estructurado con participantes, carriles, actividades, eventos y conexiones.
- **BPMN Creator**: convierte el grafo del analista en un borrador de XML BPMN 2.0 con información de distribución del diagrama.
- **BPMN Validator**: revisa el XML y los errores detectados, y propone correcciones sin cambiar el significado del proceso.

El **orquestador** coordina estos agentes, los reintentos y las respuestas al usuario. No es un agente de IA: su flujo está definido en código.

## Workflow

1. El usuario describe el proceso. El clarifier responde con preguntas si necesita más información; cuando tiene suficiente, envía un resumen al analyst.
2. El analyst genera el grafo del proceso. Si su respuesta no cumple el formato esperado, el orquestador le solicita una corrección.
3. El creator genera el XML BPMN a partir del grafo. Si no entrega XML, el orquestador lo reintenta de forma limitada.
4. El backend comprueba la sintaxis, las referencias, la fidelidad al grafo y la distribución. También intenta separar nodos superpuestos y ajustar las rutas de las conexiones de forma determinística.
5. El validator revisa el borrador junto con los errores y advertencias detectados. Su resultado se vuelve a comprobar y, si es necesario, se intenta corregir nuevamente dentro del límite establecido.
6. El orquestador devuelve el diagrama si supera las comprobaciones, con una advertencia si quedan detalles visuales sin resolver. Si no se puede obtener un XML válido, devuelve un error.

## Configuracion del backend

Crear el archivo `backend/.env` con las siguientes API keys:

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
