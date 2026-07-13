<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type SimulationNodeDatum } from 'd3-force'
import { select } from 'd3-selection'
import { zoom, zoomIdentity, type ZoomBehavior } from 'd3-zoom'
import type { MotifGraph, MotifGraphEdge, MotifGraphNode } from '../../api/motifs'
import { useI18n } from '../../i18n'

interface LayoutNode extends MotifGraphNode, SimulationNodeDatum { x: number; y: number; radius: number }
interface LayoutEdge extends MotifGraphEdge { source: LayoutNode; target: LayoutNode }

const props = defineProps<{ graph: MotifGraph; selectedId?: string | null }>()
const emit = defineEmits<{ select: [id: string] }>()
const { t } = useI18n()

const host = ref<HTMLDivElement | null>(null)
const svg = ref<SVGSVGElement | null>(null)
const viewport = ref<SVGGElement | null>(null)
const width = ref(900)
const height = ref(620)
const nodes = ref<LayoutNode[]>([])
const edges = ref<LayoutEdge[]>([])
const hoveredId = ref<string | null>(null)
let observer: ResizeObserver | null = null
let zoomBehavior: ZoomBehavior<SVGSVGElement, unknown> | null = null
let resizeTimer: number | null = null

const neighborhood = computed(() => {
  const focus = hoveredId.value || props.selectedId
  if (!focus) return new Set<string>()
  const ids = new Set<string>([focus])
  for (const edge of props.graph.edges) {
    if (edge.source_id === focus) ids.add(edge.target_id)
    if (edge.target_id === focus) ids.add(edge.source_id)
  }
  return ids
})

function radiusFor(node: MotifGraphNode): number {
  const evidence = Math.sqrt(Math.max(0, node.excerpt_count)) * 2.6
  const relations = Math.sqrt(Math.max(0, node.relation_count ?? 0)) * 1.8
  return Math.max(13, Math.min(node.is_center ? 40 : 31, (node.is_center ? 25 : 16) + evidence + relations))
}

function buildLayout() {
  const nextNodes: LayoutNode[] = props.graph.nodes.map((node, index) => ({
    ...node,
    x: width.value / 2 + Math.cos((index / Math.max(1, props.graph.nodes.length)) * Math.PI * 2) * 80,
    y: height.value / 2 + Math.sin((index / Math.max(1, props.graph.nodes.length)) * Math.PI * 2) * 80,
    radius: radiusFor(node),
  }))
  const byId = new Map(nextNodes.map((node) => [node.id, node]))
  const nextEdges: LayoutEdge[] = props.graph.edges.flatMap((edge) => {
    const source = byId.get(edge.source_id)
    const target = byId.get(edge.target_id)
    return source && target ? [{ ...edge, source, target }] : []
  })
  const simulation = forceSimulation<LayoutNode>(nextNodes)
    .force('charge', forceManyBody<LayoutNode>().strength(-260).distanceMax(560))
    .force('center', forceCenter(width.value / 2, height.value / 2))
    .force('collide', forceCollide<LayoutNode>().radius((node) => node.radius + 38).strength(0.9))
    .force('link', forceLink<LayoutNode, LayoutEdge>(nextEdges).id((node) => node.id).distance((edge) => 130 - Math.min(42, edge.weight * 5)).strength(0.32))
    .stop()
  for (let index = 0; index < 220; index += 1) simulation.tick()
  nodes.value = nextNodes
  edges.value = nextEdges
  void nextTick(() => fitView(false))
}

function edgeOpacity(edge: LayoutEdge): number {
  const focus = hoveredId.value
  if (!focus) return props.selectedId && ![edge.source.id, edge.target.id].includes(props.selectedId) ? 0.18 : 0.58
  return [edge.source.id, edge.target.id].includes(focus) ? 0.9 : 0.08
}

function nodeOpacity(node: LayoutNode): number {
  return hoveredId.value && !neighborhood.value.has(node.id) ? 0.22 : 1
}

function edgeLabel(edge: LayoutEdge): string {
  const relation = edge.relation_type ? t(`motifs.relations.types.${edge.relation_type}`) : ''
  const evidence = t('motifs.graphEvidence', { excerpts: edge.shared_excerpts, sources: edge.shared_sources })
  return [relation, edge.relation_reason, evidence].filter(Boolean).join(' · ')
}

