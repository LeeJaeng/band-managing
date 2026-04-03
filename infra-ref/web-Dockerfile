FROM node:22-alpine

WORKDIR /app
RUN corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

# ✅ nuxt prepare를 "직접" 실행해서 .nuxt 생성
RUN pnpm dlx nuxi@latest prepare

# ✅ 생성 확인 (없으면 여기서 바로 실패하게)
RUN ls -la .nuxt && test -f .nuxt/tsconfig.json

# ✅ 이제 빌드
RUN pnpm dlx nuxi@latest build

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]