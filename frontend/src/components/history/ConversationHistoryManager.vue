<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">对话历史管理</h2>
      </div>
    </div>

    <div class="history-layout">
      <!-- 左侧对话列表 -->
      <div class="history-sidebar">
        <div class="sidebar-header">
          <div class="sidebar-search">
            <el-input
              v-model="historySearch"
              clearable
              placeholder="搜索对话内容或标题"
              class="history-search-input"
              @keyup.enter="loadConversationHistory"
            />
            <div class="history-tool-actions">
              <el-button type="primary" size="small" @click="loadConversationHistory">检索</el-button>
              <el-button size="small" @click="historySearch = ''; loadConversationHistory">重置</el-button>
            </div>
          </div>
        </div>

        <div class="history-list">
          <div
            v-for="conversation in filteredConversationHistory"
            :key="conversation.conversation_id"
            class="history-list-item"
            :class="{ active: selectedConversationId === conversation.conversation_id }"
            @click="selectConversation(conversation.conversation_id)"
          >
            <div class="history-list-title">{{ conversation.title || '新对话' }}</div>
            <div class="history-list-meta">
              <span>{{ conversation.username }}</span>
              <span>{{ formatDate(conversation.updated_at) }}</span>
            </div>
          </div>

          <div v-if="filteredConversationHistory.length === 0 && !loadingHistory" class="history-list-empty">
            暂无符合条件的历史记录
          </div>
        </div>
      </div>

      <!-- 右侧对话内容 -->
      <div class="history-content" v-loading="loadingMessages">
        <div v-if="!selectedConversationId" class="history-empty">
          <el-empty description="请选择左侧对话查看完整记录" :image-size="100" />
        </div>

        <div v-else class="history-messages">
          <article
            v-for="item in conversationMessages"
            :key="item.id"
            class="history-row"
            :class="{ user: item.role === 'user', assistant: item.role !== 'user' }"
          >
            <div class="history-bubble">
              <AiMessage
                :content="item.content"
                :role="item.role"
              />
            </div>
          </article>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as adminApi from '@/api/admin'
import { exportAsMarkdown, formatConversationAsMarkdown } from '@/utils/export'
import { AiMessage } from '@/components/ai'

const conversationHistory = ref([])
const loadingHistory = ref(false)
const historySearch = ref('')
const selectedConversationId = ref(null)
const conversationMessages = ref([])
const loadingMessages = ref(false)

const filteredConversationHistory = computed(() => {
  const keyword = historySearch.value.trim().toLowerCase()
  if (!keyword) return conversationHistory.value
  return conversationHistory.value.filter(item => (item.title || '').toLowerCase().includes(keyword))
})

async function loadConversationHistory() {
  loadingHistory.value = true
  try {
    const res = await adminApi.searchHistoryConversations({ 
      keyword: historySearch.value, 
      per_page: 100 
    })
    conversationHistory.value = res.data?.conversations || []
    // 如果没有选中的对话且有对话记录，默认选中第一个
    if (!selectedConversationId.value && conversationHistory.value.length > 0) {
      await selectConversation(conversationHistory.value[0].conversation_id)
    }
  } finally {
    loadingHistory.value = false
  }
}

async function selectConversation(conversationId) {
  selectedConversationId.value = conversationId
  loadingMessages.value = true
  try {
    const res = await adminApi.getHistoryConversationDetail(conversationId)
    conversationMessages.value = res.data?.messages || []
  } catch {
    ElMessage.error('加载对话失败')
  } finally {
    loadingMessages.value = false
  }
}

async function exportHistoryMarkdown(conversation) {
  try {
    const res = await adminApi.getHistoryConversationDetail(conversation.conversation_id)
    const data = res.data || {}
    const markdown = formatConversationAsMarkdown(
      { title: data.title || conversation.title || '未命名对话' },
      data.messages || []
    )
    exportAsMarkdown(markdown, (data.title || conversation.title || 'conversation').replace(/[\/:*?"<>|]/g, '_'))
    ElMessage.success('Markdown 已导出')
  } catch {
    ElMessage.error('导出失败')
  }
}

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  loadConversationHistory()
})
</script>

<style scoped lang="scss">
.page-container {
  padding: 24px 28px;
  min-height: 100%;
  height: 100%;
  overflow: auto;
  background: linear-gradient(135deg, #FAFBFE 0%, #F3F1FF 50%, #EEEDF9 100%);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
  padding: 0 4px;
}

.header-left {
  display: flex;
  align-items: center;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  letter-spacing: -0.3px;
}

.history-layout {
  display: flex;
  height: calc(100vh - 140px);
  min-height: 0;
  gap: 20px;
}

.history-sidebar {
  width: 320px;
  background: #FFFFFF;
  border-radius: 16px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  box-shadow: 0 2px 12px rgba(79, 70, 229, 0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
}

.sidebar-search {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-search-input {
  margin-bottom: 8px;
}

.history-tool-actions {
  display: flex;
  gap: 8px;
}

.history-list {
  flex: 1;
  overflow: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-list-item {
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  font-size: 14px;
  line-height: 1.4;

  &:hover {
    background: #f1f5f9;
  }

  &.active {
    background: #e3f2fd;
    border-color: #bbdefb;
  }
}

.history-list-title {
  font-size: 13px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-list-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: #64748b;
}

.history-list-empty {
  padding: 24px 12px;
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
}

.history-content {
  flex: 1;
  background: #FFFFFF;
  border-radius: 16px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  box-shadow: 0 2px 12px rgba(79, 70, 229, 0.04);
  overflow: auto;
  padding: 20px;
}

.history-empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.history-messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 800px;
  margin: 0 auto;
}

.history-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 100%;
}

.history-bubble {
  flex: 1;
  padding: 12px 16px;
  border-radius: 12px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  box-shadow: none;
  font-size: 14px;
  line-height: 1.5;
}

.history-row.user .history-bubble {
  background: #e3f2fd;
  border-color: #bbdefb;
  align-self: flex-start;
}

.history-row.assistant .history-bubble {
  background: #f1f5f9;
  border-color: #cbd5e1;
  align-self: flex-start;
}

:deep(.history-bubble .ai-message) {
  padding: 0;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
</style>
