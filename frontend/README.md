# enterprise-rag frontend

Vue 3 + TypeScript + Vite + Pinia + Element Plus。

## 开发

```powershell
npm install
npm run dev
```

- 地址：<http://127.0.0.1:5174>
- `/api`、`/health` 代理到后端 `http://127.0.0.1:8001`

## 验证

```powershell
npm run typecheck
npm run test
npm run build
npx playwright test
```

## 页面

- `/login`、`/register`：登录/注册 + 图形验证码。
- `/chat`：会话侧栏、知识库多选、参数抽屉、流式回答、来源引用。
- `/admin/knowledge`：知识库列表/创建/删除。
- `/admin/knowledge/:kbId`：文档上传、解析状态、文档列表。
- `/admin/knowledge/:kbId/wiki`：知识库 Wiki 索引。
- `/admin/documents/:docId`：文档块预览/搜索/编辑/删除。
- `/admin/documents/:docId/wiki`：文档 Wiki。

## 说明

- 模型固定 DeepSeek Flash，不提供模型下拉。
- Top P 控件保留，但 DeepSeek 非思考模式下 `top_p` 固定为 1.0，界面有提示。
- E2E 使用独立 MySQL 库与 Milvus 集合，默认 mock LLM + hash embedder。
