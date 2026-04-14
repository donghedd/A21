<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">知识库管理</h2>
      </div>
      <el-button type="primary" @click="openCreateDialog()" class="primary-btn">
        <el-icon><Plus /></el-icon>
        创建知识库
      </el-button>
    </div>

    <!-- 知识库列表 -->
    <div v-loading="loading" class="kb-grid" element-loading-background="rgba(250, 251, 254, 0.8)">
      <div
        v-for="kb in knowledgeBases"
        :key="kb.id"
        class="kb-card"
      >
        <div class="card-top">
          <div class="card-icon">
            <el-icon :size="22"><FolderOpened /></el-icon>
          </div>
          <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, kb)">
            <el-button :icon="MoreFilled" link size="small" class="more-btn" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">
                  <el-icon><Edit /></el-icon>编辑
                </el-dropdown-item>
                <el-dropdown-item command="manage">
                  <el-icon><Document /></el-icon>管理文件
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided class="delete-item">
                  <el-icon><Delete /></el-icon>删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <h3 class="card-name">{{ kb.name }}</h3>
        <p class="card-desc">{{ kb.description || '暂无描述' }}</p>

        <div class="card-meta">
          <span class="meta-item">
            <el-icon><Document /></el-icon>
            {{ kb.file_count || 0 }} 个文件
          </span>
          <span class="meta-date">{{ formatDate(kb.created_at) }}</span>
        </div>

        <el-button type="primary" plain size="small" class="card-action" @click="manageFiles(kb)">
          管理文件
        </el-button>
      </div>

      <el-empty v-if="!loading && knowledgeBases.length === 0" class="page-empty" description="暂无知识库，点击创建开始使用" :image-size="100" />
    </div>

    <!-- 创建/编辑弹窗 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingKb ? '编辑知识库' : '创建知识库'"
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
      class="custom-dialog kb-dialog"
    >
      <button class="dialog-close-btn" @click="showCreateDialog = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><FolderOpened /></el-icon>
        </div>
        <h3 class="dialog-title">{{ editingKb ? '编辑知识库' : '创建知识库' }}</h3>
        <p class="dialog-subtitle">{{ editingKb ? '修改知识库的基本信息' : '创建一个新的知识库来存储文档' }}</p>
      </div>
      <el-form :model="kbForm" label-position="top" class="custom-form">
        <el-form-item label="知识库名称" required>
          <el-input 
            v-model="kbForm.name" 
            placeholder="输入知识库名称" 
            maxlength="50" 
            show-word-limit
            class="dialog-input"
          >
            <template #prefix>
              <el-icon><FolderOpened /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="kbForm.description" 
            type="textarea" 
            :rows="4" 
            placeholder="描述这个知识库的用途（可选）"
            class="dialog-textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showCreateDialog = false" class="cancel-btn">
            <el-icon><Close /></el-icon>
            取消
          </el-button>
          <el-button type="primary" @click="saveKnowledgeBase" :loading="saving" class="confirm-btn">
            <el-icon><Check /></el-icon>
            {{ editingKb ? '保存修改' : '确认创建' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 文件管理弹窗 -->
    <el-dialog
      v-model="showFileDialog"
      :title="`文件管理 - ${currentKb?.name || ''}`"
      width="760px"
      :close-on-click-modal="false"
      destroy-on-close
      class="custom-dialog file-dialog"
    >
      <button class="dialog-close-btn" @click="showFileDialog = false">
        <el-icon><Close /></el-icon>
      </button>
      <!-- 上传区域 -->
      <div class="upload-area">
        <el-upload
          drag
          action="#"
          :auto-upload="false"
          :on-change="handleFileSelect"
          :file-list="uploadList"
          :on-remove="handleFileRemove"
          multiple
          accept=".pdf,.doc,.docx,.txt,.md,.xlsx,.xls"
          class="custom-upload"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">
            <p class="main-text">拖拽文件到此处，或<em>点击上传</em></p>
            <p class="sub-text">支持 PDF、Word、Excel、TXT、Markdown 格式，单文件最大 50MB</p>
          </div>
        </el-upload>
        <el-button
          v-if="uploadList.length > 0"
          type="primary"
          @click="uploadFiles"
          :loading="uploading"
          class="upload-btn"
        >
          <el-icon><Upload /></el-icon>
          上传 {{ uploadList.length }} 个文件
        </el-button>
      </div>

      <el-divider content-position="left" class="custom-divider">已上传文件</el-divider>

      <!-- 文件表格 -->
      <el-table :data="currentFiles" v-loading="loadingFiles" stripe class="custom-table">
        <el-table-column prop="filename" label="文件名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="file_type" label="类型" width="70" align="center" />
        <el-table-column label="大小" width="90" align="center">
          <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type" size="small" effect="light" class="status-tag">
              {{ statusMap[row.status]?.text || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分块" width="60" align="center">
          <template #default="{ row }">{{ row.chunk_count || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'failed' || row.status === 'pending'"
              size="small"
              type="warning"
              link
              @click="reprocessFile(row)"
            >{{ row.status === 'pending' ? '处理' : '重试' }}</el-button>
            <el-button
              v-if="row.status !== 'completed'"
              size="small"
              type="info"
              link
              @click="cancelFile(row)"
            >取消</el-button>
            <el-button
              size="small"
              type="danger"
              link
              @click="deleteFile(row)"
              :disabled="row.status === 'processing'"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loadingFiles && currentFiles.length === 0" description="暂无文件" :image-size="80" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import {
  Plus, FolderOpened, Document,
  MoreFilled, UploadFilled, Edit, Delete, Upload, Check, Close
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as knowledgeApi from '@/api/knowledge'
import * as fileApi from '@/api/file'
import { getCache, setCache, invalidateCache } from '@/utils/cache'

const loading = ref(false)
const saving = ref(false)
const knowledgeBases = ref([])
const showCreateDialog = ref(false)
const editingKb = ref(null)
const kbForm = reactive({ name: '', description: '' })

const showFileDialog = ref(false)
const currentKb = ref(null)
const currentFiles = ref([])
const loadingFiles = ref(false)
const uploading = ref(false)
const uploadList = ref([])

const statusMap = {
  pending: { text: '待处理', type: 'info' },
  processing: { text: '处理中', type: 'warning' },
  completed: { text: '已完成', type: 'success' },
  failed: { text: '失败', type: 'danger' }
}

async function loadKnowledgeBases() {
  const cached = getCache('knowledge:bases')
  if (cached) {
    knowledgeBases.value = cached.data || cached || []
    loading.value = false
  } else {
    loading.value = true
  }

  try {
    const res = await knowledgeApi.getKnowledgeBases()
    knowledgeBases.value = res.data || []
    setCache('knowledge:bases', res, 30 * 1000)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function openCreateDialog(kb) {
  editingKb.value = kb || null
  kbForm.name = kb?.name || ''
  kbForm.description = kb?.description || ''
  showCreateDialog.value = true
}

function handleCommand(cmd, kb) {
  if (cmd === 'edit') openCreateDialog(kb)
  else if (cmd === 'manage') manageFiles(kb)
  else if (cmd === 'delete') deleteKnowledgeBase(kb)
}

async function saveKnowledgeBase() {
  if (!kbForm.name.trim()) return ElMessage.warning('请输入名称')
  saving.value = true
  try {
    if (editingKb.value) {
      await knowledgeApi.updateKnowledgeBase(editingKb.value.id, kbForm)
      ElMessage.success('已更新')
    } else {
      await knowledgeApi.createKnowledgeBase(kbForm)
      ElMessage.success('已创建')
    }
    invalidateCache('knowledge:bases')
    showCreateDialog.value = false
    loadKnowledgeBases()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteKnowledgeBase(kb) {
  try {
    await ElMessageBox.confirm(`确定删除「${kb.name}」？所有数据将被清除`, '确认删除', { type: 'warning' })
    await knowledgeApi.deleteKnowledgeBase(kb.id)
    knowledgeBases.value = knowledgeBases.value.filter(k => k.id !== kb.id)
    invalidateCache('knowledge:bases')
    ElMessage.success('已删除')
  } catch {}
}

async function manageFiles(kb) {
  currentKb.value = kb
  uploadList.value = []
  showFileDialog.value = true
  await loadFiles()
}

async function loadFiles() {
  if (!currentKb.value) return
  loadingFiles.value = true
  try {
    const res = await knowledgeApi.getKnowledgeBaseFiles(currentKb.value.id)
    currentFiles.value = res.data || []
    for (const f of currentFiles.value) {
      if (f.status === 'processing') pollStatus(f)
    }
  } catch (e) {} finally {
    loadingFiles.value = false
  }
}

function handleFileSelect(_, fileList) { uploadList.value = fileList }
function handleFileRemove(_, fileList) { uploadList.value = fileList }

async function uploadFiles() {
  if (!currentKb.value || !uploadList.value.length) return
  uploading.value = true
  let ok = 0, fail = 0
  for (const f of uploadList.value) {
    try {
      await fileApi.uploadFile(f.raw, currentKb.value.id)
      ok++
    } catch { fail++ }
  }
  uploading.value = false
  uploadList.value = []
  if (ok) { ElMessage.success(`成功 ${ok} 个`); invalidateCache('knowledge:bases'); loadFiles(); loadKnowledgeBases() }
  if (fail) ElMessage.error(`${fail} 个失败`)
}

async function deleteFile(file) {
  try {
    await ElMessageBox.confirm('确定删除该文件？')
    await fileApi.deleteFile(file.id)
    currentFiles.value = currentFiles.value.filter(f => f.id !== file.id)
    invalidateCache('knowledge:bases')
    loadKnowledgeBases()
    ElMessage.success('已删除')
  } catch {}
}

async function cancelFile(file) {
  try {
    await ElMessageBox.confirm('确定取消该文件当前操作？取消后文件将从知识库中移除。')
    await fileApi.deleteFile(file.id)
    currentFiles.value = currentFiles.value.filter(f => f.id !== file.id)
    invalidateCache('knowledge:bases')
    loadKnowledgeBases()
    ElMessage.success('已取消')
  } catch {}
}

async function reprocessFile(file) {
  try {
    await fileApi.reprocessFile(file.id)
    file.status = 'processing'
    pollStatus(file)
    ElMessage.success('已提交重试')
  } catch { ElMessage.error('操作失败') }
}

function pollStatus(file) {
  const timer = setInterval(async () => {
    try {
      const res = await fileApi.getFileStatus(file.id)
      Object.assign(file, res.data)
      if (['completed', 'failed'].includes(res.data.status)) {
        clearInterval(timer)
        invalidateCache('knowledge:bases')
        loadKnowledgeBases()
      }
    } catch { clearInterval(timer) }
  }, 2000)
}

function formatDate(s) { return s ? new Date(s).toLocaleDateString('zh-CN') : '' }
function formatFileSize(b) {
  if (!b) return '-'
  if (b < 1024) return b + ' B'
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1048576).toFixed(1) + ' MB'
}

onMounted(loadKnowledgeBases)
</script>

<style scoped lang="scss">
// Sapphire Elegance Theme - 与主页会话页一致
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

  .header-left {
    display: flex;
    align-items: center;
  }
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

.primary-btn {
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  border: none;
  border-radius: 10px;
  padding: 10px 20px;
  font-weight: 600;
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.25);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35);
  }

  .el-icon {
    margin-right: 6px;
  }
}

.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  min-height: 360px;
  align-content: start;
}

.page-empty {
  grid-column: 1 / -1;
  place-self: center;
}

.kb-card {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  box-shadow: 0 2px 12px rgba(79, 70, 229, 0.04);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    box-shadow: 0 8px 32px rgba(99, 102, 241, 0.12);
    transform: translateY(-3px);
    border-color: rgba(99, 102, 241, 0.18);
  }

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
  }

  .card-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.08));
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6366F1;
    transition: all 0.25s ease;

    &:hover {
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.12));
      transform: scale(1.05);
    }
  }

  .more-btn {
    color: #A5A3C9;
    transition: color 0.2s;

    &:hover {
      color: #6366F1;
    }
  }

  .card-name {
    font-size: 17px;
    font-weight: 700;
    color: #1E1B4B;
    margin: 0 0 8px;
    letter-spacing: -0.2px;
  }

  .card-desc {
    font-size: 14px;
    color: #5B5580;
    margin: 0 0 16px;
    line-height: 1.6;
    min-height: 44px;
  }

  .card-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    color: #8B87B5;
    margin-bottom: 16px;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;

      .el-icon {
        color: #6366F1;
      }
    }

    .meta-date {
      color: #A5A3C9;
    }
  }

  .card-action {
    width: 100%;
    border-radius: 10px;
    border-color: rgba(99, 102, 241, 0.25);
    color: #6366F1;
    font-weight: 500;
    transition: all 0.25s ease;

    &:hover {
      background: rgba(99, 102, 241, 0.08);
      border-color: #6366F1;
    }
  }
}

