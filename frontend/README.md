# SFQA AI 前端系统

基于 Element Plus X 组件库构建的现代化 AI 问答系统前端。

## ✨ 特性

- 🎨 **现代化 UI** - 基于 Element Plus X 的时尚优美界面设计
- 🤖 **AI 聊天** - 支持流式对话、打字机效果、消息分组
- 🎙️ **语音交互** - 语音输入/输出、实时转写
- 📝 **Markdown 渲染** - 完整的 Markdown 支持和代码高亮
- 🔄 **多模型支持** - 灵活的模型接入架构
- 📱 **响应式设计** - 完美适配桌面和移动设备
- ⚡ **高性能** - 优化的组件加载和渲染性能

## 🚀 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

### 生产构建

```bash
npm run build
```

## 📁 项目结构

```
src/
├── api/                    # API 接口
├── assets/                 # 静态资源
│   └── styles/            # 全局样式
├── components/            # 组件
│   ├── ai/               # AI 核心组件
│   │   ├── AiChat.vue   # 聊天容器
│   │   ├── AiMessage.vue # 消息组件
│   │   ├── AiVoice.vue   # 语音组件
│   │   └── SourcesPanel.vue # 来源面板
│   └── chat/             # 聊天相关组件
├── composables/          # 组合式函数
├── router/               # 路由配置
├── stores/               # 状态管理
├── utils/                # 工具函数
└── views/                # 页面视图
```

## 🧩 核心组件

### AiChat

主要的聊天容器组件，集成了消息列表、输入框、模型选择等功能。

```vue
<template>
  <AiChat
    :messages="messages"
    :is-streaming="isStreaming"
    :models="models"
    @send="handleSend"
    @stop="handleStop"
  />
</template>
```

### AiMessage

消息渲染组件，支持 Markdown、代码高亮、思考过程展示。

```vue
<template>
  <AiMessage
    :content="content"
    :thinking="thinking"
    :sources="sources"
    :role="role"
  />
</template>
```

### AiVoice

语音输入组件，支持实时转写。

```vue
<template>
  <AiVoice
    @use-transcript="handleTranscript"
  />
</template>
```

## 🎨 主题定制

### 修改主题变量

```scss
// src/assets/styles/main.scss
$primary-color: #3b82f6;
$bg-primary: #ffffff;
$text-primary: #111827;
```

### 组件样式覆盖

```scss
// 自定义 BubbleList 样式
.bubble-list {
  .bubble-content {
    background: #your-color;
  }
}
```

## 📱 响应式断点

- **Desktop**: > 1024px
- **Tablet**: 768px - 1024px
- **Mobile**: < 768px

## 🔧 配置

### 环境变量

```env
VITE_API_BASE_URL=/api
VITE_APP_TITLE=SFQA AI
```

### 模型配置

支持 Ollama 本地模型和自定义模型：

```javascript
const models = [
  { id: 'qwen3:14b', name: 'Qwen3 14B', type: 'ollama' },
  { id: 'custom-1', name: 'Custom Model', type: 'custom', base_model: 'gpt-4' }
]
```

## 📚 文档

- [AI 组件使用文档](./docs/AI_COMPONENTS.md)
- [Element Plus X 文档](https://element-plus-x.com)
- [Element Plus 文档](https://element-plus.org)

## 🤝 贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

[MIT](LICENSE)
