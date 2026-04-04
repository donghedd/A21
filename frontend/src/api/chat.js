import request from '@/utils/request'
import { getToken } from '@/utils/storage'

const API_BASE = '/api'

/**
 * Get conversation list with pagination
 */
export function getConversations(params = {}) {
  return request.get('/chat/conversations', { params })
}

/**
 * Create new conversation
 */
export function createConversation(data = {}) {
  return request.post('/chat/conversations', data)
}

/**
 * Get conversation details with messages
 */
export function getConversation(id) {
  return request.get(`/chat/conversations/${id}`)
}

/**
 * Update conversation
 */
export function updateConversation(id, data) {
  return request.put(`/chat/conversations/${id}`, data)
}

/**
 * Delete conversation
 */
export function deleteConversation(id) {
  return request.delete(`/chat/conversations/${id}`)
}

/**
 * Copy conversation
 */
export function copyConversation(id) {
  return request.post(`/chat/conversations/${id}/copy`)
}

/**
 * Search conversations
 */
export function searchConversations(params) {
  return request.get('/chat/conversations/search', { params })
}

/**
 * Export conversation
 */
export function exportConversation(id, format = 'json') {
  return request.get(`/chat/conversations/${id}/export`, {
    params: { format }
  })
}

/**
 * Send message with SSE streaming
 * Returns EventSource-like reader
 */
export function sendMessageStream(conversationId, content, model = null, customModelId = null, signal = null) {
  const token = getToken()
  const url = `${API_BASE}/chat/conversations/${conversationId}/messages`
  
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ content, model, custom_model_id: customModelId })
  }
  if (signal) options.signal = signal
  
  return fetch(url, options)
}

/**
 * Delete a message and all subsequent messages (for edit/resend)
 */
export function deleteMessagesFrom(conversationId, messageId) {
  return request.delete(`/chat/conversations/${conversationId}/messages/${messageId}`)
}

/**
 * Regenerate last assistant response with SSE streaming
 */
export function regenerateResponse(conversationId, model = null, customModelId = null, signal = null) {
  const token = getToken()
  const url = `${API_BASE}/chat/conversations/${conversationId}/regenerate`
  
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ model, custom_model_id: customModelId })
  }
  if (signal) options.signal = signal
  
  return fetch(url, options)
}

/**
 * Parse SSE data line
 */
export function parseSSEData(line) {
  if (line.startsWith('data: ')) {
    try {
      return JSON.parse(line.slice(6))
    } catch (e) {
      return null
    }
  }
  return null
}
