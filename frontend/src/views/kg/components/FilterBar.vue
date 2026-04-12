<template>
  <div class="filter-bar">
    <div class="filter-left">
      <div class="search-group">
        <span class="search-label">节点</span>
        <el-input
          v-model="localKeyword"
          class="search-input"
          placeholder="请输入设备、故障、原因等名称"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" :loading="loading" @click="handleSearch">搜索</el-button>
      </div>
    </div>

    <div class="filter-right">
      <el-button plain @click="$emit('reset')">刷新</el-button>
      <el-button plain @click="$emit('center')">居中</el-button>
      <el-button plain @click="$emit('settings')">设置</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = defineProps({
  keyword: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'update:keyword',
  'search',
  'center',
  'reset',
  'settings'
])

const localKeyword = computed({
  get: () => props.keyword,
  set: value => emit('update:keyword', value)
})

function handleSearch() {
  emit('search')
}
</script>

<style scoped lang="scss">
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 18px;
  flex: 1;
  min-width: 0;
}

.search-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.search-label,
.field-label {
  flex-shrink: 0;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.search-input {
  flex: 1;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

:deep(.filter-bar .el-input__wrapper),
:deep(.filter-bar .el-select__wrapper) {
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 0 0 1px rgba(203, 213, 225, 0.92) inset;
}

:deep(.filter-bar .el-input__wrapper.is-focus),
:deep(.filter-bar .el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.82) inset, 0 0 0 4px rgba(37, 99, 235, 0.08);
}

@media (max-width: 1180px) {
  .filter-bar,
  .filter-left {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-right {
    flex-wrap: wrap;
  }
}

@media (max-width: 760px) {
  .search-group {
    flex-wrap: wrap;
  }
}
</style>
