<template>
  <div class="chat-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <transition name="fade">
      <el-button
        v-if="sidebarCollapsed"
        class="floating-sidebar-toggle"
        :icon="Expand"
        circle
        size="small"
        @click="toggleSidebar"
      />
    </transition>

    <!-- 侧边栏 - 会话管理 -->
    <aside class="chat-sidebar">
      <!-- Logo 和新建对话 -->
      <div class="sidebar-brand">
        <div class="brand-logo">
          <el-icon :size="24"><ChatRound /></el-icon>
          <span class="brand-text">SFQA AI</span>
        </div>
        <el-button
          class="sidebar-toggle"
          :icon="sidebarCollapsed ? Expand : Fold"
          circle
          size="small"
          @click="toggleSidebar"
        />
        <el-button
          type="primary"
          :icon="Plus"
          class="new-chat-btn"
          @click="createNewChat"
        >
          新对话
        </el-button>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <div class="nav-item" @click="openSearchDialog">
          <el-icon><Search /></el-icon>
          <span>搜索</span>
        </div>
        <div class="nav-item" :class="{ active: isRouteActive('/kg') }" @click="navigateToPanel('/kg')">
          <el-icon><Share /></el-icon>
          <span>知识图谱</span>
        </div>
        <div class="nav-item" :class="{ active: isRouteActive('/knowledge') }" @click="navigateToPanel('/knowledge')">
          <el-icon><Document /></el-icon>
          <span>知识库</span>
        </div>
        <div class="nav-item" :class="{ active: isRouteActive('/workspace') }" @click="navigateToPanel('/workspace')">
          <el-icon><Setting /></el-icon>
          <span>工作空间</span>
        </div>
      </nav>

      <!-- 会话列表 -->
      <div class="conversation-list">
        <div class="list-header">
          <span class="list-title">对话历史</span>
        </div>

        <div v-if="conversations.length > 0" class="conv-items">
          <el-dropdown
            v-for="conv in conversations"
            :key="conv.id"
            :ref="(el) => setConversationDropdownRef(conv.id, el)"
            trigger="contextmenu"
            placement="right-start"
            @command="(cmd) => onConversationCommand(cmd, conv)"
          >
            <div
              class="conv-item"
              :class="{ active: conv.id === currentConversationId }"
              @click="selectConversation(conv.id)"
              @contextmenu.prevent.stop="openConversationMenu(conv.id)"
            >
              <el-icon class="conv-icon"><ChatDotRound /></el-icon>
              <span class="conv-title">{{ conv.title || '新对话' }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rename">
                  <el-icon><Edit /></el-icon>修改
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided class="delete-item">
                  <el-icon><Delete /></el-icon>删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <el-empty v-if="conversations.length === 0" description="暂无对话" :image-size="60" />
      </div>

      <!-- 用户信息 -->
      <div class="sidebar-footer">
        <div class="user-footer-row">
          <el-dropdown>
            <div class="user-info">
              <el-avatar :size="32">{{ user?.username?.[0] || 'U' }}</el-avatar>
              <span>{{ user?.username || 'User' }}</span>
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="showUserSwitchDialog = true">
                  <el-icon><Switch /></el-icon>切换用户
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button
            v-if="authStore.isAdmin"
            text
            class="switch-side-btn"
            @click="router.push({ name: 'Admin' })"
          >
            切换为管理端
          </el-button>
        </div>
      </div>
    </aside>

<<<<<<< HEAD
    <!-- 主内容区域 -->
    <section class="chat-content">
      <router-view v-slot="{ Component, route: childRoute }">
        <component
          :is="Component"
          v-if="childRoute.name === 'ChatHome'"
          :title="currentConversationTitle"
          :messages="messages"
          :is-streaming="streaming.isStreaming.value"
          :models="availableModels"
          :default-model="selectedModel"
          :user-name="user?.username"
          :show-sidebar-toggle="sidebarCollapsed"
          :sidebar-collapsed="sidebarCollapsed"
          :prompts="defaultPrompts"
          :editing-message-id="editingMessageId"
          :title-editable="!!currentConversationId"
          @send="handleSend"
          @stop="handleStop"
          @regenerate="handleRegenerate"
          @edit="handleEdit"
          @edit-submit="handleEditSubmit"
          @edit-cancel="handleEditCancel"
          @title-submit="handleTitleSubmit"
          @source-click="showSourceDetail"
          @update:model="selectedModel = $event"
          @update:sidebar-collapsed="sidebarCollapsed = $event"
        />
        <component :is="Component" v-else />
      </router-view>
    </section>
=======
    <!-- 主聊天区域 -->
    <main class="chat-main">
      <AiChat
        :title="currentConversationTitle"
        :messages="messages"
        :is-streaming="isCurrentConversationStreaming"
        :models="availableModels"
        :default-model="selectedModel"
        :user-name="user?.username"
        :show-sidebar-toggle="sidebarCollapsed"
        :sidebar-collapsed="sidebarCollapsed"
        :prompts="defaultPrompts"
        @send="handleSend"
        @stop="handleStop"
        @regenerate="handleRegenerate"
        @edit="handleEdit"
        @source-click="showSourceDetail"
        @update:model="selectedModel = $event"
        @update:sidebar-collapsed="sidebarCollapsed = $event"
      />
    </main>
>>>>>>> origin/sfqa-project

    <!-- 来源详情弹窗 -->
    <el-dialog
      v-if="isChatHomeRoute"
      v-model="sourceDialogVisible"
      width="640px"
      destroy-on-close
      class="custom-dialog source-dialog"
    >
      <button class="dialog-close-btn" @click="sourceDialogVisible = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><TrendCharts /></el-icon>
        </div>
        <h3 class="dialog-title">来源详情</h3>
        <p class="dialog-subtitle">查看引用来源的详细信息</p>
      </div>
      <div v-if="selectedSource" class="source-detail-body">
        <div class="source-meta">
          <div class="meta-item">
            <el-icon><Document /></el-icon>
            <span>{{ selectedSource.file_name || '未知文件' }}</span>
          </div>
          <div class="meta-item score">
            <el-icon><Star /></el-icon>
            <span>相关度: {{ (selectedSource.score * 100).toFixed(1) }}%</span>
          </div>
        </div>
        <div class="source-content-area">
          <div class="content-label">
            <el-icon><Reading /></el-icon>
            引用内容
          </div>
          <pre class="source-content-text">{{ selectedSource.content }}</pre>
        </div>
      </div>
    </el-dialog>

    <!-- 搜索对话框 -->
    <el-dialog
      v-if="isChatHomeRoute"
      v-model="showSearchDialog"
      title="搜索对话"
      width="520px"
      destroy-on-close
      class="custom-dialog search-dialog"
    >
      <button class="dialog-close-btn" @click="showSearchDialog = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><Search /></el-icon>
        </div>
        <h3 class="dialog-title">搜索对话</h3>
        <p class="dialog-subtitle">快速查找历史对话记录</p>
      </div>
      <div class="search-content">
        <el-input
          v-model="searchQuery"
          placeholder="输入关键词搜索对话..."
          :prefix-icon="Search"
          clearable
          @input="handleSearch"
          class="search-dialog-input"
        />
        <div class="search-results" v-if="searchQuery.trim()">
          <div
            v-for="conv in searchResults"
            :key="conv.id"
            class="search-result-item"
            @click="selectConversation(conv.id); showSearchDialog = false"
          >
            <div class="result-icon">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="result-info">
              <span class="result-title">{{ conv.title }}</span>
              <span class="result-date">{{ formatDate(conv.updated_at) }}</span>
            </div>
            <el-icon class="result-arrow"><ArrowRight /></el-icon>
          </div>
          <el-empty v-if="searchResults.length === 0" description="未找到相关对话" :image-size="80" />
        </div>
        <div v-else class="search-placeholder">
          <el-icon :size="48" class="placeholder-icon"><Search /></el-icon>
          <p class="placeholder-text">输入关键词开始搜索</p>
        </div>
      </div>
    </el-dialog>

    <!-- 用户切换对话框 -->
    <el-dialog
      v-model="showUserSwitchDialog"
      width="420px"
      destroy-on-close
      class="custom-dialog user-switch-dialog"
    >
      <button class="dialog-close-btn" @click="showUserSwitchDialog = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><Switch /></el-icon>
        </div>
        <h3 class="dialog-title">切换用户</h3>
        <p class="dialog-subtitle">切换到其他用户账号</p>
      </div>
      <div class="user-switch-content">
        <div class="current-user">
          <el-avatar :size="56">{{ user?.username?.[0] || 'U' }}</el-avatar>
          <div class="user-info-detail">
            <span class="username">{{ user?.username || 'User' }}</span>
            <span class="user-role">当前用户</span>
          </div>
        </div>
        <div class="switch-divider">
          <el-icon><Bottom /></el-icon>
        </div>
        <div class="switch-actions">
          <p class="switch-hint">切换用户将退出当前账号</p>
          <el-button type="primary" @click="handleSwitchUser" class="switch-btn">
            <el-icon><Switch /></el-icon>
            切换至其他账号
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
<<<<<<< HEAD
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
=======
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
>>>>>>> origin/sfqa-project
import {
  Plus,
  ChatRound,
  Search,
  Share,
  Document,
  Setting,
  Edit,
  Delete,
  SwitchButton,
  Switch,
  ArrowDown,
  ChatDotRound,
  Expand,
  Fold,
  Close,
  ArrowRight,
  Bottom,
  TrendCharts,
  Star,
  Reading
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useStreaming } from '@/composables/useStreaming'
<<<<<<< HEAD
=======
import { useConversationStorage } from '@/composables/useConversationStorage'
import { useGlobalStreaming } from '@/composables/useGlobalStreaming'
import { AiChat } from '@/components/ai'
>>>>>>> origin/sfqa-project
import * as chatApi from '@/api/chat'
import * as modelApi from '@/api/model'
import { getItem, setItem } from '@/utils/storage'
import { getOrFetch, invalidateCache, CACHE_TTL } from '@/utils/cache'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const streaming = useStreaming()
const conversationStorage = useConversationStorage()
const globalStreaming = useGlobalStreaming()

// Track if we're currently processing a stream for the visible conversation
const isProcessingStream = computed(() => {
  return globalStreaming.hasActiveStream(currentConversationId.value)
})

// Check if current conversation has an active stream (for input disabling)
const isCurrentConversationStreaming = computed(() => {
  const currentId = currentConversationId.value
  if (!currentId) return false

  // Check if this specific conversation has an active stream
  const hasStream = globalStreaming.hasActiveStream(currentId)
  if (hasStream) return true

  // Also check if any message in current conversation is streaming
  return messages.value.some(m => m.isStreaming)
})

// 状态
const user = computed(() => authStore.user)
const conversations = ref([])
const currentConversationId = ref(null)
const messages = ref([])
const selectedModel = ref(null)
const availableModels = ref([])
const sidebarCollapsed = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const sourceDialogVisible = ref(false)
const selectedSource = ref(null)
const showSearchDialog = ref(false)
const showUserSwitchDialog = ref(false)
const editingMessageId = ref(null)
const editingSnapshot = ref(null)
const openConversationMenuId = ref(null)
const conversationDropdownRefs = new Map()

// 默认提示
const defaultPrompts = [
  { key: '1', label: '解释概念', description: '请解释一个复杂的概念' },
  { key: '2', label: '代码帮助', description: '帮我编写或调试代码' },
  { key: '3', label: '文档总结', description: '总结一篇文档的主要内容' },
  { key: '4', label: '创意写作', description: '帮我写一篇创意文章' }
]

// 计算属性
const currentConversationTitle = computed(() => {
  if (!currentConversationId.value) return '新对话'
  const conv = conversations.value.find(c => c.id === currentConversationId.value)
  return conv?.title || ''
})
const isChatHomeRoute = computed(() => route.name === 'ChatHome')

function isRouteActive(prefix) {
  return route.path === prefix || route.path.startsWith(`${prefix}/`)
}

async function navigateToPanel(path) {
  if (route.path === path) return

  closeConversationMenu()
  showSearchDialog.value = false
  sourceDialogVisible.value = false

  await router.push(path)
}

async function openSearchDialog() {
  closeConversationMenu()
  if (route.name !== 'ChatHome') {
    await router.push({ name: 'ChatHome' })
  }

  searchQuery.value = ''
  searchResults.value = []
  showSearchDialog.value = true
}

function clearEditState() {
  editingMessageId.value = null
  editingSnapshot.value = null
}

function setConversationDropdownRef(conversationId, instance) {
  if (!instance) {
    conversationDropdownRefs.delete(conversationId)
    return
  }
  conversationDropdownRefs.set(conversationId, instance)
}

function closeConversationMenu() {
  const currentId = openConversationMenuId.value
  if (currentId) {
    const currentDropdown = conversationDropdownRefs.get(currentId)
    currentDropdown?.handleClose?.()
  }
  openConversationMenuId.value = null
}

async function openConversationMenu(conversationId) {
  if (openConversationMenuId.value === conversationId) {
    closeConversationMenu()
    await nextTick()
  } else if (openConversationMenuId.value) {
    closeConversationMenu()
    await nextTick()
  }

  openConversationMenuId.value = conversationId
  const nextDropdown = conversationDropdownRefs.get(conversationId)
  nextDropdown?.handleOpen?.()
}

function handleGlobalPointerDown(event) {
  if (!openConversationMenuId.value) return

  const target = event.target
  if (!(target instanceof Element)) {
    closeConversationMenu()
    return
  }

  if (target.closest('.conversation-list .el-dropdown')) return
  if (target.closest('.el-dropdown-menu')) return
  if (target.closest('.el-popper')) return

  closeConversationMenu()
}

function restoreEditedMessages() {
  if (!editingSnapshot.value?.restoreOnCancel) {
    clearEditState()
    return
  }

  const { targetIndex, followingMessages } = editingSnapshot.value
  const preserved = messages.value.slice(0, targetIndex + 1)
  messages.value = [...preserved, ...followingMessages]
  clearEditState()
}

function removeStreamingArtifacts() {
  messages.value = messages.value.filter(msg => !msg.isStreaming)
}

async function resolveEditableMessageId(snapshot) {
  if (!snapshot?.targetId || !String(snapshot.targetId).startsWith('temp-user-')) {
    return snapshot?.targetId
  }

  const currentMessage = messages.value[snapshot.targetIndex]
  if (!currentMessage) return null

  const res = await chatApi.getConversation(currentConversationId.value)
  const serverMessages = res.data?.messages || []
  const matchedUserMessage = [...serverMessages].reverse().find(msg => (
    msg.role === 'user' && msg.content === currentMessage.content
  ))

  if (!matchedUserMessage) return null

  snapshot.targetId = matchedUserMessage.id
  currentMessage.id = matchedUserMessage.id
  return matchedUserMessage.id
}

// 方法
async function loadModels() {
  try {
    const [ollamaRes, customRes] = await Promise.all([
      getOrFetch('models:ollama', () => modelApi.getOllamaModels(), CACHE_TTL.MODELS),
      getOrFetch('models:custom', () => modelApi.getCustomModels(), CACHE_TTL.MODELS)
    ])

    const ollamaData = (ollamaRes?.data || ollamaRes || [])
    const customData = (customRes?.data || customRes || [])

    const ollamaList = (Array.isArray(ollamaData) ? ollamaData : []).map(m => ({
      id: m.name || m.model,
      name: m.name || m.model,
      type: 'ollama'
    }))

    const customList = (Array.isArray(customData) ? customData : []).map(m => ({
      id: m.id,
      name: m.name,
      type: 'custom',
      base_model: m.base_model,
      system_prompt: m.system_prompt
    }))

    availableModels.value = [...customList, ...ollamaList]

    // Initialize default model selection
    initializeDefaultModel()
  } catch (error) {
    console.error('Failed to load models:', error)
    availableModels.value = [{ id: 'qwen3:14b', name: 'qwen3:14b', type: 'ollama' }]
    if (!selectedModel.value) {
      selectedModel.value = 'qwen3:14b'
    }
  }
}

/**
 * Initialize default model based on priority:
 * 1. User's saved default (if still available)
 * 2. First available model from the list
 */
function initializeDefaultModel() {
  if (availableModels.value.length === 0) return

  const savedDefault = getItem('sfqa_default_model')

  // Check if saved default is still available (works for both ollama and custom models)
  if (savedDefault) {
    const isSavedDefaultAvailable = availableModels.value.some(m => m.id === savedDefault)
    if (isSavedDefaultAvailable) {
      if (!selectedModel.value) {
        selectedModel.value = savedDefault
      }
      return
    }
  }

  // No saved default or it's no longer available, use first available model
  if (!selectedModel.value) {
    const firstModel = availableModels.value[0]
    selectedModel.value = firstModel.id
    // Auto-save first model as default for new users
    if (!savedDefault) {
      setItem('sfqa_default_model', firstModel.id)
    }
  }
}

async function loadConversations() {
  try {
    // First, load from localStorage for instant display
    const localConversations = conversationStorage.loadConversationsList()
    if (localConversations && localConversations.length > 0) {
      conversations.value = localConversations
    }

    // Then fetch from server/cache
    const cached = await getOrFetch('conversations:list',
      () => chatApi.getConversations({ per_page: 50 }),
      CACHE_TTL.CONVERSATIONS
    )
    const serverConversations = cached?.data?.conversations || cached?.conversations || []

    // Update if different
    if (JSON.stringify(conversations.value) !== JSON.stringify(serverConversations)) {
      conversations.value = serverConversations
    }

    // Sync to localStorage
    conversationStorage.syncConversationsFromServer(serverConversations)
  } catch (error) {
    console.error('Failed to load conversations:', error)
    // Fallback to localStorage on error
    const localConversations = conversationStorage.loadConversationsList()
    if (localConversations) {
      conversations.value = localConversations
    }
  }
}

async function createNewChat() {
  closeConversationMenu()
  clearEditState()
  currentConversationId.value = null
  messages.value = []
  await router.push({ name: 'ChatHome' })
}

async function deleteConversation(id) {
  try {
    await ElMessageBox.confirm('确定要删除该对话吗？', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await chatApi.deleteConversation(id)
    conversations.value = conversations.value.filter(c => c.id !== id)

    // Also delete from localStorage
    conversationStorage.deleteConversation(id)
    conversationStorage.saveConversationsList(conversations.value)

    invalidateCache('conversations:list')
    invalidateCache(`conversations:messages:${id}`)
    if (currentConversationId.value === id) {
      currentConversationId.value = null
      messages.value = []
      clearEditState()
    }
    ElMessage.success('对话已删除')
  } catch {}
}

// Debounce utility for selectConversation
let selectConversationTimeout = null
let isLoadingConversation = false

async function selectConversation(id) {
<<<<<<< HEAD
  closeConversationMenu()
  if (editingMessageId.value) {
    clearEditState()
  }

  if (route.name !== 'ChatHome') {
    await router.push({ name: 'ChatHome' })
  }

  if (currentConversationId.value === id && messages.value.length > 0) return
=======
  if (currentConversationId.value === id) return
  if (isLoadingConversation) return
>>>>>>> origin/sfqa-project

  // Clear any pending selection
  if (selectConversationTimeout) {
    clearTimeout(selectConversationTimeout)
  }

  // Debounce the selection to prevent rapid clicking
  selectConversationTimeout = setTimeout(async () => {
    isLoadingConversation = true
    const previousId = currentConversationId.value
    currentConversationId.value = id

    // Update global visible conversation
    const activeStream = globalStreaming.setVisibleConversation(id)

    // Clear messages immediately for better UX (prevents showing old messages)
    messages.value = []

    try {
      // Check if there's an active stream for this conversation
      if (activeStream && activeStream.isStreaming) {
        // Load all historical messages from localStorage first
        const allLocalMessages = conversationStorage.loadConversationMessages(id) || []

        // Filter out the last incomplete assistant message if exists
        const historicalMessages = allLocalMessages.filter(m => {
          // Keep all messages except the one that's currently streaming
          if (m.role === 'assistant' && m.isStreaming) {
            return false
          }
          return true
        })

        // Build complete message list: historical + current streaming
        const streamMessages = [...historicalMessages]

        // Add the current streaming assistant message from global state
        streamMessages.push({
          id: activeStream.messageId || 'streaming-assistant',
          role: 'assistant',
          content: activeStream.content,
          thinking: activeStream.thinking,
          thinkingDuration: activeStream.thinkingDuration,
          sources: activeStream.sources,
          isStreaming: true,
          loading: !activeStream.content,
          created_at: new Date().toISOString()
        })

        messages.value = streamMessages

        // Register callbacks to receive updates
        globalStreaming.registerCallbacks(id, {
          onContent: (content) => {
            const assistantMsg = messages.value.find(m => m.role === 'assistant')
            if (assistantMsg) {
              assistantMsg.content = content
              assistantMsg.loading = false
            }
          },
          onThinking: (thinking) => {
            const assistantMsg = messages.value.find(m => m.role === 'assistant')
            if (assistantMsg) {
              assistantMsg.thinking = thinking
            }
          },
          onThinkingStart: () => {
            const assistantMsg = messages.value.find(m => m.role === 'assistant')
            if (assistantMsg) {
              assistantMsg.isThinking = true
            }
          },
          onThinkingEnd: (duration) => {
            const assistantMsg = messages.value.find(m => m.role === 'assistant')
            if (assistantMsg) {
              assistantMsg.isThinking = false
              assistantMsg.thinkingDuration = duration
            }
          },
          onSources: (sources) => {
            const assistantMsg = messages.value.find(m => m.role === 'assistant')
            if (assistantMsg) {
              assistantMsg.sources = sources
            }
          },
          onDone: (result) => {
            const assistantMsg = messages.value.find(m => m.role === 'assistant')
            if (assistantMsg) {
              assistantMsg.id = result.messageId || assistantMsg.id
              assistantMsg.content = result.content
              assistantMsg.thinking = result.thinking
              assistantMsg.thinkingDuration = result.thinkingDuration
              assistantMsg.sources = result.sources || []
              assistantMsg.isStreaming = false
              assistantMsg.loading = false
            }
            // Refresh conversation list
            loadConversations()
          },
          onError: (error) => {
            ElMessage.error(error || '生成失败')
          }
        })

        isLoadingConversation = false
        return
      }

      // Check localStorage cache first for instant display
      const localMessages = conversationStorage.loadConversationMessages(id)

      if (localMessages && localMessages.length > 0) {
        // Show cached messages immediately
        messages.value = localMessages
      }

      // Then fetch from server/cache
      const cached = await getOrFetch(`conversations:messages:${id}`,
        () => chatApi.getConversation(id),
        CACHE_TTL.MESSAGES
      )

      const newMessages = (cached?.data?.messages || cached?.messages || []).map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        thinking: msg.thinking_content,
        thinkingDuration: msg.thinking_duration,
        sources: msg.sources,
        created_at: msg.created_at
      }))

      // Only update if different (prevents unnecessary re-renders)
      if (JSON.stringify(messages.value) !== JSON.stringify(newMessages)) {
        messages.value = newMessages
      }

      // Sync to localStorage
      conversationStorage.syncMessagesFromServer(id, newMessages)
    } catch (error) {
      console.error('Failed to load conversation:', error)
      if (messages.value.length === 0) {
        ElMessage.error('加载对话失败')
      }
    } finally {
      isLoadingConversation = false
    }
  }, 50) // Small delay to batch rapid clicks
}

