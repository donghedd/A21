/**
 * Export Utilities
 * Functions for exporting conversations in various formats
 */

import { saveAs } from 'file-saver'

const textEncoder = new TextEncoder()

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

function createCrc32Table() {
  const table = new Uint32Array(256)
  for (let i = 0; i < 256; i += 1) {
    let c = i
    for (let j = 0; j < 8; j += 1) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1)
    }
    table[i] = c >>> 0
  }
  return table
}

const CRC32_TABLE = createCrc32Table()

function crc32(bytes) {
  let crc = 0xFFFFFFFF
  for (const byte of bytes) {
    crc = CRC32_TABLE[(crc ^ byte) & 0xFF] ^ (crc >>> 8)
  }
  return (crc ^ 0xFFFFFFFF) >>> 0
}

function toDosDateTime(inputDate = new Date()) {
  const date = inputDate instanceof Date ? inputDate : new Date(inputDate)
  const year = Math.max(1980, date.getFullYear())
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const seconds = Math.floor(date.getSeconds() / 2)

  const dosTime = (hours << 11) | (minutes << 5) | seconds
  const dosDate = ((year - 1980) << 9) | (month << 5) | day

  return { dosTime, dosDate }
}

function writeUint16(view, offset, value) {
  view.setUint16(offset, value, true)
}

function writeUint32(view, offset, value) {
  view.setUint32(offset, value, true)
}

function sanitizeZipEntryName(filename, fallbackIndex) {
  const base = (filename || `conversation-${fallbackIndex}`).replace(/[\\/:*?"<>|]/g, '_').trim()
  return (base || `conversation-${fallbackIndex}`) + '.md'
}

function createZipBlob(files, zipName = 'conversations.zip') {
  const localChunks = []
  const centralChunks = []
  let localOffset = 0

  files.forEach((file, index) => {
    const fileName = sanitizeZipEntryName(file.name, index + 1)
    const fileNameBytes = textEncoder.encode(fileName)
    const contentBytes = textEncoder.encode(file.content || '')
    const crc = crc32(contentBytes)
    const { dosTime, dosDate } = toDosDateTime(file.updatedAt || new Date())

    const localHeader = new ArrayBuffer(30)
    const localView = new DataView(localHeader)
    writeUint32(localView, 0, 0x04034b50)
    writeUint16(localView, 4, 20)
    writeUint16(localView, 6, 0x0800)
    writeUint16(localView, 8, 0)
    writeUint16(localView, 10, dosTime)
    writeUint16(localView, 12, dosDate)
    writeUint32(localView, 14, crc)
    writeUint32(localView, 18, contentBytes.length)
    writeUint32(localView, 22, contentBytes.length)
    writeUint16(localView, 26, fileNameBytes.length)
    writeUint16(localView, 28, 0)

    localChunks.push(localHeader, fileNameBytes, contentBytes)

    const centralHeader = new ArrayBuffer(46)
    const centralView = new DataView(centralHeader)
    writeUint32(centralView, 0, 0x02014b50)
    writeUint16(centralView, 4, 20)
    writeUint16(centralView, 6, 20)
    writeUint16(centralView, 8, 0x0800)
    writeUint16(centralView, 10, 0)
    writeUint16(centralView, 12, dosTime)
    writeUint16(centralView, 14, dosDate)
    writeUint32(centralView, 16, crc)
    writeUint32(centralView, 20, contentBytes.length)
    writeUint32(centralView, 24, contentBytes.length)
    writeUint16(centralView, 28, fileNameBytes.length)
    writeUint16(centralView, 30, 0)
    writeUint16(centralView, 32, 0)
    writeUint16(centralView, 34, 0)
    writeUint16(centralView, 36, 0)
    writeUint32(centralView, 38, 0)
    writeUint32(centralView, 42, localOffset)

    centralChunks.push(centralHeader, fileNameBytes)
    localOffset += 30 + fileNameBytes.length + contentBytes.length
  })

  const centralSize = centralChunks.reduce((sum, chunk) => sum + chunk.byteLength, 0)
  const endHeader = new ArrayBuffer(22)
  const endView = new DataView(endHeader)
  writeUint32(endView, 0, 0x06054b50)
  writeUint16(endView, 4, 0)
  writeUint16(endView, 6, 0)
  writeUint16(endView, 8, files.length)
  writeUint16(endView, 10, files.length)
  writeUint32(endView, 12, centralSize)
  writeUint32(endView, 16, localOffset)
  writeUint16(endView, 20, 0)

  return {
    blob: new Blob([...localChunks, ...centralChunks, endHeader], { type: 'application/zip' }),
    filename: zipName.endsWith('.zip') ? zipName : `${zipName}.zip`
  }
}

export function exportMarkdownZip(files, zipName = 'conversations.zip') {
  const { blob, filename } = createZipBlob(files, zipName)
  saveAs(blob, filename)
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
