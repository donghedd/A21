import request from '@/utils/request'

export function getUsers(params = {}) {
  return request.get('/admin/users', { params })
}

export function updateUserRole(userId, role) {
  return request.put(`/admin/users/${userId}/role`, { role })
}

export function resetUserPassword(userId, newPassword) {
  return request.post(`/admin/users/${userId}/reset-password`, { new_password: newPassword })
}

export function deleteUser(userId) {
  return request.delete(`/admin/users/${userId}`)
}

export function searchHistoryConversations(params) {
  return request.get('/admin/history/conversations', { params })
}

export function getHistoryConversationDetail(conversationId) {
  return request.get(`/admin/history/conversations/${conversationId}`)
}

export function deleteHistoryConversation(conversationId) {
  return request.delete(`/admin/history/conversations/${conversationId}`)
}

export function getAdminKnowledgeBases(params = {}) {
  return request.get('/admin/knowledge-bases', { params })
}

export function updateAdminKnowledgeBase(id, data) {
  return request.put(`/admin/knowledge-bases/${id}`, data)
}

export function getAdminWorkspaceModels(params = {}) {
  return request.get('/admin/workspace/models', { params })
}

export function updateAdminCustomModel(id, data) {
  return request.put(`/admin/workspace/custom-models/${id}`, data)
}

export function updateAdminExternalModel(id, data) {
  return request.put(`/admin/workspace/external-models/${id}`, data)
}
