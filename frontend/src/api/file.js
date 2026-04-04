import request from '@/utils/request'
import { getToken } from '@/utils/storage'

const API_BASE = '/api'

/**
 * Upload file to knowledge base
 */
export function uploadFile(file, knowledgeBaseId, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('knowledge_base_id', knowledgeBaseId)
  
  return request.post('/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }
  })
}

/**
 * Get file processing status
 */
export function getFileStatus(fileId) {
  return request.get(`/files/${fileId}/status`)
}

/**
 * Delete file
 */
export function deleteFile(fileId) {
  return request.delete(`/files/${fileId}`)
}

/**
 * Reprocess file
 */
export function reprocessFile(fileId) {
  return request.post(`/files/${fileId}/reprocess`)
}

/**
 * Get file status as SSE stream
 */
export function getFileStatusStream(fileId) {
  const token = getToken()
  const url = `${API_BASE}/files/${fileId}/status/stream`
  
  return new EventSource(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
}
