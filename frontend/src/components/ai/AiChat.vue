<template>
  <div class="ai-chat-container">
    <!-- 头部区域 -->
    <div class="ai-chat-header">
      <div class="header-left">
        <slot name="header-left">
          <el-button
            v-if="showSidebarToggle"
            :icon="sidebarCollapsed ? Expand : Fold"
            circle
            size="small"
            @click="toggleSidebar"
          />
          <span class="header-title">{{ title }}</span>
        </slot>
      </div>
      
      <div class="header-center">
        <slot name="header-center">
          <!-- 模型选择器 -->
          <el-select
            v-if="showModelSelector"
            v-model="selectedModel"
            placeholder="选择模型"
            class="model-selector"
            :disabled="isStreaming"
          >
            <el-option-group
              v-for="group in modelGroups"
              :key="group.label"
              :label="group.label"
            >
              <el-option
                v-for="model in group.models"
                :key="model.id"
                :label="model.name"
                :value="model.id"
              >
                <div class="model-option">
                  <div class="model-option-info">
                    <span class="model-name">{{ model.name }}</span>
                    <el-tag v-if="model.tag" size="small" effect="plain" class="model-tag">{{ model.tag }}</el-tag>
                  </div>
                </div>
              </el-option>
            </el-option-group>
          </el-select>
        </slot>
      </div>
      
      <div class="header-right">
        <slot name="header-right" />
      </div>
    </div>
    
    <!-- 消息列表区域 -->
    <div class="ai-chat-messages" ref="messagesContainer">
      <!-- 欢迎区域 -->
      <div v-if="showWelcome && messages.length === 0 && !isStreaming" class="welcome-area">
        <slot name="welcome">
          <Welcome
            :title="welcomeTitle"
            :description="welcomeDescription"
            :icon="welcomeIcon"
          />
          <Prompts
            v-if="prompts.length > 0"
            :items="prompts"
            @click="handlePromptClick"
          />
        </slot>
      </div>
      
      <!-- 消息列表 -->
      <BubbleList
        v-else-if="bubbleList.length > 0"
        :key="bubbleListKey"
        :list="bubbleList"
        :typing="false"
        :loading="false"
        :btn-loading="false"
        @action="handleMessageAction"
      >
        <template #avatar="{ item }">
          <slot name="message-avatar" :item="item">
            <el-avatar
              :size="36"
              :src="item.role === 'user' ? userAvatar : aiAvatar"
              :style="item.role === 'assistant' ? aiAvatarStyle : {}"
            >
              {{ item.role === 'user' ? userName?.[0] || 'U' : 'AI' }}
            </el-avatar>
          </slot>
        </template>
        
        <template #content="{ item }">
          <slot name="message-content" :item="item">
            <div class="message-content-wrapper">
              <AiMessage
                :content="item.content"
                :thinking="item.thinking"
                :thinking-duration="item.thinkingDuration"
                :sources="item.sources"
                :role="item.role"
                :loading="item.loading"
                :interrupted="item.interrupted"
                @source-click="handleSourceClick"
              />
              <div class="message-actions-inline">
                <el-tooltip content="复制" placement="bottom">
                  <el-button link size="small" @click="copyMessage(item.content)">
                    <el-icon><DocumentCopy /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="item.role === 'assistant' && isLastMessage(item)" content="重新生成" placement="bottom">
                  <el-button link size="small" @click="regenerateMessage(item)">
                    <el-icon><RefreshRight /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="item.role === 'user' && isLastUserMessage(item)" content="编辑" placement="bottom">
                  <el-button link size="small" @click="editMessage(item)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
          </slot>
        </template>
      </BubbleList>
      
      <!-- 滚动到底部按钮 -->
      <transition name="fade">
        <div v-if="showScrollBtn" class="scroll-to-bottom" @click="scrollToBottom(true)">
          <el-icon :size="20"><ArrowDown /></el-icon>
        </div>
      </transition>
    </div>
    
    <!-- 输入区域 -->
    <div class="ai-chat-input">
      <slot name="input">
        <div class="custom-sender">
          <div class="sender-wrapper">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 6 }"
              :placeholder="inputPlaceholder"
              :disabled="inputDisabled"
              resize="none"
              @keydown.enter.exact.prevent="handleSend"
            />
          </div>
          <div class="sender-actions">
            <slot name="input-prefix" />
            <!-- 语音按钮 -->
            <el-tooltip
              v-if="allowSpeech"
              :content="speechLoading ? '正在录音...' : '语音输入'"
              placement="top"
            >
              <el-button
                :type="speechLoading ? 'danger' : 'default'"
                :icon="speechLoading ? VideoPause : Microphone"
                circle
                size="small"
                :loading="speechLoading"
                @click="$emit('speech')"
              />
            </el-tooltip>
            <!-- 发送/停止按钮 -->
            <el-button
              v-if="isStreaming"
              type="danger"
              :icon="VideoPause"
              circle
              size="small"
              @click="handleStop"
            />
            <el-button
              v-else
              type="primary"
              :icon="Promotion"
              circle
              size="small"
              :disabled="!inputMessage.trim() || inputDisabled"
              @click="handleSend"
            />
            <slot name="input-suffix" />
          </div>
        </div>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Expand,
  Fold,
  DocumentCopy,
  RefreshRight,
  Edit,
  ArrowDown,
  Microphone,
  VideoPause,
  Promotion
} from '@element-plus/icons-vue'
import { Welcome, Prompts, BubbleList } from 'vue-element-plus-x'
import AiMessage from './AiMessage.vue'

