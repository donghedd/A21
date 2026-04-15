<template>
  <div class="page-container" :class="{ 'detail-mode': adminShowingDetail }">
    <div v-if="!adminShowingDetail" class="page-header">
      <div class="header-left">
        <h2 class="page-title">{{ adminMode ? '全局对话历史管理' : '对话历史管理' }}</h2>
      </div>
    </div>

    <section class="section">
      <div class="panel-card" :class="{ 'history-admin-card': adminMode }">
        <div
          v-if="adminMode"
          class="history-admin-shell"
          :class="{
            'detail-only': adminShowingDetail,
            'manage-only': !adminShowingDetail
          }"
        >
          <div v-if="!adminShowingDetail" class="history-admin-left">
            <div class="users-toolbar history-toolbar">
              <el-input
                v-model="filters.keyword"
                clearable
                :placeholder="adminMode ? '按标题或消息关键词搜索' : '按标题搜索历史对话'"
                class="users-search"
                @keyup.enter="applyFilters"
              />
              <el-input
                v-if="adminMode"
                v-model="filters.username"
                clearable
                placeholder="按成员搜索"
                class="history-member-input"
                @keyup.enter="applyFilters"
              />
              <el-date-picker
                v-model="filters.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                class="history-date-range"
              />
              <el-button type="primary" @click="applyFilters">筛选</el-button>
              <el-button @click="resetFilters">重置</el-button>
              <el-button @click="loadConversationHistory">刷新</el-button>
            </div>

            <el-table
              ref="historyTableRef"
              :data="displayConversationHistory"
              v-loading="loadingHistory"
              stripe
              class="custom-table"
              row-key="id"
              height="100%"
              @selection-change="handleSelectionChange"
              @row-click="(row) => openConversationDetail(row.id)"
            >
              <el-table-column type="selection" width="48" :reserve-selection="true" />
              <el-table-column prop="title" label="对话标题" min-width="220" show-overflow-tooltip />
              <el-table-column prop="username" label="成员" min-width="120" show-overflow-tooltip />
              <el-table-column label="更新时间" min-width="180">
                <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
              </el-table-column>
              <el-table-column label="消息数" width="90" align="center">
                <template #default="{ row }">{{ row.message_count ?? '-' }}</template>
              </el-table-column>
              <el-table-column label="操作" width="240" fixed="right">
                <template #default="{ row }">
                  <div class="row-actions">
                    <el-button size="small" link type="primary" @click.stop="openConversationDetail(row.id)">
                      查看
                    </el-button>
                    <el-button size="small" link type="primary" @click.stop="exportHistoryMarkdown(row)">
                      导出 Markdown
                    </el-button>
                    <el-button size="small" link type="danger" @click.stop="deleteConversation(row)">
                      删除
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>

            <el-pagination
              v-if="pagination.total > pagination.per_page"
              class="history-pagination"
              background
              layout="total, prev, pager, next"
              :total="pagination.total"
              :page-size="pagination.per_page"
              :current-page="pagination.page"
              @current-change="handlePageChange"
            />
          </div>

          <div v-if="adminShowingDetail" class="history-admin-right detail-only-panel">
            <div v-if="detailConversation.id || loadingDetail" class="history-chat-view">
              <AiChat
                :title="detailConversation.title || '未命名对话'"
                :messages="detailDisplayMessages"
                :is-streaming="false"
                :show-welcome="false"
                :show-model-selector="false"
                :allow-speech="false"
                :hide-input-area="true"
                :readonly="true"
                :title-editable="false"
                :user-name="detailConversation.username || 'Admin'"
                class="history-admin-chat"
              />
            </div>
            <el-empty
              v-else
              description="未找到该对话记录"
              :image-size="100"
            />
          </div>
        </div>

        <template v-else>
        <div class="users-toolbar history-toolbar">
          <el-input
            v-model="filters.keyword"
            clearable
            :placeholder="adminMode ? '按标题或消息关键词搜索' : '按标题搜索历史对话'"
            class="users-search"
            @keyup.enter="applyFilters"
          />
          <el-input
            v-if="adminMode"
            v-model="filters.username"
            clearable
            placeholder="按成员搜索"
            class="history-member-input"
            @keyup.enter="applyFilters"
          />
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            class="history-date-range"
          />
          <el-button type="primary" @click="applyFilters">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button @click="loadConversationHistory">刷新</el-button>
        </div>

        <el-table
          ref="historyTableRef"
          :data="displayConversationHistory"
          v-loading="loadingHistory"
          stripe
          class="custom-table"
          row-key="id"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="48" :reserve-selection="true" />
          <el-table-column prop="title" label="对话标题" min-width="220" show-overflow-tooltip />
          <el-table-column v-if="adminMode" prop="username" label="成员" min-width="120" show-overflow-tooltip />
          <el-table-column label="更新时间" min-width="180">
            <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column v-if="adminMode" label="消息数" width="90" align="center">
            <template #default="{ row }">{{ row.message_count ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" :width="adminMode ? 240 : 220" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button size="small" link type="primary" @click="openConversationDetail(row.id)">
                  查看
                </el-button>
                <el-button size="small" link type="primary" @click="exportHistoryMarkdown(row)">
                  导出 Markdown
                </el-button>
                <el-button size="small" link type="danger" @click="deleteConversation(row)">
                  删除
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="pagination.total > pagination.per_page"
          class="history-pagination"
          background
          layout="total, prev, pager, next"
          :total="pagination.total"
          :page-size="pagination.per_page"
          :current-page="pagination.page"
          @current-change="handlePageChange"
        />
        </template>
      </div>
    </section>

    <transition name="batch-bar-fade">
      <div v-if="selectedRows.length > 0" class="history-bottom-bar">
        <span class="batch-count">已选 {{ selectedRows.length }} 项</span>
        <div class="batch-actions">
          <el-button size="small" @click="exportSelectedMarkdown">打包 zip 下载</el-button>
          <el-button size="small" type="danger" @click="deleteSelectedConversations">多选删除</el-button>
        </div>
      </div>
    </transition>

    <el-dialog
      v-if="!adminMode"
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
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ChatDotRound, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as chatApi from '@/api/chat'
import * as adminApi from '@/api/admin'
import { exportAsMarkdown, exportMarkdownZip, formatConversationAsMarkdown } from '@/utils/export'
import { AiChat } from '@/components/ai'

