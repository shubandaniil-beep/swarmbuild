FROM node:22-slim

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY . .

# NEXT_PUBLIC_* are inlined into the client bundle at BUILD time, so the public
# backend URL must be a build arg — a runtime env var would never reach the
# already-compiled browser code. Pass e.g. https://api.yourdomain.com.
ARG NEXT_PUBLIC_API_URL="http://localhost:8000"
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