// 弹窗样式
:deep(.custom-dialog) {
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 24px 60px rgba(99, 102, 241, 0.2);

  .el-dialog__header {
    display: none;
  }

  .el-dialog__body {
    padding: 0;
  }

  .el-dialog__footer {
    padding: 20px 28px 28px;
    border-top: 1px solid rgba(99, 102, 241, 0.08);
  }
}

// 弹窗关闭按钮
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

  &:active {
    transform: rotate(90deg) scale(0.95);
  }

  .el-icon {
    font-size: 18px;
    font-weight: 600;
  }
}

// 知识库弹窗头部
.dialog-header-icon {
  text-align: center;
  padding: 32px 28px 24px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.04) 100%);
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  position: relative;

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

// 表单区域
.custom-form {
  padding: 24px 28px;

  .el-form-item__label {
    font-weight: 600;
    color: #312E4A;
    padding-bottom: 8px;
    font-size: 14px;
  }

  .el-form-item {
    margin-bottom: 20px;

    &:last-child {
      margin-bottom: 0;
    }
  }
}

.dialog-input {
  .el-input__wrapper {
    border-radius: 12px;
    padding: 8px 16px;
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.15) inset;
    transition: all 0.25s ease;

    &:hover {
      box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.3) inset;
    }

    &.is-focus {
      box-shadow: 0 0 0 1px #6366F1 inset, 0 0 0 4px rgba(99, 102, 241, 0.1);
    }
  }

  .el-input__prefix {
    color: #A5A3C9;
    margin-right: 8px;
  }

  .el-input__inner {
    font-size: 15px;
    color: #1E1B4B;

    &::placeholder {
      color: #A5A3C9;
    }
  }

  .el-input__count {
    color: #A5A3C9;
  }
}

