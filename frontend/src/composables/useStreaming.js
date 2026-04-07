import { ref } from 'vue'
import { parseSSEData } from '@/api/chat'

/**
 * Composable for handling SSE streaming responses
 * Supports thinking process with duration tracking and abort
 */
export function useStreaming() {
  const isStreaming = ref(false)
  const currentContent = ref('')
  const thinkingContent = ref('')
  const isThinking = ref(false)
  const thinkingDuration = ref(0)
  const sources = ref([])
  const error = ref(null)
  const status = ref('')
  const isAborted = ref(false)

  // Abort support
  let abortController = null
  let currentReader = null

  /**
   * Create a new AbortController for the next stream
   * @returns {AbortSignal}
   */
  function createAbortSignal() {
    abortController = new AbortController()
    return abortController.signal
  }

  /**
   * Abort the current streaming
   */
  function abort() {
    const reader = currentReader
    const controller = abortController
    currentReader = null
    abortController = null
    isStreaming.value = false
    isThinking.value = false
    isAborted.value = true

    if (reader) {
      reader.cancel().catch(() => {})
    }
    if (controller) {
      try { controller.abort() } catch (e) { /* already aborted */ }
    }
  }

  /**
   * Process a fetch response as SSE stream
   * @param {Response} response - Fetch response object
   * @param {Object} callbacks - Event callbacks
   */
  async function processStream(response, callbacks = {}) {
    const {
      onContent,
      onThinking,
      onThinkingStart,
      onThinkingEnd,
      onSources,
      onStatus,
      onDone,
      onError
    } = callbacks

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMsg = errorData.message || `HTTP error ${response.status}`
      error.value = errorMsg
      onError?.(errorMsg)
      return
    }

    isStreaming.value = true
    isAborted.value = false
    currentContent.value = ''
    thinkingContent.value = ''
    isThinking.value = false
    thinkingDuration.value = 0
    sources.value = []
    error.value = null

    const reader = response.body.getReader()
    currentReader = reader
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        
        // Process complete lines
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.trim()) continue
          
          const data = parseSSEData(line)
          if (!data) continue

          switch (data.type) {
            case 'content':
              currentContent.value += data.content
              onContent?.(data.content, currentContent.value)
              break
              
            case 'thinking_start':
              isThinking.value = true
              thinkingDuration.value = 0
              onThinkingStart?.()
              break
              
            case 'thinking':
              thinkingContent.value += data.content
              onThinking?.(data.content, thinkingContent.value)
              break
              
            case 'thinking_end':
              isThinking.value = false
              thinkingDuration.value = data.duration || 0
              onThinkingEnd?.(data.duration || 0)
              break
              
            case 'sources':
              sources.value = data.sources || []
              onSources?.(sources.value)
              break
              
            case 'status':
              status.value = data.message
              onStatus?.(data.message)
              break
              
            case 'done':
              onDone?.({
                content: currentContent.value,
                thinking: thinkingContent.value,
                thinkingDuration: data.thinking_duration || thinkingDuration.value,
                sources: data.sources || sources.value,
                messageId: data.message_id,
                userMessageId: data.user_message_id
              })
              break
              
            case 'error':
              error.value = data.message
              onError?.(data.message)
              break
          }
        }
      }
    } catch (e) {
      if (e.name === 'AbortError' || isAborted.value) {
        onDone?.({
          content: currentContent.value,
          thinking: thinkingContent.value,
          thinkingDuration: thinkingDuration.value,
          sources: sources.value,
          messageId: null,
          userMessageId: null,
          aborted: true
        })
        return
      } else {
        error.value = e.message
        onError?.(e.message)
      }
    } finally {
      currentReader = null
      isStreaming.value = false
      isThinking.value = false
    }
  }

  /**
   * Reset streaming state
   */
  function reset() {
    isStreaming.value = false
    currentContent.value = ''
    thinkingContent.value = ''
    isThinking.value = false
    thinkingDuration.value = 0
    sources.value = []
    error.value = null
    status.value = ''
    isAborted.value = false
    abortController = null
    currentReader = null
  }

  return {
    isStreaming,
    isAborted,
    currentContent,
    thinkingContent,
    isThinking,
    thinkingDuration,
    sources,
    error,
    status,
    processStream,
    createAbortSignal,
    abort,
    reset
  }
}
