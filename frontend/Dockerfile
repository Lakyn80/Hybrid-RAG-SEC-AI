FROM node:20-alpine

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
