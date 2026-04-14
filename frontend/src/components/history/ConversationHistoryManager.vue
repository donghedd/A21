<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">对话历史管理</h2>
      </div>
    </div>

    <section class="section">
      <div class="panel-card">
        <div class="users-toolbar">
          <el-input
            v-model="historySearch"
            clearable
            placeholder="按标题搜索历史对话"
            class="users-search"
          />
          <el-button @click="loadConversationHistory">刷新</el-button>
        </div>

        <el-table :data="filteredConversationHistory" v-loading="loadingHistory" stripe class="custom-table">
          <el-table-column prop="title" label="对话标题" min-width="220" />
          <el-table-column label="更新时间" min-width="180">
            <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="exportHistoryMarkdown(row)">
                导出 Markdown
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as chatApi from '@/api/chat'
import { exportAsMarkdown, formatConversationAsMarkdown } from '@/utils/export'

const conversationHistory = ref([])
const loadingHistory = ref(false)
const historySearch = ref('')

const filteredConversationHistory = computed(() => {
  const keyword = historySearch.value.trim().toLowerCase()
  if (!keyword) return conversationHistory.value
  return conversationHistory.value.filter(item => (item.title || '').toLowerCase().includes(keyword))
})

async function loadConversationHistory() {
  loadingHistory.value = true
  try {
    const res = await chatApi.getConversations({ per_page: 100 })
    conversationHistory.value = res.data?.conversations || []
  } finally {
    loadingHistory.value = false
  }
}

async function exportHistoryMarkdown(conversation) {
  try {
    const res = await chatApi.getConversation(conversation.id)
    const data = res.data || {}
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
</style>
