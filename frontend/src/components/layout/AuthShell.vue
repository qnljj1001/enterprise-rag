<script setup lang="ts">
defineProps<{
  eyebrow?: string
  title: string
  subtitle: string
}>()
</script>

<template>
  <div class="app-canvas auth">
    <div class="aurora aurora--violet" aria-hidden="true" />
    <div class="aurora aurora--cyan" aria-hidden="true" />

    <section class="auth__visual">
      <div class="auth__brand">
        <span class="auth__mark">知</span>
        <span>
          <strong>知策</strong>
          <small>政策知识问答</small>
        </span>
      </div>

      <div class="auth__headline">
        <p class="auth__eyebrow">ENTERPRISE KNOWLEDGE RAG</p>
        <h1>把散落的资料，<br /><span class="zc-gradient-text">变成可追问的答案。</span></h1>
        <p class="auth__lead">
          多知识库检索、可追溯引用、流式回答。让每一条结论都能回到原文。
        </p>
      </div>

      <ul class="auth__points">
        <li><span>01</span> 混合检索：bge-m3 语义 + BM25 关键词</li>
        <li><span>02</span> 回答带来源：文件名、页码、片段可核验</li>
        <li><span>03</span> 权限分离：管理员维护知识，用户专注提问</li>
      </ul>

      <div class="auth__orb auth__orb--one" aria-hidden="true" />
      <div class="auth__orb auth__orb--two" aria-hidden="true" />
    </section>

    <section class="auth__panel">
      <div class="auth__card zc-card zc-fade-up">
        <p class="auth__eyebrow">{{ eyebrow || 'WELCOME' }}</p>
        <h2>{{ title }}</h2>
        <p class="auth__subtitle">{{ subtitle }}</p>
        <slot />
      </div>
    </section>
  </div>
</template>

<style scoped>
.auth {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(420px, 0.95fr);
  min-height: 100vh;
}

.auth__visual {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 38px;
  padding: 64px clamp(40px, 7vw, 110px);
  overflow: hidden;
  color: #fff;
  background:
    radial-gradient(600px 420px at 18% 10%, rgba(255, 255, 255, 0.2), transparent 60%),
    linear-gradient(145deg, #17183f 0%, #2b2470 45%, #4c3ed6 100%);
}

.auth__brand {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.auth__brand span:last-child {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.auth__brand strong {
  font-size: 17px;
  letter-spacing: 0.08em;
}

.auth__brand small {
  color: rgba(255, 255, 255, 0.66);
  font-size: 10.5px;
  letter-spacing: 0.12em;
}

.auth__mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 19px;
  font-weight: 800;
  backdrop-filter: blur(8px);
}

.auth__headline {
  position: relative;
  z-index: 1;
  max-width: 560px;
}

.auth__eyebrow {
  margin: 0 0 12px;
  color: var(--zc-primary);
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.18em;
}

.auth__visual .auth__eyebrow {
  color: rgba(255, 255, 255, 0.55);
}

.auth__headline h1 {
  margin: 0;
  font-size: clamp(34px, 4.2vw, 58px);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.12;
}

.auth__headline h1 .zc-gradient-text {
  background: linear-gradient(100deg, #c4b5fd 0%, #a5f3fc 60%, #fbcfe8 100%);
  -webkit-background-clip: text;
  background-clip: text;
}

.auth__lead {
  max-width: 480px;
  margin-top: 20px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 14.5px;
  line-height: 1.8;
}

.auth__points {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 12px;
  max-width: 520px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.auth__points li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.07);
  color: rgba(255, 255, 255, 0.82);
  font-size: 12.5px;
  backdrop-filter: blur(10px);
}

.auth__points span {
  color: #a5f3fc;
  font-family: var(--zc-font-mono);
  font-size: 10px;
  font-weight: 700;
}

.auth__orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
  pointer-events: none;
}

.auth__orb--one {
  right: -90px;
  bottom: -100px;
  width: 300px;
  height: 300px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: radial-gradient(circle at 30% 30%, rgba(34, 211, 238, 0.35), transparent 68%);
}

.auth__orb--two {
  top: 12%;
  right: 8%;
  width: 120px;
  height: 120px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  animation: zc-float 12s ease-in-out infinite alternate;
}

.auth__panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  background: rgba(247, 247, 254, 0.7);
}

.auth__card {
  width: min(420px, 100%);
  padding: 38px 36px 32px;
}

.auth__card h2 {
  margin: 0;
  font-size: 27px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.auth__subtitle {
  margin: 8px 0 26px;
  color: var(--zc-muted);
  font-size: 13px;
}

@media (max-width: 980px) {
  .auth {
    grid-template-columns: 1fr;
  }
  .auth__visual {
    display: none;
  }
  .auth__panel {
    min-height: 100vh;
    padding: 28px 16px;
  }
  .auth__card {
    padding: 30px 22px 26px;
  }
}
</style>