async function handleSend({ content, model }) {
  const conversationId = currentConversationId.value

  if (!conversationId) {
    try {
      const res = await chatApi.createConversation({ title: content.slice(0, 50) })
      const conv = res.data
      conversations.value.unshift(conv)
      currentConversationId.value = conv.id

      // Save new conversation to localStorage
      conversationStorage.saveConversation(conv)
      conversationStorage.saveConversationsList(conversations.value)
    } catch (error) {
      ElMessage.error('创建对话失败')
      return
    }
  }

  const currentId = currentConversationId.value

  // 添加用户消息
<<<<<<< HEAD
  const userMessageId = 'temp-user-' + Date.now()
  messages.value.push({
=======
  const userMessageId = 'temp-' + Date.now()
  const userMessage = {
>>>>>>> origin/sfqa-project
    id: userMessageId,
    role: 'user',
    content,
    created_at: new Date().toISOString()
  }
  messages.value.push(userMessage)

  // Save user message to localStorage immediately
  conversationStorage.appendMessage(currentId, userMessage)

  // 添加临时的助手消息用于流式显示
  const assistantMessageId = 'temp-assistant-' + Date.now()
  const assistantMessage = {
    id: assistantMessageId,
    role: 'assistant',
    content: '',
    thinking: '',
    thinkingDuration: 0,
    sources: [],
    created_at: new Date().toISOString(),
    isStreaming: true,
    loading: true,
    interrupted: false
  }
  messages.value.push(assistantMessage)

  // Save initial assistant message to localStorage
  conversationStorage.appendMessage(currentId, assistantMessage)

  // Start global stream tracking
  globalStreaming.startStream(currentId, {
    userMessageId,
    messageId: assistantMessageId
  })

  // Track last localStorage save time
  let lastLocalSave = Date.now()
  const localSaveInterval = 1000 // Save every 1 second during streaming

  // Register callbacks for global streaming
  globalStreaming.registerCallbacks(currentId, {
    onContent: (content) => {
      // This will be called even when viewing other conversations
      // The content is already updated in global state
    },
    onDone: (result) => {
      // Stream completed
    },
    onError: (error) => {
      // Stream errored
    }
  })

  try {
    const signal = streaming.createAbortSignal()
    const modelInfo = availableModels.value.find(m => m.id === model)
    const modelParam = modelInfo?.type === 'ollama' ? model : null
    const customModelIdParam = modelInfo?.type === 'custom' ? model : null

    // Store abort controller in global state
    globalStreaming.setAbortController(currentId, streaming.abortController)

    const response = await chatApi.sendMessageStream(
      currentId,
      content,
      modelParam,
      customModelIdParam,
      signal
    )

    await streaming.processStream(response, {
      onContent: (chunk, fullContent) => {
        // Update global state
        globalStreaming.updateStreamContent(currentId, fullContent)

        // Update local message if this conversation is visible
        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        const isVisible = currentConversationId.value === currentId

        if (assistantMsg) {
          assistantMsg.content = fullContent
          if (fullContent && assistantMsg.loading) {
            assistantMsg.loading = false
          }
        }

        // Always save to localStorage regardless of visibility
        // This ensures messages are preserved when switching conversations
        const now = Date.now()
        if (now - lastLocalSave >= localSaveInterval) {
          if (isVisible) {
            // Current conversation is visible, save from messages array
            conversationStorage.saveConversationMessages(currentId, messages.value)
          } else {
            // Conversation is not visible, load existing messages and update
            const existingMessages = conversationStorage.loadConversationMessages(currentId) || []
            const updatedMessages = existingMessages.map(m => {
              if (m.id === assistantMessageId) {
                return { ...m, content: fullContent, loading: false }
              }
              return m
            })
            conversationStorage.saveConversationMessages(currentId, updatedMessages)
          }
          lastLocalSave = now
        }
      },
      onThinking: (chunk, fullThinking) => {
        // Update global state
        globalStreaming.updateStreamThinking(currentId, fullThinking)

        // Update local message if this conversation is visible
        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        const isVisible = currentConversationId.value === currentId

        if (assistantMsg) {
          assistantMsg.thinking = fullThinking
          if (fullThinking && assistantMsg.loading) {
            assistantMsg.loading = false
          }
        }

        // Also update localStorage for background conversations
        if (!isVisible) {
          const existingMessages = conversationStorage.loadConversationMessages(currentId) || []
          const updatedMessages = existingMessages.map(m => {
            if (m.id === assistantMessageId) {
              return { ...m, thinking: fullThinking }
            }
            return m
          })
          conversationStorage.saveConversationMessages(currentId, updatedMessages)
        }
      },
      onThinkingStart: () => {
        globalStreaming.markThinkingStarted(currentId)
      },
      onThinkingEnd: (duration) => {
        globalStreaming.markThinkingEnded(currentId, duration)

        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        if (assistantMsg) {
          assistantMsg.thinkingDuration = duration
        }
      },
      onSources: (sources) => {
        globalStreaming.updateStreamSources(currentId, sources)

        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        const isVisible = currentConversationId.value === currentId

        if (assistantMsg) {
          assistantMsg.sources = sources
        }

        // Also update localStorage for background conversations
        if (!isVisible) {
          const existingMessages = conversationStorage.loadConversationMessages(currentId) || []
          const updatedMessages = existingMessages.map(m => {
            if (m.id === assistantMessageId) {
              return { ...m, sources }
            }
            return m
          })
          conversationStorage.saveConversationMessages(currentId, updatedMessages)
        }
      },
      onDone: (result) => {
<<<<<<< HEAD
        const userMsg = messages.value.find(m => m.id === userMessageId)
        if (userMsg && result.userMessageId) {
          userMsg.id = result.userMessageId
        }

=======
        // Complete global stream
        globalStreaming.completeStream(currentId, {
          messageId: result.messageId,
          userMessageId: result.userMessageId,
          content: result.content,
          thinking: result.thinking,
          thinkingDuration: result.thinkingDuration,
          sources: result.sources,
          aborted: result.aborted
        })

        const isVisible = currentConversationId.value === currentId

        // Update local message if visible
>>>>>>> origin/sfqa-project
        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        if (assistantMsg) {
          assistantMsg.id = result.messageId || assistantMessageId
          assistantMsg.content = result.content
          assistantMsg.thinking = result.thinking
          assistantMsg.thinkingDuration = result.thinkingDuration
          assistantMsg.sources = result.sources || []
          assistantMsg.isStreaming = false
          assistantMsg.loading = false
          assistantMsg.interrupted = result.aborted
        }

        // Final save to localStorage with complete data
        if (isVisible) {
          conversationStorage.saveConversationMessages(currentId, messages.value)
        } else {
          // For background conversations, update the saved messages
          const existingMessages = conversationStorage.loadConversationMessages(currentId) || []
          const updatedMessages = existingMessages.map(m => {
            if (m.id === assistantMessageId) {
              return {
                ...m,
                id: result.messageId || assistantMessageId,
                content: result.content,
                thinking: result.thinking,
                thinkingDuration: result.thinkingDuration,
                sources: result.sources || [],
                isStreaming: false,
                loading: false,
                interrupted: result.aborted
              }
            }
            return m
          })
          conversationStorage.saveConversationMessages(currentId, updatedMessages)
        }

        if (result.aborted) {
          ElMessage.info('已终止生成')
        }

        streaming.reset()
        invalidateCache(`conversations:messages:${currentId}`)
        invalidateCache('conversations:list')
        loadConversations()
      },
      onError: (error) => {
        // Mark global stream as errored
        globalStreaming.errorStream(currentId, error)

        // 移除临时消息
        const idx = messages.value.findIndex(m => m.id === assistantMessageId)
        if (idx > -1) {
          messages.value.splice(idx, 1)
        }
        // Also update localStorage to remove failed assistant message
        conversationStorage.saveConversationMessages(currentConversationId.value, messages.value)

        ElMessage.error(error || '生成失败')
        streaming.reset()
      }
    })
  } catch (error) {
    // 移除临时消息
    const idx = messages.value.findIndex(m => m.id === assistantMessageId)
    if (idx > -1) {
      messages.value.splice(idx, 1)
    }
    // Update localStorage
    conversationStorage.saveConversationMessages(currentConversationId.value, messages.value)

    if (error.name !== 'AbortError') {
      ElMessage.error('发送失败')
    }
    streaming.reset()
  }
}

<<<<<<< HEAD
function handleStop({ keepPartial = true } = {}) {
  streaming.abort()

  if (!keepPartial) {
    removeStreamingArtifacts()
    streaming.reset()
    return
=======
function handleStop() {
  const currentId = currentConversationId.value

  // Abort the stream
  streaming.abort()

  // Also abort via global streaming
  if (currentId) {
    globalStreaming.abortStream(currentId)
>>>>>>> origin/sfqa-project
  }

  // 立即更新当前正在流式传输的消息状态
  const streamingMsg = messages.value.find(m => m.isStreaming)
  if (streamingMsg) {
    streamingMsg.loading = false
    streamingMsg.interrupted = true
    streamingMsg.isStreaming = false
  }
}

async function handleRegenerate(item) {
<<<<<<< HEAD
  if (!currentConversationId.value || streaming.isStreaming.value || editingMessageId.value) return
=======
  const currentId = currentConversationId.value
  if (!currentId || globalStreaming.hasActiveStream(currentId)) return
>>>>>>> origin/sfqa-project

  // 移除最后一条助手消息
  const lastIdx = messages.value.length - 1
  if (lastIdx >= 0 && messages.value[lastIdx].role === 'assistant') {
    messages.value.splice(lastIdx, 1)
  }

  // 添加临时的助手消息用于流式显示
  const assistantMessageId = 'temp-assistant-' + Date.now()
  messages.value.push({
    id: assistantMessageId,
    role: 'assistant',
    content: '',
    thinking: '',
    thinkingDuration: 0,
    sources: [],
    created_at: new Date().toISOString(),
    isStreaming: true,
    loading: true,
    interrupted: false
  })

  try {
    const signal = streaming.createAbortSignal()
    const modelInfo = availableModels.value.find(m => m.id === selectedModel.value)
    const modelParam = modelInfo?.type === 'ollama' ? selectedModel.value : null
    const customModelIdParam = modelInfo?.type === 'custom' ? selectedModel.value : null

    const response = await chatApi.regenerateResponse(
      currentConversationId.value,
      modelParam,
      customModelIdParam,
      signal
    )

    await streaming.processStream(response, {
      onContent: (chunk, fullContent) => {
        // 实时更新助手消息内容
        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        if (assistantMsg) {
          assistantMsg.content = fullContent
          if (fullContent && assistantMsg.loading) {
            assistantMsg.loading = false
          }
        }
      },
      onThinking: (chunk, fullThinking) => {
        // 实时更新思考内容
        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        if (assistantMsg) {
          assistantMsg.thinking = fullThinking
          if (fullThinking && assistantMsg.loading) {
            assistantMsg.loading = false
          }
        }
      },
      onThinkingStart: () => {},
      onThinkingEnd: (duration) => {
        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        if (assistantMsg) {
          assistantMsg.thinkingDuration = duration
        }
      },
      onSources: (sources) => {
        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        if (assistantMsg) {
          assistantMsg.sources = sources
        }
      },
      onDone: (result) => {
        const assistantMsg = messages.value.find(m => m.id === assistantMessageId)
        if (assistantMsg) {
          assistantMsg.id = result.messageId || assistantMessageId
          assistantMsg.content = result.content
          assistantMsg.thinking = result.thinking
          assistantMsg.thinkingDuration = result.thinkingDuration
          assistantMsg.sources = result.sources || []
          assistantMsg.isStreaming = false
          assistantMsg.loading = false
          assistantMsg.interrupted = result.aborted
        }

        if (result.aborted) {
          ElMessage.info('已终止生成')
        }

        streaming.reset()
      },
      onError: (error) => {
        const idx = messages.value.findIndex(m => m.id === assistantMessageId)
        if (idx > -1) {
          messages.value.splice(idx, 1)
        }
        ElMessage.error(error || '重新生成失败')
        streaming.reset()
      }
    })
  } catch (error) {
    // 移除临时消息
    const idx = messages.value.findIndex(m => m.id === assistantMessageId)
    if (idx > -1) {
      messages.value.splice(idx, 1)
    }
    if (error.name !== 'AbortError') {
      ElMessage.error('重新生成失败')
    }
    streaming.reset()
  }
}

function handleEdit(item) {
  if (!currentConversationId.value) return

  if (editingMessageId.value === item.id) return

  if (editingMessageId.value) {
    restoreEditedMessages()
  }

  const targetIndex = messages.value.findIndex(msg => msg.id === item.id)
  if (targetIndex < 0) return

  const followingMessages = messages.value.slice(targetIndex + 1)
  const wasStreaming = streaming.isStreaming.value

  if (wasStreaming) {
    handleStop({ keepPartial: false })
  }

  editingSnapshot.value = {
    targetId: item.id,
    targetIndex,
    followingMessages: wasStreaming ? [] : followingMessages,
    restoreOnCancel: !wasStreaming
  }
  editingMessageId.value = item.id
  messages.value = messages.value.slice(0, targetIndex + 1)
}

async function handleEditSubmit({ item, content }) {
  const nextContent = content?.trim()
  if (!nextContent || !currentConversationId.value) return

  const snapshot = editingSnapshot.value
  if (!snapshot?.targetId) return

  try {
    const targetId = await resolveEditableMessageId(snapshot)
    if (!targetId) {
      throw new Error('missing_target_id')
    }

    await chatApi.deleteMessagesFrom(currentConversationId.value, targetId)
    messages.value = messages.value.slice(0, snapshot.targetIndex)
    clearEditState()
    invalidateCache(`conversations:messages:${currentConversationId.value}`)
    invalidateCache('conversations:list')
    await handleSend({ content: nextContent, model: selectedModel.value })
  } catch (error) {
    ElMessage.error('编辑消息失败')
  }
}

function handleEditCancel() {
  restoreEditedMessages()
}

function showSourceDetail(source) {
  selectedSource.value = source
  sourceDialogVisible.value = true
}

function toggleSidebar() {
  closeConversationMenu()
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function onConversationCommand(command, conversation) {
  closeConversationMenu()
  if (command === 'rename') {
    handleRename(conversation)
    return
  }

  if (command === 'delete') {
    deleteConversation(conversation.id)
  }
}

async function handleRename(conversation) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新标题', '重命名对话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: conversation.title || '新对话'
    })

    if (value && value.trim()) {
      await chatApi.updateConversation(conversation.id, { title: value.trim() })
      const conv = conversations.value.find(c => c.id === conversation.id)
      if (conv) conv.title = value.trim()
      invalidateCache('conversations:list')
      ElMessage.success('重命名成功')
    }
  } catch {
    // 用户取消
  }
}

async function handleTitleSubmit(title) {
  const nextTitle = title?.trim()
  if (!nextTitle || !currentConversationId.value) return

  try {
    await chatApi.updateConversation(currentConversationId.value, { title: nextTitle })
    const currentConversation = conversations.value.find(c => c.id === currentConversationId.value)
    if (currentConversation) {
      currentConversation.title = nextTitle
    }
    invalidateCache('conversations:list')
  } catch (error) {
    ElMessage.error('标题更新失败')
  }
}

let searchTimeout = null
async function handleSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    if (searchQuery.value.trim()) {
      try {
        const res = await chatApi.searchConversations({ q: searchQuery.value })
        searchResults.value = res.data?.conversations || []
      } catch (error) {
        console.error('Search failed:', error)
        searchResults.value = []
      }
    } else {
      searchResults.value = []
    }
  }, 300)
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