const props = defineProps({
  adminMode: { type: Boolean, default: false },
  selectedConversationId: { type: String, default: '' }
})

const conversationHistory = ref([])
const loadingHistory = ref(false)
const selectedRows = ref([])
const selectedRowMap = ref(new Map())
const historyTableRef = ref(null)
const detailVisible = ref(false)
const loadingDetail = ref(false)
const detailConversation = ref({})
const detailMessages = ref([])
const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})
const filters = reactive({
  keyword: '',
  username: '',
  dateRange: []
})

const roleLabelMap = {
  user: '用户',
  assistant: '助手',
  system: '系统'
}

const adminShowingDetail = computed(() => props.adminMode && !!props.selectedConversationId)

const detailDisplayMessages = computed(() => (
  detailMessages.value.map(message => ({
    id: message.id,
    role: message.role,
    content: message.content,
    thinking: message.thinking_content || '',
    thinkingDuration: message.thinking_duration || 0,
    sources: message.sources || [],
    loading: false,
    interrupted: false,
    created_at: message.created_at
  }))
))

const filteredConversationHistory = computed(() => {
  if (props.adminMode) return conversationHistory.value

  const keyword = filters.keyword.trim().toLowerCase()
  const [startDate, endDate] = filters.dateRange || []

  return conversationHistory.value.filter(item => {
    const titleMatch = !keyword || (item.title || '').toLowerCase().includes(keyword)
    const updatedAt = item.updated_at ? new Date(item.updated_at) : null
    const afterStart = !startDate || (updatedAt && updatedAt >= new Date(`${startDate}T00:00:00`))
    const beforeEnd = !endDate || (updatedAt && updatedAt <= new Date(`${endDate}T23:59:59`))
    return titleMatch && afterStart && beforeEnd
  })
})

const displayConversationHistory = computed(() => {
  if (props.adminMode) return filteredConversationHistory.value

  const start = (pagination.page - 1) * pagination.per_page
  const end = start + pagination.per_page
  return filteredConversationHistory.value.slice(start, end)
})

function syncSelectedRows() {
  selectedRows.value = Array.from(selectedRowMap.value.values())
}

