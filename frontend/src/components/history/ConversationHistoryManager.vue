<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">{{ adminMode ? '全局对话历史管理' : '对话历史管理' }}</h2>
      </div>
    </div>

    <section class="section">
      <div class="panel-card">
        <div class="users-toolbar">
          <el-input
            v-model="historySearch"
            clearable
            :placeholder="adminMode ? '按标题或用户名搜索历史对话' : '按标题搜索历史对话'"
            class="users-search"
          />
          <el-button @click="loadConversationHistory">刷新</el-button>
        </div>

        <el-table :data="filteredConversationHistory" v-loading="loadingHistory" stripe class="custom-table">
          <el-table-column prop="title" label="对话标题" min-width="220" />
          <el-table-column v-if="adminMode" prop="username" label="用户" min-width="120" />
          <el-table-column label="更新时间" min-width="180">
            <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column v-if="adminMode" label="消息数" width="90" align="center">
            <template #default="{ row }">{{ row.message_count ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" :width="adminMode ? 200 : 140" fixed="right">
            <template #default="{ row }">
              <el-button
                size="small"
                link
                type="primary"
                @click="openConversationDetail(row.id)"
              >
                查看
              </el-button>
              <el-button size="small" link type="primary" @click="exportHistoryMarkdown(row)">
                导出 Markdown
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <el-dialog
      v-model="detailVisible"
      width="860px"
      destroy-on-close
      class="custom-dialog history-detail-dialog"
    >
      <button class="dialog-close-btn" @click="detailVisible = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><ChatDotRound /></el-icon>
        </div>
        <h3 class="dialog-title">{{ detailConversation.title || '未命名对话' }}</h3>
        <p class="dialog-subtitle">
          {{ adminMode ? (detailConversation.username || '未知用户') : '当前用户' }}
          <span v-if="detailConversation.updated_at"> · {{ formatDate(detailConversation.updated_at) }}</span>
        </p>
      </div>

      <div class="detail-body" v-loading="loadingDetail">
        <el-empty
          v-if="!loadingDetail && detailMessages.length === 0"
          description="暂无消息"
          :image-size="80"
        />
        <div v-else class="detail-messages">
          <div
            v-for="message in detailMessages"
            :key="message.id"
            class="detail-message"
            :class="`role-${message.role}`"
          >
            <div class="message-meta">
              <span class="message-role">{{ roleLabelMap[message.role] || message.role }}</span>
              <span class="message-time">{{ formatDate(message.created_at) }}</span>
            </div>
            <div class="message-content">{{ message.content }}</div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ChatDotRound, Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as chatApi from '@/api/chat'
import * as adminApi from '@/api/admin'
import { exportAsMarkdown, formatConversationAsMarkdown } from '@/utils/export'

const props = defineProps({
  adminMode: { type: Boolean, default: false },
  selectedConversationId: { type: String, default: '' }
})

const conversationHistory = ref([])
const loadingHistory = ref(false)
const historySearch = ref('')
const detailVisible = ref(false)
const loadingDetail = ref(false)
const detailConversation = ref({})
const detailMessages = ref([])

const roleLabelMap = {
  user: '用户',
  assistant: '助手',
  system: '系统'
}

const filteredConversationHistory = computed(() => {
  const keyword = historySearch.value.trim().toLowerCase()
  if (!keyword) return conversationHistory.value
  return conversationHistory.value.filter(item => (
    (item.title || '').toLowerCase().includes(keyword) ||
    (props.adminMode && (item.username || '').toLowerCase().includes(keyword))
  ))
})

async function loadConversationHistory() {
  loadingHistory.value = true
  try {
    if (props.adminMode) {
      const res = await adminApi.searchHistoryConversations({ per_page: 1000 })
      conversationHistory.value = (res.data?.items || []).map(item => ({
        id: item.conversation_id,
        title: item.conversation_title || '未命名对话',
        username: item.username || '',
        email: item.email || '',
        updated_at: item.updated_at,
        message_count: item.message_count || 0
      }))
    } else {
      const res = await chatApi.getConversations({ per_page: 100 })
      conversationHistory.value = (res.data?.conversations || []).map(item => ({
        id: item.id,
        title: item.title || '未命名对话',
        updated_at: item.updated_at
      }))
    }
  } finally {
    loadingHistory.value = false
  }
}

async function openConversationDetail(conversationId) {
  if (!conversationId) return
  loadingDetail.value = true
  detailVisible.value = true
  detailConversation.value = {}
  detailMessages.value = []

  try {
    if (props.adminMode) {
      const res = await adminApi.getHistoryConversationDetail(conversationId)
      detailConversation.value = res.data?.conversation || {}
      detailMessages.value = res.data?.messages || []
    } else {
      const res = await chatApi.getConversation(conversationId)
      detailConversation.value = {
        id: res.data?.id,
        title: res.data?.title,
        updated_at: res.data?.updated_at
      }
      detailMessages.value = res.data?.messages || []
    }
  } catch {
    detailVisible.value = false
    ElMessage.error('加载对话详情失败')
  } finally {
    loadingDetail.value = false
  }
}

async function exportHistoryMarkdown(conversation) {
  try {
    const res = props.adminMode
      ? await adminApi.getHistoryConversationDetail(conversation.id)
      : await chatApi.getConversation(conversation.id)

    const data = props.adminMode
      ? {
          title: res.data?.conversation?.title,
          messages: res.data?.messages || []
        }
      : (res.data || {})

    const markdown = formatConversationAsMarkdown(
      { title: data.title || conversation.title || '未命名对话' },
      data.messages || []
    )
    exportAsMarkdown(markdown, (data.title || conversation.title || 'conversation').replace(/[\\/:*?"<>|]/g, '_'))
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

watch(
  () => props.selectedConversationId,
  async (conversationId) => {
    if (!props.adminMode || !conversationId || loadingHistory.value) return
    await nextTick()
    openConversationDetail(conversationId)
  },
  { immediate: true }
)
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

.section {
  margin-bottom: 32px;
}

.panel-card {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  box-shadow: 0 2px 12px rgba(79, 70, 229, 0.04);
}

.users-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 18px;
}

.users-search {
  flex: 1;
}

:deep(.history-detail-dialog .el-dialog__header) {
  display: none;
}

:deep(.history-detail-dialog .el-dialog__body) {
  padding: 0;
}

.dialog-close-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
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
}

.dialog-header-icon {
  text-align: center;
  padding: 32px 28px 24px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.04) 100%);
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);

  .icon-wrapper {
    width: 64px;
    height: 64px;
    border-radius: 18px;
    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.35);

    .el-icon {
      color: #fff;
    }
  }

  .dialog-title {
    font-size: 20px;
    font-weight: 700;
    color: #1E1B4B;
    margin: 0 0 6px;
  }

  .dialog-subtitle {
    font-size: 14px;
    color: #8B87B5;
    margin: 0;
  }
}

.detail-body {
  padding: 24px 28px 28px;
  min-height: 180px;
}

.detail-messages {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-message {
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  background: rgba(255, 255, 255, 0.82);

  &.role-user {
    background: rgba(99, 102, 241, 0.06);
  }

  &.role-assistant {
    background: rgba(16, 185, 129, 0.05);
  }
}

.message-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.message-role {
  font-size: 13px;
  font-weight: 700;
  color: #4F46E5;
}

.message-time {
  font-size: 12px;
  color: #8B87B5;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  color: #312E4A;
}
</style>
