FROM python:3.11-slim

WORKDIR /code

# Evita que Python genere archivos .pyc y fuerza logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias primero (aprovecha la caché de capas de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copiamos el código (en dev será sobrescrito por el volumen)
COPY ./app /code/app

# Comando por defecto con hot reload activo
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]