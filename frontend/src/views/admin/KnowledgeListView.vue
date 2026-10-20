<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, Delete, Document, Plus, Reading } from '@element-plus/icons-vue'

import { apiErrorMessage } from '@/api/http'
import { useKbStore } from '@/stores/kb'

const kbStore = useKbStore()
const router = useRouter()

const dialogOpen = ref(false)
const saving = ref(false)
const form = reactive({
  name: '',
  description: '',
  default_chunk_size: 800,
  default_chunk_overlap: 120,
  retrieval_mode: 'hybrid' as 'dense' | 'hybrid',
})

function openCreate() {
  form.name = ''
  form.description = ''
  form.default_chunk_size = 800
  form.default_chunk_overlap = 120
  form.retrieval_mode = 'hybrid'
  dialogOpen.value = true
}

async function create() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入知识库名称。')
    return
  }
  if (form.default_chunk_overlap >= form.default_chunk_size) {
    ElMessage.warning('重叠大小必须小于切块大小。')
    return
  }
  saving.value = true
  try {
    const kb = await kbStore.create({
      name: form.name.trim(),
      description: form.description.trim(),
      default_chunk_size: form.default_chunk_size,
      default_chunk_overlap: form.default_chunk_overlap,
      retrieval_mode: form.retrieval_mode,
    })
    dialogOpen.value = false
    ElMessage.success('知识库已创建')
    await router.push(`/admin/knowledge/${kb.id}`)
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  } finally {
    saving.value = false
  }
}

