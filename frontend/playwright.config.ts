import { defineConfig, devices } from '@playwright/test'

const projectRoot = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5174',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'uv run uvicorn enterprise_rag.main:app --host 127.0.0.1 --port 8001',
      cwd: projectRoot,
      url: 'http://127.0.0.1:8001/health',
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        APP_ENV: 'dev',
        DATABASE_URL:
          'mysql+pymysql://rag:rag@127.0.0.1:3306/enterprise_rag_e2e?charset=utf8mb4',
        AUTO_CREATE_TABLES: 'true',
        MILVUS_COLLECTION: 'kb_chunks_e2e',
        EMBEDDING_PROVIDER: 'hash',
        LLM_PROVIDER: 'mock',
        EMBEDDING_PRELOAD: 'false',
        ENABLE_WORKER: 'true',
        EXPOSE_CAPTCHA_CODE: 'true',
        ADMIN_USERNAME: 'admin',
        ADMIN_PASSWORD: 'admin123456',
        JWT_SECRET: 'e2e-secret-key-with-at-least-32-bytes',
        UPLOAD_DIR: 'data/e2e/uploads',
        LOG_DIR: 'logs/e2e',
        PYTHONIOENCODING: 'utf-8',
      },
    },
    {
      command: 'npm run dev',
      cwd: projectRoot + '/frontend',
      url: 'http://127.0.0.1:5174',
      timeout: 120_000,
      reuseExistingServer: true,
    },
  ],
})