async function restoreCurrentPageSelection() {
  await nextTick()
  const table = historyTableRef.value
  if (!table?.toggleRowSelection) return

  for (const row of displayConversationHistory.value) {
    table.toggleRowSelection(row, selectedRowMap.value.has(row.id))
  }
}

async function loadConversationHistory(page = pagination.page) {
  loadingHistory.value = true
  try {
    if (props.adminMode) {
      const [startDate, endDate] = filters.dateRange || []
      const res = await adminApi.searchHistoryConversations({
        page,
        per_page: pagination.per_page,
        keyword: filters.keyword || undefined,
        username: filters.username || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined
      })
      conversationHistory.value = (res.data?.items || []).map(item => ({
        id: item.conversation_id,
        title: item.conversation_title || '未命名对话',
        username: item.username || '',
        email: item.email || '',
        updated_at: item.updated_at,
        message_count: item.message_count || 0
      }))
      pagination.page = res.data?.pagination?.page || page
      pagination.per_page = res.data?.pagination?.per_page || pagination.per_page
      pagination.total = res.data?.pagination?.total || 0
    } else {
      const res = await chatApi.getConversations({ per_page: 1000 })
      conversationHistory.value = (res.data?.conversations || []).map(item => ({
        id: item.id,
        title: item.title || '未命名对话',
        updated_at: item.updated_at
      }))
      pagination.page = page
      pagination.total = conversationHistory.value.length
    }
    await restoreCurrentPageSelection()
  } finally {
    loadingHistory.value = false
  }
}

function applyFilters() {
  pagination.page = 1
  if (props.adminMode) {
    loadConversationHistory(1)
    return
  }
  pagination.total = filteredConversationHistory.value.length
  restoreCurrentPageSelection()
}

function resetFilters() {
  filters.keyword = ''
  filters.username = ''
  filters.dateRange = []
  pagination.page = 1
  loadConversationHistory(1)
}

function handlePageChange(page) {
  if (props.adminMode) {
    loadConversationHistory(page)
    return
  }
  pagination.page = page
  restoreCurrentPageSelection()
}

