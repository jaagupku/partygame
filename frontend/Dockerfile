FROM node:26-alpine AS dependencies
WORKDIR /app
COPY package.json pnpm-lock.yaml .npmrc ./
RUN npm install -g "$(node -p 'require("./package.json").packageManager')"
RUN pnpm install --frozen-lockfile

FROM dependencies AS development
RUN apk --no-cache add curl
# Let jsdom provide browser storage in tests instead of Node's experimental implementation.
ENV NODE_OPTIONS=--no-experimental-webstorage
COPY . .
EXPOSE 3000
CMD ["pnpm", "run", "dev", "--host", "0.0.0.0", "--port", "3000", "--strictPort"]

FROM dependencies AS builder
COPY . .
RUN pnpm run build
RUN pnpm prune --prod

FROM node:26-alpine
RUN apk --no-cache add curl
WORKDIR /app
COPY --from=builder /app/build build/
COPY --from=builder /app/node_modules node_modules/
COPY package.json .
EXPOSE 3000
ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
CMD [ "node", "build" ]
