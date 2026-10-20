<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Delete, Document, Refresh, UploadFilled, View } from '@element-plus/icons-vue'

import { apiErrorMessage } from '@/api/http'
import type { DocumentItem } from '@/api/types'
import { formatBytes, formatDate, statusLabel, statusType } from '@/utils/format'
import { useKbStore } from '@/stores/kb'
import { useMetaStore } from '@/stores/meta'

const route = useRoute()
const router = useRouter()
const kbStore = useKbStore()
const meta = useMetaStore()
const kbId = computed(() => String(route.params.kbId || ''))

const uploadOpen = ref(false)
const uploadFile = ref<File | null>(null)
const chunkSize = ref(800)
const chunkOverlap = ref(120)
const editOpen = ref(false)
const saving = ref(false)
const editForm = reactive({
  name: '',
  description: '',
  default_chunk_size: 800,
  default_chunk_overlap: 120,
  retrieval_mode: 'hybrid' as 'dense' | 'hybrid',
})
let pollTimer: number | undefined

const processing = computed(() =>
  kbStore.documents.some((item) =>
    ['pending', 'parsing', 'chunking', 'embedding', 'indexing'].includes(item.status),
  ),
)

function processingCount() {
  return kbStore.documents.filter((item) =>
    ['pending', 'parsing', 'chunking', 'embedding', 'indexing'].includes(item.status),
  ).length
}

async function load() {
  try {
    await kbStore.loadKb(kbId.value)
    await kbStore.loadDocuments(kbId.value)
    if (kbStore.current) {
      chunkSize.value = kbStore.current.default_chunk_size
      chunkOverlap.value = kbStore.current.default_chunk_overlap
    }
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
    await router.push('/admin/knowledge')
  }
}

async function refreshDocuments() {
  try {
    await kbStore.loadDocuments(kbId.value)
  } catch {
    // 轮询失败静默
  }
}

function startPolling() {
  pollTimer = window.setInterval(() => {
    if (processing.value) void refreshDocuments()
  }, 2500)
}

function selectUploadFile(event: Event) {
  const target = event.target as HTMLInputElement
  uploadFile.value = target.files?.[0] || null
}

async function doUpload() {
  if (!uploadFile.value) {
    ElMessage.warning('请选择文件。')
    return
  }
  if (chunkOverlap.value >= chunkSize.value) {
    ElMessage.warning('重叠大小必须小于切块大小。')
    return
  }
  try {
    await kbStore.upload(kbId.value, uploadFile.value, chunkSize.value, chunkOverlap.value)
    ElMessage.success('上传成功，正在后台解析')
    uploadOpen.value = false
    uploadFile.value = null
    await Promise.all([refreshDocuments(), kbStore.loadKb(kbId.value)])
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  }
}

function openEdit() {
  const kb = kbStore.current
  if (!kb) return
  editForm.name = kb.name
  editForm.description = kb.description
  editForm.default_chunk_size = kb.default_chunk_size
  editForm.default_chunk_overlap = kb.default_chunk_overlap
  editForm.retrieval_mode = kb.retrieval_mode === 'dense' ? 'dense' : 'hybrid'
  editOpen.value = true
}

async function saveEdit() {
  if (!editForm.name.trim()) {
    ElMessage.warning('名称不能为空。')
    return
  }
  if (editForm.default_chunk_overlap >= editForm.default_chunk_size) {
    ElMessage.warning('重叠大小必须小于切块大小。')
    return
  }
  saving.value = true
  try {
    await kbStore.update(kbId.value, {
      name: editForm.name.trim(),
      description: editForm.description.trim(),
      default_chunk_size: editForm.default_chunk_size,
      default_chunk_overlap: editForm.default_chunk_overlap,
      retrieval_mode: editForm.retrieval_mode,
    })
    editOpen.value = false
    ElMessage.success('已保存')
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  } finally {
    saving.value = false
  }
}

