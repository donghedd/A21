<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">工作空间</h2>
      </div>
    </div>

    <!-- Ollama 模型区 -->
    <section class="section">
      <div class="section-head">
        <h3 class="section-title">Ollama 可用模型</h3>
        <el-button text @click="loadOllamaModels" :loading="loadingOllama" class="refresh-btn">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
      <div v-if="ollamaModels.length > 0" class="tag-group">
        <el-tag v-for="m in ollamaModels" :key="m.name" size="large" round effect="light" class="model-tag">
          {{ m.name }}
        </el-tag>
      </div>
      <el-empty v-else-if="!loadingOllama" description="未检测到 Ollama 模型" :image-size="80" />
    </section>

    <!-- 自定义模型区 -->
    <section class="section">
      <div class="section-head">
        <h3 class="section-title">我的模型</h3>
        <el-button type="primary" @click="openCreateDialog()" class="primary-btn">
          <el-icon><Plus /></el-icon>
          新建模型
        </el-button>
      </div>

      <div v-loading="loadingCustom" class="model-grid" element-loading-background="rgba(250, 251, 254, 0.8)">
        <div
          v-for="m in customModels"
          :key="m.id"
          class="model-card"
        >
          <div class="card-top">
            <span class="model-name">{{ m.name }}</span>
            <el-dropdown trigger="click" @command="(cmd) => onModelCmd(cmd, m)">
              <el-button :icon="MoreFilled" link size="small" class="more-btn" />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">
                    <el-icon><Edit /></el-icon>编辑
                  </el-dropdown-item>
                  <el-dropdown-item v-if="m.type === 'external'" command="test">
                    <el-icon><Check /></el-icon>测试连通
                  </el-dropdown-item>
                  <el-dropdown-item command="kb">
                    <el-icon><FolderOpened /></el-icon>知识库绑定
                  </el-dropdown-item>
                  <el-dropdown-item command="del" divided class="delete-item">
                    <el-icon><Delete /></el-icon>删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <p class="model-desc">{{ m.description || '暂无描述' }}</p>

          <div class="model-tags">
            <el-tag size="small" :type="m.type === 'external' ? 'warning' : 'primary'" effect="light" class="base-tag">
              {{ m.type === 'external' ? '云端模型' : '本地模型' }}
            </el-tag>
            <el-tag size="small" type="primary" effect="light" class="base-tag">
              {{ m.type === 'external' ? (m.model_name || m.name) : m.base_model }}
            </el-tag>
            <el-tag size="small" type="info" effect="light" class="kb-tag">
              {{ `${m.knowledge_bases?.length || 0} 个知识库` }}
            </el-tag>
          </div>

          <div v-if="m.system_prompt" class="sys-prompt">
            {{ truncate(m.system_prompt, 60) }}
          </div>
        </div>

        <el-empty v-if="!loadingCustom && customModels.length === 0" class="page-empty" description="暂无自定义模型，点击新建开始使用" :image-size="100" />
      </div>
    </section>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="showModelDialog"
      :title="editingModel ? '编辑模型' : '新建模型'"
      width="600px"
      destroy-on-close
      class="custom-dialog model-dialog"
    >
      <button class="dialog-close-btn" @click="showModelDialog = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><Edit v-if="editingModel" /><Plus v-else /></el-icon>
        </div>
        <h3 class="dialog-title">{{ editingModel ? '编辑模型' : '新建模型' }}</h3>
        <p class="dialog-subtitle">{{ editingModel ? '修改自定义模型的配置信息' : '创建一个新的自定义模型用于对话' }}</p>
      </div>
      <el-form :model="modelForm" label-position="top" class="custom-form">
        <el-form-item label="模型名称" required>
          <el-input 
            v-model="modelForm.name" 
            placeholder="输入模型名称" 
            maxlength="30" 
            show-word-limit
            class="dialog-input"
          >
            <template #prefix>
              <el-icon><Document /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <div class="form-row">
          <el-form-item label="模型来源" required class="form-item-half">
            <el-radio-group v-model="modelForm.type" class="provider-radio-group" :disabled="Boolean(editingModel)">
              <el-radio-button label="local">本地大模型</el-radio-button>
              <el-radio-button label="external">云端大模型</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item :label="modelForm.type === 'external' ? '云端模型名称' : '本地模型名称'" required class="form-item-half">
            <el-select
              v-if="modelForm.type === 'local'"
              v-model="modelForm.base_model"
              placeholder="选择本地模型"
              style="width: 100%"
              class="custom-select dialog-select"
            >
              <el-option v-for="m in ollamaModels" :key="m.name" :label="m.name" :value="m.name" />
            </el-select>
            <el-input
              v-else
              v-model="modelForm.model_name"
              placeholder="例如 gpt-4o-mini / qwen-max / deepseek-chat"
              class="dialog-input"
            />
          </el-form-item>
        </div>
        <div v-if="modelForm.type === 'external'" class="form-row">
          <el-form-item label="API 基地址" class="form-item-half">
            <el-input
              v-model="modelForm.api_base_url"
              placeholder="例如 https://api.openai.com/v1"
              class="dialog-input"
            />
          </el-form-item>
          <el-form-item label="API 密钥" required class="form-item-half">
            <el-input
              v-model="modelForm.api_key"
              type="password"
              show-password
              :placeholder="editingModel?.type === 'external'
                ? (externalKeyMasked ? `已保存：${externalKeyMasked}，留空则保留原密钥` : '编辑时可留空，保留原密钥')
                : '输入 API Key'"
              class="dialog-input"
            />
          </el-form-item>
        </div>
        <el-form-item label="系统提示词">
          <el-input
            v-model="modelForm.system_prompt"
            type="textarea"
            :rows="5"
            placeholder="定义模型的行为和角色，例如：你是一个专业的助手，擅长回答各种问题..."
            class="dialog-textarea"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="modelForm.description" 
            placeholder="简要描述这个模型的用途（可选）"
            class="dialog-input"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showModelDialog = false" class="cancel-btn">
            <el-icon><Close /></el-icon>
            取消
          </el-button>
          <el-button type="primary" @click="saveModel" :loading="saving" class="confirm-btn">
            <el-icon><Check /></el-icon>
            {{ editingModel ? '保存修改' : '创建模型' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 知识库绑定弹窗 -->
    <el-dialog v-model="showKbDialog" title="知识库绑定" width="560px" destroy-on-close class="custom-dialog kb-bind-dialog">
      <button class="dialog-close-btn" @click="showKbDialog = false">
        <el-icon><Close /></el-icon>
      </button>
      <div class="dialog-header-icon">
        <div class="icon-wrapper">
          <el-icon :size="28"><FolderOpened /></el-icon>
        </div>
        <h3 class="dialog-title">知识库绑定</h3>
        <p class="dialog-subtitle">为模型绑定知识库，使其能访问知识库内容进行问答</p>
      </div>

      <div class="binding-block">
        <h4 class="block-title">已绑定</h4>
        <div class="tag-list">
          <el-tag
            v-for="kb in boundKbs"
            :key="kb.id"
            closable
            size="large"
            round
            @close="unbindKb(kb)"
            class="bound-tag"
          >
            <el-icon><FolderOpened /></el-icon>
            {{ kb.name }}
          </el-tag>
          <el-empty v-if="boundKbs.length === 0" description="未绑定任何知识库" :image-size="60" />
        </div>
      </div>

      <el-divider class="custom-divider" />

      <div class="binding-block">
        <h4 class="block-title">可绑定</h4>
        <div class="tag-list">
          <el-tag
            v-for="kb in availKbs"
            :key="kb.id"
            size="large"
            round
            class="clickable-tag"
            @click="bindKb(kb)"
          >
            <el-icon><Plus /></el-icon>
            {{ kb.name }}
          </el-tag>
          <el-empty v-if="availKbs.length === 0" description="没有可绑定的知识库" :image-size="60" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus, Refresh, MoreFilled, Edit, Delete, FolderOpened, Document, Check, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as modelApi from '@/api/model'
import * as knowledgeApi from '@/api/knowledge'
import { getCache, setCache, invalidateCache } from '@/utils/cache'

const loadingOllama = ref(false)
const loadingCustom = ref(false)
const saving = ref(false)
const ollamaModels = ref([])
const customModels = ref([])
const allKbs = ref([])

const showModelDialog = ref(false)
const editingModel = ref(null)
const modelForm = reactive({
  type: 'local',
  name: '',
  base_model: '',
  model_name: '',
  api_key: '',
  api_base_url: 'https://api.openai.com/v1',
  system_prompt: '',
  description: ''
})
const externalKeyMasked = ref('')

const showKbDialog = ref(false)
const currentModel = ref(null)

const boundKbs = computed(() => currentModel.value?.knowledge_bases || [])
const availKbs = computed(() => {
  const boundIds = boundKbs.value.map(k => k.id)
  return allKbs.value.filter(k => !boundIds.includes(k.id))
})

async function loadOllamaModels() {
  const cached = getCache('models:ollama')
  if (cached) {
    ollamaModels.value = cached.data || cached || []
    loadingOllama.value = false
  } else {
    loadingOllama.value = true
  }

  try {
    const res = await modelApi.getOllamaModels()
    ollamaModels.value = res.data || []
    setCache('models:ollama', res, 5 * 60 * 1000)
  }
  catch (e) {} finally { loadingOllama.value = false }
}

async function loadCustomModels() {
  const cached = getCache('models:custom')
  if (cached) {
    customModels.value = cached.data || cached || []
    loadingCustom.value = false
  } else {
    loadingCustom.value = true
  }

  try {
    const [customRes, externalRes] = await Promise.all([
      modelApi.getCustomModels(),
      modelApi.getExternalModels()
    ])
    const localModels = (customRes.data || []).map(m => ({ ...m, type: 'local' }))
    const externalModels = (externalRes.data || []).map(m => ({ ...m, type: 'external' }))
    customModels.value = [...externalModels, ...localModels]
    setCache('models:custom', { data: customModels.value }, 5 * 60 * 1000)
  }
  catch (e) {} finally { loadingCustom.value = false }
}

async function loadAllKbs() {
  const cached = getCache('knowledge:bases')
  if (cached) {
    allKbs.value = cached.data || cached || []
  }

  try {
    const res = await knowledgeApi.getKnowledgeBases()
    allKbs.value = res.data || []
    setCache('knowledge:bases', res, 30 * 1000)
  } catch {}
}

function openCreateDialog(m) {
  editingModel.value = m || null
  externalKeyMasked.value = m?.api_key_masked || ''
  Object.assign(modelForm, m ? {
    type: m.type || 'local',
    name: m.name,
    base_model: m.base_model || '',
    model_name: m.model_name || '',
    api_key: '',
    api_base_url: m.api_base_url || 'https://api.openai.com/v1',
    system_prompt: m.system_prompt || '',
    description: m.description || ''
  } : {
    type: 'local',
    name: '',
    base_model: '',
    model_name: '',
    api_key: '',
    api_base_url: 'https://api.openai.com/v1',
    system_prompt: '',
    description: ''
  })
  showModelDialog.value = true
}

function onModelCmd(cmd, m) {
  if (cmd === 'edit') openCreateDialog(m)
  else if (cmd === 'test') testModelConnection(m)
  else if (cmd === 'kb') openKbDialog(m)
  else if (cmd === 'del') deleteModel(m)
}

async function saveModel() {
  if (!modelForm.name) return ElMessage.warning('请填写模型名称')
  if (modelForm.type === 'local' && !modelForm.base_model) return ElMessage.warning('请选择本地模型')
  if (modelForm.type === 'external' && !modelForm.model_name) return ElMessage.warning('请填写云端模型名称')
  if (modelForm.type === 'external' && !editingModel.value && !modelForm.api_key) return ElMessage.warning('云端模型创建时 API 密钥必填')
  saving.value = true
  try {
    const payload = {
      name: modelForm.name,
      system_prompt: modelForm.system_prompt,
      description: modelForm.description
    }

    if (modelForm.type === 'local') {
      payload.base_model = modelForm.base_model
    } else {
      payload.model_name = modelForm.model_name
      payload.api_base_url = modelForm.api_base_url
      if (modelForm.api_key) payload.api_key = modelForm.api_key
    }

    if (editingModel.value) {
      if (editingModel.value.type === 'external') {
        await modelApi.updateExternalModel(editingModel.value.id, payload)
      } else {
        await modelApi.updateCustomModel(editingModel.value.id, payload)
      }
      ElMessage.success('已更新')
    } else {
      if (modelForm.type === 'external') {
        await modelApi.createExternalModel(payload)
      } else {
        await modelApi.createCustomModel(payload)
      }
      ElMessage.success('已创建')
    }
    invalidateCache('models:custom')
    invalidateCache('models:external')
    showModelDialog.value = false
    loadCustomModels()
  } catch { ElMessage.error('保存失败') } finally { saving.value = false }
}

async function deleteModel(m) {
  try {
    await ElMessageBox.confirm(`确定删除「${m.name}」？`, '确认', { type: 'warning' })
    if (m.type === 'external') {
      await modelApi.deleteExternalModel(m.id)
    } else {
      await modelApi.deleteCustomModel(m.id)
    }
    customModels.value = customModels.value.filter(x => x.id !== m.id)
    invalidateCache('models:custom')
    invalidateCache('models:external')
    ElMessage.success('已删除')
  } catch {}
}

async function testModelConnection(m) {
  if (m.type !== 'external') return
  try {
    const res = await modelApi.testExternalModel(m.id)
    const baseUrl = res.data?.base_url || m.api_base_url || ''
    ElMessage.success(`连通成功: ${baseUrl}`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '连通失败')
  }
}

function openKbDialog(m) {
  currentModel.value = m
  showKbDialog.value = true
}

async function bindKb(kb) {
  try {
    if (currentModel.value.type === 'external') {
      await modelApi.bindExternalKnowledgeBase(currentModel.value.id, kb.id)
    } else {
      await modelApi.bindKnowledgeBase(currentModel.value.id, kb.id)
    }
    if (!currentModel.value.knowledge_bases) currentModel.value.knowledge_bases = []
    currentModel.value.knowledge_bases.push(kb)
    ElMessage.success('已绑定')
  } catch { ElMessage.error('绑定失败') }
}

async function unbindKb(kb) {
  try {
    if (currentModel.value.type === 'external') {
      await modelApi.unbindExternalKnowledgeBase(currentModel.value.id, kb.id)
    } else {
      await modelApi.unbindKnowledgeBase(currentModel.value.id, kb.id)
    }
    currentModel.value.knowledge_bases = currentModel.value.knowledge_bases.filter(k => k.id !== kb.id)
    ElMessage.success('已解绑')
  } catch { ElMessage.error('解绑失败') }
}

function truncate(s, n) { return s?.length > n ? s.slice(0, n) + '...' : s }

onMounted(() => {
  loadCustomModels()
  loadAllKbs()

  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    window.requestIdleCallback(() => loadOllamaModels(), { timeout: 1500 })
  } else {
    setTimeout(() => loadOllamaModels(), 250)
  }
})
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

.section {
  margin-bottom: 32px;

  .section-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
    padding: 0 4px;
  }

  .section-title {
    font-size: 17px;
    font-weight: 700;
    color: #1E1B4B;
    margin: 0;
  }

  .refresh-btn {
    color: #5B5580;
    font-weight: 500;
    padding: 8px 12px;
    border-radius: 10px;
    transition: all 0.25s ease;

    &:hover {
      color: #6366F1;
      background: rgba(99, 102, 241, 0.08);
    }

    .el-icon {
      margin-right: 6px;
    }
  }
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

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;

  .model-tag {
    background: rgba(99, 102, 241, 0.08);
    border-color: rgba(99, 102, 241, 0.15);
    color: #6366F1;
    font-weight: 500;
    padding: 8px 16px;
    transition: all 0.25s ease;

    &:hover {
      background: rgba(99, 102, 241, 0.12);
      border-color: rgba(99, 102, 241, 0.25);
    }
  }
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
  min-height: 280px;
}

