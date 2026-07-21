# Frontend: se compila con Node y se sirve con nginx.
#
# Construccion en dos etapas. La primera necesita Node y las ~200 MB de
# node_modules; la segunda se queda SOLO con el resultado (unos pocos archivos
# estaticos) sobre una imagen de nginx de ~25 MB. Node no viaja en la imagen
# final porque, una vez compilado, React es HTML + CSS + JS: no hace falta
# ningun servidor de Node para servirlo.
FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./

# La URL del backend se resuelve AL COMPILAR (Vite la reemplaza en el codigo,
# no la lee en tiempo de ejecucion). Por eso viene como argumento de
# construccion: si se cambia, hay que reconstruir la imagen.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---------- imagen final ----------
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