function handleSwitchUser() {
  showUserSwitchDialog.value = false
  handleLogout()
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 24 * 60 * 60 * 1000) {
    if (diff < 60 * 60 * 1000) {
      const minutes = Math.floor(diff / (60 * 1000))
      return minutes < 1 ? '刚刚' : `${minutes}分钟前`
    }
    const hours = Math.floor(diff / (60 * 60 * 1000))
    return `${hours}小时前`
  }

  if (diff < 7 * 24 * 60 * 60 * 1000) {
    const days = Math.floor(diff / (24 * 60 * 60 * 1000))
    return `${days}天前`
  }

  return date.toLocaleDateString('zh-CN')
}

let prefetchedWorkspaceRoutes = false
function prefetchWorkspaceRoutes() {
  if (prefetchedWorkspaceRoutes) return
  prefetchedWorkspaceRoutes = true

  const prefetch = () => {
    import('@/views/kg/KnowledgeGraphView.vue')
    import('@/views/knowledge/KnowledgeView.vue')
    import('@/views/workspace/WorkspaceView.vue')
    import('@/views/workspace/ModelDetailView.vue')
  }

  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    window.requestIdleCallback(prefetch, { timeout: 1500 })
    return
  }

  setTimeout(prefetch, 400)
}

// 生命周期
onMounted(() => {
  document.addEventListener('pointerdown', handleGlobalPointerDown)
  loadConversations()
  loadModels()
  prefetchWorkspaceRoutes()
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', handleGlobalPointerDown)
})
</script>

