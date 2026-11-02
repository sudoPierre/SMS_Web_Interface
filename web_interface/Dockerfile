FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
# npm ci installs the locked tree without resolving it, which keeps memory low on small build hosts
RUN npm ci --no-audit --no-fund
COPY . .
# Always call the API on the same origin (nginx proxies /api and /webhook),
# even if the platform injects VITE_BACKEND_API_URL as a build arg
RUN VITE_BACKEND_API_URL= npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
