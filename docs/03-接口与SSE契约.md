# 03 · 接口与 SSE 契约

> 版本 v1.0｜日期：2026-10-20
> Base URL：`http://127.0.0.1:8001`｜业务前缀：`/api/v1`
> 自动生成契约：[`openapi.json`](openapi.json)（`uv run python scripts/export_openapi.py`）

---

## 1. 通用约定

- JSON `snake_case`。
- 认证：`Authorization: Bearer <JWT>`。
- 时间：ISO 8601（存 UTC，前端本地化）。
- 分页：`{items, total, page, page_size}`。
- 错误：

```json
{
  "detail": {
    "code": "VALIDATION_FAILED",
    "message": "参数校验失败，请检查输入。",
    "request_id": "req_..."
  }
}
```

- 每个响应带 `X-Request-ID`。

---

## 2. 认证

### `GET /api/v1/auth/captcha`

公开。响应：

```json
{
  "captcha_id": "c_...",
  "image_base64": "iVBORw0...",
  "expires_in": 300,
  "debug_code": null
}
```

> `debug_code` 仅在 `APP_ENV=test` 或 `EXPOSE_CAPTCHA_CODE=true` 时返回，生产环境必须为 `null`。

### `POST /api/v1/auth/register`

```json
{
  "username": "zhangsan",
  "password": "user123456",
  "confirm_password": "user123456",
  "captcha_id": "c_...",
  "captcha_code": "A7K2"
}
```

成功 201：`{access_token, token_type, expires_in, user}`。

### `POST /api/v1/auth/login`

```json
{
  "username": "admin",
  "password": "admin123456",
  "captcha_id": "c_...",
  "captcha_code": "A7K2"
}
```

成功 200：同上。

### `GET /api/v1/auth/me`

返回当前用户：`{id, username, role, created_at, last_login_at}`。

### `POST /api/v1/auth/logout`

204；JWT 无状态，前端删除本地 token。

---

## 3. 知识库

### 用户可用列表（登录用户）

- `GET /api/v1/knowledge-bases`
- `GET /api/v1/knowledge-bases/{kb_id}`

返回 `id/name/description/default_chunk_size/default_chunk_overlap/retrieval_mode/embedding_model/embedding_dim/document_count/chunk_count/created_at/updated_at`。

### 管理员

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/admin/knowledge-bases` | 全部知识库 |
| POST | `/api/v1/admin/knowledge-bases` | 创建 |
| GET | `/api/v1/admin/knowledge-bases/{id}` | 详情 |
| PATCH | `/api/v1/admin/knowledge-bases/{id}` | 更新名称/描述/切块默认值/检索模式 |
| DELETE | `/api/v1/admin/knowledge-bases/{id}` | 删除（含文档、块、向量、文件） |

创建请求：

```json
{
  "name": "西部计划政策库",
  "description": "2021-2026 政策文件",
  "default_chunk_size": 800,
  "default_chunk_overlap": 120,
  "retrieval_mode": "hybrid"
}
```

`retrieval_mode`：`dense` / `hybrid`；`chunk_overlap < chunk_size`。

---

## 4. 文档

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/admin/knowledge-bases/{kb_id}/documents?page=&page_size=&status=` | 文档列表 |
| POST | `/api/v1/admin/knowledge-bases/{kb_id}/documents` | multipart 上传 |
| GET | `/api/v1/admin/documents/{doc_id}` | 详情 |
| DELETE | `/api/v1/admin/documents/{doc_id}` | 删除文档 |
| POST | `/api/v1/admin/documents/{doc_id}/reparse` | 重新解析 |
| GET | `/api/v1/admin/documents/{doc_id}/chunks?page=&page_size=&q=` | 文档块列表 |

上传 `multipart/form-data`：

- `file`：`.pdf`、`.pptx`、`.md`、`.markdown`、`.png`、`.jpg`、`.jpeg`、`.webp`、`.docx`
- `chunk_size`：100–4000，可选，默认知识库值
- `chunk_overlap`：0–1000，必须小于 `chunk_size`

返回 202：

```json
{
  "id": "doc_...",
  "kb_id": "kb_...",
  "filename": "政策.pdf",
  "file_type": "pdf",
  "size_bytes": 920926,
  "chunk_size": 800,
  "chunk_overlap": 120,
  "status": "pending",
  "progress": 0,
  "chunk_count": 0,
  "error_message": null,
  "created_at": "...",
  "updated_at": "..."
}
```

前端每 2.5 秒轮询文档状态，直到 `ready` 或 `failed`。

---

## 5. 文档块

### `PATCH /api/v1/admin/chunks/{chunk_id}`

```json
{ "content": "编辑后的内容" }
```

