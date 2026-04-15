FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --no-audit --no-fund

COPY . .

ENV NODE_ENV=production
ENV NUXT_PUBLIC_API_BASE=

RUN npm run build

FROM node:22-alpine

WORKDIR /app

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
ENV NUXT_PUBLIC_API_BASE=

COPY --from=build /app/.output ./.output
COPY --from=build /app/package.json ./

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