<style scoped lang="scss">
.chat-layout {
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, #FAFBFE 0%, #F3F1FF 50%, #EEEDF9 100%);

  &.sidebar-collapsed {
    .chat-sidebar {
      width: 0;
      overflow: hidden;
      border-right: none;
    }
  }
}

.chat-sidebar {
  width: 280px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-right: 1px solid rgba(99, 102, 241, 0.08);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-brand {
  padding: 18px 16px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  position: relative;

  .brand-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;

    .el-icon {
      background: linear-gradient(135deg, #6366F1, #8B5CF6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .brand-text {
      font-size: 20px;
      font-weight: 800;
      background: linear-gradient(135deg, #4F46E5, #7C3AED);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.5px;
    }
  }

  .sidebar-toggle {
    position: absolute;
    top: 18px;
    right: 16px;
    border: none;
    background: transparent;
    color: #8B87B5;

    &:hover {
      background: rgba(99, 102, 241, 0.08);
      color: #6366F1;
    }
  }

  .new-chat-btn {
    width: 100%;
    border-radius: 10px;
    font-weight: 600;
    padding: 11px;
    background: linear-gradient(135deg, #6366F1, #8B5CF6);
    border: none;
    box-shadow: 0 2px 10px rgba(99, 102, 241, 0.25);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      background: linear-gradient(135deg, #4F46E5, #7C3AED);
      transform: translateY(-1px);
      box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35);
    }

    &:active {
      transform: translateY(0);
    }
  }
}

.sidebar-nav {
  padding: 10px 8px;

  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 13px;
    border-radius: 10px;
    cursor: pointer;
    color: #5B5580;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.25s ease;
    margin: 2px 0;

    &:hover {
      background: rgba(99, 102, 241, 0.07);
      color: #4F46E5;
    }

    &.active {
      background: rgba(99, 102, 241, 0.12);
      color: #4F46E5;
      font-weight: 600;

      .el-icon {
        color: #6366F1;
      }
    }

    .el-icon {
      font-size: 18px;
      color: #A5A3C9;
      transition: color 0.25s;
    }

    &:hover .el-icon {
      color: #6366F1;
    }
  }
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;

  :deep(.el-dropdown) {
    display: block;
  }

  .list-header {
    padding: 10px 14px;
    margin-bottom: 6px;

    .list-title {
      font-size: 11px;
      font-weight: 700;
      color: #A5A3C9;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
  }

  .conv-items {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .conv-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;

    &:hover {
      background: rgba(99, 102, 241, 0.07);

      .conv-actions {
        opacity: 1;
      }
    }

    &.active {
      background: rgba(99, 102, 241, 0.12);

      .conv-title {
        color: #4F46E5;
        font-weight: 600;
      }

      .conv-icon {
        color: #6366F1;
      }
    }

    .conv-icon {
      color: #A5A3C9;
      font-size: 16px;
      flex-shrink: 0;
      transition: color 0.2s;
    }

    .conv-title {
      flex: 1;
      font-size: 13.5px;
      color: #4B5563;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      transition: all 0.2s;
    }

  }
}

.floating-sidebar-toggle {
  position: fixed;
  top: 20px;
  left: 18px;
  z-index: 2200;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(99, 102, 241, 0.14);
  box-shadow: 0 10px 28px rgba(99, 102, 241, 0.18);
  color: #6366F1;

  &:hover {
    color: #4F46E5;
    background: #FFFFFF;
  }
}

.sidebar-footer {
  padding: 14px 16px;
  border-top: 1px solid rgba(99, 102, 241, 0.08);
  background: rgba(255, 255, 255, 0.5);
}

.user-footer-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 8px;
  border-radius: 10px;
  transition: all 0.25s ease;

  &:hover {
    background: rgba(99, 102, 241, 0.07);
  }

  span {
    flex: 1;
    font-size: 14px;
    font-weight: 600;
    color: #312E4A;
  }

  .dropdown-icon {
    font-size: 12px;
    color: #A5A3C9;
  }
}

.switch-side-btn {
  flex-shrink: 0;
  color: #6366F1;
  font-weight: 600;
  padding: 8px 10px;
  border-radius: 10px;

  &:hover {
    background: rgba(99, 102, 241, 0.08);
    color: #4F46E5;
  }
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: transparent;
}

.source-detail {
  .source-content {
    max-height: 400px;
    overflow-y: auto;
    white-space: pre-wrap;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.04), rgba(139, 92, 246, 0.03));
    padding: 14px;
    border-radius: 10px;
    font-size: 13.5px;
    line-height: 1.65;
    color: #312E4A;
  }
}

