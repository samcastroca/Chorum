# Chorum frontend — imagen de desarrollo (Vite dev server).
FROM node:20-alpine

WORKDIR /app

# Instala dependencias primero (capa cacheable) desde el lockfile.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# `--host` expone el dev server fuera del contenedor.
CMD ["npm", "run", "dev", "--", "--host"]