function handleSelectionChange(rows) {
  const currentPageIds = new Set(displayConversationHistory.value.map(item => item.id))

  for (const id of currentPageIds) {
    selectedRowMap.value.delete(id)
  }

  for (const row of rows) {
    selectedRowMap.value.set(row.id, row)
  }

  syncSelectedRows()
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
      detailVisible.value = false
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

async function fetchConversationMessages(conversationId) {
  if (props.adminMode) {
    const res = await adminApi.getHistoryConversationDetail(conversationId)
    return {
      title: res.data?.conversation?.title,
      messages: res.data?.messages || []
    }
  }

  const res = await chatApi.getConversation(conversationId)
  return {
    title: res.data?.title,
    messages: res.data?.messages || []
  }
}

async function exportHistoryMarkdown(conversation, showMessage = true) {
  try {
    const data = await fetchConversationMessages(conversation.id)
    const markdown = formatConversationAsMarkdown(
      { title: data.title || conversation.title || '未命名对话' },
      data.messages || []
    )
    exportAsMarkdown(markdown, (data.title || conversation.title || 'conversation').replace(/[\\/:*?"<>|]/g, '_'))
    if (showMessage) ElMessage.success('Markdown 已导出')
  } catch {
    if (showMessage) ElMessage.error('导出失败')
    throw new Error('export failed')
  }
}

async function exportSelectedMarkdown() {
  if (!selectedRows.value.length) return

  const files = []
  for (const row of selectedRows.value) {
    try {
      const data = await fetchConversationMessages(row.id)
      const markdown = formatConversationAsMarkdown(
        { title: data.title || row.title || '未命名对话' },
        data.messages || []
      )
      files.push({
        name: data.title || row.title || `conversation-${row.id}`,
        content: markdown,
        updatedAt: row.updated_at
      })
    } catch {}
  }

  if (files.length > 0) {
    const prefix = props.adminMode ? 'admin-history' : 'my-history'
    exportMarkdownZip(files, `${prefix}-${new Date().toISOString().slice(0, 10)}.zip`)
    ElMessage.success(`已打包导出 ${files.length} 个 Markdown 文件`)
  } else {
    ElMessage.error('批量导出失败')
  }
}

async function deleteConversation(conversation) {
  try {
    await ElMessageBox.confirm(`确定删除「${conversation.title || '未命名对话'}」？`, '确认删除', {
      type: 'warning'
    })
    if (props.adminMode) {
      await adminApi.deleteHistoryConversation(conversation.id)
    } else {
      await chatApi.deleteConversation(conversation.id)
    }

    if (detailConversation.value?.id === conversation.id) {
      detailVisible.value = false
    }

    selectedRowMap.value.delete(conversation.id)
    syncSelectedRows()

    ElMessage.success('已删除')
    await loadConversationHistory(props.adminMode ? pagination.page : 1)
  } catch {}
}

async function deleteSelectedConversations() {
  if (!selectedRows.value.length) return

  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 条对话？`, '批量删除', {
      type: 'warning'
    })

    for (const row of selectedRows.value) {
      if (props.adminMode) {
        await adminApi.deleteHistoryConversation(row.id)
      } else {
        await chatApi.deleteConversation(row.id)
      }
    }

    for (const row of selectedRows.value) {
      selectedRowMap.value.delete(row.id)
    }
    syncSelectedRows()
    detailVisible.value = false
    ElMessage.success(`已删除 ${selectedRows.value.length} 条对话`)
    await loadConversationHistory(props.adminMode ? 1 : 1)
  } catch {}
}

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  loadConversationHistory()
})

watch(
  filteredConversationHistory,
  (items) => {
    if (!props.adminMode) {
      pagination.total = items.length
      const maxPage = Math.max(1, Math.ceil(items.length / pagination.per_page))
      if (pagination.page > maxPage) {
        pagination.page = maxPage
      }
    }
    restoreCurrentPageSelection()
  },
  { immediate: true }
)

watch(
  () => props.selectedConversationId,
  async (conversationId) => {
    if (!props.adminMode) return
    if (!conversationId) {
      detailConversation.value = {}
      detailMessages.value = []
      loadingDetail.value = false
      return
    }
    if (loadingHistory.value) return
    await nextTick()
    openConversationDetail(conversationId)
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
.page-container {
  padding: 24px 28px;
  padding-bottom: 112px;
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

.page-container.detail-mode {
  padding-top: 12px;
}

.panel-card {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  box-shadow: 0 2px 12px rgba(79, 70, 229, 0.04);
}

.history-admin-card {
  padding: 18px;
  height: calc(100vh - 170px);
  min-height: 620px;
  overflow: hidden;
}

.history-admin-shell {
  display: grid;
  grid-template-columns: minmax(420px, 1.1fr) minmax(420px, 1fr);
  gap: 18px;
  height: 100%;
}

.history-admin-shell.manage-only {
  grid-template-columns: minmax(0, 1fr);
}

.history-admin-shell.detail-only {
  grid-template-columns: minmax(0, 1fr);
}

.history-admin-left,
.history-admin-right {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.history-admin-left {
  overflow: hidden;
}

.history-admin-right {
  border: none;
  border-radius: 16px;
  background: transparent;
  overflow: hidden;
}

.detail-only-panel {
  min-width: 0;
}

.history-chat-view {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.history-admin-chat {
  flex: 1;
  min-height: 0;
  border-radius: 0;

  :deep(.ai-chat-container) {
    background: transparent;
  }

  :deep(.ai-chat-header) {
    border-radius: 0;
    padding: 18px 20px;
    background: rgba(255, 255, 255, 0.82);
    border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  }

  :deep(.ai-chat-messages) {
    padding: 16px 12px 18px;
  }
}

.users-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 18px;
}

.history-toolbar {
  flex-wrap: wrap;
}

.users-search {
  flex: 1;
  min-width: 220px;
}

.history-member-input {
  width: 180px;
}

.history-date-range {
  width: 320px;
}

.history-bottom-bar {
  position: fixed;
  left: 50%;
  bottom: 22px;
  transform: translateX(-50%);
  z-index: 2600;
  min-width: 360px;
  max-width: min(720px, calc(100vw - 32px));
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(99, 102, 241, 0.14);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  box-shadow: 0 16px 36px rgba(99, 102, 241, 0.18);
}

.batch-count {
  font-size: 13px;
  font-weight: 600;
  color: #4F46E5;
}

.batch-actions {
  display: flex;
  gap: 10px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.history-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

.batch-bar-fade-enter-active,
.batch-bar-fade-leave-active {
  transition: all 0.2s ease;
}

.batch-bar-fade-enter-from,
.batch-bar-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
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
