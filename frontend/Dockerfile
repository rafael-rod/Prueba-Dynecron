FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Usar build legacy para evitar problemas de SSR
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
