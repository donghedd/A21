/**
 * Export Utilities
 * Functions for exporting conversations in various formats
 */

import { saveAs } from 'file-saver'

/**
 * Export data as JSON file
 */
export function exportAsJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json;charset=utf-8'
  })
  saveAs(blob, `${filename}.json`)
}

/**
 * Export data as plain text file
 */
export function exportAsText(content, filename) {
  const blob = new Blob([content], {
    type: 'text/plain;charset=utf-8'
  })
  saveAs(blob, `${filename}.txt`)
}

/**
 * Export data as Markdown file
 */
export function exportAsMarkdown(content, filename) {
  const blob = new Blob([content], {
    type: 'text/markdown;charset=utf-8'
  })
  saveAs(blob, `${filename}.md`)
}

/**
 * Format conversation for text export
 */
export function formatConversationAsText(conversation, messages) {
  const lines = []
  lines.push(`# ${conversation.title}`)
  lines.push(`Exported: ${new Date().toISOString()}`)
  lines.push('-'.repeat(50))
  lines.push('')
  
  for (const msg of messages) {
    const role = msg.role.toUpperCase()
    const time = msg.created_at ? new Date(msg.created_at).toLocaleString() : ''
    lines.push(`[${role}] (${time})`)
    lines.push(msg.content)
    lines.push('')
  }
  
  return lines.join('\n')
}

/**
 * Format conversation for Markdown export
 */
export function formatConversationAsMarkdown(conversation, messages) {
  const lines = []
  lines.push(`# ${conversation.title}`)
  lines.push('')
  lines.push(`*Exported: ${new Date().toISOString()}*`)
  lines.push('')
  lines.push('---')
  lines.push('')
  
  for (const msg of messages) {
    if (msg.role === 'user') {
      lines.push('### You')
    } else if (msg.role === 'assistant') {
      lines.push('### Assistant')
    } else {
      lines.push(`### ${msg.role}`)
    }
    lines.push('')
    lines.push(msg.content)
    lines.push('')
    
    if (msg.sources?.length) {
      lines.push('**Sources:**')
      for (const src of msg.sources) {
        const preview = src.content?.slice(0, 100) || ''
        lines.push(`- [${src.index}] ${preview}...`)
      }
      lines.push('')
    }
  }
  
  return lines.join('\n')
}

/**
 * Download a blob from URL
 */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
