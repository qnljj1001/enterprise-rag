<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  Delete,
  EditPen,
  Plus,
  Promotion,
  Setting,
  VideoPause,
} from '@element-plus/icons-vue'

import { listKnowledgeBases } from '@/api/kb'
import type { Citation, KnowledgeBase } from '@/api/types'
import { formatDate, formatScore } from '@/utils/format'
import { renderMarkdown } from '@/utils/markdown'
import { useChatStore } from '@/stores/chat'
import { useMetaStore } from '@/stores/meta'

const chat = useChatStore()
const meta = useMetaStore()

const kbs = ref<KnowledgeBase[]>([])
const kbsLoading = ref(false)
const input = ref('')
const settingsOpen = ref(false)
const sidebarOpen = ref(false)
const citationOpen = ref(false)
const activeCitation = ref<Citation | null>(null)
const transcript = ref<HTMLElement | null>(null)
const composer = ref<HTMLTextAreaElement | null>(null)

const suggestions = [
  '西部计划志愿者的服务期一般是几年？',
  '服务期间的生活补贴由谁发放？',
  '服务期满后在考研方面有什么优惠？',
]

const hasMessages = computed(() => chat.messages.length > 0)
const currentTitle = computed(() => chat.currentSession?.title || '新对话')
const readyKbs = computed(() => kbs.value)

async function loadKbs() {
  kbsLoading.value = true
  try {
    kbs.value = await listKnowledgeBases()
    const valid = new Set(kbs.value.map((item) => item.id))
    chat.settings.kb_ids = chat.settings.kb_ids.filter((id) => valid.has(id))
    if (chat.settings.kb_ids.length === 0) {
      chat.settings.kb_ids = kbs.value.map((item) => item.id)
    }
  } catch (err) {
    ElMessage.error((err as Error).message || '加载知识库失败')
  } finally {
    kbsLoading.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  const element = transcript.value
  if (element) element.scrollTop = element.scrollHeight
}

watch(
  () => [chat.messages.length, chat.messages.at(-1)?.content],
  () => {
    void scrollToBottom()
  },
)

watch(settingsOpen, (open) => {
  if (open) void meta.load()
})

async function submit() {
  const text = input.value.trim()
  if (!text) return
  if (chat.settings.kb_ids.length === 0) {
    ElMessage.warning('请至少选择一个知识库。')
    return
  }
  input.value = ''
  await chat.send(text)
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void submit()
  }
}

async function newSession() {
  if (chat.streaming) chat.stop()
  await chat.createSession()
  sidebarOpen.value = false
  await nextTick()
  composer.value?.focus()
}

async function selectSession(id: string) {
  await chat.selectSession(id)
  sidebarOpen.value = false
  await scrollToBottom()
}

async function renameCurrent() {
  const session = chat.currentSession
  if (!session) return
  try {
    const result = await ElMessageBox.prompt('输入新的会话名称', '重命名会话', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: session.title,
      inputValidator: (value) => (value?.trim() ? true : '名称不能为空'),
    })
    await chat.renameSession(session.id, result.value.trim())
  } catch {
    // 取消
  }
}

