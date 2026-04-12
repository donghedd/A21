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