.page-empty {
  grid-column: 1 / -1;
  place-self: center;
}

.model-card {
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
    align-items: center;
    margin-bottom: 12px;
  }

  .model-name {
    font-size: 17px;
    font-weight: 700;
    color: #1E1B4B;
    letter-spacing: -0.2px;
  }

  .more-btn {
    color: #A5A3C9;
    transition: color 0.2s;

    &:hover {
      color: #6366F1;
    }
  }

  .model-desc {
    font-size: 14px;
    color: #5B5580;
    margin: 0 0 14px;
    line-height: 1.6;
    min-height: 22px;
  }

  .model-tags {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;

    .base-tag {
      background: rgba(99, 102, 241, 0.08);
      border-color: rgba(99, 102, 241, 0.15);
      color: #6366F1;
    }

    .kb-tag {
      background: rgba(139, 92, 246, 0.06);
      border-color: rgba(139, 92, 246, 0.12);
      color: #8B5CF6;
    }
  }

  .sys-prompt {
    font-size: 13px;
    color: #8B87B5;
    background: rgba(99, 102, 241, 0.04);
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid rgba(99, 102, 241, 0.08);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

// 弹窗头部
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


.form-row {
  display: flex;
  gap: 16px;

  .form-item-half {
    flex: 1;
    margin-bottom: 20px;
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

.dialog-select {
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



// 知识库绑定弹窗
.dialog-tip {
  color: #5B5580;
  font-size: 14px;
  margin-bottom: 20px;
  padding: 0 4px;
}

.binding-block {
  margin-bottom: 20px;

  .block-title {
    font-size: 14px;
    font-weight: 600;
    color: #312E4A;
    margin: 0 0 12px;
    padding: 0 4px;
  }
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  min-height: 48px;
  align-content: flex-start;
  justify-content: center;
  text-align: center;

  .bound-tag {
    background: rgba(99, 102, 241, 0.08);
    border-color: rgba(99, 102, 241, 0.15);
    color: #6366F1;
    padding: 8px 14px;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    justify-content: center;

    .el-icon {
      margin-right: 6px;
    }

    &:hover {
      background: rgba(99, 102, 241, 0.12);
    }
  }

  .clickable-tag {
    cursor: pointer;
    border-style: dashed;
    border-color: rgba(99, 102, 241, 0.25);
    color: #6366F1;
    padding: 8px 14px;
    font-weight: 500;
    transition: all 0.25s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;

    &:hover {
      border-style: solid;
      border-color: #6366F1;
      background: rgba(99, 102, 241, 0.08);
    }

    .el-icon {
      margin-right: 6px;
    }
  }
}

.custom-divider {
  margin: 20px 0;

  :deep(.el-divider__text) {
    color: #8B87B5;
    font-size: 13px;
    font-weight: 500;
    background: #FAFBFE;
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
