<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download } from '@element-plus/icons-vue'

import { downloadWiki, fetchDocumentWiki, fetchKnowledgeBaseWiki } from '@/api/kb'
import { apiErrorMessage } from '@/api/http'
import type { Wiki } from '@/api/types'
import { formatDate } from '@/utils/format'
import { renderMarkdown, stripFrontmatter } from '@/utils/markdown'

const props = defineProps<{ kind: 'document' | 'knowledge-base' }>()
const route = useRoute()
const router = useRouter()

const wiki = ref<Wiki | null>(null)
const loading = ref(false)
const downloading = ref(false)

const id = computed(() =>
  props.kind === 'document' ? String(route.params.docId || '') : String(route.params.kbId || ''),
)

const backPath = computed(() =>
  props.kind === 'document'
    ? `/admin/documents/${id.value}`
    : `/admin/knowledge/${id.value}`,
)

const backLabel = computed(() => (props.kind === 'document' ? '返回文档预览' : '返回知识库'))

async function load() {
  loading.value = true
  try {
    wiki.value =
      props.kind === 'document'
        ? await fetchDocumentWiki(id.value)
        : await fetchKnowledgeBaseWiki(id.value)
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  } finally {
    loading.value = false
  }
}

async function download() {
  downloading.value = true
  try {
    const blob = await downloadWiki(props.kind, id.value)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${wiki.value?.title || 'wiki'}.md`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  } finally {
    downloading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="zc-page zc-fade-up">
    <div class="zc-page-header">
      <div>
        <button class="back" type="button" @click="router.push(backPath)">
          <el-icon><ArrowLeft /></el-icon>
          {{ backLabel }}
        </button>
        <h1 class="zc-page-title">{{ wiki?.title || 'Wiki 视图' }}</h1>
        <p class="zc-page-subtitle">
          只读视图，由当前文档块实时拼装；编辑文档块后会自动反映。
          <span v-if="wiki">生成于 {{ formatDate(wiki.generated_at) }}</span>
        </p>
      </div>
      <div class="head-actions">
        <span class="zc-chip zc-chip--primary">只读</span>
        <button class="zc-btn" type="button" :disabled="downloading" data-testid="wiki-download" @click="download">
          <el-icon><Download /></el-icon>
          {{ downloading ? '下载中…' : '下载 Markdown' }}
        </button>
      </div>
    </div>

    <div v-loading="loading" class="wiki zc-card">
      <article
        v-if="wiki"
        class="markdown"
        data-testid="wiki-content"
        v-html="renderMarkdown(stripFrontmatter(wiki.markdown))"
      />
      <div v-else-if="!loading" class="zc-empty">
        <span class="zc-empty__icon">W</span>
        <p>暂无 Wiki 内容</p>
      </div>
    </div>
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

.wiki {
  min-height: 300px;
  padding: clamp(22px, 4vw, 44px);
}

.markdown {
  max-width: 860px;
  margin: 0 auto;
  color: var(--zc-ink-soft);
  font-size: 14px;
  line-height: 1.95;
}

.markdown :deep(h1) {
  margin: 0 0 18px;
  color: var(--zc-ink);
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.markdown :deep(h2) {
  margin: 30px 0 10px;
  padding-top: 16px;
  border-top: 1px dashed var(--zc-line);
  color: var(--zc-ink);
  font-size: 17px;
  font-weight: 750;
}

.markdown :deep(h3) {
  margin: 20px 0 8px;
  font-size: 15px;
}

.markdown :deep(p) {
  margin: 8px 0;
}

.markdown :deep(blockquote) {
  margin: 12px 0;
  padding: 10px 14px;
  border-left: 3px solid #d9d4ff;
  border-radius: 0 10px 10px 0;
  color: var(--zc-muted);
  background: var(--zc-surface-soft);
}

.markdown :deep(ul),
.markdown :deep(ol) {
  padding-left: 22px;
}

.markdown :deep(code) {
  padding: 1px 5px;
  border-radius: 5px;
  background: #f2f1ff;
  font-family: var(--zc-font-mono);
  font-size: 12px;
}

.markdown :deep(pre) {
  padding: 14px;
  overflow-x: auto;
  border-radius: 12px;
  color: #e8e7f4;
  background: #17182e;
}
</style>
