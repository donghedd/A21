<template>
  <div class="paper-table">
    <header class="paper-header">
      <span class="paper-title">关联资料</span>
      <span class="paper-count">共 {{ paperList.length }} 条</span>
    </header>

    <div class="paper-body">
      <div v-if="paperList.length" class="paper-grid">
        <button
          v-for="(paper, index) in paperList"
          :key="paper.id || `${paper.title}-${index}`"
          type="button"
          class="paper-card"
          @click="handleOpen(paper)"
        >
          <div class="paper-meta">
            <el-icon class="paper-icon"><Document /></el-icon>
            <div class="paper-info">
              <div class="paper-name" :title="paper.title">{{ paper.title }}</div>
              <div class="paper-desc">
                <span :title="paper.journal">{{ paper.journal || '本地图谱来源' }}</span>
                <span>{{ paper.year || '----' }}年</span>
              </div>
            </div>
          </div>

          <div class="paper-arrow">
            <el-icon><Right /></el-icon>
          </div>
        </button>
      </div>

      <div v-else class="paper-empty">
        <span>暂无关联资料</span>
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="760px"
      :close-on-click-modal="false"
      append-to-body
    >
      <div class="paper-dialog">
        <div v-if="dialogContent" class="paper-dialog-content">{{ dialogContent }}</div>
        <el-empty v-else description="暂无资料详情" />
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button v-if="dialogContent" type="primary" @click="copyContent">复制详情</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Right } from '@element-plus/icons-vue'

defineProps({
  paperList: {
    type: Array,
    default: () => []
  }
})

const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogContent = ref('')

function handleOpen(paper) {
  if (paper.url || paper.link) {
    window.open(paper.url || paper.link, '_blank', 'noopener')
    return
  }

  dialogTitle.value = paper.title || '资料详情'
  dialogContent.value = [
    `标题：${paper.title || '未命名资料'}`,
    `来源：${paper.journal || '本地图谱来源'}`,
    paper.year ? `年份：${paper.year}` : '年份：未知',
    '说明：该资料来自技术图谱节点关联来源，用于说明当前节点的上下文与出处。'
  ].join('\n')
  dialogVisible.value = true
}

async function copyContent() {
  if (!dialogContent.value) return
  try {
    await navigator.clipboard.writeText(dialogContent.value)
    ElMessage.success('资料详情已复制')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}
</script>

<style scoped lang="scss">
.paper-table {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  overflow: hidden;
}

.paper-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(248, 250, 252, 0.9);
}

.paper-title {
  padding-left: 10px;
  border-left: 4px solid #3b82f6;
  color: #334155;
  font-size: 14px;
  font-weight: 800;
}

.paper-count {
  color: #94a3b8;
  font-size: 12px;
}

.paper-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px;
  background: #f8fafc;
}

.paper-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.paper-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  min-height: 78px;
  padding: 14px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 14px;
  background: #ffffff;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
}

.paper-card:hover {
  border-color: rgba(59, 130, 246, 0.6);
  box-shadow: 0 10px 24px rgba(59, 130, 246, 0.08);
}

.paper-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.paper-icon {
  color: #3b82f6;
  font-size: 22px;
  flex-shrink: 0;
}

.paper-info {
  min-width: 0;
}

.paper-name {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.45;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.paper-desc {
  display: flex;
  gap: 10px;
  margin-top: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.paper-arrow {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  color: #64748b;
  background: #eff6ff;
  flex-shrink: 0;
}

.paper-empty {
  height: 100%;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 13px;
}

.paper-dialog {
  min-height: 320px;
  max-height: 60vh;
  overflow: auto;
  padding: 16px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.paper-dialog-content {
  white-space: pre-wrap;
  word-break: break-word;
  color: #334155;
  font-size: 13px;
  line-height: 1.8;
}

@media (max-width: 1280px) {
  .paper-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .paper-grid {
    grid-template-columns: 1fr;
  }
}
</style>