async function removeCurrent() {
  const session = chat.currentSession
  if (!session) return
  try {
    await ElMessageBox.confirm('删除后会话与消息不可恢复，确定删除吗？', '删除会话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await chat.removeSession(session.id)
}

function useSuggestion(text: string) {
  input.value = text
  void submit()
}

function onCiteClick(event: MouseEvent, message: { citations: Citation[] }) {
  const target = event.target as HTMLElement | null
  const node = target?.closest('[data-cite]') as HTMLElement | null
  if (!node) return
  const index = Number(node.dataset.cite) - 1
  const citation = message.citations[index]
  if (citation) openCitation(citation)
}

function openCitation(citation: Citation) {
  activeCitation.value = citation
  citationOpen.value = true
  if (chat.streaming) chat.stop()
}

function citationLabel(citation: Citation, index: number) {
  return `[${index + 1}] ${citation.filename}`
}

onMounted(async () => {
  await Promise.all([loadKbs(), chat.loadSessions()])
  await scrollToBottom()
})
</script>

<template>
  <div class="chat">
    <aside class="chat-sidebar" :class="{ 'is-open': sidebarOpen }">
      <div class="chat-sidebar__top">
        <button class="zc-btn zc-btn--primary new-session" type="button" data-testid="chat-new-session" @click="newSession">
          <el-icon><Plus /></el-icon>
          新建对话
        </button>
        <button class="sidebar-close" type="button" aria-label="关闭侧栏" @click="sidebarOpen = false">
          ×
        </button>
      </div>

      <div class="session-list" data-testid="chat-sessions">
        <button
          v-for="session in chat.sessions"
          :key="session.id"
          class="session"
          :class="{ 'is-active': session.id === chat.currentSessionId }"
          type="button"
          @click="selectSession(session.id)"
        >
          <span class="session__icon"><el-icon><ChatDotRound /></el-icon></span>
          <span class="session__body">
            <span class="session__title">{{ session.title }}</span>
            <span class="session__time">{{ formatDate(session.updated_at) }}</span>
          </span>
        </button>
        <div v-if="chat.sessions.length === 0" class="session-empty">
          <span class="zc-empty__icon"><el-icon><ChatDotRound /></el-icon></span>
          <p>还没有对话</p>
          <small>点击上方“新建对话”开始</small>
        </div>
      </div>

      <div class="chat-sidebar__bottom">
        <span class="side-note">DeepSeek Flash · bge-m3</span>
        <span class="side-note">知识库问答</span>
      </div>
    </aside>

    <div v-if="sidebarOpen" class="sidebar-mask" @click="sidebarOpen = false" />

    <section class="chat-main">
      <header class="chat-head">
        <button class="mobile-sidebar-btn" type="button" aria-label="打开会话列表" @click="sidebarOpen = true">
          <span />
          <span />
          <span />
        </button>
        <div class="chat-head__title">
          <h1>{{ currentTitle }}</h1>
          <p>
            <span class="dot" :class="{ 'dot--live': chat.streaming }" />
            {{ chat.streaming ? '正在生成回答…' : '选择知识库后开始提问' }}
          </p>
        </div>
        <div class="chat-head__tools">
          <el-select
            v-model="chat.settings.kb_ids"
            class="kb-select"
            multiple
            collapse-tags
            collapse-tags-tooltip
            :max-collapse-tags="2"
            :loading="kbsLoading"
            placeholder="选择知识库"
            data-testid="chat-kb-select"
          >
            <el-option v-for="kb in readyKbs" :key="kb.id" :label="kb.name" :value="kb.id" />
          </el-select>
          <button class="zc-btn icon-btn" type="button" title="重命名会话" data-testid="chat-rename" :disabled="!chat.currentSession" @click="renameCurrent">
            <el-icon><EditPen /></el-icon>
          </button>
          <button class="zc-btn icon-btn" type="button" title="删除会话" data-testid="chat-delete" :disabled="!chat.currentSession" @click="removeCurrent">
            <el-icon><Delete /></el-icon>
          </button>
          <button class="zc-btn icon-btn" type="button" title="推理参数" data-testid="chat-settings" @click="settingsOpen = true">
            <el-icon><Setting /></el-icon>
          </button>
        </div>
      </header>

      <div ref="transcript" class="transcript" data-testid="chat-transcript">
        <div v-if="!hasMessages" class="welcome zc-fade-up">
          <div class="welcome__mark">知</div>
          <h2>你好，我是知策</h2>
          <p>选择知识库，问一个具体问题。我会基于检索到的资料回答，并给出可核验的来源。</p>
          <div class="suggestions">
            <button
              v-for="item in suggestions"
              :key="item"
              class="suggestion"
              type="button"
              @click="useSuggestion(item)"
            >
              <span>{{ item }}</span>
              <el-icon><Promotion /></el-icon>
            </button>
          </div>
          <p v-if="readyKbs.length === 0" class="welcome__empty">
            当前还没有可用知识库，请先联系管理员创建并上传文档。
          </p>
        </div>

        <div v-else class="messages">
          <article
            v-for="message in chat.messages"
            :key="message.id"
            class="message"
            :class="`message--${message.role}`"
            data-testid="chat-message"
          >
            <div v-if="message.role === 'assistant'" class="message__avatar">知</div>
            <div class="message__body">
              <div v-if="message.role === 'user'" class="message__bubble message__bubble--user">
                {{ message.content }}
              </div>
              <div v-else class="message__bubble message__bubble--assistant">
                <div
                  v-if="message.content"
                  class="markdown"
                  v-html="renderMarkdown(message.content)"
                  @click="onCiteClick($event, message)"
                />
                <div v-else class="typing" aria-label="正在生成">
                  <span /><span /><span />
                </div>
                <span v-if="message.status === 'streaming' && message.content" class="cursor" aria-hidden="true" />
                <p v-if="message.status === 'error'" class="message-error">
                  {{ message.error_message || '回答失败，请重试。' }}
                </p>
                <div v-if="message.citations.length > 0" class="citations">
                  <button
                    v-for="(citation, index) in message.citations"
                    :key="citation.chunk_id"
                    class="citation"
                    type="button"
                    data-testid="chat-citation"
                    @click="openCitation(citation)"
                  >
                    <span class="citation__index">{{ index + 1 }}</span>
                    <span class="citation__text">
                      {{ citation.filename }}
                      <small v-if="citation.page_no">第 {{ citation.page_no }} 页</small>
                    </span>
                  </button>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>

      <div v-if="chat.error" class="chat-error" role="alert">{{ chat.error }}</div>

      <div class="composer-wrap">
        <div class="composer">
          <textarea
            ref="composer"
            v-model="input"
            class="composer__input"
            rows="1"
            placeholder="输入问题，Enter 发送，Shift + Enter 换行"
            data-testid="chat-composer"
            @keydown="onKeydown"
          />
          <div class="composer__actions">
            <span class="composer__hint">回答仅基于所选知识库</span>
            <button
              v-if="chat.streaming"
              class="zc-btn zc-btn--danger stop-btn"
              type="button"
              data-testid="chat-stop"
              @click="chat.stop()"
            >
              <el-icon><VideoPause /></el-icon>
              停止
            </button>
            <button
              v-else
              class="zc-btn zc-btn--primary send-btn"
              type="button"
              data-testid="chat-send"
              :disabled="!input.trim()"
              @click="submit"
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </section>

    <el-drawer v-model="settingsOpen" title="推理参数" direction="rtl" size="360px">
      <div class="settings">
        <div class="setting-row">
          <span class="zc-label">大模型</span>
          <span class="zc-chip zc-chip--primary">{{ meta.meta?.llm_model || 'deepseek-flash' }}</span>
          <p class="zc-hint">固定使用 DeepSeek Flash；系统不提供模型切换。</p>
        </div>

        <div class="setting-row">
          <span class="zc-label">温度 temperature：{{ chat.settings.temperature.toFixed(1) }}</span>
          <el-slider v-model="chat.settings.temperature" :min="0" :max="2" :step="0.1" />
          <p class="zc-hint">越低越稳定，越高越发散。</p>
        </div>

        <div class="setting-row">
          <span class="zc-label">Top P：{{ chat.settings.top_p.toFixed(2) }}</span>
          <el-slider v-model="chat.settings.top_p" :min="0.1" :max="1" :step="0.05" />
          <p class="zc-hint">{{ meta.meta?.top_p_note || '受 DeepSeek 当前 API 限制，非思考模式下不生效。' }}</p>
        </div>

        <div class="setting-row">
          <span class="zc-label">最长输出 token</span>
          <el-input-number v-model="chat.settings.max_tokens" :min="128" :max="4096" :step="128" />
        </div>

        <div class="setting-row">
          <span class="zc-label">历史对话轮数</span>
          <el-input-number v-model="chat.settings.history_rounds" :min="0" :max="20" />
          <p class="zc-hint">默认 5 轮；0 表示不携带历史。</p>
        </div>

        <button class="zc-btn zc-btn--primary settings__close" type="button" @click="settingsOpen = false">
          完成
        </button>
      </div>
    </el-drawer>

    <el-drawer v-model="citationOpen" title="来源详情" direction="rtl" size="420px">
      <div v-if="activeCitation" class="citation-detail">
        <div class="citation-detail__meta">
          <span class="zc-chip zc-chip--primary">{{ activeCitation.kb_name }}</span>
          <span class="zc-chip">{{ activeCitation.filename }}</span>
          <span v-if="activeCitation.page_no" class="zc-chip">第 {{ activeCitation.page_no }} 页</span>
          <span class="zc-chip">相关度 {{ formatScore(activeCitation.score) }}</span>
        </div>
        <p class="citation-detail__label">原文片段</p>
        <div class="citation-detail__content">{{ activeCitation.content }}</div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.chat {
  display: flex;
  width: 100%;
  min-height: 0;
  height: calc(100vh - var(--zc-header-height));
}

.chat-sidebar {
  display: flex;
  flex: none;
  flex-direction: column;
  width: 272px;
  padding: 18px 14px;
  border-right: 1px solid var(--zc-line);
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(16px);
}

.chat-sidebar__top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.new-session {
  flex: 1;
}

.sidebar-close {
  display: none;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 10px;
  color: var(--zc-muted);
  background: transparent;
  font-size: 22px;
  cursor: pointer;
}

.session-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  margin-top: 18px;
  overflow-y: auto;
}

.session {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition:
    background var(--zc-transition),
    border-color var(--zc-transition);
}

.session:hover {
  background: rgba(109, 93, 246, 0.06);
}

.session.is-active {
  border-color: #ddd8ff;
  background: var(--zc-primary-soft);
}

.session__icon {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  color: var(--zc-primary);
  background: #fff;
  font-size: 14px;
}

.session__body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.session__title {
  overflow: hidden;
  color: var(--zc-ink-soft);
  font-size: 12.5px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session__time {
  color: var(--zc-muted-2);
  font-size: 10px;
}

.session-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 36px 12px;
  color: var(--zc-muted);
  text-align: center;
}

.session-empty p {
  margin-top: 8px;
  font-size: 12.5px;
  font-weight: 650;
}

.session-empty small {
  color: var(--zc-muted-2);
  font-size: 10.5px;
}

.chat-sidebar__bottom {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 12px;
  border-top: 1px solid var(--zc-line);
}

.side-note {
  color: var(--zc-muted-2);
  font-size: 10px;
  letter-spacing: 0.03em;
}

.chat-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  background: rgba(255, 255, 255, 0.42);
}

