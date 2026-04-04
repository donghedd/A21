import request from '@/utils/request'

/**
 * Get user's knowledge bases
 */
export function getKnowledgeBases() {
  return request.get('/knowledge/')
}

/**
 * Create knowledge base
 */
export function createKnowledgeBase(data) {
  return request.post('/knowledge/', data)
}

/**
 * Get knowledge base details
 */
export function getKnowledgeBase(id) {
  return request.get(`/knowledge/${id}`)
}

/**
 * Update knowledge base
 */
export function updateKnowledgeBase(id, data) {
  return request.put(`/knowledge/${id}`, data)
}

/**
 * Delete knowledge base
 */
export function deleteKnowledgeBase(id) {
  return request.delete(`/knowledge/${id}`)
}

/**
 * Get knowledge base files
 */
export function getKnowledgeBaseFiles(id) {
  return request.get(`/knowledge/${id}/files`)
}
