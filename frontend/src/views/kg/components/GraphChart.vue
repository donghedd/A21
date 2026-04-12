<template>
  <div class="graph-chart">
    <div class="graph-stage">
      <div ref="chartRef" class="chart-canvas"></div>

      <transition name="detail-fade">
        <div v-if="currentNode" class="detail-popup">
          <div class="detail-card">
            <button class="detail-close" @click="closePopup">×</button>

            <div class="detail-head">
              <div class="detail-line"></div>
              <div>
                <div class="detail-caption">技术详情</div>
                <h3 class="detail-name">{{ currentNode.name || '未知技术' }}</h3>
              </div>
            </div>

            <div class="detail-row">
              <span class="detail-label">技术名称</span>
              <span class="detail-value">{{ currentNode.name || '未知技术' }}</span>
            </div>

            <div class="detail-row">
              <span class="detail-label">技术类型</span>
              <span class="detail-value">{{ currentNode.category || formatNodeType(currentNode.labels) }}</span>
            </div>

            <div class="detail-row">
              <span class="detail-label">详细说明</span>
              <span class="detail-value detail-text">
                {{ currentNode.description || currentNode.properties?.description || currentNode.properties?.summary || '暂无说明' }}
              </span>
            </div>

            <div class="metric-grid">
              <div class="metric-card blue">
                <div class="metric-name">资料数</div>
                <div class="metric-value">
                  {{ currentNode.totalPapers !== undefined ? currentNode.totalPapers : currentNode.metrics?.paperCount || 0 }}
                </div>
              </div>
              <div class="metric-card green">
                <div class="metric-name">关系数</div>
                <div class="metric-value">{{ currentNode.metrics?.citationCount || currentNode.degree || 0 }}</div>
              </div>
              <div class="metric-card purple">
                <div class="metric-name">中心度</div>
                <div class="metric-value">{{ currentNode.metrics?.hIndex || 0 }}</div>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  nodes: {
    type: Array,
    default: () => []
  },
  edges: {
    type: Array,
    default: () => []
  },
  activeNode: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['node-click', 'close-detail'])

const chartRef = ref(null)
const currentNode = ref(null)
let chart = null

let currentZoomScale = 1
const MIN_ZOOM = 0.8
const MAX_ZOOM = 2
const BASE_SYMBOL_SIZE = 50
const BASE_FONT_SIZE = 10
const BASE_LABEL_LINE_HEIGHT = 12

function formatNodeType(labels = []) {
  return Array.isArray(labels) && labels.length ? labels.join(' / ') : 'Entity'
}

function nodeColor(category = '') {
  const palette = {
    Device: '#409EFF',
    Fault: '#E85D75',
    Cause: '#F59E0B',
    Symptom: '#8B5CF6',
    Action: '#10B981',
    Parameter: '#06B6D4'
  }
  return palette[category] || '#409EFF'
}

function buildChartNodes() {
  const centerId = props.activeNode?.id
  return props.nodes.map((node, index) => {
    const isCenter = centerId ? node.id === centerId : index === 0
    const scale = isCenter ? 1.2 : 1
    return {
      id: node.id,
      name: node.name,
      category: node.category,
      labels: node.labels,
      description: node.description,
      metrics: node.metrics,
      totalPapers: node.totalPapers,
      properties: node.properties,
      degree: node.degree,
      symbolSize: BASE_SYMBOL_SIZE * currentZoomScale * scale,
      itemStyle: {
        color: nodeColor(node.category || node.labels?.[0]),
        borderColor: '#fff',
        borderWidth: isCenter ? 3 : 2,
        shadowBlur: isCenter ? 10 : 4,
        shadowColor: 'rgba(15, 23, 42, 0.15)'
      },
      label: {
        fontSize: BASE_FONT_SIZE * currentZoomScale + (isCenter ? 1 : 0),
        lineHeight: BASE_LABEL_LINE_HEIGHT * currentZoomScale
      },
      isCenter
    }
  })
}

function buildChartLinks() {
  const nodeIds = new Set(props.nodes.map(node => node.id))
  return props.edges
    .filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .map(edge => ({
      source: edge.source,
      target: edge.target,
      relationType: edge.type || edge.relationType || '关联',
      lineStyle: {
        color: '#A0CFFF',
        width: Math.min(3, 1.5 + Number(edge.properties?.weight || edge.weight || 1) * 0.3),
        opacity: 0.62,
        curveness: 0.1
      }
    }))
}