.chat-head {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--zc-line);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
}

.mobile-sidebar-btn {
  display: none;
  flex-direction: column;
  gap: 4px;
  width: 36px;
  height: 36px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--zc-line);
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
}

.mobile-sidebar-btn span {
  width: 15px;
  height: 1.5px;
  border-radius: 2px;
  background: var(--zc-ink-soft);
}

.chat-head__title {
  min-width: 0;
}

.chat-head__title h1 {
  overflow: hidden;
  font-size: 15.5px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-head__title p {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
  color: var(--zc-muted-2);
  font-size: 10.5px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--zc-success);
}

.dot--live {
  background: var(--zc-primary);
  animation: zc-blink 1.2s ease-in-out infinite;
}

.chat-head__tools {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-left: auto;
}

.kb-select {
  width: min(280px, 30vw);
}

.icon-btn {
  width: 36px;
  min-height: 36px;
  padding: 0;
}

.transcript {
  flex: 1;
  padding: 28px max(24px, calc((100% - 880px) / 2));
  overflow-y: auto;
  scroll-behavior: smooth;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 660px;
  margin: 6vh auto 0;
  text-align: center;
}

.welcome__mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 20px;
  color: #fff;
  background: linear-gradient(135deg, #6d5df6 0%, #8b5cf6 52%, #06b6d4 120%);
  box-shadow: 0 18px 40px rgba(109, 93, 246, 0.3);
  font-size: 28px;
  font-weight: 800;
}

