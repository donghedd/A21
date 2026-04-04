<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { setItem } from '@/utils/storage'

const route = useRoute()

watch(() => route.path, () => {
  window.scrollTo(0, 0)
})

onMounted(() => {
  const theme = localStorage.getItem('sfqa_theme') || 'light'
  document.documentElement.setAttribute('data-theme', theme)
})
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 全局 ElMessageBox 弹窗样式优化 - Sapphire Elegance Theme */
.el-message-box__wrapper {
  backdrop-filter: blur(8px);
}

.el-message-box {
  border-radius: 20px;
  padding: 0;
  border: none;
  box-shadow: 0 24px 60px rgba(99, 102, 241, 0.25);
  overflow: hidden;
}

.el-message-box__header {
  display: flex;
  align-items: center;
  padding: 28px 28px 16px;
  background: transparent;
  position: relative;
}

.el-message-box__title {
  font-size: 18px;
  font-weight: 700;
  color: #1E1B4B;
  padding-left: 44px;
  width: 100%;
}

.el-message-box__status {
  position: absolute;
  top: 28px;
  left: 28px;
  font-size: 26px;
}

.el-message-box__content {
  padding: 8px 28px 20px;
}

.el-message-box__message {
  font-size: 15px;
  line-height: 1.6;
  color: #312E4A;
}

.el-message-box__btns {
  padding: 0 28px 28px;
  gap: 12px;
}

.el-message-box__btns .el-button {
  border-radius: 10px;
  padding: 10px 20px;
  font-weight: 600;
  transition: all 0.25s ease;
}

.el-message-box__btns .el-button:not(.el-button--primary) {
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.12);
  color: #5B5580;

  &:hover {
    background: rgba(99, 102, 241, 0.1);
    border-color: rgba(99, 102, 241, 0.25);
    color: #6366F1;
  }
}

.el-message-box__btns .el-button--primary {
  background: linear-gradient(135deg, #6366F1, #8B5CF6);
  border: none;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);

  &:hover {
    background: linear-gradient(135deg, #4F46E5, #7C3AED);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
    transform: translateY(-1px);
  }
}

/* 成功图标 */
.el-message-box__status.el-icon-success {
  color: #10B981;
}

/* 警告图标 */
.el-message-box__status.el-icon-warning {
  color: #F59E0B;
}

/* 错误图标 */
.el-message-box__status.el-icon-error {
  color: #EF4444;
}

/* 确认框图标 */
.el-message-box__status.el-icon-info {
  color: #6366F1;
}

/* 输入框样式优化 */
.el-message-box__input {
  margin-top: 16px;
}

.el-message-box__input .el-input__wrapper {
  border-radius: 10px;
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.15) inset;
  background: rgba(255, 255, 255, 0.8);
  transition: all 0.25s ease;

  &:hover {
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.25) inset;
  }

  &.is-focus {
    box-shadow: 0 0 0 1px #6366F1 inset, 0 0 0 4px rgba(99, 102, 241, 0.1);
  }
}

/* 全局 Select 下拉面板样式优化 */
.el-select-dropdown {
  border-radius: 16px;
  padding: 10px;
  box-shadow: 0 20px 60px rgba(99, 102, 241, 0.2), 0 8px 24px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.12);
}

.el-select-dropdown__item {
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 15px;
  color: #312E4A;
  transition: all 0.2s ease;
  height: auto;
  line-height: 1.5;
  margin-bottom: 4px;

  &:last-child {
    margin-bottom: 0;
  }

  &:hover {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.06));
    color: #6366F1;
    transform: translateX(2px);
  }

  &.selected {
    color: #6366F1;
    font-weight: 700;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08));
  }

  &.is-disabled {
    color: #A5A3C9;
    &:hover {
      background: transparent;
      color: #A5A3C9;
      transform: none;
    }
  }
}

.el-select-group__wrap {
  padding: 4px 6px;
}

.el-select-group__title {
  font-size: 11px;
  font-weight: 800;
  color: #8B87B5;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 14px 12px 10px;
  margin-top: 4px;

  &:first-child {
    margin-top: 0;
  }
}

.el-select-dropdown__empty {
  padding: 32px 24px;
  color: #A5A3C9;
  font-size: 15px;
}
</style>