const props = defineProps({
  // 基础配置
  title: { type: String, default: 'AI 助手' },
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  isStreaming: { type: Boolean, default: false },
  
  // 欢迎区域
  showWelcome: { type: Boolean, default: true },
  welcomeTitle: { type: String, default: '你好，我是 AI 助手' },
  welcomeDescription: { type: String, default: '有什么我可以帮你的吗？' },
  welcomeIcon: { type: String, default: '' },
  prompts: { type: Array, default: () => [] },
  
  // 用户配置
  userName: { type: String, default: 'User' },
  userAvatar: { type: String, default: '' },
  aiAvatar: { type: String, default: '' },
  aiAvatarStyle: { type: Object, default: () => ({ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }) },
  
  // 模型配置
  showModelSelector: { type: Boolean, default: true },
  models: { type: Array, default: () => [] },
  defaultModel: { type: String, default: '' },
  
  // 输入配置
  inputPlaceholder: { type: String, default: '输入您的问题...' },
  inputDisabled: { type: Boolean, default: false },
  allowSpeech: { type: Boolean, default: true },
  speechLoading: { type: Boolean, default: false },
  
  // 布局配置
  showSidebarToggle: { type: Boolean, default: false },
  sidebarCollapsed: { type: Boolean, default: false }
})

const emit = defineEmits([
  'update:sidebarCollapsed',
  'send',
  'stop',
  'regenerate',
  'edit',
  'prompt-click',
  'source-click',
  'speech',
  'update:model'
])

// 状态
const inputMessage = ref('')
const selectedModel = ref(props.defaultModel)
const messagesContainer = ref(null)
const showScrollBtn = ref(false)
const bubbleListKey = ref(0)
let userAtBottom = true

// 计算属性
const bubbleList = computed(() => {
  return props.messages.map(msg => ({
    ...msg,
    key: msg.id || `msg-${Date.now()}-${Math.random()}`,
    placement: msg.role === 'user' ? 'end' : 'start',
    loading: msg.loading || false
  }))
})

const modelGroups = computed(() => {
  const groups = []
  const customModels = props.models.filter(m => m.type === 'custom')
  const ollamaModels = props.models.filter(m => m.type === 'ollama')
  
  if (customModels.length) {
    groups.push({
      label: '自定义模型',
      models: customModels.map(m => ({ ...m, tag: m.base_model }))
    })
  }
  
  if (ollamaModels.length) {
    groups.push({
      label: 'Ollama 基础模型',
      models: ollamaModels
    })
  }
  
  return groups
})

// 方法
function toggleSidebar() {
  emit('update:sidebarCollapsed', !props.sidebarCollapsed)
}