.welcome h2 {
  margin-top: 18px;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.welcome p {
  max-width: 520px;
  margin-top: 8px;
  color: var(--zc-muted);
  font-size: 13.5px;
  line-height: 1.8;
}

.suggestions {
  display: grid;
  gap: 9px;
  width: min(560px, 100%);
  margin-top: 24px;
}

.suggestion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 16px;
  border: 1px solid var(--zc-line);
  border-radius: 14px;
  color: var(--zc-ink-soft);
  background: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition:
    transform var(--zc-transition),
    border-color var(--zc-transition),
    box-shadow var(--zc-transition);
}

.suggestion:hover {
  border-color: #d8d2ff;
  box-shadow: var(--zc-shadow-card);
  transform: translateY(-2px);
}

.suggestion .el-icon {
  color: var(--zc-primary);
}

.welcome__empty {
  margin-top: 18px;
  color: var(--zc-warning);
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 22px;
  max-width: 880px;
  margin: 0 auto;
}

.message {
  display: flex;
  gap: 10px;
  animation: zc-fade-up 260ms ease both;
}

.message--user {
  justify-content: flex-end;
}

.message__avatar {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin-top: 2px;
  border-radius: 10px;
  color: #fff;
  background: linear-gradient(135deg, #8b5cf6, #22d3ee);
  font-size: 14px;
  font-weight: 800;
}

.message__body {
  min-width: 0;
  max-width: min(720px, 86%);
}

.message--user .message__body {
  display: flex;
  justify-content: flex-end;
}

.message__bubble {
  position: relative;
  padding: 13px 16px;
  border-radius: 16px;
  font-size: 13.8px;
  line-height: 1.85;
}

.message__bubble--user {
  color: #fff;
  background: linear-gradient(130deg, #6d5df6, #7c5cf0);
  box-shadow: 0 10px 24px rgba(109, 93, 246, 0.18);
}

.message__bubble--assistant {
  border: 1px solid var(--zc-line);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 10px 26px rgba(18, 20, 43, 0.045);
}

.markdown :deep(p) {
  margin: 0 0 10px;
}

.markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown :deep(h1),
.markdown :deep(h2),
.markdown :deep(h3) {
  margin: 14px 0 8px;
  font-size: 15px;
  font-weight: 750;
}

.markdown :deep(ul),
.markdown :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.markdown :deep(li) {
  margin: 3px 0;
}

.markdown :deep(code) {
  padding: 1px 5px;
  border-radius: 5px;
  background: #f2f1ff;
  font-family: var(--zc-font-mono);
  font-size: 12px;
}

.markdown :deep(pre) {
  padding: 12px;
  overflow-x: auto;
  border-radius: 10px;
  background: #17182e;
  color: #e8e7f4;
}

.markdown :deep(blockquote) {
  margin: 10px 0;
  padding-left: 12px;
  border-left: 3px solid #d9d4ff;
  color: var(--zc-muted);
}

.markdown :deep(.cite-ref) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 18px;
  padding: 0 4px;
  border: 0;
  border-radius: 5px;
  color: var(--zc-primary-strong);
  background: var(--zc-primary-soft);
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  vertical-align: 1px;
}

.cursor {
  display: inline-block;
  width: 7px;
  height: 14px;
  margin-left: 2px;
  border-radius: 2px;
  background: var(--zc-primary);
  animation: zc-blink 0.9s step-end infinite;
  vertical-align: -2px;
}

.typing {
  display: inline-flex;
  gap: 4px;
  padding: 4px 0;
}

.typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--zc-primary);
  animation: zc-bounce 1s ease-in-out infinite;
}

