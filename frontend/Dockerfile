FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .

ENV HOST=0.0.0.0

CMD ["npm", "start"]