async function removeDocument(doc: DocumentItem) {
  try {
    await ElMessageBox.confirm(`确定删除文档“${doc.filename}”吗？`, '删除文档', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await kbStore.deleteDocument(doc.id)
    ElMessage.success('文档已删除')
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  }
}

async function reparse(doc: DocumentItem) {
  try {
    await ElMessageBox.confirm('将清空该文档的旧片段并重新解析，确定继续吗？', '重新解析', {
      confirmButtonText: '重新解析',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await kbStore.reparseDocument(doc.id)
    ElMessage.success('已提交重新解析')
    await refreshDocuments()
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  }
}

function openDocument(doc: DocumentItem) {
  void router.push(`/admin/documents/${doc.id}`)
}

function openWiki() {
  void router.push(`/admin/knowledge/${kbId.value}/wiki`)
}

onMounted(async () => {
  void meta.load()
  await load()
  startPolling()
})

onBeforeUnmount(() => {
  if (pollTimer) window.clearInterval(pollTimer)
})
</script>

<template>
  <div class="zc-page zc-fade-up">
    <div class="zc-page-header">
      <div>
        <button class="back" type="button" @click="router.push('/admin/knowledge')">
          <el-icon><ArrowLeft /></el-icon>
          返回知识库列表
        </button>
        <h1 class="zc-page-title">{{ kbStore.current?.name || '知识库详情' }}</h1>
        <p class="zc-page-subtitle">{{ kbStore.current?.description || '暂无描述' }}</p>
      </div>
      <div class="head-actions">
        <button class="zc-btn" type="button" @click="openEdit">编辑设置</button>
        <button class="zc-btn" type="button" @click="openWiki">Wiki 视图</button>
        <button class="zc-btn zc-btn--primary" type="button" data-testid="doc-upload-open" @click="uploadOpen = true">
          <el-icon><UploadFilled /></el-icon>
          上传文档
        </button>
      </div>
    </div>

    <div class="stat-row">
      <div class="stat zc-card">
        <span>文档</span>
        <strong>{{ kbStore.current?.document_count ?? 0 }}</strong>
      </div>
      <div class="stat zc-card">
        <span>文档块</span>
        <strong>{{ kbStore.current?.chunk_count ?? 0 }}</strong>
      </div>
      <div class="stat zc-card">
        <span>检索模式</span>
        <strong>{{ kbStore.current?.retrieval_mode === 'hybrid' ? '混合' : '稠密' }}</strong>
      </div>
      <div class="stat zc-card">
        <span>处理中</span>
        <strong>{{ processingCount() }}</strong>
      </div>
    </div>

    <section class="panel zc-card">
      <div class="panel__head">
        <div>
          <h2>文档列表</h2>
          <p>上传后自动解析、切块、向量化；状态每 2.5 秒刷新。</p>
        </div>
        <span v-if="processing" class="zc-chip zc-chip--warning">后台处理中…</span>
      </div>

      <el-table :data="kbStore.documents" class="doc-table" empty-text="还没有文档，点击右上角上传">
        <el-table-column label="文件" min-width="240">
          <template #default="{ row }">
            <button class="doc-name" type="button" data-testid="doc-row" @click="openDocument(row)">
              <span class="doc-icon"><el-icon><Document /></el-icon></span>
              <span>
                <strong>{{ row.filename }}</strong>
                <small>{{ row.file_type.toUpperCase() }} · {{ formatBytes(row.size_bytes) }}</small>
              </span>
            </button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="150">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
            <el-progress
              v-if="!['ready', 'failed'].includes(row.status)"
              :percentage="row.progress"
              :stroke-width="4"
              :show-text="false"
              class="doc-progress"
            />
          </template>
        </el-table-column>
        <el-table-column label="片段" width="80">
          <template #default="{ row }">{{ row.chunk_count }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="160">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="250" align="right">
          <template #default="{ row }">
            <button class="row-btn" type="button" @click="openDocument(row)">
              <el-icon><View /></el-icon>
              预览
            </button>
            <button class="row-btn" type="button" @click="router.push(`/admin/documents/${row.id}/wiki`)">
              Wiki
            </button>
            <button class="row-btn" type="button" @click="reparse(row)">
              <el-icon><Refresh /></el-icon>
            </button>
            <button class="row-btn row-btn--danger" type="button" @click="removeDocument(row)">
              <el-icon><Delete /></el-icon>
            </button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="uploadOpen" title="上传文档" width="520px" data-testid="doc-upload-dialog">
      <div class="upload-form">
        <label class="upload-drop">
          <input type="file" accept=".pdf,.pptx,.md,.markdown,.png,.jpg,.jpeg,.webp,.docx" data-testid="doc-upload-input" @change="selectUploadFile" />
          <el-icon :size="26"><UploadFilled /></el-icon>
          <strong>{{ uploadFile ? uploadFile.name : '点击选择文件' }}</strong>
          <small>PDF / PPTX / Markdown / 图片 / DOCX，最大 {{ meta.meta?.max_upload_mb || 50 }} MB</small>
        </label>
        <div class="upload-grid">
          <div>
            <label class="zc-label">切块大小（字符）</label>
            <el-input-number v-model="chunkSize" :min="100" :max="4000" :step="100" />
          </div>
          <div>
            <label class="zc-label">重叠大小（字符）</label>
            <el-input-number v-model="chunkOverlap" :min="0" :max="1000" :step="20" />
          </div>
        </div>
        <el-progress v-if="kbStore.uploading" :percentage="kbStore.uploadPercent" :stroke-width="6" />
      </div>
      <template #footer>
        <button class="zc-btn" type="button" @click="uploadOpen = false">取消</button>
        <button class="zc-btn zc-btn--primary" type="button" :disabled="kbStore.uploading" data-testid="doc-upload-submit" @click="doUpload">
          {{ kbStore.uploading ? '上传中…' : '上传并解析' }}
        </button>
      </template>
    </el-dialog>

    <el-dialog v-model="editOpen" title="编辑知识库" width="520px">
      <div class="upload-form">
        <label class="zc-label">名称</label>
        <input v-model="editForm.name" class="zc-input" />
        <label class="zc-label upload-gap">描述</label>
        <textarea v-model="editForm.description" class="zc-input upload-textarea" />
        <div class="upload-grid upload-gap">
          <div>
            <label class="zc-label">默认切块大小</label>
            <el-input-number v-model="editForm.default_chunk_size" :min="100" :max="4000" :step="100" />
          </div>
          <div>
            <label class="zc-label">默认重叠大小</label>
            <el-input-number v-model="editForm.default_chunk_overlap" :min="0" :max="1000" :step="20" />
          </div>
        </div>
        <label class="zc-label upload-gap">检索模式</label>
        <el-radio-group v-model="editForm.retrieval_mode">
          <el-radio-button value="hybrid">混合检索</el-radio-button>
          <el-radio-button value="dense">稠密检索</el-radio-button>
        </el-radio-group>
      </div>
      <template #footer>
        <button class="zc-btn" type="button" @click="editOpen = false">取消</button>
        <button class="zc-btn zc-btn--primary" type="button" :disabled="saving" @click="saveEdit">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
  padding: 0;
  border: 0;
  color: var(--zc-muted);
  background: transparent;
  font-size: 12px;
  cursor: pointer;
}

.back:hover {
  color: var(--zc-primary-strong);
}

.head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 16px 18px;
}

.stat span {
  color: var(--zc-muted);
  font-size: 11px;
}

.stat strong {
  font-size: 23px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.panel {
  padding: 20px;
}

.panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel__head h2 {
  font-size: 16px;
  font-weight: 750;
}

.panel__head p {
  margin-top: 3px;
  color: var(--zc-muted);
  font-size: 11.5px;
}

.doc-table {
  width: 100%;
}

.doc-name {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.doc-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  color: var(--zc-primary);
  background: var(--zc-primary-soft);
}

.doc-name strong {
  display: block;
  max-width: 300px;
  overflow: hidden;
  color: var(--zc-ink-soft);
  font-size: 12.5px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-name small {
  display: block;
  color: var(--zc-muted-2);
  font-size: 10px;
}

.doc-progress {
  margin-top: 5px;
  width: 110px;
}

.row-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 4px 7px;
  border: 0;
  border-radius: 7px;
  color: var(--zc-muted);
  background: transparent;
  font-size: 11px;
  cursor: pointer;
}

.row-btn:hover {
  color: var(--zc-primary-strong);
  background: var(--zc-primary-soft);
}

.row-btn--danger:hover {
  color: var(--zc-danger);
  background: var(--zc-danger-soft);
}

.upload-form {
  display: flex;
  flex-direction: column;
}

.upload-drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 26px 16px;
  border: 1px dashed #cfc8ff;
  border-radius: 16px;
  color: var(--zc-muted);
  background: #fbfaff;
  cursor: pointer;
}

.upload-drop:hover {
  border-color: var(--zc-primary);
  background: var(--zc-primary-soft);
}

.upload-drop input {
  display: none;
}

.upload-drop strong {
  color: var(--zc-ink-soft);
  font-size: 13px;
}

.upload-drop small {
  font-size: 10.5px;
}

.upload-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 16px;
}

.upload-gap {
  margin-top: 15px;
}

.upload-textarea {
  min-height: 76px;
  resize: vertical;
}

@media (max-width: 900px) {
  .stat-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