.typing span:nth-child(2) {
  animation-delay: 0.14s;
}

.typing span:nth-child(3) {
  animation-delay: 0.28s;
}

@keyframes zc-bounce {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  40% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

.message-error {
  margin-top: 8px;
  color: var(--zc-danger);
  font-size: 12px;
}

.citations {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--zc-line);
}

.citation {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 4px 9px 4px 4px;
  border: 1px solid var(--zc-line);
  border-radius: 999px;
  color: var(--zc-muted);
  background: var(--zc-surface-soft);
  font-size: 10.5px;
  cursor: pointer;
  transition:
    border-color var(--zc-transition),
    background var(--zc-transition);
}

.citation:hover {
  border-color: #d9d4ff;
  background: var(--zc-primary-soft);
}

.citation__index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  color: #fff;
  background: var(--zc-primary);
  font-size: 9px;
  font-weight: 700;
}

.citation__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.citation__text small {
  margin-left: 3px;
  color: var(--zc-muted-2);
}

.chat-error {
  margin: 0 24px 8px;
  padding: 9px 12px;
  border: 1px solid #f3cfcc;
  border-radius: 10px;
  color: var(--zc-danger);
  background: var(--zc-danger-soft);
  font-size: 12.5px;
}

.composer-wrap {
  padding: 10px max(24px, calc((100% - 880px) / 2)) 20px;
}

