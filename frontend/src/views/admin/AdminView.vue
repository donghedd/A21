<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="sidebar-top">
        <div class="sidebar-header">
          <h1 class="brand-title">管理端</h1>
          <p class="brand-subtitle">仅管理员可访问</p>
        </div>

        <div class="sidebar-section">
          <div class="list-header">
            <span class="list-title">管理目录</span>
          </div>
          <div class="admin-nav-items">
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
              :class="{ active: activeTab === 'knowledge' }"
              @click="activeTab = 'knowledge'"
            >
              <el-icon><FolderOpened /></el-icon>
              <span>知识库管理</span>
            </div>
            <div
              class="sidebar-item"
              :class="{ active: activeTab === 'workspace' }"
              @click="activeTab = 'workspace'"
            >
              <el-icon><Setting /></el-icon>
              <span>工作空间</span>
            </div>
            <div
              class="sidebar-item"
              :class="{ active: activeTab === 'history' }"
              @click="activeTab = 'history'"
            >
              <el-icon><Document /></el-icon>
              <span>对话历史管理</span>
            </div>
          </div>
        </div>
      </div>

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

      <section v-else-if="activeTab === 'knowledge'" class="admin-panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">知识库管理</h2>
            <p class="panel-subtitle">查看并编辑所有管理员创建的知识库</p>
          </div>
        </div>

        <div class="panel-card">
          <div class="users-toolbar">
            <el-input
              v-model="knowledgeFilters.keyword"
              clearable
              placeholder="按知识库名称、描述或创建者搜索"
              class="users-search"
              @keyup.enter="loadAdminKnowledgeBases"
            />
            <el-button type="primary" @click="loadAdminKnowledgeBases">查找</el-button>
            <el-button @click="resetKnowledgeFilters">重置</el-button>
          </div>

          <el-table :data="adminKnowledgeBases" v-loading="loadingKnowledgeBases" stripe class="custom-table">
            <el-table-column prop="name" label="知识库名称" min-width="160" />
            <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            <el-table-column prop="owner_username" label="创建管理员" min-width="120" />
            <el-table-column label="文件数" width="90" align="center">
              <template #default="{ row }">{{ row.file_count || 0 }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_system ? 'success' : 'info'">
                  {{ row.is_system ? '公共' : '私人' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="160">
              <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" link type="primary" @click="openKnowledgeDialog(row)">
                  编辑
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </section>

      <section v-else-if="activeTab === 'workspace'" class="admin-panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">工作空间</h2>
            <p class="panel-subtitle">查看并编辑所有管理员创建的大模型</p>
          </div>
        </div>

        <div class="panel-card">
          <div class="users-toolbar">
            <el-input
              v-model="workspaceFilters.keyword"
              clearable
              placeholder="按模型名称、模型标识或创建者搜索"
              class="users-search"
              @keyup.enter="loadAdminWorkspaceModels"
            />
            <el-button type="primary" @click="loadAdminWorkspaceModels">查找</el-button>
            <el-button @click="resetWorkspaceFilters">重置</el-button>
          </div>

          <el-table :data="adminWorkspaceModels" v-loading="loadingWorkspaceModels" stripe class="custom-table">
            <el-table-column prop="name" label="模型名称" min-width="150" />
            <el-table-column label="类型" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.type === 'external' ? 'warning' : 'primary'">
                  {{ row.type === 'external' ? '云端' : '本地' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="模型标识" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">{{ row.type === 'external' ? row.model_name : row.base_model }}</template>
            </el-table-column>
            <el-table-column prop="owner_username" label="创建管理员" min-width="120" />
            <el-table-column label="知识库" width="90" align="center">
              <template #default="{ row }">{{ row.knowledge_bases?.length || 0 }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_system ? 'success' : 'info'">
                  {{ row.is_system ? '公共' : '私人' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="160">
              <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" link type="primary" @click="openWorkspaceDialog(row)">
                  编辑
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </section>

      <section v-else-if="activeTab === 'history'" class="history-layout">
        <ConversationHistoryManager />
      </section>
    </main>

    <el-dialog v-model="showKnowledgeDialog" width="520px" destroy-on-close class="custom-dialog search-dialog">
      <button class="dialog-close-btn" @click="showKnowledgeDialog = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><FolderOpened /></el-icon>
        </div>
        <h3 class="dialog-title">编辑知识库</h3>
      </div>
      <div class="search-dialog-body">
        <el-form :model="knowledgeForm" label-position="top" class="history-form">
          <el-form-item label="知识库名称">
            <el-input v-model="knowledgeForm.name" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="knowledgeForm.description" type="textarea" :rows="4" />
          </el-form-item>
          <el-form-item label="公共知识库">
            <el-switch v-model="knowledgeForm.is_system" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showKnowledgeDialog = false">取消</el-button>
          <el-button type="primary" @click="saveKnowledgeBase">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="showWorkspaceDialog" width="560px" destroy-on-close class="custom-dialog search-dialog">
      <button class="dialog-close-btn" @click="showWorkspaceDialog = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><Setting /></el-icon>
        </div>
        <h3 class="dialog-title">编辑模型</h3>
      </div>
      <div class="search-dialog-body">
        <el-form :model="workspaceForm" label-position="top" class="history-form">
          <el-form-item label="模型名称">
            <el-input v-model="workspaceForm.name" />
          </el-form-item>
          <el-form-item :label="workspaceForm.type === 'external' ? '云端模型名称' : '本地模型名称'">
            <el-input v-if="workspaceForm.type === 'external'" v-model="workspaceForm.model_name" />
            <el-input v-else v-model="workspaceForm.base_model" />
          </el-form-item>
          <el-form-item v-if="workspaceForm.type === 'external'" label="API 基地址">
            <el-input v-model="workspaceForm.api_base_url" />
          </el-form-item>
          <el-form-item v-if="workspaceForm.type === 'external'" label="API 密钥">
            <el-input v-model="workspaceForm.api_key" type="password" show-password placeholder="留空则保留原密钥" />
          </el-form-item>
          <el-form-item label="系统提示词">
            <el-input v-model="workspaceForm.system_prompt" type="textarea" :rows="4" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="workspaceForm.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="公共模型">
            <el-switch v-model="workspaceForm.is_system" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showWorkspaceDialog = false">取消</el-button>
          <el-button type="primary" @click="saveWorkspaceModel">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { User, Close, Document, FolderOpened, Setting } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as adminApi from '@/api/admin'
import ConversationHistoryManager from '@/components/history/ConversationHistoryManager.vue'

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
const adminKnowledgeBases = ref([])
const loadingKnowledgeBases = ref(false)
const knowledgeFilters = reactive({ keyword: '' })
const showKnowledgeDialog = ref(false)
const editingKnowledge = ref(null)
const knowledgeForm = reactive({
  id: '',
  name: '',
  description: '',
  is_system: false
})
const adminWorkspaceModels = ref([])
const loadingWorkspaceModels = ref(false)
const workspaceFilters = reactive({ keyword: '' })
const showWorkspaceDialog = ref(false)
const editingWorkspace = ref(null)
const workspaceForm = reactive({
  id: '',
  type: 'local',
  name: '',
  base_model: '',
  model_name: '',
  api_base_url: '',
  api_key: '',
  system_prompt: '',
  description: '',
  is_system: false
})
const user = computed(() => authStore.user)

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

async function loadAdminKnowledgeBases() {
  loadingKnowledgeBases.value = true
  try {
    const res = await adminApi.getAdminKnowledgeBases({
      keyword: knowledgeFilters.keyword
    })
    adminKnowledgeBases.value = res.data || []
  } finally {
    loadingKnowledgeBases.value = false
  }
}

function resetKnowledgeFilters() {
  knowledgeFilters.keyword = ''
  loadAdminKnowledgeBases()
}

function openKnowledgeDialog(item) {
  editingKnowledge.value = item
  Object.assign(knowledgeForm, {
    id: item.id,
    name: item.name || '',
    description: item.description || '',
    is_system: !!item.is_system
  })
  showKnowledgeDialog.value = true
}

async function saveKnowledgeBase() {
  if (!editingKnowledge.value) return
  try {
    await adminApi.updateAdminKnowledgeBase(editingKnowledge.value.id, {
      name: knowledgeForm.name,
      description: knowledgeForm.description,
      is_system: knowledgeForm.is_system
    })
    ElMessage.success('知识库已更新')
    showKnowledgeDialog.value = false
    loadAdminKnowledgeBases()
  } catch {}
}

async function loadAdminWorkspaceModels() {
  loadingWorkspaceModels.value = true
  try {
    const res = await adminApi.getAdminWorkspaceModels({
      keyword: workspaceFilters.keyword
    })
    adminWorkspaceModels.value = res.data || []
  } finally {
    loadingWorkspaceModels.value = false
  }
}

function resetWorkspaceFilters() {
  workspaceFilters.keyword = ''
  loadAdminWorkspaceModels()
}

function openWorkspaceDialog(item) {
  editingWorkspace.value = item
  Object.assign(workspaceForm, {
    id: item.id,
    type: item.type || 'local',
    name: item.name || '',
    base_model: item.base_model || '',
    model_name: item.model_name || '',
    api_base_url: item.api_base_url || '',
    api_key: '',
    system_prompt: item.system_prompt || '',
    description: item.description || '',
    is_system: !!item.is_system
  })
  showWorkspaceDialog.value = true
}

async function saveWorkspaceModel() {
  if (!editingWorkspace.value) return
  const payload = {
    name: workspaceForm.name,
    system_prompt: workspaceForm.system_prompt,
    description: workspaceForm.description,
    is_system: workspaceForm.is_system
  }
  try {
    if (workspaceForm.type === 'external') {
      payload.model_name = workspaceForm.model_name
      payload.api_base_url = workspaceForm.api_base_url
      if (workspaceForm.api_key) payload.api_key = workspaceForm.api_key
      await adminApi.updateAdminExternalModel(editingWorkspace.value.id, payload)
    } else {
      payload.base_model = workspaceForm.base_model
      await adminApi.updateAdminCustomModel(editingWorkspace.value.id, payload)
    }
    ElMessage.success('模型已更新')
    showWorkspaceDialog.value = false
    loadAdminWorkspaceModels()
  } catch {}
}

function formatDateTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  loadUsers()
  loadAdminKnowledgeBases()
  loadAdminWorkspaceModels()
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
  width: 300px;
  height: 100vh;
  background: rgba(255, 255, 255, 0.9);
  border-right: 1px solid rgba(99, 102, 241, 0.12);
  padding: 20px 16px;
  box-shadow: 12px 0 30px rgba(99, 102, 241, 0.08);
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.sidebar-top {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  margin-bottom: 26px;
  padding: 0 8px;
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
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
  padding: 8px;
}

.list-header {
  padding: 10px 14px;
  margin-bottom: 6px;
}

.list-title {
  font-size: 11px;
  font-weight: 700;
  color: #A5A3C9;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.admin-nav-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
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
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  color: #5B5580;
  transition: all 0.2s ease;
  position: relative;

  .el-icon {
    color: #A5A3C9;
    font-size: 16px;
    flex-shrink: 0;
    transition: color 0.2s ease;
  }

  span {
    flex: 1;
    font-size: 13.5px;
    color: #4B5563;
    transition: color 0.2s ease, font-weight 0.2s ease;
  }

  &:hover {
    background: rgba(99, 102, 241, 0.07);

    .el-icon,
    span {
      color: #6366F1;
    }
  }

  &.active {
    background: rgba(99, 102, 241, 0.12);

    .el-icon {
      color: #6366F1;
    }

    span {
      color: #4F46E5;
      font-weight: 600;
    }
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
  display: flex;
  flex-direction: column;
}

.history-layout :deep(.page-container) {
  padding: 0;
  min-height: 0;
}

.history-form {
  margin-top: 16px;
}

.sidebar-section::-webkit-scrollbar {
  width: 5px;
}

.sidebar-section::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-section::-webkit-scrollbar-thumb {
  background: rgba(99, 102, 241, 0.15);
  border-radius: 10px;
}

.sidebar-section::-webkit-scrollbar-thumb:hover {
  background: rgba(99, 102, 241, 0.28);
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
</style>
