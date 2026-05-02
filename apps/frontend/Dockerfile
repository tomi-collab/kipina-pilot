# --- Build stage ---
FROM node:20-alpine AS builder

WORKDIR /app

# Asenna riippuvuudet ensin parempaa cachausta varten
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

# Kopioi loput ja buildaa
COPY . .
RUN npm run build

# --- Runtime stage ---
FROM nginx:alpine

# Korvataan oletuskonfiguraatio omalla SPA-yhteensopivalla
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Kopioi buildi
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# nginx:alpine -imagen oletus käynnistys riittää
