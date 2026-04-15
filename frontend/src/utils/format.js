/**
 * Format Utilities
 * Common formatting functions
 */

const BEIJING_TIME_ZONE = 'Asia/Shanghai'

function parseBackendDate(dateStr) {
  if (!dateStr) return null
  if (dateStr instanceof Date) return dateStr

  const value = String(dateStr)
  const hasTimezone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(value)
  return new Date(hasTimezone ? value : `${value}Z`)
}

/**
 * Format date to locale string
 */
export function formatDate(dateStr, options = {}) {
  if (!dateStr) return ''
  const date = parseBackendDate(dateStr)
  return date.toLocaleDateString('zh-CN', {
    timeZone: BEIJING_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...options
  })
}

/**
 * Format time to locale string
 */
export function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = parseBackendDate(dateStr)
  return date.toLocaleTimeString('zh-CN', {
    timeZone: BEIJING_TIME_ZONE,
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * Format datetime to locale string
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return ''
  const date = parseBackendDate(dateStr)
  return date.toLocaleString('zh-CN', {
    timeZone: BEIJING_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateStr) {
  if (!dateStr) return ''
  
  const date = parseBackendDate(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 7) {
    return formatDate(dateStr)
  } else if (days > 0) {
    return `${days} 天前`
  } else if (hours > 0) {
    return `${hours} 小时前`
  } else if (minutes > 0) {
    return `${minutes} 分钟前`
  } else {
    return '刚刚'
  }
}

/**
 * Format file size
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + units[i]
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text, length, suffix = '...') {
  if (!text) return ''
  if (text.length <= length) return text
  return text.slice(0, length) + suffix
}

/**
 * Format number with commas
 */
export function formatNumber(num) {
  if (num === null || num === undefined) return ''
  return num.toLocaleString('zh-CN')
}

/**
 * Format percentage
 */
export function formatPercent(value, decimals = 1) {
  if (value === null || value === undefined) return ''
  return `${(value * 100).toFixed(decimals)}%`
}

export function parseDateTime(dateStr) {
  return parseBackendDate(dateStr)
}

/**
 * Highlight search term in text
 */
export function highlightText(text, term) {
  if (!text || !term) return text
  const regex = new RegExp(`(${escapeRegExp(term)})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

/**
 * Escape special regex characters
 */
function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
