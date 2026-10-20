<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Delete, EditPen, Search } from '@element-plus/icons-vue'

import {
  deleteChunk,
  getDocument,
  listChunks,
  updateChunk,
} from '@/api/kb'
import { apiErrorMessage } from '@/api/http'
import type { Chunk, DocumentItem } from '@/api/types'
import { formatBytes, formatDate, statusLabel } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const docId = computed(() => String(route.params.docId || ''))

const document = ref<DocumentItem | null>(null)
const chunks = ref<Chunk[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const loading = ref(false)
const editOpen = ref(false)
const editing = ref<Chunk | null>(null)
const editContent = ref('')
const saving = ref(false)

async function loadDocument() {
  document.value = await getDocument(docId.value)
}

async function loadChunks() {
  loading.value = true
  try {
    const data = await listChunks(docId.value, {
      page: page.value,
      page_size: pageSize.value,
      q: keyword.value.trim() || undefined,
    })
    chunks.value = data.items
    total.value = data.total
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  } finally {
    loading.value = false
  }
}

async function reload() {
  try {
    await Promise.all([loadDocument(), loadChunks()])
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
    await router.push('/admin/knowledge')
  }
}

function search() {
  page.value = 1
  void loadChunks()
}

function openEdit(chunk: Chunk) {
  editing.value = chunk
  editContent.value = chunk.content
  editOpen.value = true
}

async function saveEdit() {
  if (!editing.value) return
  if (!editContent.value.trim()) {
    ElMessage.warning('内容不能为空。')
    return
  }
  saving.value = true
  try {
    await updateChunk(editing.value.id, editContent.value.trim())
    editOpen.value = false
    ElMessage.success('文档块已更新，向量已重建')
    await Promise.all([loadChunks(), loadDocument()])
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  } finally {
    saving.value = false
  }
}

async function removeChunk(chunk: Chunk) {
  try {
    await ElMessageBox.confirm('删除后该片段不再参与检索，确定继续吗？', '删除文档块', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteChunk(chunk.id)
    ElMessage.success('文档块已删除')
    await Promise.all([loadChunks(), loadDocument()])
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  }
}

function changePage(next: number) {
  page.value = next
  void loadChunks()
}

function backToKb() {
  if (document.value) void router.push(`/admin/knowledge/${document.value.kb_id}`)
  else void router.push('/admin/knowledge')
}

onMounted(reload)
</script>

<template>
  <div class="zc-page zc-fade-up">
    <div class="zc-page-header">
      <div>
        <button class="back" type="button" @click="backToKb">
          <el-icon><ArrowLeft /></el-icon>
          返回知识库
        </button>
        <h1 class="zc-page-title">{{ document?.filename || '文档预览' }}</h1>
        <p class="zc-page-subtitle">
          {{ document?.file_type?.toUpperCase() }} ·
          {{ document ? formatBytes(document.size_bytes) : '—' }} ·
          切块 {{ document?.chunk_size }} / 重叠 {{ document?.chunk_overlap }}
        </p>
      </div>
      <div class="head-actions">
        <span v-if="document" class="zc-chip" :class="`zc-chip--${document.status === 'ready' ? 'success' : 'warning'}`">
          {{ statusLabel(document.status) }}
        </span>
        <button
          v-if="document"
          class="zc-btn"
          type="button"
          @click="router.push(`/admin/documents/${document.id}/wiki`)"
        >
          Wiki 视图
        </button>
      </div>
    </div>

    <div class="toolbar zc-card">
      <div class="toolbar__meta">
        <span>{{ total }} 个文档块</span>
        <span v-if="document?.error_message" class="toolbar__error">{{ document.error_message }}</span>
      </div>
      <div class="toolbar__search">
        <el-input
          v-model="keyword"
          placeholder="搜索片段内容"
          clearable
          data-testid="chunk-search"
          @keyup.enter="search"
          @clear="search"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <button class="zc-btn" type="button" @click="search">搜索</button>
      </div>
    </div>

    <div v-loading="loading" class="chunk-list">
      <article v-for="chunk in chunks" :key="chunk.id" class="chunk zc-card" data-testid="chunk-card">
        <header class="chunk__head">
          <div class="chunk__meta">
            <span class="zc-chip zc-chip--primary">片段 {{ chunk.chunk_index + 1 }}</span>
            <span v-if="chunk.page_no" class="zc-chip">第 {{ chunk.page_no }} 页</span>
            <span class="zc-chip">字符 {{ chunk.char_start }}–{{ chunk.char_end }}</span>
            <span class="chunk__time">{{ formatDate(chunk.updated_at) }}</span>
          </div>
          <div class="chunk__actions">
            <button class="zc-btn chunk-btn" type="button" data-testid="chunk-edit" @click="openEdit(chunk)">
              <el-icon><EditPen /></el-icon>
              编辑
            </button>
            <button class="zc-btn zc-btn--danger chunk-btn" type="button" @click="removeChunk(chunk)">
              <el-icon><Delete /></el-icon>
              删除
            </button>
          </div>
        </header>
        <p class="chunk__content">{{ chunk.content }}</p>
      </article>

      <div v-if="!loading && chunks.length === 0" class="zc-empty">
        <span class="zc-empty__icon"><el-icon><Search /></el-icon></span>
        <p>没有匹配的文档块</p>
        <small>换个关键词，或等待解析完成。</small>
      </div>
    </div>

    <div v-if="total > pageSize" class="pager">
      <el-pagination
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="changePage"
      />
    </div>

    <el-dialog v-model="editOpen" title="编辑文档块" width="640px">
      <p class="zc-hint edit-hint">保存后会重新计算该片段的 bge-m3 向量，并更新 Milvus 索引。</p>
      <textarea v-model="editContent" class="zc-input edit-textarea" rows="14" data-testid="chunk-edit-content" />
      <template #footer>
        <button class="zc-btn" type="button" @click="editOpen = false">取消</button>
        <button class="zc-btn zc-btn--primary" type="button" :disabled="saving" data-testid="chunk-edit-save" @click="saveEdit">
          {{ saving ? '保存中…' : '保存并重建向量' }}
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
  align-items: center;
  gap: 8px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 18px;
  margin-bottom: 14px;
}

.toolbar__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: var(--zc-muted);
  font-size: 11.5px;
}

.toolbar__error {
  max-width: 640px;
  color: var(--zc-danger);
}

.toolbar__search {
  display: flex;
  gap: 8px;
}

.chunk-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 200px;
}

.chunk {
  padding: 16px 18px;
}

.chunk__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.chunk__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.chunk__time {
  color: var(--zc-muted-2);
  font-size: 10px;
}

.chunk__actions {
  display: flex;
  gap: 5px;
}

.chunk-btn {
  min-height: 30px;
  padding-inline: 10px;
  font-size: 11px;
}

.chunk__content {
  margin-top: 11px;
  color: var(--zc-ink-soft);
  font-size: 13px;
  line-height: 1.9;
  white-space: pre-wrap;
}

.pager {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}

.edit-hint {
  margin-bottom: 10px;
}

.edit-textarea {
  min-height: 300px;
  resize: vertical;
  line-height: 1.8;
}
</style>