// 搜索弹窗样式
.search-dialog {
  :deep(.el-dialog__header) {
    display: none;
  }

  :deep(.el-dialog__body) {
    padding: 0;
  }
}

.search-content {
  padding: 20px 24px 24px;
}

.search-dialog-input {
  margin-bottom: 16px;

  :deep(.el-input__wrapper) {
    border-radius: 12px;
    padding: 8px 16px;
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.15) inset;
    background: rgba(255, 255, 255, 0.8);
    transition: all 0.25s ease;

    &:hover {
      box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.3) inset;
    }

    &.is-focus {
      box-shadow: 0 0 0 1px #6366F1 inset, 0 0 0 4px rgba(99, 102, 241, 0.1);
    }
  }

  :deep(.el-input__inner) {
    font-size: 15px;
    color: #1E1B4B;

    &::placeholder {
      color: #A5A3C9;
    }
  }

  :deep(.el-input__icon) {
    color: #A5A3C9;
  }
}

.search-placeholder {
  text-align: center;
  padding: 40px 20px;
  color: #A5A3C9;

  .placeholder-icon {
    color: rgba(99, 102, 241, 0.2);
    margin-bottom: 12px;
  }

  .placeholder-text {
    font-size: 14px;
    margin: 0;
  }
}

.search-results {
  max-height: 320px;
  overflow-y: auto;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  border: 1px solid transparent;

  &:hover {
    background: rgba(99, 102, 241, 0.06);
    border-color: rgba(99, 102, 241, 0.1);
    transform: translateX(4px);

    .result-arrow {
      opacity: 1;
      transform: translateX(0);
    }
  }

  .result-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.08));
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    .el-icon {
      color: #6366F1;
      font-size: 18px;
    }
  }

  .result-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .result-title {
    font-size: 14px;
    font-weight: 600;
    color: #312E4A;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .result-date {
    font-size: 12px;
    color: #A5A3C9;
  }

  .result-arrow {
    color: #6366F1;
    font-size: 16px;
    opacity: 0;
    transform: translateX(-8px);
    transition: all 0.25s ease;
  }
}

