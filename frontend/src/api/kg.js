import request from '@/utils/request'

export function getKGHealth() {
  return request.get('/kg/health')
}

export function getKGBooks() {
  return request.get('/kg/books')
}

export function searchKG(params) {
  return request.get('/kg/search', { params })
}

export function getKGNode(id) {
  return request.get(`/kg/node/${encodeURIComponent(id)}`)
}

export function getKGNeighbors(id, params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      value.forEach(item => searchParams.append(key, item))
      return
    }
    searchParams.append(key, value)
  })
  return request.get(`/kg/node/${encodeURIComponent(id)}/neighbors`, { params: searchParams })
}

export function findKGPath(params) {
  return request.get('/kg/path', { params })
}

export function searchTechKG(params) {
  return request.get('/kg/tech/search', { params })
}

export function getTechRelations(id, params = {}) {
  return request.get(`/kg/tech/relations/${encodeURIComponent(id)}`, { params })
}

export function getTechVisualize(params) {
  return request.get('/kg/tech/visualize', { params })
}

export function getTechResources(id) {
  return request.get(`/kg/tech/resources/${encodeURIComponent(id)}`)
}
