<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="sidebar-top">
        <div class="sidebar-header">
          <h1 class="brand-title">管理端</h1>
          <p class="brand-subtitle">仅管理员可访问</p>
        </div>

        <div class="sidebar-section">
          <div
            class="sidebar-item"
            :class="{ active: activeTab === 'users' }"
            @click="activeTab = 'users'"
          >
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </div>
          <div
            class="sidebar-item"
            :class="{ active: activeTab === 'history' }"
            @click="activeTab = 'history'"
          >
            <el-icon><Document /></el-icon>
            <span>用户对话记录</span>
          </div>
        </div>
      </div>

      <template v-if="activeTab === 'history'">
        <div class="sidebar-history-area">
          <div class="sidebar-history-tools">
            <div class="search-entry" @click="showHistorySearchDialog = true">
              <el-icon><Search /></el-icon>
              <span>{{ historySearchSummary }}</span>
            </div>
          </div>

          <div class="sidebar-history-list">
            <div
              v-for="conversation in historyConversations"
              :key="conversation.conversation_id"
              class="history-list-item"
              :class="{ active: selectedConversationId === conversation.conversation_id }"
              @click="selectConversation(conversation.conversation_id)"
            >
              <div class="history-list-title">{{ formatConversationTitle(conversation.conversation_title) }}</div>
              <div class="history-list-meta">
                <span>{{ conversation.username }}</span>
                <span>{{ conversation.message_count }} 条</span>
              </div>
            </div>

            <div v-if="historyConversations.length === 0 && !loadingHistoryList" class="history-list-empty">
              暂无符合条件的历史记录
            </div>
          </div>

          <div class="sidebar-pagination">
            <el-pagination
              background
              small
              layout="prev, pager, next"
              :total="historyPagination.total"
              :page-size="historyPagination.per_page"
              :current-page="historyPagination.page"
              @current-change="loadHistory"
            />
          </div>
        </div>
      </template>
      <div v-else class="sidebar-fill"></div>

      <div class="sidebar-footer">
        <div class="user-footer-row">
          <div class="admin-user-info">
            <el-avatar :size="32">{{ user?.username?.[0] || 'A' }}</el-avatar>
            <span>{{ user?.username || 'Admin' }}</span>
          </div>
          <el-button text class="switch-side-btn" @click="router.push({ name: 'ChatHome' })">
            切换为用户端
          </el-button>
        </div>
      </div>
    </aside>

    <main class="admin-main">
      <section v-if="activeTab === 'users'" class="admin-panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">用户管理</h2>
            <p class="panel-subtitle">查看用户信息并执行管理操作</p>
          </div>
        </div>

        <div class="panel-card">
          <div class="users-toolbar">
            <el-input
              v-model="userFilters.keyword"
              clearable
              placeholder="按用户名或邮箱查找"
              class="users-search"
              @keyup.enter="loadUsers(1)"
            />
            <el-select v-model="userPagination.per_page" class="users-page-size" @change="loadUsers(1)">
              <el-option :value="10" label="10 / 页" />
              <el-option :value="20" label="20 / 页" />
              <el-option :value="50" label="50 / 页" />
              <el-option :value="100" label="100 / 页" />
            </el-select>
            <el-button type="primary" @click="loadUsers(1)">查找</el-button>
            <el-button @click="resetUserFilters">重置</el-button>
          </div>

          <el-table :data="users" v-loading="loadingUsers" stripe class="custom-table">
            <el-table-column prop="username" label="用户名" min-width="120" />
            <el-table-column prop="email" label="邮箱" min-width="180" />
            <el-table-column label="创建时间" min-width="150">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="最后登录" min-width="150">
              <template #default="{ row }">{{ formatDateTime(row.last_login_at) || '未登录' }}</template>
            </el-table-column>
            <el-table-column label="总会话数" width="100" align="center">
              <template #default="{ row }">{{ row.conversation_count || 0 }}</template>
            </el-table-column>
            <el-table-column label="角色" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="280" fixed="right">
              <template #default="{ row }">
                <el-button size="small" link type="primary" @click="toggleUserRole(row)">
                  {{ row.role === 'admin' ? '取消管理员' : '设为管理员' }}
                </el-button>
                <el-button size="small" link type="warning" @click="resetPassword(row)">
                  重置密码
                </el-button>
                <el-button size="small" link type="danger" @click="removeUser(row)">
                  删除用户
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="users-pagination">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :total="userPagination.total"
              :page-size="userPagination.per_page"
              :current-page="userPagination.page"
              @current-change="loadUsers"
            />
          </div>
        </div>
      </section>

      <section v-else class="history-layout">
        <div class="history-main">
          <div class="history-toolbar">
            <div class="toolbar-meta">
              <span v-if="selectedConversation">
                {{ selectedConversation.username }}
                <template v-if="showConversationTitle(selectedConversation.title)"> / {{ selectedConversation.title }}</template>
              </span>
              <span v-else>请选择左侧历史记录</span>
            </div>
            <span class="toolbar-date" v-if="selectedConversation">{{ formatDateTime(selectedConversation.updated_at) }}</span>
          </div>

          <div class="history-conversation" v-loading="loadingHistoryDetail">
            <div v-if="historyMessages.length === 0" class="history-empty">
              <el-empty description="请选择左侧会话查看完整记录" :image-size="100" />
            </div>

            <div v-else class="history-messages">
              <article
                v-for="item in historyMessages"
                :key="item.id"
                class="history-row"
                :class="{ user: item.role === 'user', assistant: item.role !== 'user' }"
              >
                <el-avatar class="history-avatar" :size="36">
                  {{ item.role === 'user' ? (selectedConversation?.username?.[0] || 'U') : 'AI' }}
                </el-avatar>
                <div class="history-bubble">
                  <div class="message-meta">
                    <span class="message-user">
                      {{ item.role === 'user' ? selectedConversation?.username : 'assistant' }}
                    </span>
                    <span class="message-time">{{ formatDateTime(item.created_at) }}</span>
                  </div>
                  <AiMessage
                    :content="item.content"
                    :role="item.role"
                  />
                </div>
              </article>
            </div>
          </div>
        </div>
      </section>
    </main>

    <el-dialog
      v-model="showHistorySearchDialog"
      width="520px"
      destroy-on-close
      class="custom-dialog search-dialog"
    >
      <button class="dialog-close-btn" @click="showHistorySearchDialog = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><Search /></el-icon>
        </div>
        <h3 class="dialog-title">检索用户对话记录</h3>
      </div>
      <div class="search-dialog-body">
        <el-form label-position="top" class="history-form">
          <el-form-item label="关键词">
            <el-input v-model="historyFilters.keyword" clearable placeholder="消息内容或标题" />
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="historyFilters.username" clearable placeholder="按用户名筛选" />
          </el-form-item>
          <el-form-item label="开始日期">
            <el-date-picker
              v-model="historyFilters.start_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="开始日期"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker
              v-model="historyFilters.end_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="结束日期"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="每页条数">
            <el-select v-model="historyFilters.per_page" style="width: 100%">
              <el-option :value="10" label="10" />
              <el-option :value="20" label="20" />
              <el-option :value="50" label="50" />
              <el-option :value="100" label="100" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="resetHistoryFilters">重置</el-button>
          <el-button type="primary" @click="applyHistorySearch">检索</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Search, User, Close, Document } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as adminApi from '@/api/admin'