function edgePoint(edge: LayoutEdge, side: 'source' | 'target'): { x: number; y: number } {
  const dx = edge.target.x - edge.source.x
  const dy = edge.target.y - edge.source.y
  const distance = Math.max(1, Math.hypot(dx, dy))
  const inset = (side === 'source' ? edge.source.radius : edge.target.radius) + 5
  const sign = side === 'source' ? 1 : -1
  const node = side === 'source' ? edge.source : edge.target
  return {
    x: node.x + sign * (dx / distance) * inset,
    y: node.y + sign * (dy / distance) * inset,
  }
}

function directionMarker(edge: LayoutEdge, end: 'start' | 'end'): string | undefined {
  if (!edge.relation_type || edge.relation_direction === 'undirected' || !edge.relation_direction) return undefined
  if (end === 'end' && edge.relation_direction === 'a_to_b') return 'url(#motif-arrow)'
  if (end === 'start' && edge.relation_direction === 'b_to_a') return 'url(#motif-arrow)'
  return undefined
}

function applyTransform(transform: ReturnType<typeof zoomIdentity.translate>) {
  if (!svg.value || !zoomBehavior) return
  select(svg.value).call(zoomBehavior.transform, transform)
}

function fitView(animated = true) {
  if (!nodes.value.length || !svg.value || !zoomBehavior) return
  const minX = Math.min(...nodes.value.map((node) => node.x - node.radius - 70))
  const maxX = Math.max(...nodes.value.map((node) => node.x + node.radius + 70))
  const minY = Math.min(...nodes.value.map((node) => node.y - node.radius - 50))
  const maxY = Math.max(...nodes.value.map((node) => node.y + node.radius + 50))
  const scale = Math.max(0.32, Math.min(1.65, 0.9 / Math.max((maxX - minX) / width.value, (maxY - minY) / height.value)))
  const transform = zoomIdentity.translate(width.value / 2, height.value / 2).scale(scale).translate(-(minX + maxX) / 2, -(minY + maxY) / 2)
  if (animated) applyTransform(transform)
  else select(svg.value).call(zoomBehavior.transform, transform)
}

function zoomBy(factor: number) {
  if (!svg.value || !zoomBehavior) return
  select(svg.value).call(zoomBehavior.scaleBy, factor)
}

function centerSelected() {
  if (!svg.value || !zoomBehavior) return
  const node = nodes.value.find((item) => item.id === props.selectedId) ?? nodes.value.find((item) => item.is_center)
  if (!node) return fitView()
  applyTransform(zoomIdentity.translate(width.value / 2, height.value / 2).scale(1.25).translate(-node.x, -node.y))
}

function installZoom() {
  if (!svg.value || !viewport.value) return
  zoomBehavior = zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.25, 3.5])
    .filter((event) => !event.button && event.type !== 'dblclick')
    .on('zoom', (event) => select(viewport.value).attr('transform', event.transform.toString()))
  select(svg.value).call(zoomBehavior)
}

watch(() => props.graph, buildLayout, { deep: true })
watch(() => props.selectedId, () => {
  if (props.selectedId) centerSelected()
})

onMounted(() => {
  installZoom()
  observer = new ResizeObserver(([entry]) => {
    if (!entry) return
    width.value = Math.max(420, Math.round(entry.contentRect.width))
    height.value = Math.max(460, Math.round(entry.contentRect.height))
    if (resizeTimer) window.clearTimeout(resizeTimer)
    resizeTimer = window.setTimeout(buildLayout, 80)
  })
  if (host.value) observer.observe(host.value)
  buildLayout()
})
onBeforeUnmount(() => {
  observer?.disconnect()
  if (resizeTimer) window.clearTimeout(resizeTimer)
})

defineExpose({ fitView, centerSelected })
</script>

