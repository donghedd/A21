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
        :loading="loading"
        @search="handleSearch"
        @center="handleCenterGraph"
        @reset="handleResetView"
        @settings="settingsVisible = true"
      />

      <div class="content-shell">
        <div class="graph-panel">
          <GraphChart
            ref="graphRef"
            :nodes="displayNodes"
            :edges="displayEdges"
            :active-node="detailNode"
            :focus-node-id="currentNodeData?._focusNodeId || ''"
            @node-click="handleNodeClick"
            @node-dblclick="handleNodeDblClick"
            @close-detail="handleCloseDetail"
          />
        </div>
      </div>

      <el-drawer
        v-model="settingsVisible"
        direction="rtl"
        size="340px"
        :with-header="false"
        class="settings-drawer"
      >
        <div class="drawer-body">
          <div class="drawer-title">图谱设置</div>

          <div class="drawer-block">
            <div class="drawer-label">显示关系</div>
            <el-checkbox-group v-model="selectedRelationTypes" class="drawer-grid">
              <el-checkbox v-for="item in relationOptions" :key="item" :label="item">
                {{ item }}
              </el-checkbox>
            </el-checkbox-group>
          </div>

          <div class="drawer-block">
            <div class="drawer-label">显示实体类型</div>
            <el-checkbox-group v-model="selectedEntityTypes" class="drawer-grid">
              <el-checkbox v-for="item in entityOptions" :key="item" :label="item">
                {{ item }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-drawer>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import FilterBar from './components/FilterBar.vue'
import GraphChart from './components/GraphChart.vue'
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

const allNodes = ref([])
const allEdges = ref([])
const currentNodeData = ref(null)
const detailNode = ref(null)
const graphRef = ref(null)
const loading = ref(false)
const settingsVisible = ref(false)
const searchKeyword = ref('')
const selectedRelationTypes = ref([...relationOptions])
const selectedEntityTypes = ref([])

const kgHealth = ref(null)
const kgUnavailable = ref(false)
const kgUnavailableMessage = ref('请检查技术图谱服务配置。')

const nodeRelationsCache = ref(new Map())

const entityOptions = computed(() => {
  const values = new Set()

  ;(kgHealth.value?.labels || []).forEach(item => {
    const label = item?.label
    if (label && label !== 'Book') values.add(label)
  })

  allNodes.value.forEach(node => {
    if (node.category && node.category !== 'Book') values.add(node.category)
    ;(node.labels || []).forEach(label => {
      if (label && label !== 'Book') values.add(label)
    })
  })

  return Array.from(values).sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

watch(entityOptions, options => {
  if (!options.length) return
  if (!selectedEntityTypes.value.length) {
    selectedEntityTypes.value = [...options]
    return
  }
  selectedEntityTypes.value = selectedEntityTypes.value.filter(item => options.includes(item))
  if (!selectedEntityTypes.value.length) {
    selectedEntityTypes.value = [...options]
  }
}, { immediate: true })

function filterGraph(nodes = [], edges = [], focusId = '') {
  const activeEntityTypes = new Set(selectedEntityTypes.value)
  const activeRelationTypes = new Set(selectedRelationTypes.value)

  const filteredNodes = (nodes || []).filter(node => {
    if (focusId && node.id === focusId) return true
    if (!activeEntityTypes.size) return true
    return activeEntityTypes.has(node.category || node.labels?.[0] || '')
  })

  const visibleNodeIds = new Set(filteredNodes.map(node => node.id))
  const filteredEdges = (edges || []).filter(edge => {
    const typeAllowed = !activeRelationTypes.size || activeRelationTypes.has(edge.type || edge.relationType)
    return typeAllowed && visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
  })

  const connectedNodeIds = new Set(filteredEdges.flatMap(edge => [edge.source, edge.target]))
  const finalNodes = filteredNodes.filter(node => {
    if (focusId && node.id === focusId) return true
    return !filteredEdges.length ? visibleNodeIds.has(node.id) : connectedNodeIds.has(node.id)
  })

  return {
    nodes: finalNodes,
    edges: filteredEdges
  }
}

const displayNodes = computed(() => {
  if (currentNodeData.value) {
    const cacheKey = currentNodeData.value._relationKey || buildRelationCacheKey(currentNodeData.value.id)
    const cached = nodeRelationsCache.value.get(cacheKey)
    return cached ? filterGraph(cached.nodes, cached.edges, currentNodeData.value.id).nodes : []
  }

  if (searchKeyword.value.trim()) {
    const keyword = searchKeyword.value.trim().toLowerCase()
    const nodes = allNodes.value.filter(node => node.name.toLowerCase().includes(keyword))
    return filterGraph(nodes, []).nodes
  }

  return filterGraph(allNodes.value, []).nodes
})

const displayEdges = computed(() => {
  if (currentNodeData.value) {
    const cacheKey = currentNodeData.value._relationKey || buildRelationCacheKey(currentNodeData.value.id)
    const cached = nodeRelationsCache.value.get(cacheKey)
    return cached ? filterGraph(cached.nodes, cached.edges, currentNodeData.value.id).edges : []
  }

  if (searchKeyword.value.trim()) {
    const nodeIds = new Set(displayNodes.value.map(node => node.id))
    return filterGraph([], allEdges.value).edges.filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  }

  return filterGraph([], allEdges.value).edges
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
  return `${nodeId}|all`
}

function buildDirectRelationCacheKey(nodeId) {
  return `${nodeId}|direct`
}

async function loadKeywordsAsNodes(keyword) {
  try {
    loading.value = true
    allNodes.value = []
    allEdges.value = []
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

async function loadNodeDetail(node) {
  try {
    const res = await kgApi.getKGNode(node.id)
    return normalizeTechNode({ ...node, ...(res.data || {}) })
  } catch (error) {
    return normalizeTechNode(node)
  }
}

async function loadDirectNodeRelations(centerNode) {
  const relationKey = buildDirectRelationCacheKey(centerNode.id)
  try {
    if (nodeRelationsCache.value.has(relationKey)) return relationKey

    const relationRes = await kgApi.getTechRelations(centerNode.id)
    const graphData = relationRes.data || {}
    const apiNodes = Array.isArray(graphData.nodes) ? graphData.nodes : []
    const apiEdges = Array.isArray(graphData.edges) ? graphData.edges : []

    const normalizedCenter = normalizeTechNode(centerNode)
    const nodeMap = new Map([[normalizedCenter.id, normalizedCenter]])

    apiNodes.forEach((item, index) => {
      const normalized = normalizeTechNode(item, index)
      nodeMap.set(normalized.id, normalized)
    })

    const nodes = Array.from(nodeMap.values())
    const nodeIds = new Set(nodes.map(node => node.id))
    let edges = apiEdges
      .map(item => normalizeEdge(item))
      .filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))

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

    nodeRelationsCache.value.set(relationKey, { nodes, edges })
    return relationKey
  } catch (error) {
    console.error('获取直接关联失败:', error)
    nodeRelationsCache.value.set(relationKey, {
      nodes: [normalizeTechNode(centerNode)],
      edges: []
    })
    return relationKey
  }
}

async function handleNodeClick(node) {
  const normalized = normalizeTechNode(node)
  detailNode.value = await loadNodeDetail(normalized)
}

async function handleNodeDblClick(node) {
  const normalized = normalizeTechNode(node)
  const detail = await loadNodeDetail(normalized)
  detailNode.value = detail
  const relationKey = await loadDirectNodeRelations(detail)
  currentNodeData.value = {
    ...detail,
    _relationKey: relationKey,
    _focusNodeId: detail.id
  }
  graphRef.value?.handleCenter()
}

async function handleSearch() {
  await loadKeywordsAsNodes(searchKeyword.value.trim())
}

async function handleResetView() {
  currentNodeData.value = null
  detailNode.value = null
  selectedRelationTypes.value = [...relationOptions]
  selectedEntityTypes.value = [...entityOptions.value]
  await loadKeywordsAsNodes()
  ElMessage.info('已刷新图谱')
}

function handleCenterGraph() {
  graphRef.value?.handleCenter()
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

watch([selectedRelationTypes, selectedEntityTypes], async () => {
  if (currentNodeData.value) {
    const relationKey = await loadDirectNodeRelations(currentNodeData.value)
    currentNodeData.value = {
      ...currentNodeData.value,
      _relationKey: relationKey,
      _focusNodeId: currentNodeData.value.id
    }
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
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 20px 20px;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.08), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
}

.content-shell {
  flex: 1;
  height: 100%;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.graph-panel {
  flex: 1;
  height: 100%;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.kg-unavailable {
  flex: 1;
  min-height: 0;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.94);
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.settings-drawer :deep(.el-drawer) {
  background: rgba(255, 255, 255, 0.98);
}

.drawer-body {
  padding: 24px;
}

.drawer-title {
  margin-bottom: 22px;
  color: #0f172a;
  font-size: 22px;
  font-weight: 800;
}

.drawer-block {
  margin-bottom: 28px;
}

.drawer-label {
  margin-bottom: 12px;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.drawer-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

@media (max-width: 760px) {
  .tech-kg-page {
    padding: 12px;
  }
}
</style>