- 更新 MySQL 内容。
- upsert Milvus 向量（不阻塞 flush；后台 flush）。
- 返回更新后的 `ChunkOut`。

### `DELETE /api/v1/admin/chunks/{chunk_id}`

204；删除 MySQL 块并尽力删除 Milvus 向量。

---

## 6. Wiki（只读）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/admin/documents/{doc_id}/wiki` | 文档 Wiki |
| GET | `/api/v1/admin/knowledge-bases/{kb_id}/wiki` | 知识库 Wiki 索引 |

默认返回：

```json
{
  "title": "政策.pdf · Wiki",
  "markdown": "---\n...",
  "generated_at": "2026-10-20T..."
}
```

`?download=1` 返回 `text/markdown` 附件。

---

## 7. 对话

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/chat/sessions` | 当前用户会话 |
| POST | `/api/v1/chat/sessions` | 新建 |
| PATCH | `/api/v1/chat/sessions/{id}` | 重命名 |
| DELETE | `/api/v1/chat/sessions/{id}` | 删除（级联消息） |
| GET | `/api/v1/chat/sessions/{id}/messages` | 历史消息 |
| POST | `/api/v1/chat/sessions/{id}/messages/stream` | 流式问答 |

新建会话：

```json
{ "title": "新对话", "settings": {} }
```

### 流式请求

```json
{
  "content": "西部计划服务期是几年？",
  "kb_ids": ["kb_...", "kb_..."],
  "temperature": 0.7,
  "top_p": 0.8,
  "max_tokens": 2048,
  "history_rounds": 5
}
```

- `kb_ids` 至少 1 个。
- `temperature` 0–2；`top_p` (0,1]；`max_tokens` 128–8192；`history_rounds` 0–20。
- 请求体**没有 `model` 字段**，服务端固定 `deepseek-flash`。

### SSE 事件

响应头：

```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

| 事件 | 数据 | 时机 |
|---|---|---|
| `meta` | `{session_id, message_id, request_id, model}` | 开始 |
| `ping` | `{ts}` | 心跳 |
| `citations` | `{items: Citation[]}` | 检索完成 |
| `delta` | `{text}` | 每个 token/片段 |
| `done` | `{message_id, finish_reason, usage}` | 正常结束 |
| `error` | `{code, message, request_id}` | 异常 |

`Citation`：

```json
{
  "chunk_id": "chk_...",
  "document_id": "doc_...",
  "filename": "政策.pdf",
  "kb_name": "西部计划政策库",
  "page_no": 3,
  "content": "原文片段",
  "score": 0.0327
}
```

前端用 `fetch` + `ReadableStream` 解析（EventSource 不支持 POST + Authorization）。

---

## 8. 系统

### `GET /health`

```json
{
  "status": "ok",
  "db": "ok",
  "milvus": "ok",
  "llm": "configured",
  "embedding": "bge_m3"
}
```

### `GET /api/v1/meta`

```json
{
  "app_title": "知策 · 政策知识问答助手",
  "llm_model": "deepseek-flash",
  "llm_thinking": "disabled",
  "embedding_model": "BAAI/bge-m3",
  "embedding_dim": 1024,
  "retrieval_modes": ["dense", "hybrid"],
  "upload_types": [".pdf", ".pptx", ".md", ".png", ".jpg", ".jpeg", ".webp", ".docx"],
  "max_upload_mb": 50,
  "top_p_note": "DeepSeek 官方文档说明：非思考模式下 top_p 固定为 1.0..."
}
```

---

## 9. 错误码

| code | HTTP | 含义 |
|---|---:|---|
| `UNAUTHORIZED` | 401 | 未登录 / token 失效 |
| `FORBIDDEN` | 403 | 非管理员 / 无权限 |
| `INVALID_CREDENTIALS` | 401 | 账号或密码错误 |
| `USERNAME_TAKEN` | 409 | 用户名已占用 |
| `CAPTCHA_INVALID` | 400 | 验证码错误 / 过期 / 已使用 |
| `VALIDATION_FAILED` | 422 | 参数校验失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `UNSUPPORTED_FILE_TYPE` | 400 | 不支持的文件类型 |
| `FILE_TOO_LARGE` | 413 | 文件超限 |
| `DOCUMENT_DUPLICATE` | 409 | 同一知识库重复文件 |
| `NO_KNOWLEDGE_BASE` | 400 | 未选择有效知识库 |
| `VECTOR_STORE_UNAVAILABLE` | 503 | Milvus 不可用 |
| `LLM_UNAVAILABLE` | 200 SSE | DeepSeek 未配置/调用失败 |
| `INTERNAL` | 500 / SSE | 未预期错误 |
