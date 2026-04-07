<template>
  <el-dialog
    v-model="visible"
    width="640px"
    destroy-on-close
    class="custom-dialog source-detail-dialog"
  >
    <button class="dialog-close-btn" @click="visible = false">
      <el-icon><Close /></el-icon>
    </button>
    <div class="dialog-header-icon">
      <div class="icon-wrapper">
        <el-icon :size="28"><Document /></el-icon>
      </div>
      <h3 class="dialog-title">来源详情</h3>
      <p class="dialog-subtitle">查看引用来源的详细信息</p>
    </div>

    <div v-if="source" class="detail-body">
      <div class="meta-row">
        <div class="meta-item">
          <el-icon><Files /></el-icon>
          <span>{{ source.file_name || '未知文件' }}</span>
        </div>
        <div class="meta-item score">
          <el-icon><TrendCharts /></el-icon>
          <span>相关度: {{ (source.score * 100).toFixed(1) }}%</span>
        </div>
      </div>

      <div class="content-area">
        <div class="content-label">
          <el-icon><Reading /></el-icon>
          引用内容
        </div>
        <pre class="content-text">{{ source.content }}</pre>
      </div>

      <div v-if="source.section_path && source.section_path.length" class="section-info">
        <div class="section-label">
          <el-icon><FolderOpened /></el-icon>
          文档路径
        </div>
        <div class="section-path">
          <span v-for="(path, index) in source.section_path" :key="index" class="path-item">
            {{ path }}
            <el-icon v-if="index < source.section_path.length - 1"><ArrowRight /></el-icon>
          </span>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false" class="cancel-btn">
          <el-icon><Close /></el-icon>
          关闭
        </el-button>
        <el-button type="primary" @click="copyContent" class="confirm-btn">
          <el-icon><DocumentCopy /></el-icon>
          复制内容
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Files, TrendCharts, Reading, FolderOpened, ArrowRight, Close, DocumentCopy } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  source: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

async function copyContent() {
  if (!props.source?.content) return
  try {
    await navigator.clipboard.writeText(props.source.content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = props.source.content
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制到剪贴板')
  }
}
</script>

<style scoped lang="scss">
.detail-body {
  padding: 24px 28px;
}

.meta-row {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

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

.content-area {
  margin-bottom: 16px;

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

.content-text {
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

.section-info {
  padding: 14px 16px;
  background: rgba(99, 102, 241, 0.04);
  border-radius: 10px;
  border: 1px solid rgba(99, 102, 241, 0.08);

  .section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 700;
    color: #8B5CF6;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;

    .el-icon {
      font-size: 14px;
    }
  }

  .section-path {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    font-size: 13px;
    color: #5B5580;

    .path-item {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(139, 92, 246, 0.08);
      padding: 4px 10px;
      border-radius: 6px;

      .el-icon {
        font-size: 12px;
        color: #A5A3C9;
      }
    }
  }
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 0 28px 28px;

  .el-button {
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 600;
    transition: all 0.25s ease;
  }

  .cancel-btn {
    background: rgba(99, 102, 241, 0.06);
    border: 1px solid rgba(99, 102, 241, 0.12);
    color: #5B5580;

    &:hover {
      background: rgba(99, 102, 241, 0.1);
      border-color: rgba(99, 102, 241, 0.25);
      color: #6366F1;
    }
  }

  .confirm-btn {
    background: linear-gradient(135deg, #6366F1, #8B5CF6);
    border: none;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
    color: #fff;

    &:hover {
      background: linear-gradient(135deg, #4F46E5, #7C3AED);
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
      transform: translateY(-1px);
    }
  }
}
</style>

<style lang="scss">
/* Source Detail Dialog 全局样式 */
.source-detail-dialog {
  &.el-dialog {
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 24px 60px rgba(99, 102, 241, 0.2);
  }

  .el-dialog__header {
    display: none;
  }

  .el-dialog__body {
    padding: 0;
  }

  .el-dialog__footer {
    padding: 0;
    border-top: none;
  }
}
</style>