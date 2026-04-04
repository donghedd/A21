# AI 组件库使用文档

## 简介

本项目基于 **Element Plus X** 组件库进行了全面重构，实现了现代化的 AI 交互界面。Element Plus X 是一个开箱即用的企业级 AI 组件库，基于 Vue 3 + Element Plus 构建。

## 核心组件

### 1. AiChat 组件

`AiChat` 是主要的聊天容器组件，集成了消息列表、输入框、模型选择等功能。

#### 基本用法

```vue
<template>
  <AiChat
    :title="'AI 助手'"
    :messages="messages"
    :is-streaming="isStreaming"
    :models="availableModels"
    :default-model="selectedModel"
    @send="handleSend"
    @stop="handleStop"
    @regenerate="handleRegenerate"
  />
</template>

<script setup>
import { AiChat } from '@/components/ai'

const messages = ref([
  { id: 1, role: 'user', content: '你好' },
  { id: 2, role: 'assistant', content: '你好！有什么我可以帮你的吗？' }
])

const handleSend = ({ content, model }) => {
  // 处理发送消息
}
</script>
```

#### Props

| 属性名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| title | String | 'AI 助手' | 聊天标题 |
| messages | Array | [] | 消息列表 |
| isStreaming | Boolean | false | 是否正在流式输出 |
| loading | Boolean | false | 是否加载中 |
| models | Array | [] | 可用模型列表 |
| defaultModel | String | '' | 默认选中的模型 |
| userName | String | 'User' | 用户名 |
| userAvatar | String | '' | 用户头像 URL |
| aiAvatar | String | '' | AI 头像 URL |
| showWelcome | Boolean | true | 是否显示欢迎区域 |
| welcomeTitle | String | '你好，我是 AI 助手' | 欢迎标题 |
| welcomeDescription | String | '有什么我可以帮你的吗？' | 欢迎描述 |
| prompts | Array | [] | 提示词列表 |
| inputPlaceholder | String | '输入您的问题...' | 输入框占位符 |
| allowSpeech | Boolean | true | 是否允许语音输入 |

#### Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| send | { content, model } | 发送消息 |
| stop | - | 停止生成 |
| regenerate | item | 重新生成 |
| edit | item | 编辑消息 |
| source-click | source | 点击来源引用 |
| prompt-click | prompt | 点击提示词 |

### 2. AiMessage 组件

`AiMessage` 用于渲染单条消息，支持 Markdown、代码高亮、思考过程展示等功能。

#### 基本用法

```vue
<template>
  <AiMessage
    :content="message.content"
    :thinking="message.thinking"
    :thinking-duration="message.thinkingDuration"
    :sources="message.sources"
    :role="message.role"
    @source-click="handleSourceClick"
  />
</template>

<script setup>
import { AiMessage } from '@/components/ai'
</script>
```

#### Props

| 属性名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| content | String | '' | 消息内容 |
| thinking | String | '' | 思考过程内容 |
| thinkingDuration | Number | 0 | 思考时长（秒） |
| isThinking | Boolean | false | 是否正在思考 |
| sources | Array | [] | 来源引用列表 |
| role | String | 'assistant' | 角色（user/assistant） |
| loading | Boolean | false | 是否加载中 |
| enableTyping | Boolean | false | 是否启用打字机效果 |
| typingSpeed | Number | 30 | 打字速度（毫秒/字符） |

### 3. AiVoice 组件

`AiVoice` 提供语音输入和实时转写功能。

#### 基本用法

```vue
<template>
  <AiVoice
    :allow-speech="true"
    :max-duration="60"
    @transcript="handleTranscript"
    @use-transcript="handleUseTranscript"
  />
</template>

<script setup>
import { AiVoice } from '@/components/ai'

const handleUseTranscript = (text) => {
  // 使用转写的文本
}
</script>
```

#### Props

| 属性名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| autoStart | Boolean | false | 是否自动开始录音 |
| maxDuration | Number | 60 | 最大录音时长（秒） |
| showTranscript | Boolean | true | 是否显示转写面板 |
| language | String | 'zh-CN' | 语音识别语言 |

#### Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| transcript | text | 实时转写结果 |
| recording-start | - | 开始录音 |
| recording-stop | { duration, transcript } | 停止录音 |
| recording-error | error | 录音错误 |
| use-transcript | text | 使用转写文本 |

### 4. SourcesPanel 组件

`SourcesPanel` 用于展示消息的来源引用。

#### 基本用法

```vue
<template>
  <SourcesPanel
    :sources="sources"
    @source-click="handleSourceClick"
  />
</template>

<script setup>
import { SourcesPanel } from '@/components/ai'

const sources = [
  { id: 1, file_name: 'document.pdf', score: 0.95, content: '...' }
]
</script>
```

## 样式定制

### 主题变量

```scss
// 主色调
$primary-color: #3b82f6;
$primary-hover: #2563eb;

// 背景色
$bg-primary: #ffffff;
$bg-secondary: #f9fafb;
$bg-tertiary: #f3f4f6;

// 文字色
$text-primary: #111827;
$text-secondary: #4b5563;
$text-tertiary: #6b7280;
```

### 组件样式覆盖

```scss
// 自定义 BubbleList 样式
.bubble-list {
  .bubble-item {
    .bubble-content {
      background: #your-color;
    }
  }
}

// 自定义 Sender 样式
.sender {
  border-radius: 20px;
}
```

## 响应式设计

组件库支持响应式布局，在移动设备上会自动调整：

- 侧边栏会自动收起
- 消息气泡宽度调整为 90%
- 输入框适配屏幕宽度

```css
@media (max-width: 768px) {
  .chat-sidebar {
    position: fixed;
    transform: translateX(-100%);
  }
  
  .bubble-content {
    max-width: 90%;
  }
}
```

## 最佳实践

### 1. 消息数据格式

```javascript
const message = {
  id: 'unique-id',
  role: 'assistant', // 'user' 或 'assistant'
  content: '消息内容',
  thinking: '思考过程',
  thinkingDuration: 5, // 秒
  sources: [
    { id: 1, file_name: 'doc.pdf', score: 0.95 }
  ],
  created_at: '2024-01-01T00:00:00Z'
}
```

### 2. 流式输出处理

```javascript
import { useStreaming } from '@/composables/useStreaming'

const streaming = useStreaming()

const handleSend = async (content) => {
  const signal = streaming.createAbortSignal()
  const response = await fetch('/api/chat', { signal })
  
  await streaming.processStream(response, {
    onContent: (chunk, full) => {
      // 更新消息内容
    },
    onDone: (result) => {
      // 完成处理
    }
  })
}
```

### 3. 性能优化

- 使用 `v-once` 渲染历史消息
- 对大列表使用虚拟滚动
- 图片懒加载
- 代码分割和按需加载

## 常见问题

### Q: 如何自定义消息渲染？

A: 使用 `AiChat` 组件的插槽：

```vue
<AiChat :messages="messages">
  <template #message-content="{ item }">
    <CustomMessage :content="item.content" />
  </template>
</AiChat>
```

### Q: 如何添加自定义操作按钮？

A: 使用 `header-right` 插槽：

```vue
<AiChat>
  <template #header-right>
    <el-button @click="customAction">自定义操作</el-button>
  </template>
</AiChat>
```

### Q: 语音输入不支持怎么办？

A: 检查浏览器兼容性，或使用降级方案：

```javascript
if (!('webkitSpeechRecognition' in window)) {
  // 使用第三方语音识别服务
}
```

## 更新日志

### v2.0.0 (2024-01)

- ✨ 集成 Element Plus X 组件库
- ✨ 新增 AiChat、AiMessage、AiVoice 组件
- ✨ 支持流式对话和打字机效果
- ✨ 支持语音输入和实时转写
- ✨ 现代化 UI 设计
- ✨ 响应式布局支持

## 参考链接

- [Element Plus X 官方文档](https://element-plus-x.com)
- [Element Plus 文档](https://element-plus.org)
- [Vue 3 文档](https://vuejs.org)