function handleSend() {
  if (!inputMessage.value.trim()) return

  if (props.isStreaming) {
    ElMessageBox.confirm('当前正在生成回答，发送新消息将暂停回答。确定继续吗？', '确认发送', {
      confirmButtonText: '发送',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      const messageToSend = inputMessage.value.trim()
      emit('stop')
      nextTick(() => {
        bubbleListKey.value++
        emit('send', {
          content: messageToSend,
          model: selectedModel.value
        })
        inputMessage.value = ''
      })
    }).catch(() => {})
  } else {
    bubbleListKey.value++
    emit('send', {
      content: inputMessage.value.trim(),
      model: selectedModel.value
    })
    inputMessage.value = ''
  }
}

function handleStop() {
  emit('stop')
}

function handlePromptClick(prompt) {
  emit('prompt-click', prompt)
  inputMessage.value = prompt.content || prompt.label
}

function handleMessageAction(action, item) {
  if (action === 'copy') {
    copyMessage(item.content)
  } else if (action === 'regenerate') {
    emit('regenerate', item)
  }
}

function handleSourceClick(source) {
  emit('source-click', source)
}

function handleSpeech() {
  emit('speech')
}

async function copyMessage(content) {
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = content
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('已复制到剪贴板')
  }
}

function regenerateMessage(item) {
  emit('regenerate', item)
}

function editMessage(item) {
  emit('edit', item)
  inputMessage.value = item.content
}

function isLastMessage(item) {
  const lastMsg = props.messages[props.messages.length - 1]
  return lastMsg && lastMsg.id === item.id
}

function isLastUserMessage(item) {
  for (let i = props.messages.length - 1; i >= 0; i--) {
    if (props.messages[i].role === 'user') {
      return props.messages[i].id === item.id
    }
  }
  return false
}

function isNearBottom() {
  const el = messagesContainer.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight < 100
}

function onScroll() {
  userAtBottom = isNearBottom()
  showScrollBtn.value = !userAtBottom
}

function scrollToBottom(force = false) {
  if (!force && !userAtBottom) return
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      userAtBottom = true
      showScrollBtn.value = false
    }
  })
}

// 监听
watch(() => props.messages, () => {
  scrollToBottom()
}, { deep: true })

watch(() => props.isStreaming, (val) => {
  if (val) {
    scrollToBottom(true)
  } else {
    nextTick(() => {
      scrollToBottom(true)
    })
  }
})

watch(selectedModel, (val) => {
  emit('update:model', val)
})

onMounted(() => {
  if (messagesContainer.value) {
    messagesContainer.value.addEventListener('scroll', onScroll)
  }
})
</script>

<style scoped lang="scss">
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: linear-gradient(180deg, #FAFBFE 0%, #F3F1FF 50%, #EEEDF9 100%);
}

.ai-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  height: 56px;
  flex-shrink: 0;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    
    .header-title {
      font-size: 16px;
      font-weight: 700;
      background: linear-gradient(135deg, #4F46E5, #7C3AED);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.3px;
    }
  }
  
  .header-center {
    display: flex;
    align-items: center;
    gap: 8px;

    .model-selector {
      width: 240px;

      :deep(.el-input__wrapper) {
        border-radius: 12px;
        box-shadow: none;
        background: rgba(99, 102, 241, 0.06);
        border: 1px solid rgba(99, 102, 241, 0.12);
        transition: all 0.25s ease;
        padding: 4px 14px;

        &:hover {
          background: rgba(99, 102, 241, 0.1);
          border-color: rgba(99, 102, 241, 0.22);
        }

        &.is-focus {
          background: rgba(255, 255, 255, 0.95);
          border-color: #6366F1;
          box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
        }
      }

      :deep(.el-select__caret) {
        color: #6366F1;
        font-weight: 700;
        font-size: 16px;
      }

      :deep(.el-input__inner) {
        color: #1E1B4B;
        font-weight: 600;
        font-size: 15px;

        &::placeholder {
          color: #A5A3C9;
          font-size: 15px;
        }
      }
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    justify-content: flex-end;
  }
}

.model-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;

  .model-option-info {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
  }

  .model-name {
    font-size: 14px;
    font-weight: 600;
    color: #1E1B4B;
    flex: 1;
  }

  .model-tag {
    border-radius: 6px;
    font-weight: 500;
    font-size: 12px;
    background: rgba(99, 102, 241, 0.08);
    border-color: rgba(99, 102, 241, 0.2);
    color: #6366F1;
  }
}