// 弹窗头部样式
.dialog-header-icon {
  text-align: center;
  padding: 28px 24px 20px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.04) 100%);
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  position: relative;

  .icon-wrapper {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.3);

    .el-icon {
      color: #fff;
    }
  }

  .dialog-title {
    font-size: 18px;
    font-weight: 700;
    color: #1E1B4B;
    margin: 0 0 4px;
  }

  .dialog-subtitle {
    font-size: 13px;
    color: #8B87B5;
    margin: 0;
  }
}

// 弹窗关闭按钮
.dialog-close-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8B87B5;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;

  &:hover {
    background: rgba(239, 68, 68, 0.1);
    color: #EF4444;
    transform: rotate(90deg);
  }

  &:active {
    transform: rotate(90deg) scale(0.95);
  }

  .el-icon {
    font-size: 16px;
    font-weight: 600;
  }
}

.user-switch-content {
  .current-user {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px;

    .user-info-detail {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .username {
        font-size: 16px;
        font-weight: 700;
        color: #1E1B4B;
      }

      .user-role {
        font-size: 13px;
        color: #8B87B5;
      }
    }
  }

  .switch-actions {
    .switch-hint {
      font-size: 13px;
      color: #8B87B5;
      margin-bottom: 16px;
      text-align: center;
    }
  }
}

