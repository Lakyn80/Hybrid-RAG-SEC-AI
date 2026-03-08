FROM node:20-alpine

ARG NEXT_PUBLIC_BACKEND_URL=http://localhost:8021

ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

WORKDIR /app

COPY package*.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