function renderChart() {
  if (!chart) return

  if (!props.nodes.length) {
    chart.setOption({
      graphic: {
        elements: [
          {
            type: 'text',
            left: 'center',
            top: 'center',
            style: {
              text: '暂无数据',
              fontSize: 16,
              fill: '#94A3B8'
            }
          }
        ]
      },
      series: []
    }, true)
    return
  }

  const option = {
    graphic: [],
    tooltip: {
      show: true,
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#E2E8F0',
      borderWidth: 1,
      textStyle: { color: '#334155', fontSize: 12 },
      formatter: params => {
        const data = params.data || {}
        if (params.dataType === 'edge') {
          return `<div style="font-weight:700;">关系详情</div><div style="margin-top:4px;">类型：${data.relationType || '关联关系'}</div>`
        }
        return `<div style="font-weight:700;">${data.name || '未知节点'}</div><div style="margin-top:4px;">类型：${data.category || formatNodeType(data.labels)}</div>`
      }
    },
    series: [
      {
        id: 'mainGraph',
        type: 'graph',
        layout: 'force',
        data: buildChartNodes(),
        links: buildChartLinks(),
        roam: true,
        draggable: true,
        scaleLimit: {
          min: MIN_ZOOM,
          max: MAX_ZOOM
        },
        label: {
          show: true,
          position: 'inside',
          color: '#fff',
          formatter: params => {
            const name = params.data?.name || ''
            return name.length > 4 ? `${name.slice(0, 4)}..` : name
          }
        },
        lineStyle: {
          color: '#A0CFFF',
          curveness: 0.1,
          width: 1.5,
          opacity: 0.6
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 4,
            color: '#409EFF',
            opacity: 1
          },
          itemStyle: {
            shadowBlur: 12,
            shadowColor: 'rgba(15, 23, 42, 0.25)'
          },
          label: {
            show: true,
            fontWeight: 'bold'
          }
        },
        blur: {
          itemStyle: { opacity: 0.2 },
          lineStyle: { opacity: 0.1 },
          label: { show: false }
        },
        force: {
          repulsion: 320,
          gravity: 0.05,
          edgeLength: 120,
          layoutAnimation: true
        }
      }
    ]
  }

  chart.setOption(option, true)
}

function closePopup() {
  currentNode.value = null
  emit('close-detail')
  chart?.dispatchAction({ type: 'downplay' })
}

function handleCenter() {
  if (!chart) return
  currentZoomScale = 1
  chart.dispatchAction({ type: 'restore' })
  renderChart()
}

function handleZoom() {
  if (!chart) return
  const width = chart.getWidth()
  const height = chart.getHeight()
  chart.dispatchAction({
    type: 'graphRoam',
    zoom: 1.2,
    originX: width / 2,
    originY: height / 2
  })
}

function handleResize() {
  chart?.resize()
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  renderChart()

  chart.on('graphRoam', params => {
    if (params.zoom != null) {
      let newScale = currentZoomScale * params.zoom
      if (newScale < MIN_ZOOM) newScale = MIN_ZOOM
      if (newScale > MAX_ZOOM) newScale = MAX_ZOOM
      if (Math.abs(newScale - currentZoomScale) > 0.001) {
        currentZoomScale = newScale
        renderChart()
      }
    }
  })

  chart.on('click', params => {
    if (params.dataType === 'node' && params.data) {
      currentNode.value = params.data
      emit('node-click', params.data)
    }
  })

  chart.getZr().on('click', params => {
    if (!params.target) {
      closePopup()
    }
  })
}

defineExpose({
  handleCenter,
  handleZoom
})

watch(
  () => [props.nodes, props.edges],
  () => {
    renderChart()
  },
  { deep: true }
)

watch(
  () => props.activeNode,
  value => {
    currentNode.value = value || null
    renderChart()
  },
  { immediate: true, deep: true }
)

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped lang="scss">
.graph-chart {
  height: 100%;
  background: #f8fafc;
  padding: 16px;
}

.graph-stage {
  position: relative;
  width: 100%;
  height: 100%;
  border: 2px dashed rgba(203, 213, 225, 0.9);
  border-radius: 20px;
  overflow: hidden;
  background: #f8f9fc;
}

.chart-canvas {
  width: 100%;
  height: 100%;
  min-height: 520px;
}

.detail-popup {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 320px;
  max-width: calc(100% - 32px);
  z-index: 20;
  pointer-events: none;
}

.detail-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.12);
  pointer-events: auto;
}

.detail-close {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding-right: 24px;
}

.detail-line {
  width: 4px;
  min-width: 4px;
  height: 38px;
  border-radius: 999px;
  background: linear-gradient(180deg, #2563eb 0%, #60a5fa 100%);
}

.detail-caption {
  color: #64748b;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-name {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 18px;
  line-height: 1.35;
}

.detail-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
  font-size: 13px;
  line-height: 1.7;
}

.detail-label {
  color: #475569;
  font-weight: 700;
}

.detail-value {
  color: #334155;
}

.detail-text {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  padding: 12px 8px;
  border-radius: 14px;
  text-align: center;
}

.metric-card.blue {
  background: #eff6ff;
}

.metric-card.green {
  background: #ecfdf5;
}

.metric-card.purple {
  background: #f5f3ff;
}

.metric-name {
  font-size: 11px;
  color: #64748b;
}

.metric-value {
  margin-top: 6px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 800;
}

.detail-fade-enter-active,
.detail-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.detail-fade-enter-from,
.detail-fade-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

@media (max-width: 900px) {
  .detail-popup {
    left: 16px;
    right: 16px;
    width: auto;
    max-width: none;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .detail-row {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>
