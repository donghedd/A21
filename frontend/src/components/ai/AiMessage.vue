<template>
  <div class="ai-message" :class="{ 'is-user': role === 'user', 'is-loading': isLoadingState }">
    <!-- 加载状态：显示"正在加载" -->
    <transition name="fade" mode="out-in">
      <div v-if="isInterruptedState" key="interrupted" class="loading-state interrupted">
        <el-icon><Warning /></el-icon>
        <span class="loading-text">回答已中断</span>
      </div>
      <div v-else-if="isLoadingState" key="loading" class="loading-state">
        <span class="loading-spinner"></span>
        <span class="loading-text">正在加载</span>
      </div>

      <!-- 内容状态：显示思考和内容 -->
      <div v-else key="content" class="content-wrapper">
        <!-- 思考过程 -->
        <div v-if="showThinking" class="thinking-block" :class="{ 'is-collapsed': !expanded && hasContent }">
          <div class="thinking-header" @click="toggleThinking">
            <div class="thinking-label">
              <span v-if="isThinking" class="thinking-spinner"></span>
              <el-icon v-else><CircleCheck /></el-icon>
              <span v-if="thinkingDuration">
                思考了 {{ formatThinkingDuration(thinkingDuration) }}
              </span>
              <span v-else-if="isThinking">思考中...</span>
              <span v-else>思考过程</span>
            </div>
            <el-icon class="thinking-arrow" :class="{ open: expanded }">
              <ArrowRight />
            </el-icon>
          </div>
          <transition name="collapse">
            <div v-show="expanded" class="thinking-content">
              <div v-html="renderMarkdown(thinking || thinkingContent)"></div>
            </div>
          </transition>
          <!-- 收缩时显示预览 -->
          <div v-if="!expanded && hasContent" class="thinking-preview">
            <span>思考完成，已生成回答...</span>
          </div>
        </div>

        <!-- 消息内容 -->
        <div v-if="showContent" class="message-content" v-html="renderedContent" @click="handleContentClick"></div>

        <!-- 来源引用 -->
        <SourcesPanel
          v-if="showSources"
          :sources="sources"
          @source-click="handleSourceClick"
        />
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ArrowRight, CircleCheck, Warning } from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import plaintext from 'highlight.js/lib/languages/plaintext'
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import SourcesPanel from './SourcesPanel.vue'

const props = defineProps({
  content: { type: String, default: '' },
  thinking: { type: String, default: '' },
  thinkingContent: { type: String, default: '' },
  thinkingDuration: { type: Number, default: 0 },
  isThinking: { type: Boolean, default: false },
  sources: { type: Array, default: () => [] },
  role: { type: String, default: 'assistant' },
  loading: { type: Boolean, default: false },
  interrupted: { type: Boolean, default: false },
  enableTyping: { type: Boolean, default: false },
  typingSpeed: { type: Number, default: 30 }
})

const emit = defineEmits(['source-click'])

// 状态
const expanded = ref(true) // 默认展开
const displayContent = ref('')
const isTyping = ref(false)

hljs.registerLanguage('plaintext', plaintext)
hljs.registerLanguage('text', plaintext)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('sh', bash)
hljs.registerLanguage('shell', bash)
hljs.registerLanguage('css', css)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('md', markdown)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('xml', xml)

// 配置 marked
marked.setOptions({
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return escapeHtml(code)
  },
  breaks: true,
  gfm: true
})

// 计算属性
const hasContent = computed(() => !!props.content?.trim())
const hasThinking = computed(() => !!(props.thinking || props.thinkingContent)?.trim())

// 加载状态：loading为true且没有内容和思考内容时显示
const isLoadingState = computed(() => {
  return props.loading && !hasContent.value && !hasThinking.value
})

const isInterruptedState = computed(() => {
  return props.interrupted && !hasContent.value && !hasThinking.value
})

const showThinking = computed(() => {
  return hasThinking.value && props.role !== 'user'
})

const showContent = computed(() => {
  return hasContent.value
})

const showSources = computed(() => {
  // 只在有内容且不在思考中的时候显示来源
  return props.sources?.length > 0 && hasContent.value && !props.isThinking
})

const renderedContent = computed(() => {
  const contentToRender = props.enableTyping && isTyping.value
    ? displayContent.value
    : props.content
  return renderMarkdown(contentToRender)
})

// 方法
function toggleThinking() {
  expanded.value = !expanded.value
}

function renderMarkdown(content) {
  if (!content) return ''

  // 渲染 markdown
  let html = marked(content)

  // 使引用标记 [1], [2] 等可点击
  html = html.replace(
    /\[(\d+)\]/g,
    '<span class="citation-marker" data-citation="$1">[$1]</span>'
  )

  return html
}