.composer {
  padding: 12px 14px 10px;
  border: 1px solid var(--zc-line);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 14px 34px rgba(18, 20, 43, 0.07);
  transition:
    border-color var(--zc-transition),
    box-shadow var(--zc-transition);
}

.composer:focus-within {
  border-color: #cfc8ff;
  box-shadow: 0 16px 38px rgba(109, 93, 246, 0.12);
}

.composer__input {
  width: 100%;
  min-height: 44px;
  padding: 2px 2px 8px;
  border: 0;
  outline: none;
  resize: none;
  color: var(--zc-ink);
  background: transparent;
  font-size: 13.5px;
  line-height: 1.7;
}

.composer__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.composer__hint {
  color: var(--zc-muted-2);
  font-size: 10.5px;
}

.send-btn,
.stop-btn {
  min-height: 34px;
  margin-left: auto;
  padding-inline: 18px;
}

.settings {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.setting-row {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.settings__close {
  margin-top: 4px;
}

.citation-detail__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}

.citation-detail__label {
  margin-bottom: 7px;
  color: var(--zc-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.citation-detail__content {
  padding: 14px;
  border: 1px solid var(--zc-line);
  border-radius: 12px;
  color: var(--zc-ink-soft);
  background: var(--zc-surface-soft);
  font-size: 13px;
  line-height: 1.9;
  white-space: pre-wrap;
}

@media (max-width: 980px) {
  .chat-sidebar {
    position: fixed;
    z-index: 45;
    top: var(--zc-header-height);
    bottom: 0;
    left: 0;
    transform: translateX(-102%);
    transition: transform var(--zc-transition);
  }
  .chat-sidebar.is-open {
    transform: translateX(0);
  }
  .sidebar-close,
  .mobile-sidebar-btn {
    display: flex;
  }
  .sidebar-mask {
    position: fixed;
    z-index: 44;
    inset: var(--zc-header-height) 0 0;
    background: rgba(18, 20, 43, 0.28);
    backdrop-filter: blur(2px);
  }
}

@media (max-width: 720px) {
  .chat-head {
    flex-wrap: wrap;
    padding: 12px 14px;
  }
  .chat-head__tools {
    width: 100%;
    margin-left: 0;
  }
  .kb-select {
    flex: 1;
    width: auto;
  }
  .transcript {
    padding: 20px 14px;
  }
  .composer-wrap {
    padding: 8px 12px 14px;
  }
  .message__body {
    max-width: 92%;
  }
  .welcome h2 {
    font-size: 24px;
  }
  .composer__hint {
    display: none;
  }
}
</style>
