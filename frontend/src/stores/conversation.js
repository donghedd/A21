import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * 对话消息存储 Store
 * 使用 Pinia 替代 localStorage，实现用户消息与AI消息的键值对对应存储
 * 确保消息的正确渲染关联
 */
export const useConversationStore = defineStore('conversation', () => {
  // ==================== State ====================
  
  // 对话列表
  const conversations = ref([])
  
  // 当前激活的对话ID
  const currentConversationId = ref(null)
  
  // 消息存储结构：{ conversationId: { messagePairs: [], orphanMessages: [] } }
  // messagePairs: [{ userMessage: {}, assistantMessage: {}, status: 'pending' | 'completed' | 'error' }]
  const conversationMessages = ref(new Map())
  
  // 流式响应状态
  const streamingStates = ref(new Map())

  // ==================== Getters ====================
  
  /**
   * 获取当前对话的消息列表（按顺序渲染）
   */
  const currentMessages = computed(() => {
    const convId = currentConversationId.value
    if (!convId) return []
    
    const convData = conversationMessages.value.get(convId)
    if (!convData) return []
    
    // 将消息对展开为顺序数组
    const messages = []
    
    // 添加成对的消息
    convData.messagePairs.forEach(pair => {
      if (pair.userMessage) {
        messages.push(pair.userMessage)
      }
      if (pair.assistantMessage) {
        messages.push(pair.assistantMessage)
      }
    })
    
    // 添加孤儿消息（没有对应关系的消息）
    if (convData.orphanMessages) {
      messages.push(...convData.orphanMessages)
    }
    
    // 按创建时间排序
    messages.sort((a, b) => {
      const timeA = a.created_at ? new Date(a.created_at).getTime() : 0
      const timeB = b.created_at ? new Date(b.created_at).getTime() : 0
      return timeA - timeB
    })
    
    return messages
  })
  
  /**
   * 获取指定对话的消息
   */
  const getConversationMessages = computed(() => (conversationId) => {
    if (!conversationId) return []
    
    const convData = conversationMessages.value.get(conversationId)
    if (!convData) return []
    
    const messages = []
    
    convData.messagePairs.forEach(pair => {
      if (pair.userMessage) messages.push(pair.userMessage)
      if (pair.assistantMessage) messages.push(pair.assistantMessage)
    })
    
    if (convData.orphanMessages) {
      messages.push(...convData.orphanMessages)
    }
    
    messages.sort((a, b) => {
      const timeA = a.created_at ? new Date(a.created_at).getTime() : 0
      const timeB = b.created_at ? new Date(b.created_at).getTime() : 0
      return timeA - timeB
    })
    
    return messages
  })
  
  /**
   * 检查是否有正在进行的流式响应
   */
  const hasActiveStreaming = computed(() => (conversationId) => {
    if (!conversationId) return false
    const state = streamingStates.value.get(conversationId)
    return state?.isStreaming ?? false
  })
  
  /**
   * 获取当前对话的流式状态
   */
  const currentStreamingState = computed(() => {
    const convId = currentConversationId.value
    if (!convId) return null
    return streamingStates.value.get(convId) || null
  })

  // ==================== Actions ====================
  
  /**
   * 设置对话列表
   */
  function setConversations(list) {
    conversations.value = list || []
  }
  
  /**
   * 设置当前对话ID
   */
  function setCurrentConversation(id) {
    currentConversationId.value = id
  }
  
  /**
   * 初始化对话消息存储结构
   */
  function initConversationStorage(conversationId) {
    if (!conversationId) return
    
    if (!conversationMessages.value.has(conversationId)) {
      conversationMessages.value.set(conversationId, {
        messagePairs: [],
        orphanMessages: [],
        lastUpdated: Date.now()
      })
    }
  }
  
  /**
   * 添加用户消息并创建新的消息对
   * @returns {string} 消息对的ID
   */
  function addUserMessage(conversationId, message) {
    if (!conversationId || !message) return null
    
    initConversationStorage(conversationId)
    
    const convData = conversationMessages.value.get(conversationId)
    
    // 确保消息有唯一ID
    const messageWithId = {
      ...message,
      id: message.id || `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    }
    
    // 创建新的消息对
    const pairId = `pair-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const newPair = {
      id: pairId,
      userMessage: messageWithId,
      assistantMessage: null,
      status: 'pending', // pending | streaming | completed | error
      createdAt: Date.now()
    }
    
    convData.messagePairs.push(newPair)
    convData.lastUpdated = Date.now()
    
    return pairId
  }
  
  /**
   * 为指定的用户消息添加AI回复
   */
  function addAssistantMessage(conversationId, userMessageId, assistantMessage) {
    if (!conversationId || !userMessageId || !assistantMessage) return false
    
    const convData = conversationMessages.value.get(conversationId)
    if (!convData) return false
    
    // 查找对应的消息对
    const pair = convData.messagePairs.find(p => 
      p.userMessage?.id === userMessageId
    )
    
    if (pair) {
      // 找到对应的消息对，添加AI消息
      pair.assistantMessage = {
        ...assistantMessage,
        id: assistantMessage.id || `assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        parentMessageId: userMessageId // 建立关联
      }
      pair.status = assistantMessage.isStreaming ? 'streaming' : 'completed'
      convData.lastUpdated = Date.now()
      return true
    } else {
      // 没有找到对应的消息对，作为孤儿消息添加
      const orphanMessage = {
        ...assistantMessage,
        id: assistantMessage.id || `assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        parentMessageId: userMessageId
      }
      convData.orphanMessages.push(orphanMessage)
      convData.lastUpdated = Date.now()
      return false
    }
  }
  
  /**
   * 更新AI消息内容（用于流式响应）
   */
  function updateAssistantMessage(conversationId, assistantMessageId, updates) {
    if (!conversationId || !assistantMessageId) return false
    
    const convData = conversationMessages.value.get(conversationId)
    if (!convData) return false
    
    // 在消息对中查找
    for (const pair of convData.messagePairs) {
      if (pair.assistantMessage?.id === assistantMessageId) {
        pair.assistantMessage = { ...pair.assistantMessage, ...updates }
        convData.lastUpdated = Date.now()
        return true
      }
    }
    
    // 在孤儿消息中查找
    const orphanIndex = convData.orphanMessages.findIndex(
      m => m.id === assistantMessageId
    )
    if (orphanIndex !== -1) {
      convData.orphanMessages[orphanIndex] = {
        ...convData.orphanMessages[orphanIndex],
        ...updates
      }
      convData.lastUpdated = Date.now()
      return true
    }
    
    return false
  }
  
  /**
   * 从服务器同步消息（用于初始加载）
   * 服务器消息优先，但保留本地临时消息
   */
  function syncMessagesFromServer(conversationId, serverMessages) {
    if (!conversationId || !Array.isArray(serverMessages)) return
    
    initConversationStorage(conversationId)
    const convData = conversationMessages.value.get(conversationId)
    
    // 保存现有的临时消息对
    const tempPairs = convData.messagePairs.filter(p => 
      p.userMessage?.id?.startsWith('temp-') || 
      p.assistantMessage?.id?.startsWith('temp-') ||
      p.status === 'streaming'
    )
    
    // 清空现有消息对
    convData.messagePairs = []
    convData.orphanMessages = []
    
    // 按顺序处理服务器消息，重建消息对
    let currentPair = null
    
    serverMessages.forEach(msg => {
      if (msg.role === 'user') {
        // 用户消息，创建新对
        currentPair = {
          id: `pair-server-${msg.id || Date.now()}`,
          userMessage: { ...msg },
          assistantMessage: null,
          status: 'pending',
          createdAt: msg.created_at ? new Date(msg.created_at).getTime() : Date.now()
        }
        convData.messagePairs.push(currentPair)
      } else if (msg.role === 'assistant' && currentPair) {
        // AI消息，关联到当前对
        currentPair.assistantMessage = { ...msg }
        currentPair.status = 'completed'
      } else if (msg.role === 'assistant') {
        // 孤儿AI消息
        convData.orphanMessages.push({ ...msg })
      }
    })
    
    // 恢复临时消息对
    tempPairs.forEach(pair => {
      // 检查是否已存在相同ID的消息
      const exists = convData.messagePairs.some(p => 
        p.userMessage?.id === pair.userMessage?.id
      )
      if (!exists) {
        convData.messagePairs.push(pair)
      }
    })
    
    // 重新排序
    convData.messagePairs.sort((a, b) => a.createdAt - b.createdAt)
    convData.lastUpdated = Date.now()
  }
  
  /**
   * 删除消息对
   */
  function removeMessagePair(conversationId, pairId) {
    if (!conversationId || !pairId) return false
    
    const convData = conversationMessages.value.get(conversationId)
    if (!convData) return false
    
    const index = convData.messagePairs.findIndex(p => p.id === pairId)
    if (index !== -1) {
      convData.messagePairs.splice(index, 1)
      convData.lastUpdated = Date.now()
      return true
    }
    return false
  }
  
  /**
   * 删除指定消息
   */
  function removeMessage(conversationId, messageId) {
    if (!conversationId || !messageId) return false
    
    const convData = conversationMessages.value.get(conversationId)
    if (!convData) return false
    
    // 查找并删除消息对中的消息
    for (let i = convData.messagePairs.length - 1; i >= 0; i--) {
      const pair = convData.messagePairs[i]
      
      if (pair.userMessage?.id === messageId) {
        // 删除整个对（包括AI回复）
        convData.messagePairs.splice(i, 1)
        convData.lastUpdated = Date.now()
        return true
      }
      
      if (pair.assistantMessage?.id === messageId) {
        // 只删除AI消息，保留用户消息
        pair.assistantMessage = null
        pair.status = 'pending'
        convData.lastUpdated = Date.now()
        return true
      }
    }
    
    // 查找孤儿消息
    const orphanIndex = convData.orphanMessages.findIndex(m => m.id === messageId)
    if (orphanIndex !== -1) {
      convData.orphanMessages.splice(orphanIndex, 1)
      convData.lastUpdated = Date.now()
      return true
    }
    
    return false
  }
  
  /**
   * 开始流式响应
   */
  function startStreaming(conversationId, userMessageId, assistantMessageId) {
    if (!conversationId) return
    
    streamingStates.value.set(conversationId, {
      isStreaming: true,
      userMessageId,
      assistantMessageId,
      content: '',
      thinking: '',
      thinkingDuration: 0,
      sources: [],
      startedAt: Date.now()
    })
    
    // 更新消息对状态
    const convData = conversationMessages.value.get(conversationId)
    if (convData) {
      const pair = convData.messagePairs.find(p => 
        p.userMessage?.id === userMessageId
      )
      if (pair) {
        pair.status = 'streaming'
      }
    }
  }
  
  /**
   * 更新流式响应内容
   */
  function updateStreamingContent(conversationId, content) {
    const state = streamingStates.value.get(conversationId)
    if (state) {
      state.content = content
    }
  }
  
  /**
   * 更新流式思考内容
   */
  function updateStreamingThinking(conversationId, thinking) {
    const state = streamingStates.value.get(conversationId)
    if (state) {
      state.thinking = thinking
    }
  }
  
  /**
   * 更新流式来源
   */
  function updateStreamingSources(conversationId, sources) {
    const state = streamingStates.value.get(conversationId)
    if (state) {
      state.sources = sources
    }
  }
  
  /**
   * 标记思考开始
   */
  function markThinkingStarted(conversationId) {
    const state = streamingStates.value.get(conversationId)
    if (state) {
      state.isThinking = true
      state.thinkingStartedAt = Date.now()
    }
  }
  
  /**
   * 标记思考结束
   */
  function markThinkingEnded(conversationId, duration) {
    const state = streamingStates.value.get(conversationId)
    if (state) {
      state.isThinking = false
      state.thinkingDuration = duration
    }
  }
  
  /**
   * 完成流式响应
   */
  function completeStreaming(conversationId, result = {}) {
    const state = streamingStates.value.get(conversationId)
    if (state) {
      state.isStreaming = false
      state.completedAt = Date.now()
      
      // 更新消息对状态
      const convData = conversationMessages.value.get(conversationId)
      if (convData && state.userMessageId) {
        const pair = convData.messagePairs.find(p => 
          p.userMessage?.id === state.userMessageId
        )
        if (pair) {
          pair.status = 'completed'
          if (pair.assistantMessage) {
            pair.assistantMessage.isStreaming = false
            pair.assistantMessage.loading = false
          }
        }
      }
      
      // 延迟清理流式状态
      setTimeout(() => {
        streamingStates.value.delete(conversationId)
      }, 5000)
    }
  }
  
  /**
   * 中止流式响应
   */
  function abortStreaming(conversationId) {
    const state = streamingStates.value.get(conversationId)
    if (state) {
      state.isStreaming = false
      state.isAborted = true
      
      // 更新消息对状态
      const convData = conversationMessages.value.get(conversationId)
      if (convData && state.userMessageId) {
        const pair = convData.messagePairs.find(p => 
          p.userMessage?.id === state.userMessageId
        )
        if (pair) {
          pair.status = 'completed'
          if (pair.assistantMessage) {
            pair.assistantMessage.isStreaming = false
            pair.assistantMessage.loading = false
            pair.assistantMessage.interrupted = true
          }
        }
      }
    }
  }
  
  /**
   * 删除对话的所有消息
   */
  function clearConversation(conversationId) {
    if (!conversationId) return
    
    conversationMessages.value.delete(conversationId)
    streamingStates.value.delete(conversationId)
  }
  
  /**
   * 清理所有数据
   */
  function clearAll() {
    conversations.value = []
    currentConversationId.value = null
    conversationMessages.value.clear()
    streamingStates.value.clear()
  }

  return {
    // State
    conversations,
    currentConversationId,
    conversationMessages,
    streamingStates,
    
    // Getters
    currentMessages,
    getConversationMessages,
    hasActiveStreaming,
    currentStreamingState,
    
    // Actions
    setConversations,
    setCurrentConversation,
    initConversationStorage,
    addUserMessage,
    addAssistantMessage,
    updateAssistantMessage,
    syncMessagesFromServer,
    removeMessagePair,
    removeMessage,
    startStreaming,
    updateStreamingContent,
    updateStreamingThinking,
    updateStreamingSources,
    markThinkingStarted,
    markThinkingEnded,
    completeStreaming,
    abortStreaming,
    clearConversation,
    clearAll
  }
})
