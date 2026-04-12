<template>
  <div class="tech-kg-page">
    <div v-if="kgUnavailable" class="kg-unavailable">
      <el-result
        icon="warning"
        title="技术图谱当前不可用"
        :sub-title="kgUnavailableMessage"
      />
    </div>

    <template v-else>
      <FilterBar
        v-model:keyword="searchKeyword"
        v-model:depth="depth"
        v-model:relation-type="relationType"
        :depth-options="depthOptions"
        :relation-options="relationOptions"
        :loading="loading"
        @search="handleSearch"
        @center="handleCenterGraph"
        @zoom="handleZoomGraph"
        @reset="handleResetView"
      />

      <div class="content-shell">
        <div class="graph-panel">
          <GraphChart
            ref="graphRef"
            :nodes="displayNodes"
            :edges="displayEdges"
            :active-node="detailNode"
            @node-click="handleNodeClick"
            @close-detail="handleCloseDetail"
          />
        </div>

        <div class="resource-panel">
          <PaperTable :paper-list="paperList" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import FilterBar from './components/FilterBar.vue'
import GraphChart from './components/GraphChart.vue'
import PaperTable from './components/PaperTable.vue'
import * as kgApi from '@/api/kg'

const relationOptions = [
  'HAS_FAULT',
  'CAUSED_BY',
  'HAS_SYMPTOM',
  'RESOLVED_BY',
  'TARGETS',
  'AFFECTS_PARAMETER',
  'SHOWS_AS',
  'HAS_COMPONENT',
  'COVERS'
]

const depthOptions = [1, 2, 3]

const allNodes = ref([])
const allEdges = ref([])
const currentNodeData = ref(null)
const detailNode = ref(null)
const paperList = ref([])
const graphRef = ref(null)
const loading = ref(false)
const searchKeyword = ref('')
const relationType = ref('')
const depth = ref(Number(import.meta.env.VITE_KG_TECH_MAX_DEPTH || 2))

const kgHealth = ref(null)
const kgUnavailable = ref(false)
const kgUnavailableMessage = ref('请检查技术图谱服务配置。')

const nodeRelationsCache = ref(new Map())
const nodeResourcesCache = ref(new Map())

const displayNodes = computed(() => {
  if (currentNodeData.value) {
    const cached = nodeRelationsCache.value.get(buildRelationCacheKey(currentNodeData.value.id))
    return cached ? cached.nodes : []
  }
  if (searchKeyword.value.trim()) {
    const keyword = searchKeyword.value.trim().toLowerCase()
    return allNodes.value.filter(node => node.name.toLowerCase().includes(keyword))
  }
  return allNodes.value
})

const displayEdges = computed(() => {
  if (currentNodeData.value) {
    const cached = nodeRelationsCache.value.get(buildRelationCacheKey(currentNodeData.value.id))
    return cached ? cached.edges : []
  }
  if (searchKeyword.value.trim()) {
    const nodeIds = new Set(displayNodes.value.map(node => node.id))
    return allEdges.value.filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  }
  return allEdges.value
})

function normalizeTechNode(node = {}, index = 0) {
  const labels = node.labels || []
  const properties = node.properties || {}
  const name = node.name || node.text || properties.name || '未知节点'
  const degree = Number(node.degree || node.metrics?.citationCount || 0)
  const totalPapers = Number(node.totalPapers || node.metrics?.paperCount || 0)
  return {
    id: String(node.id),
    name,
    category: node.category || labels[0] || '知识实体',
    level: node.level || (index < 5 ? '核心' : '普通'),
    description: node.description || properties.description || properties.summary || properties.definition || `图谱节点：${name}`,
    metrics: {
      paperCount: totalPapers,
      citationCount: Number(node.metrics?.citationCount || degree),
      hIndex: Number(node.metrics?.hIndex || Math.max(0, Math.min(degree, 12)))
    },
    keywordId: node.keywordId || node.id,
    labels,
    properties,
    degree,
    totalPapers
  }
}

function normalizeEdge(edge = {}) {
  return {
    id: edge.id || `${edge.source}-${edge.target}-${edge.type || edge.relationType || '关联'}`,
    source: String(edge.source),
    target: String(edge.target),
    type: edge.type || edge.relationType || '关联',
    properties: edge.properties || { weight: edge.weight || edge.strength || 1 }
  }
}

function buildRelationCacheKey(nodeId) {
  return `${nodeId}|${depth.value}|${relationType.value || 'all'}`
}

async function loadKeywordsAsNodes(keyword) {
  try {
    loading.value = true
    allNodes.value = []
    allEdges.value = []
    paperList.value = []
    currentNodeData.value = null
    detailNode.value = null
    nodeRelationsCache.value.clear()

    const res = await kgApi.searchTechKG({
      q: keyword || undefined,
      page: 1,
      size: Number(import.meta.env.VITE_KG_TECH_PAGE_SIZE || 50)
    })

    let keywordsData = []
    let rawData = res
    if (res && res.data) rawData = res.data

    if (Array.isArray(rawData)) {
      keywordsData = rawData
    } else if (rawData && typeof rawData === 'object') {
      if (Array.isArray(rawData.list)) keywordsData = rawData.list
      else if (Array.isArray(rawData.records)) keywordsData = rawData.records
    }

    if (!keywordsData.length) {
      ElMessage.warning('未找到相关节点')
      return
    }

    allNodes.value = keywordsData.map((item, index) => normalizeTechNode(item, index))
    allEdges.value = []
  } catch (error) {
    console.error('加载技术关键词失败:', error)
    ElMessage.error('技术图谱数据加载失败')
  } finally {
    loading.value = false
  }
}

