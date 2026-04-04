import request from '@/utils/request'

/**
 * Get Ollama available models
 */
export function getOllamaModels() {
  return request.get('/models/ollama')
}

/**
 * Get user's custom models
 */
export function getCustomModels() {
  return request.get('/models/custom')
}

/**
 * Create custom model
 */
export function createCustomModel(data) {
  return request.post('/models/custom', data)
}

/**
 * Get custom model details
 */
export function getCustomModel(id) {
  return request.get(`/models/custom/${id}`)
}

/**
 * Update custom model
 */
export function updateCustomModel(id, data) {
  return request.put(`/models/custom/${id}`, data)
}

/**
 * Delete custom model
 */
export function deleteCustomModel(id) {
  return request.delete(`/models/custom/${id}`)
}

/**
 * Bind knowledge base to model
 */
export function bindKnowledgeBase(modelId, knowledgeBaseId) {
  return request.post(`/models/custom/${modelId}/knowledge`, {
    knowledge_base_id: knowledgeBaseId
  })
}

/**
 * Unbind knowledge base from model
 */
export function unbindKnowledgeBase(modelId, knowledgeBaseId) {
  return request.delete(`/models/custom/${modelId}/knowledge/${knowledgeBaseId}`)
}
