# Backend: FastAPI + uvicorn.
#
# Imagen slim (no la `alpine`): psycopg2-binary trae ruedas precompiladas para
# glibc, y en alpine (musl) habria que compilar contra libpq, que alarga la
# construccion sin ganar nada aca.
FROM python:3.12-slim

WORKDIR /app

# Las dependencias van en una capa aparte y ANTES del codigo: mientras
# requirements.txt no cambie, Docker reutiliza esta capa y no reinstala todo
# en cada cambio de una linea de codigo.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

EXPOSE 8000

# Sin --reload: eso es para desarrollo. Aca la imagen es inmutable.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
