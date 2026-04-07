<template>
  <div v-if="sources && sources.length > 0" class="sources-panel">
    <div class="sources-header">
      <el-icon><Document /></el-icon>
      <span>参考来源 ({{ sources.length }})</span>
    </div>
    
    <!-- 快速引用标签 -->
    <div class="reference-tags">
      <span class="reference-label">快速引用:</span>
      <div class="tags-list">
        <el-tag
          v-for="source in sources"
          :key="source.id"
          class="reference-tag"
          :class="{ active: activeSource === source.id }"
          size="small"
          effect="plain"
          @click="handleSourceClick(source)"
        >
          [{{ source.id }}] {{ truncate(source.file_name || '未知', 15) }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Document } from '@element-plus/icons-vue'

const props = defineProps({
  sources: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['source-click'])

const activeSource = ref(null)

const truncate = (text, maxLength) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

const handleSourceClick = (source) => {
  activeSource.value = source.id
  emit('source-click', source)
}
</script>

<style scoped lang="scss">
.sources-panel {
  margin-top: 16px;
  padding: 14px;
  background: #f9fafb;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}

.sources-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e5e7eb;
  
  .el-icon {
    font-size: 16px;
    color: #6b7280;
  }
}

/* 引用标签样式 */
.reference-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.reference-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
  white-space: nowrap;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.reference-tag {
  cursor: pointer;
  transition: all 0.2s;
  font-family: monospace;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #4b5563;
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
    border-color: #3b82f6;
    color: #3b82f6;
  }
  
  &.active {
    background-color: #3b82f6;
    color: white;
    border-color: #3b82f6;
  }
}
</style>