import { AiMessage } from '@/components/ai'

const router = useRouter()
const authStore = useAuthStore()
const activeTab = ref('users')
const users = ref([])
const loadingUsers = ref(false)
const userFilters = reactive({
  keyword: ''
})
const userPagination = reactive({
  total: 0,
  page: 1,
  per_page: 20
})
const historyConversations = ref([])
const historyMessages = ref([])
const selectedConversationId = ref(null)
const selectedConversation = ref(null)
const loadingHistoryList = ref(false)
const loadingHistoryDetail = ref(false)
const showHistorySearchDialog = ref(false)
const historyPagination = reactive({
  total: 0,
  page: 1,
  per_page: 20
})
const historyFilters = reactive({
  keyword: '',
  username: '',
  start_date: '',
  end_date: '',
  per_page: 20
})
const user = computed(() => authStore.user)
const historySearchSummary = computed(() => {
  const parts = []
  if (historyFilters.keyword) parts.push(`关键词：${historyFilters.keyword}`)
  if (historyFilters.username) parts.push(`用户：${historyFilters.username}`)
  if (historyFilters.start_date) parts.push(`开始：${historyFilters.start_date}`)
  if (historyFilters.end_date) parts.push(`结束：${historyFilters.end_date}`)
  parts.push(`每页：${historyFilters.per_page}`)
  return parts.length ? parts.join('  ·  ') : '点击检索用户对话记录'
})