.ai-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px;
  position: relative;
  scroll-behavior: smooth;
  
  .welcome-area {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 28px;
  }
}

.scroll-to-bottom {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 4px 20px rgba(79, 70, 229, 0.18), 0 1px 3px rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  color: #6366F1;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid rgba(99, 102, 241, 0.12);
  
  &:hover {
    background: linear-gradient(135deg, #6366F1, #8B5CF6);
    color: #fff;
    box-shadow: 0 6px 24px rgba(99, 102, 241, 0.35);
    transform: translateX(-50%) translateY(-2px);
  }
}

.ai-chat-input {
  padding: 16px 28px 20px;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-top: 1px solid rgba(99, 102, 241, 0.08);
  flex-shrink: 0;
}

.custom-sender {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.14);
  border-radius: 18px;
  padding: 10px 14px;
  box-shadow: 0 2px 12px rgba(79, 70, 229, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    border-color: rgba(99, 102, 241, 0.25);
    box-shadow: 0 4px 20px rgba(79, 70, 229, 0.1);
  }

  &:focus-within {
    border-color: #6366F1;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12), 0 4px 20px rgba(79, 70, 229, 0.08);
  }

  .sender-wrapper {
    flex: 1;
    min-width: 0;

    :deep(.el-textarea__inner) {
      border: none;
      box-shadow: none;
      resize: none;
      padding: 6px 4px;
      font-size: 15px;
      line-height: 1.6;
      color: #1E1B4B;

      &::placeholder {
        color: #A5A3C9;
      }
      
      &:focus {
        box-shadow: none;
      }
    }
  }

  .sender-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    padding-bottom: 2px;

    .el-button {
      width: 34px;
      height: 34px;
      border-color: transparent;

      &.el-button--primary {
        background: linear-gradient(135deg, #6366F1, #8B5CF6);
        border-color: transparent;

        &:hover:not(:disabled) {
          background: linear-gradient(135deg, #4F46E5, #7C3AED);
          transform: scale(1.06);
          box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
        }
      }

      &:not(.el-button--primary):hover {
        background: rgba(99, 102, 241, 0.08);
        color: #6366F1;
        border-color: transparent;
      }
    }
  }
}

.message-actions-inline {
  display: flex;
  gap: 2px;
  padding: 6px 0 0;
  opacity: 1;

  .el-button {
    color: #8B87B5;
    padding: 4px 8px;
    border-radius: 6px;

    &:hover {
      color: #6366F1;
      background: rgba(99, 102, 241, 0.08);
    }
  }
}

.message-content-wrapper {
  display: flex;
  flex-direction: column;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

// EPX BubbleList 消息气泡深度覆盖
.ai-chat-messages {
  :deep(.el-bubble-list) {
    // 定义气泡宽度变量：85% of 列表宽度
    --bubble-max-width: 85%;

    // 气泡容器透明，宽度由内容决定
    .el-bubble {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      width: var(--bubble-max-width);
      max-width: var(--bubble-max-width);
    }

    // AI 消息气泡靠左
    .el-bubble-start {
      margin-right: auto;
    }

    // 用户消息气泡靠右
    .el-bubble-end {
      margin-left: auto;
    }

    // 第二层: .el-bubble-content-wrapper
    .el-bubble-content-wrapper {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      width: 100%;
      max-width: 100%;
    }

    // 第三层: .el-bubble-content 成为flex容器控制对齐
    .el-bubble-content {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      width: 100%;
      max-width: 100%;
      display: flex !important;
      flex-direction: column;
    }

    // AI消息靠左
    .el-bubble-start .el-bubble-content {
      align-items: flex-start;
    }

    // 用户消息靠右
    .el-bubble-end .el-bubble-content {
      align-items: flex-end;
    }
  }
}

// 滚动条样式
.ai-chat-messages {
  &::-webkit-scrollbar {
    width: 5px;
  }
  
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.2);
    border-radius: 10px;
    
    &:hover {
      background: rgba(99, 102, 241, 0.35);
    }
  }
}
</style>
