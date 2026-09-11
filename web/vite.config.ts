import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// 산출물은 `web/dist` 이고, 그대로 backend image 에 들어가 FastAPI 가 서빙한다
// (app/web/spa.py). 별도 frontend Pod/Service 를 만들지 않는다.
//
// `base: "/"` 를 유지한다 — SPA fallback 이 index.html 을 어느 경로에서 돌려주든
// asset 참조가 절대경로여야 한다.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    port: 5173,
    // 로컬 개발: API 는 same-origin 상대경로로 부른다. backend 를 8080 에 띄워 두고
    // 여기서 프록시한다. **이 설정은 개발 전용이며 이미지에는 들어가지 않는다.**
    proxy: {
      "/api": "http://127.0.0.1:8080",
      "/login": "http://127.0.0.1:8080",
      "/logout": "http://127.0.0.1:8080",
      "/health": "http://127.0.0.1:8080",
      "/ready": "http://127.0.0.1:8080",
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    // 기본 5s 는 jsdom + React render 에 빠듯해서 빌드 머신이 바쁘면 간헐적으로
    // "Test timed out" 이 난다(로직 실패가 아니라 대기 초과다). 이 테스트들은
    // 성능을 재지 않으므로 여유를 준다 — CI 플레이크 방지가 목적이다.
    testTimeout: 20_000,
    hookTimeout: 20_000,
  },
});