<template>
  <div ref="host" class="relative h-full min-h-[460px] w-full overflow-hidden bg-[#f7f8f7]" data-testid="motif-graph-canvas">
    <div class="absolute right-3 top-3 z-10 flex items-center gap-1 rounded-md border border-stone-200 bg-white/95 p-1 shadow-sm" data-tour="motif-graph-controls">
      <button type="button" class="h-8 w-8 rounded text-lg text-stone-700 hover:bg-stone-100" :title="t('motifs.zoomIn')" :aria-label="t('motifs.zoomIn')" @click="zoomBy(1.24)">+</button>
      <button type="button" class="h-8 w-8 rounded text-lg text-stone-700 hover:bg-stone-100" :title="t('motifs.zoomOut')" :aria-label="t('motifs.zoomOut')" @click="zoomBy(0.8)">−</button>
      <button type="button" class="h-8 rounded px-2 text-xs font-medium text-stone-700 hover:bg-stone-100" :title="t('motifs.fitView')" @click="fitView()">{{ t('motifs.fit') }}</button>
      <button type="button" class="h-8 rounded px-2 text-xs font-medium text-stone-700 hover:bg-stone-100" :title="t('motifs.centerSelected')" @click="centerSelected">{{ t('motifs.center') }}</button>
    </div>
    <svg ref="svg" class="h-full w-full cursor-grab active:cursor-grabbing" :viewBox="`0 0 ${width} ${height}`" role="img" :aria-label="t('motifs.graphAria')">
      <defs>
        <marker id="motif-arrow" viewBox="0 -5 10 10" refX="9" refY="0" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,-5L10,0L0,5" fill="#64748b" /></marker>
      </defs>
      <g ref="viewport">
        <g aria-hidden="true">
          <line v-for="edge in edges" :key="`${edge.source_id}:${edge.target_id}`" :x1="edgePoint(edge, 'source').x" :y1="edgePoint(edge, 'source').y" :x2="edgePoint(edge, 'target').x" :y2="edgePoint(edge, 'target').y" :stroke="edge.relation_type ? '#64748b' : '#a8a29e'" :stroke-width="Math.min(4, 1 + Math.log2(edge.weight + 1))" :opacity="edgeOpacity(edge)" :marker-end="directionMarker(edge, 'end')" :marker-start="directionMarker(edge, 'start')" vector-effect="non-scaling-stroke"><title>{{ edgeLabel(edge) }}</title></line>
        </g>
        <g v-for="node in nodes" :key="node.id" :transform="`translate(${node.x}, ${node.y})`" :opacity="nodeOpacity(node)" class="cursor-pointer" role="button" tabindex="0" :aria-label="node.name" @mouseenter="hoveredId = node.id" @mouseleave="hoveredId = null" @click.stop="emit('select', node.id)" @keydown.enter.prevent="emit('select', node.id)" @keydown.space.prevent="emit('select', node.id)">
          <circle :r="node.radius + (node.id === selectedId ? 5 : 0)" :fill="node.needs_enrichment ? '#fafaf9' : node.pinned ? '#fef3c7' : node.id === selectedId ? '#ccfbf1' : '#ffffff'" :stroke="node.id === selectedId ? '#0f766e' : node.pinned ? '#d97706' : '#78716c'" :stroke-width="node.id === selectedId ? 3 : 1.5" :stroke-dasharray="node.needs_enrichment ? '4 3' : undefined" vector-effect="non-scaling-stroke" />
          <circle v-if="node.excerpt_count" :r="Math.max(2.5, Math.min(5, 2 + Math.sqrt(node.excerpt_count)))" :cx="node.radius * 0.62" :cy="-node.radius * 0.62" fill="#0f766e" />
          <text text-anchor="middle" :y="node.radius + 20" class="select-none fill-stone-800 text-[13px] font-semibold" style="paint-order: stroke; stroke: #f7f8f7; stroke-width: 5px; stroke-linejoin: round">{{ node.name }}</text>
          <text v-if="node.needs_enrichment" text-anchor="middle" y="4" class="select-none fill-stone-500 text-[10px]">{{ t('motifs.needsEnrichmentShort') }}</text>
        </g>
      </g>
    </svg>
    <div v-if="!nodes.length" class="absolute inset-0 flex items-center justify-center text-sm text-stone-500">{{ t('motifs.emptyGraph') }}</div>
  </div>
</template>