function escapeHtml(content) {
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function formatThinkingDuration(seconds) {
  if (!seconds || seconds < 1) return '不到 1 秒'
  if (seconds < 60) return `${seconds} 秒`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return secs > 0 ? `${mins} 分 ${secs} 秒` : `${mins} 分钟`
}

function handleSourceClick(source) {
  emit('source-click', source)
}

// 事件委托: 处理引用标记点击
function handleContentClick(event) {
  const target = event.target.closest('.citation-marker')
  if (!target) return

  const citationId = target.getAttribute('data-citation')
  if (!citationId) return

  // 从 sources 中查找匹配的来源（id 或序号匹配）
  const source = props.sources?.find(s =>
    String(s.id) === citationId || String(props.sources.indexOf(s) + 1) === citationId
  )

  if (source) {
    emit('source-click', source)
  }
}

// 打字机效果
async function typeContent(content) {
  if (!props.enableTyping || !content) {
    displayContent.value = content
    return
  }

  isTyping.value = true
  displayContent.value = ''

  const chars = content.split('')
  for (let i = 0; i < chars.length; i++) {
    displayContent.value += chars[i]
    await new Promise(resolve => setTimeout(resolve, props.typingSpeed))
  }

  isTyping.value = false
}

// 监听
watch(() => props.content, (newVal, oldVal) => {
  if (newVal && newVal !== oldVal && props.enableTyping) {
    typeContent(newVal)
  } else {
    displayContent.value = newVal
  }
}, { immediate: true })

// 关键：当有内容时自动收缩思考过程
watch(() => props.content, (newVal) => {
  if (newVal?.trim() && hasThinking.value) {
    expanded.value = false
  }
})

// 思考开始时自动展开
watch(() => props.isThinking, (val) => {
  if (val) expanded.value = true
})
</script>

<style scoped lang="scss">
// 覆盖外层 Bubble 组件的灰色背景
:deep(.el-bubble-content) {
  background-color: #FFFFFF !important;
}

.ai-message {
  line-height: 1.75;
  font-size: 15px;
  color: #312E4A;
  min-height: 48px;
  padding: 16px 18px; // 保留内边距给底部按钮
  box-sizing: border-box;

  // AI 消息：白色背景 + 边框 + 阴影
  &.is-assistant,
  &:not(.is-user) {
    display: block;
    background: #FFFFFF;
    border-radius: 14px;
    margin: 0;
    padding: 16px 18px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(0, 0, 0, 0.06);
    width: auto; // 由内容决定
    max-width: 100%; // 最大85%
    word-break: break-word;
  }

  // 用户消息：白色背景 + 边框 + 阴影，自适应内容宽度
  &.is-user {
    display: block;
    background: #FFFFFF;
    border-radius: 14px;
    margin: 0;
    padding: 16px 18px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(0, 0, 0, 0.06);
    color: #1E1B4B;
    width: auto; // 由内容决定
    max-width: 100%; // 最大85%
    word-break: break-word;
  }

  // 加载状态样式
  &.is-loading {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 60px;
  }
}

// 加载状态
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 8px 0;

  .loading-spinner {
    display: inline-block;
    width: 18px;
    height: 18px;
    border: 2.5px solid rgba(99, 102, 241, 0.15);
    border-top-color: #6366F1;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  .loading-text {
    color: #6366F1;
    font-size: 14px;
    font-weight: 500;
  }

  &.interrupted {
    .el-icon {
      color: #F59E0B;
      font-size: 18px;
    }

    .loading-text {
      color: #D97706;
    }
  }
}

// 内容包装器
.content-wrapper {
  width: 100%;
}

// 思考块样式
.thinking-block {
  margin-bottom: 18px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.03), rgba(139, 92, 246, 0.04));
  transition: all 0.3s ease;

  &.is-collapsed {
    opacity: 0.85;
    margin-bottom: 12px;
  }
}

.thinking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 16px;
  cursor: pointer;
  user-select: none;
  transition: all 0.25s ease;

  &:hover {
    background: rgba(99, 102, 241, 0.05);
  }
}

.thinking-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #5B5580;
  font-weight: 600;

  .el-icon {
    color: #8B5CF6;
    font-size: 16px;
  }
}

.thinking-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2.5px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366F1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.thinking-arrow {
  font-size: 14px;
  color: #A5A3C9;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &.open {
    transform: rotate(90deg);
  }
}