async function remove(id: string, name: string) {
  try {
    await ElMessageBox.confirm(
      `删除“${name}”会同时删除其文档、文档块和向量索引，确定继续吗？`,
      '删除知识库',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await kbStore.remove(id)
    ElMessage.success('知识库已删除')
  } catch (err) {
    ElMessage.error(apiErrorMessage(err))
  }
}

function open(kbId: string) {
  void router.push(`/admin/knowledge/${kbId}`)
}

onMounted(() => {
  kbStore.loadAdminList().catch((err) => ElMessage.error(apiErrorMessage(err)))
})
</script>

<template>
  <div class="zc-page zc-fade-up">
    <div class="zc-page-header">
      <div>
        <h1 class="zc-page-title">知识库管理</h1>
        <p class="zc-page-subtitle">创建知识库、上传文档、查看解析状态与只读 Wiki。</p>
      </div>
      <button class="zc-btn zc-btn--primary" type="button" data-testid="kb-create-open" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建知识库
      </button>
    </div>

    <div v-loading="kbStore.loading" class="kb-grid">
      <button
        v-for="kb in kbStore.knowledgeBases"
        :key="kb.id"
        class="kb-card"
        type="button"
        data-testid="kb-card"
        @click="open(kb.id)"
      >
        <div class="kb-card__top">
          <span class="kb-card__icon"><el-icon><Collection /></el-icon></span>
          <span class="zc-chip" :class="kb.retrieval_mode === 'hybrid' ? 'zc-chip--primary' : ''">
            {{ kb.retrieval_mode === 'hybrid' ? '混合检索' : '稠密检索' }}
          </span>
        </div>
        <h2>{{ kb.name }}</h2>
        <p>{{ kb.description || '暂无描述' }}</p>
        <div class="kb-card__stats">
          <span><el-icon><Document /></el-icon>{{ kb.document_count }} 份文档</span>
          <span><el-icon><Reading /></el-icon>{{ kb.chunk_count }} 个片段</span>
        </div>
        <div class="kb-card__foot">
          <span>切块 {{ kb.default_chunk_size }} / 重叠 {{ kb.default_chunk_overlap }}</span>
          <span class="kb-card__delete" @click.stop="remove(kb.id, kb.name)">
            <el-icon><Delete /></el-icon>
          </span>
        </div>
      </button>

      <div v-if="!kbStore.loading && kbStore.knowledgeBases.length === 0" class="zc-empty kb-empty">
        <span class="zc-empty__icon"><el-icon><Collection /></el-icon></span>
        <p>还没有知识库</p>
        <small>创建第一个知识库，然后上传 PDF、PPTX、Markdown 或图片。</small>
        <button class="zc-btn zc-btn--primary" type="button" @click="openCreate">新建知识库</button>
      </div>
    </div>

    <el-dialog v-model="dialogOpen" title="新建知识库" width="520px" data-testid="kb-create-dialog">
      <div class="create-form">
        <label class="zc-label" for="kb-name">知识库名称</label>
        <input id="kb-name" v-model="form.name" class="zc-input" placeholder="例如：西部计划政策库" data-testid="kb-create-name" />

        <label class="zc-label create-form__gap" for="kb-desc">描述</label>
        <textarea id="kb-desc" v-model="form.description" class="zc-input create-form__textarea" placeholder="简单说明这个知识库包含什么" />

        <div class="create-form__row">
          <div>
            <label class="zc-label">切块大小（字符）</label>
            <el-input-number v-model="form.default_chunk_size" :min="100" :max="4000" :step="100" />
          </div>
          <div>
            <label class="zc-label">重叠大小（字符）</label>
            <el-input-number v-model="form.default_chunk_overlap" :min="0" :max="1000" :step="20" />
          </div>
        </div>

        <label class="zc-label create-form__gap">检索模式</label>
        <el-radio-group v-model="form.retrieval_mode">
          <el-radio-button value="hybrid">混合检索（推荐）</el-radio-button>
          <el-radio-button value="dense">稠密检索</el-radio-button>
        </el-radio-group>
        <p class="zc-hint">混合检索 = bge-m3 语义向量 + Milvus BM25 关键词检索。</p>
      </div>
      <template #footer>
        <button class="zc-btn" type="button" @click="dialogOpen = false">取消</button>
        <button class="zc-btn zc-btn--primary" type="button" :disabled="saving" data-testid="kb-create-submit" @click="create">
          {{ saving ? '创建中…' : '创建' }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  min-height: 240px;
}

.kb-card {
  display: flex;
  flex-direction: column;
  padding: 20px;
  border: 1px solid var(--zc-line);
  border-radius: var(--zc-radius-lg);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--zc-shadow-card);
  text-align: left;
  cursor: pointer;
  transition:
    transform var(--zc-transition),
    box-shadow var(--zc-transition),
    border-color var(--zc-transition);
}

.kb-card:hover {
  border-color: #d8d2ff;
  box-shadow: var(--zc-shadow-lift);
  transform: translateY(-3px);
}

.kb-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kb-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 13px;
  color: var(--zc-primary);
  background: var(--zc-primary-soft);
  font-size: 20px;
}

.kb-card h2 {
  margin-top: 15px;
  font-size: 17px;
  font-weight: 780;
  letter-spacing: -0.02em;
}

.kb-card p {
  display: -webkit-box;
  margin-top: 5px;
  overflow: hidden;
  color: var(--zc-muted);
  font-size: 12px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.kb-card__stats {
  display: flex;
  gap: 14px;
  margin-top: 16px;
  color: var(--zc-ink-soft);
  font-size: 11.5px;
}

.kb-card__stats span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.kb-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--zc-line);
  color: var(--zc-muted-2);
  font-size: 10.5px;
}

.kb-card__delete {
  display: inline-flex;
  padding: 4px;
  border-radius: 7px;
  cursor: pointer;
}

.kb-card__delete:hover {
  color: var(--zc-danger);
  background: var(--zc-danger-soft);
}

.kb-empty {
  grid-column: 1 / -1;
}

.kb-empty small {
  margin-bottom: 14px;
}

.create-form {
  display: flex;
  flex-direction: column;
}

.create-form__gap {
  margin-top: 15px;
}

.create-form__textarea {
  min-height: 78px;
  resize: vertical;
}

.create-form__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 15px;
}
</style>