// 滚动条样式
.conversation-list {
  &::-webkit-scrollbar {
    width: 5px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.15);
    border-radius: 10px;

    &:hover {
      background: rgba(99, 102, 241, 0.28);
    }
  }
}

// 来源详情弹窗样式
.source-dialog {
  :deep(.el-dialog__header) {
    display: none;
  }

  :deep(.el-dialog__body) {
    padding: 0;
  }
}

.source-detail-body {
  padding: 24px 28px;
}

.source-meta {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 20px;

  .meta-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #5B5580;
    font-weight: 500;

    .el-icon {
      color: #6366F1;
      font-size: 18px;
    }

    &.score {
      .el-icon {
        color: #8B5CF6;
      }
    }
  }
}

.source-content-area {
  .content-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 700;
    color: #5B5580;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;

    .el-icon {
      color: #6366F1;
      font-size: 16px;
    }
  }
}

.source-content-text {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.04), rgba(139, 92, 246, 0.03));
  border: 1px solid rgba(99, 102, 241, 0.1);
  border-radius: 12px;
  padding: 18px;
  max-height: 320px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  line-height: 1.75;
  color: #312E4A;
  margin: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

// 用户切换弹窗样式
.user-switch-dialog {
  :deep(.el-dialog__header) {
    display: none;
  }

  :deep(.el-dialog__body) {
    padding: 0;
  }
}

