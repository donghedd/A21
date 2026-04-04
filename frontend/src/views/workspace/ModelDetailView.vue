<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" @click="$router.push('/workspace')" text class="back-btn">返回工作空间</el-button>
        <h2 class="page-title">模型详情</h2>
      </div>
    </div>

    <div v-loading="loading" class="detail-content">
      <!-- 基本信息 -->
      <section class="info-section">
        <h3 class="section-title">基本信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">模型名称</span>
            <span class="value">{{ model?.name || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">基础模型</span>
            <el-tag type="primary" effect="light" class="model-tag">{{ model?.base_model || '-' }}</el-tag>
          </div>
          <div class="info-item full">
            <span class="label">描述</span>
            <span class="value">{{ model?.description || '暂无描述' }}</span>
          </div>
        </div>
      </section>

      <!-- 系统提示词 -->
      <section class="info-section">
        <h3 class="section-title">系统提示词</h3>
        <div class="prompt-box">
          <pre v-if="model?.system_prompt">{{ model.system_prompt }}</pre>
          <p v-else class="empty-text">未配置系统提示词</p>
        </div>
      </section>

      <!-- 绑定知识库 -->
      <section class="info-section">
        <h3 class="section-title">
          已绑定知识库
          <span class="count">{{ model?.knowledge_bases?.length || 0 }}</span>
        </h3>
        <div v-if="model?.knowledge_bases?.length" class="kb-list">
          <div v-for="kb in model.knowledge_bases" :key="kb.id" class="kb-item">
            <el-icon><FolderOpened /></el-icon>
            <span>{{ kb.name }}</span>
          </div>
        </div>
        <el-empty v-else description="未绑定任何知识库" :image-size="60" />
      </section>

      <!-- 操作 -->
      <section class="action-bar">
        <el-button type="primary" @click="$router.push(`/workspace/model/${modelId}/edit`)" class="primary-btn">
          <el-icon><Edit /></el-icon> 编辑模型
        </el-button>
        <el-button @click="$router.push('/workspace')" class="secondary-btn">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
      </section>

      <el-empty v-if="!loading && !model" description="模型不存在或已被删除" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Edit, FolderOpened } from '@element-plus/icons-vue'
import * as modelApi from '@/api/model'

const route = useRoute()
const router = useRouter()
const modelId = route.params.id
const loading = ref(false)
const model = ref(null)

onMounted(async () => {
  if (!modelId) return
  loading.value = true
  try {
    const res = await modelApi.getCustomModels()
    model.value = (res.data || []).find(m => m.id === Number(modelId)) || null
  } catch {} finally {
    loading.value = false
  }
})
</script>

<style scoped lang="scss">
.page-container {
  padding: 24px 28px;
  min-height: 100vh;
  background: linear-gradient(135deg, #FAFBFE 0%, #F3F1FF 50%, #EEEDF9 100%);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .back-btn {
    color: #6366F1;
    font-weight: 500;
    
    &:hover {
      color: #4F46E5;
      background: rgba(99, 102, 241, 0.08);
    }
  }

  .page-title {
    font-size: 22px;
    font-weight: 700;
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
  }
}

.detail-content {
  max-width: 800px;
}

.info-section {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.06);
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.12);
    border-color: rgba(99, 102, 241, 0.2);
  }

  .section-title {
    font-size: 15px;
    font-weight: 600;
    color: #4B5563;
    margin: 0 0 18px;

    .count {
      font-size: 13px;
      font-weight: 500;
      color: #6366F1;
      margin-left: 6px;
      background: rgba(99, 102, 241, 0.1);
      padding: 2px 10px;
      border-radius: 12px;
    }
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 6px;

    &.full {
      grid-column: 1 / -1;
    }

    .label {
      font-size: 13px;
      color: #9CA3AF;
      font-weight: 500;
    }

    .value {
      font-size: 15px;
      font-weight: 600;
      color: #1F2937;
    }
  }
}

.model-tag {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.2);
  color: #6366F1;
  font-weight: 500;
}

.prompt-box {
  background: linear-gradient(135deg, #FAFBFE 0%, #F5F3FF 100%);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 12px;
  padding: 16px;
  max-height: 300px;
  overflow-y: auto;

  pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 14px;
    line-height: 1.7;
    color: #374151;
    font-family: 'JetBrains Mono', Consolas, monospace;
  }

  .empty-text {
    color: #9CA3AF;
    text-align: center;
    margin: 20px 0 0;
    font-style: italic;
  }
}

.kb-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kb-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #FAFBFE 0%, #F5F3FF 100%);
  border-radius: 10px;
  font-size: 14px;
  color: #4B5563;
  border: 1px solid rgba(99, 102, 241, 0.1);
  transition: all 0.25s ease;

  &:hover {
    background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%);
    border-color: rgba(99, 102, 241, 0.2);
    transform: translateX(4px);
  }

  .el-icon {
    color: #6366F1;
  }
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.primary-btn {
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  border: none;
  border-radius: 10px;
  padding: 10px 20px;
  font-weight: 500;
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.25);
  transition: all 0.25s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
  }
}

.secondary-btn {
  background: #fff;
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 10px;
  padding: 10px 20px;
  color: #6366F1;
  font-weight: 500;
  transition: all 0.25s ease;

  &:hover {
    background: rgba(99, 102, 241, 0.08);
    border-color: rgba(99, 102, 241, 0.4);
    color: #4F46E5;
  }
}

:deep(.el-empty) {
  padding: 40px 0;
  
  .el-empty__description {
    color: #9CA3AF;
  }
}

:deep(.el-loading-mask) {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
}
</style>