.thinking-content {
  padding: 14px 18px;
  border-top: 1px solid rgba(99, 102, 241, 0.08);
  font-size: 13.5px;
  color: #4B4870;
  line-height: 1.65;
  max-height: 400px;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.7);

  :deep(p) {
    margin: 7px 0;
  }

  :deep(code) {
    background: rgba(99, 102, 241, 0.08);
    padding: 2px 7px;
    border-radius: 5px;
    font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
    font-size: 12.5px;
    color: #6366F1;
  }

  :deep(pre) {
    background: #1E1B2E;
    padding: 16px;
    border-radius: 10px;
    overflow-x: auto;
    margin: 12px 0;

    code {
      background: transparent;
      color: #EDE9FE;
      padding: 0;
    }
  }
}

// 思考预览（收缩时显示）
.thinking-preview {
  padding: 8px 16px;
  font-size: 12px;
  color: #8B5CF6;
  background: rgba(139, 92, 246, 0.05);
  border-top: 1px solid rgba(99, 102, 241, 0.08);

  span {
    display: flex;
    align-items: center;
    gap: 6px;

    &::before {
      content: '';
      display: inline-block;
      width: 6px;
      height: 6px;
      background: #8B5CF6;
      border-radius: 50%;
    }
  }
}

// 消息内容样式
.message-content {
  word-break: break-word;

  :deep(p) {
    margin: 10px 0;

    &:first-child { margin-top: 0; }
    &:last-child { margin-bottom: 0; }
  }

  :deep(ul), :deep(ol) {
    padding-left: 24px;
    margin: 10px 0;
  }

  :deep(li) {
    margin: 5px 0;
  }

  :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
    margin: 18px 0 10px;
    font-weight: 700;
    color: #1E1B4B;
  }

  :deep(h1) { font-size: 1.5em; }
  :deep(h2) { font-size: 1.32em; }
  :deep(h3) { font-size: 1.15em; }

  :deep(blockquote) {
    border-left: 3px solid #8B5CF6;
    padding-left: 16px;
    margin: 14px 0;
    color: #5B5580;
    font-style: italic;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;

    th, td {
      border: 1px solid rgba(99, 102, 241, 0.1);
      padding: 10px 14px;
      text-align: left;
    }

    th {
      background: rgba(99, 102, 241, 0.06);
      font-weight: 600;
      color: #1E1B4B;
    }

    tr:nth-child(even) {
      background: rgba(99, 102, 241, 0.02);
    }
  }

  // 代码块样式
  :deep(pre) {
    background: linear-gradient(135deg, #1E1B2E, #2D2640);
    padding: 18px;
    border-radius: 12px;
    overflow-x: auto;
    margin: 14px 0;
    position: relative;
    box-shadow: 0 4px 20px rgba(30, 27, 46, 0.3);

    code {
      color: #EDE9FE;
      background: transparent;
      padding: 0;
      font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
      font-size: 13px;
      line-height: 1.65;
    }

    .hljs-keyword { color: #C4B5FD; }
    .hljs-string { color: #A5D6A7; }
    .hljs-number { color: #FBBF24; }
    .hljs-function { color: #93C5FD; }
    .hljs-comment { color: #6B7280; font-style: italic; opacity: 0.7; }
    .hljs-operator { color: #67E8F9; }
    .hljs-punctuation { color: #C4B5FD; opacity: 0.6; }
  }

  // 行内代码
  :deep(code:not(pre code)) {
    background: rgba(99, 102, 241, 0.08);
    color: #7C3AED;
    padding: 2px 7px;
    border-radius: 5px;
    font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    font-weight: 500;
  }

  // 引用标记样式
  :deep(.citation-marker) {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 5px;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.08));
    color: #6366F1;
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 5px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'SF Mono', 'Menlo', monospace;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    margin: 0 2px;
    vertical-align: middle;

    &:hover {
      background: linear-gradient(135deg, #6366F1, #8B5CF6);
      color: white;
      border-color: transparent;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
    }
  }

  // 链接样式
  :deep(a) {
    color: #6366F1;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;

    &:hover {
      color: #4F46E5;
      text-decoration: underline;
      text-underline-offset: 3px;
    }
  }

  // 图片样式
  :deep(img) {
    max-width: 100%;
    border-radius: 12px;
    margin: 14px 0;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  }

  // 分割线
  :deep(hr) {
    border: none;
    border-top: 1px solid rgba(99, 102, 241, 0.1);
    margin: 18px 0;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// 淡入淡出过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(5px);
}

// 折叠动画
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  max-height: 400px;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>

<!-- 非scoped样式：强制覆盖Bubble组件的背景为透明 -->
<style>
.el-bubble-content-wrapper .el-bubble-content {
  background-color: transparent !important;
  box-shadow: none !important;
  border: none !important;
}

.el-bubble-content-wrapper .el-bubble-footer {
  background-color: transparent !important;
}
</style>