function processResourceResponse(resources = []) {
  return resources.map(item => ({
    id: item.id,
    title: item.title || '未命名资料',
    journal: item.journal || '本地图谱来源',
    year: item.year,
    link: item.url || '',
    url: item.url || ''
  }))
}

async function updatePaperListByNode(node) {
  const nodeId = String(node.id)

  if (nodeResourcesCache.value.has(nodeId)) {
    paperList.value = nodeResourcesCache.value.get(nodeId)
    return
  }

  try {
    const res = await kgApi.getTechResources(nodeId)
    const resourceList = processResourceResponse(res.data || [])
    nodeResourcesCache.value.set(nodeId, resourceList)
    paperList.value = resourceList
  } catch (error) {
    console.error('获取关联资料失败:', error)
    paperList.value = []
  }
}

async function loadNodeRelations(centerNode) {
  try {
    const relationKey = buildRelationCacheKey(centerNode.id)
    if (nodeRelationsCache.value.has(relationKey)) {
      await updatePaperListByNode(centerNode)
      return
    }

    let graphData = null
    if (!relationType.value && Number(depth.value) > 1) {
      const graphRes = await kgApi.getTechVisualize({
        q: centerNode.name,
        depth: Number(depth.value)
      })
      graphData = graphRes.data
    } else {
      const relationRes = await kgApi.getTechRelations(centerNode.id, {
        relation_type: relationType.value || undefined
      })
      graphData = relationRes.data
    }

    const apiNodes = Array.isArray(graphData?.nodes) ? graphData.nodes : []
    const apiEdges = Array.isArray(graphData?.edges) ? graphData.edges : []

    const normalizedCenter = normalizeTechNode(centerNode)
    const nodeMap = new Map([[normalizedCenter.id, normalizedCenter]])

    apiNodes.forEach((item, index) => {
      const normalized = normalizeTechNode(item, index)
      nodeMap.set(normalized.id, normalized)
    })

    const nodes = Array.from(nodeMap.values())
    let edges = apiEdges.map(item => normalizeEdge(item))

    if (!edges.length && nodes.length > 1) {
      edges = nodes
        .filter(node => node.id !== normalizedCenter.id)
        .map(node => normalizeEdge({
          source: normalizedCenter.id,
          target: node.id,
          relationType: '关联',
          strength: 1
        }))
    }

    nodeRelationsCache.value.set(relationKey, {
      nodes,
      edges
    })

    await updatePaperListByNode(normalizedCenter)
  } catch (error) {
    console.error('获取节点关联失败:', error)
    ElMessage.error('获取节点关联关系失败')
    nodeRelationsCache.value.set(buildRelationCacheKey(centerNode.id), {
      nodes: [normalizeTechNode(centerNode)],
      edges: []
    })
    paperList.value = []
  }
}

async function loadNodeDetail(node) {
  try {
    const res = await kgApi.getKGNode(node.id)
    return normalizeTechNode({ ...node, ...(res.data || {}) })
  } catch (error) {
    return normalizeTechNode(node)
  }
}

async function handleNodeClick(node) {
  const normalized = normalizeTechNode(node)
  const detail = await loadNodeDetail(normalized)
  currentNodeData.value = detail
  detailNode.value = detail
  await loadNodeRelations(detail)
}

async function handleSearch() {
  await loadKeywordsAsNodes(searchKeyword.value.trim())
}

async function handleResetView() {
  currentNodeData.value = null
  detailNode.value = null
  paperList.value = []
  relationType.value = ''
  await loadKeywordsAsNodes()
  ElMessage.info('已重置视图')
}

function handleCenterGraph() {
  graphRef.value?.handleCenter()
}

function handleZoomGraph() {
  graphRef.value?.handleZoom()
}

function handleCloseDetail() {
  detailNode.value = null
}

async function loadKGHealth() {
  try {
    const res = await kgApi.getKGHealth()
    kgHealth.value = res.data

    if (!res.data?.enabled) {
      kgUnavailable.value = true
      kgUnavailableMessage.value = '后端配置中 KG_ENABLED=false，技术图谱未启用。'
      return
    }

    if (!res.data?.connected) {
      kgUnavailable.value = true
      kgUnavailableMessage.value = `Neo4j 连接失败：${res.data?.error || '未知错误'}`
      return
    }

    kgUnavailable.value = false
  } catch (error) {
    kgUnavailable.value = true
    kgUnavailableMessage.value = error?.message || '技术图谱健康检查失败'
  }
}

watch([relationType, depth], async () => {
  if (currentNodeData.value) {
    nodeRelationsCache.value.delete(buildRelationCacheKey(currentNodeData.value.id))
    await loadNodeRelations(currentNodeData.value)
  }
})

onMounted(async () => {
  if (import.meta.env.VITE_ENABLE_KG !== 'true') {
    kgUnavailable.value = true
    kgUnavailableMessage.value = '前端图谱开关未开启，请将 VITE_ENABLE_KG 设为 true。'
    return
  }

  await loadKGHealth()
  if (!kgUnavailable.value) {
    await loadKeywordsAsNodes()
  }
})
</script>

<style scoped lang="scss">
.tech-kg-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 20px 20px;
  background:
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.08), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
}

.content-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.graph-panel {
  flex: 1;
  min-height: 0;
}

.resource-panel {
  height: 256px;
  flex-shrink: 0;
}

.kg-unavailable {
  flex: 1;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.94);
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.92);
}

@media (max-width: 760px) {
  .tech-kg-page {
    padding: 12px;
  }

  .resource-panel {
    height: 320px;
  }
}
</style>