async function loadUsers(page = userPagination.page) {
  loadingUsers.value = true
  try {
    const res = await adminApi.getUsers({
      keyword: userFilters.keyword,
      page,
      per_page: userPagination.per_page
    })
    users.value = res.data?.items || []
    userPagination.total = res.data?.pagination?.total || 0
    userPagination.page = res.data?.pagination?.page || page
    userPagination.per_page = res.data?.pagination?.per_page || userPagination.per_page
  } finally {
    loadingUsers.value = false
  }
}

function resetUserFilters() {
  userFilters.keyword = ''
  userPagination.per_page = 20
  loadUsers(1)
}

async function toggleUserRole(user) {
  const nextRole = user.role === 'admin' ? 'user' : 'admin'
  try {
    await adminApi.updateUserRole(user.id, nextRole)
    user.role = nextRole
    ElMessage.success('角色已更新')
  } catch {}
}

async function resetPassword(user) {
  try {
    const { value } = await ElMessageBox.prompt(
      `请输入 ${user.username} 的新密码`,
      '重置密码',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputValue: '123456',
        inputPattern: /^.{6,}$/,
        inputErrorMessage: '密码至少 6 位'
      }
    )
    await adminApi.resetUserPassword(user.id, value)
    ElMessage.success(`密码已重置为：${value}`)
  } catch {}
}