.user-switch-content {
  padding: 24px 28px;

  .current-user {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.04), rgba(139, 92, 246, 0.03));
    border-radius: 14px;
    border: 1px solid rgba(99, 102, 241, 0.08);

    .el-avatar {
      background: linear-gradient(135deg, #6366F1, #8B5CF6);
      color: #fff;
      font-weight: 700;
      font-size: 20px;
    }

    .user-info-detail {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .username {
        font-size: 17px;
        font-weight: 700;
        color: #1E1B4B;
      }

      .user-role {
        font-size: 13px;
        color: #8B87B5;
      }
    }
  }

  .switch-divider {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px 0;
    color: #A5A3C9;

    .el-icon {
      font-size: 20px;
    }
  }

  .switch-actions {
    .switch-hint {
      font-size: 13px;
      color: #8B87B5;
      margin-bottom: 16px;
      text-align: center;
      padding: 12px 16px;
      background: rgba(245, 158, 11, 0.08);
      border-radius: 10px;
      border: 1px dashed rgba(245, 158, 11, 0.2);
    }

    .switch-btn {
      width: 100%;
      border-radius: 12px;
      padding: 12px 20px;
      font-weight: 600;
      font-size: 15px;
      background: linear-gradient(135deg, #6366F1, #8B5CF6);
      border: none;
      box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
      transition: all 0.25s ease;

      &:hover {
        background: linear-gradient(135deg, #4F46E5, #7C3AED);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
        transform: translateY(-2px);
      }
    }
  }
}
</style>