.dialog-textarea {
  .el-textarea__inner {
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.15) inset;
    transition: all 0.25s ease;
    font-size: 15px;
    color: #1E1B4B;
    line-height: 1.6;

    &:hover {
      box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.3) inset;
    }

    &:focus {
      box-shadow: 0 0 0 1px #6366F1 inset, 0 0 0 4px rgba(99, 102, 241, 0.1);
    }

    &::placeholder {
      color: #A5A3C9;
    }
  }
}

// 底部按钮
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.cancel-btn {
  border-radius: 10px;
  padding: 10px 20px;
  font-weight: 500;
  color: #5B5580;
  border-color: rgba(99, 102, 241, 0.2);
  transition: all 0.25s ease;

  &:hover {
    color: #6366F1;
    border-color: rgba(99, 102, 241, 0.4);
    background: rgba(99, 102, 241, 0.05);
  }

  .el-icon {
    margin-right: 4px;
  }
}



// 文件管理弹窗
.upload-area {
  margin-bottom: 20px;

  .custom-upload {
    :deep(.el-upload-dragger) {
      border: 2px dashed rgba(99, 102, 241, 0.2);
      border-radius: 12px;
      background: rgba(99, 102, 241, 0.02);
      transition: all 0.25s ease;

      &:hover {
        border-color: #6366F1;
        background: rgba(99, 102, 241, 0.04);
      }
    }
  }

  .upload-icon {
    font-size: 40px;
    color: #A5A3C9;
    margin-bottom: 12px;
  }

  .upload-text {
    .main-text {
      font-size: 15px;
      color: #312E4A;
      margin: 0 0 6px;

      em {
        color: #6366F1;
        font-style: normal;
        font-weight: 600;
      }
    }

    .sub-text {
      font-size: 13px;
      color: #8B87B5;
      margin: 0;
    }
  }

  .upload-btn {
    width: 100%;
    background: linear-gradient(135deg, #6366F1, #8B5CF6);
    border: none;
    border-radius: 10px;
    padding: 12px;
    font-weight: 600;
    margin-top: 16px;

    &:hover {
      background: linear-gradient(135deg, #4F46E5, #7C3AED);
    }

    .el-icon {
      margin-right: 6px;
    }
  }
}

.custom-divider {
  margin: 24px 0;

  :deep(.el-divider__text) {
    color: #8B87B5;
    font-size: 13px;
    font-weight: 500;
    background: #FAFBFE;
  }
}

.custom-table {
  :deep(th) {
    background: rgba(99, 102, 241, 0.04);
    color: #312E4A;
    font-weight: 600;
  }

  :deep(td) {
    color: #5B5580;
  }

  .status-tag {
    border-radius: 6px;
  }
}

.delete-item {
  color: #EF4444;

  &:hover {
    color: #DC2626;
    background: rgba(239, 68, 68, 0.08);
  }
}
</style>