async function removeUser(user) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${user.username}」？`, '确认删除', {
      type: 'warning'
    })
    await adminApi.deleteUser(user.id)
    users.value = users.value.filter(item => item.id !== user.id)
    ElMessage.success('用户已删除')
  } catch {}
}

async function loadHistory(page = historyPagination.page) {
  loadingHistoryList.value = true
  try {
    const res = await adminApi.searchHistoryConversations({
      ...historyFilters,
      page,
      per_page: historyFilters.per_page
    })
    historyConversations.value = res.data?.items || []
    historyPagination.total = res.data?.pagination?.total || 0
    historyPagination.page = res.data?.pagination?.page || page
    historyPagination.per_page = res.data?.pagination?.per_page || historyFilters.per_page
    if (historyConversations.value.length > 0) {
      const nextId = historyConversations.value.some(item => item.conversation_id === selectedConversationId.value)
        ? selectedConversationId.value
        : historyConversations.value[0].conversation_id
      await selectConversation(nextId)
    } else {
      selectedConversationId.value = null
      selectedConversation.value = null
      historyMessages.value = []
    }
  } finally {
    loadingHistoryList.value = false
  }
}

async function selectConversation(conversationId) {
  if (!conversationId) return
  selectedConversationId.value = conversationId
  loadingHistoryDetail.value = true
  try {
    const res = await adminApi.getHistoryConversationDetail(conversationId)
    selectedConversation.value = res.data?.conversation || null
    historyMessages.value = res.data?.messages || []
  } finally {
    loadingHistoryDetail.value = false
  }
}

function applyHistorySearch() {
  showHistorySearchDialog.value = false
  loadHistory(1)
}

function resetHistoryFilters() {
  historyFilters.keyword = ''
  historyFilters.username = ''
  historyFilters.start_date = ''
  historyFilters.end_date = ''
  historyFilters.per_page = 20
}

function showConversationTitle(title) {
  return !!title && title !== 'New Conversation'
}

function formatConversationTitle(title) {
  if (showConversationTitle(title)) return title
  return '新对话'
}

function formatDateTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  loadUsers()
  loadHistory(1)
})
</script>

<style scoped lang="scss">
.admin-layout {
  height: 100vh;
  display: flex;
  background: linear-gradient(135deg, #FAFBFE 0%, #F3F1FF 50%, #EEEDF9 100%);
  overflow: hidden;
}

.admin-sidebar {
  width: 260px;
  height: 100vh;
  background: rgba(255, 255, 255, 0.9);
  border-right: 1px solid rgba(99, 102, 241, 0.12);
  padding: 28px 18px;
  box-shadow: 12px 0 30px rgba(99, 102, 241, 0.08);
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.sidebar-top {
  flex-shrink: 0;
}

.sidebar-header {
  margin-bottom: 26px;
}

.brand-title {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: #1E1B4B;
}

.brand-subtitle {
  margin: 8px 0 0;
  color: #7C7AA3;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sidebar-history-tools {
  flex-shrink: 0;
}

.sidebar-history-area {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-fill {
  flex: 1;
  min-height: 0;
}

.sidebar-history-list {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.sidebar-footer {
  flex-shrink: 0;
  padding-top: 16px;
  border-top: 1px solid rgba(99, 102, 241, 0.12);
  background: rgba(255, 255, 255, 0.96);
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  cursor: pointer;
  color: #5B5580;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(99, 102, 241, 0.08);
    color: #4F46E5;
  }

  &.active {
    background: rgba(99, 102, 241, 0.14);
    color: #4F46E5;
    font-weight: 700;
  }
}

.user-footer-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.admin-user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  color: #312E4A;
  font-weight: 600;
}

.admin-main {
  flex: 1;
  height: 100vh;
  min-width: 0;
  padding: 28px;
  overflow: hidden;
}

.admin-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  height: 100%;
  min-height: 0;
}

.panel-head,
.filter-head {
  margin-bottom: 16px;
}

.panel-title {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: #1E1B4B;
}

.panel-subtitle {
  margin: 8px 0 0;
  color: #7C7AA3;
}

.panel-card,
.history-main {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 24px;
  box-shadow: 0 16px 40px rgba(99, 102, 241, 0.09);
}

.panel-card {
  padding: 20px;
  flex: 1;
  min-height: 0;
  overflow: auto;
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

.users-page-size {
  width: 120px;
}

.users-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

.history-layout {
  height: 100%;
  min-height: 0;
}

.history-form {
  margin-top: 16px;
}

.history-list-item {
  padding: 12px 14px;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;

  &:hover {
    background: rgba(99, 102, 241, 0.08);
  }

  &.active {
    background: rgba(99, 102, 241, 0.12);
    border-color: rgba(99, 102, 241, 0.16);
  }
}

.history-list-title {
  font-size: 14px;
  font-weight: 700;
  color: #1E1B4B;
  margin-bottom: 6px;
}

.history-list-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #7C7AA3;
}

.history-list-empty {
  padding: 18px 6px;
  color: #8C8AB0;
  font-size: 13px;
}

.sidebar-pagination {
  flex-shrink: 0;
}

.search-entry {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 12px;
  cursor: pointer;
  color: #1E1B4B;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.15) inset;
  transition: all 0.25s ease;

  &:hover {
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.3) inset;
  }

  .el-icon {
    color: #A5A3C9;
  }
}

.history-main {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.history-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
}

.toolbar-meta {
  color: #6B688F;
  font-size: 14px;
  font-weight: 600;
}

.toolbar-date {
  color: #8C8AB0;
  font-size: 13px;
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

.history-conversation {
  flex: 1;
  overflow: auto;
  padding: 24px;
}

.history-empty {
  min-height: 100%;
  display: grid;
  place-items: center;
}

.history-messages {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.history-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  max-width: min(900px, 92%);

  &.user {
    align-self: flex-end;
    flex-direction: row-reverse;
  }

  &.assistant {
    align-self: flex-start;
  }
}

.history-avatar {
  flex-shrink: 0;
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  color: #fff;
}

.history-bubble {
  flex: 1;
  padding: 18px 20px;
  border-radius: 20px;
  background: #FFFFFF;
  border: 1px solid rgba(99, 102, 241, 0.1);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.08);
}

.history-row.user .history-bubble {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.1));
}

.message-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #7C7AA3;
  margin-bottom: 8px;
}

.message-user {
  font-weight: 700;
  color: #4F46E5;
}

:deep(.history-bubble .ai-message) {
  padding: 0;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

:deep(.search-dialog .el-dialog__header) {
  display: none;
}

:deep(.search-dialog .el-dialog__body) {
  padding: 0;
}

.search-dialog-body {
  padding: 20px 24px 0;
}

:deep(.search-dialog .dialog-close-btn) {
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

  &:active {
    transform: rotate(90deg) scale(0.95);
  }
}

:deep(.search-dialog .dialog-header-icon) {
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
    margin: 0;
  }
}

:deep(.search-dialog .el-input__wrapper) {
  border-radius: 12px;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.15) inset;
  transition: all 0.25s ease;

  &:hover {
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.3) inset;
  }

  &.is-focus {
    box-shadow: 0 0 0 1px #6366F1 inset, 0 0 0 4px rgba(99, 102, 241, 0.1);
  }
}

@media (max-width: 1100px) {
  .history-row {
    max-width: 100%;
  }

  .history-message {
    max-width: 100%;
  }
}
</style>
