<template>
  <main class="chat-panel">
    <AiChat
      :title="title"
      :messages="messages"
      :is-streaming="isStreaming"
      :models="models"
      :default-model="defaultModel"
      :user-name="userName"
      :show-sidebar-toggle="showSidebarToggle"
      :sidebar-collapsed="sidebarCollapsed"
      :prompts="prompts"
      :input-disabled="inputDisabled"
      :input-placeholder="inputPlaceholder"
      :editing-message-id="editingMessageId"
      :title-editable="titleEditable"
      @send="$emit('send', $event)"
      @stop="$emit('stop')"
      @regenerate="$emit('regenerate', $event)"
      @edit="$emit('edit', $event)"
      @edit-submit="$emit('edit-submit', $event)"
      @edit-cancel="$emit('edit-cancel')"
      @title-submit="$emit('title-submit', $event)"
      @source-click="$emit('source-click', $event)"
      @update:model="$emit('update:model', $event)"
      @update:sidebar-collapsed="$emit('update:sidebarCollapsed', $event)"
    />
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { AiChat } from '@/components/ai'

const props = defineProps({
  title: { type: String, default: '新对话' },
  messages: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
  models: { type: Array, default: () => [] },
  defaultModel: { type: String, default: '' },
  userName: { type: String, default: 'User' },
  showSidebarToggle: { type: Boolean, default: false },
  sidebarCollapsed: { type: Boolean, default: false },
  prompts: { type: Array, default: () => [] },
  editingMessageId: { type: String, default: null },
  titleEditable: { type: Boolean, default: false }
})

defineEmits([
  'send',
  'stop',
  'regenerate',
  'edit',
  'edit-submit',
  'edit-cancel',
  'title-submit',
  'source-click',
  'update:model',
  'update:sidebarCollapsed'
])

const inputDisabled = computed(() => !!props.editingMessageId)
const inputPlaceholder = computed(() => (
  props.editingMessageId
    ? '正在编辑历史消息，请在消息气泡内提交'
    : '输入您的问题...'
))
</script>

<style scoped lang="scss">
.chat-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
