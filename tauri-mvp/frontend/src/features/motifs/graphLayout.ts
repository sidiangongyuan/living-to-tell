import type { MotifGraph, MotifGraphEdge, MotifGraphNode } from '../../api/motifs'

export interface PositionedMotifNode extends MotifGraphNode {
  x: number
  y: number
  radius: number
  labelLines: string[]
  labelBoxX: number
  labelBoxY: number
  labelBoxWidth: number
  labelBoxHeight: number
  labelTextX: number
  labelFirstLineY: number
  labelConnectorX1: number
  labelConnectorY1: number
  labelConnectorX2: number
  labelConnectorY2: number
}

export interface PositionedMotifEdge extends MotifGraphEdge {
  x1: number
  y1: number
  x2: number
  y2: number
}

export interface PositionedMotifGraph {
  nodes: PositionedMotifNode[]
  edges: PositionedMotifEdge[]
}

export interface LayoutOptions {
  width: number
  height: number
}

type LabelSide = 'top' | 'right' | 'bottom' | 'left'

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function nodeRadius(node: MotifGraphNode): number {
  const base = node.is_center ? 31 : 18
  return clamp(base + Math.sqrt(Math.max(0, node.excerpt_count)) * 3, 16, node.is_center ? 44 : 32)
}

export function densityToLimit(value: number, total: number): number {
  if (total <= 0) return 0
  const density = clamp(value, 0, 100)
  const min = Math.min(total, Math.max(1, Math.min(10, Math.ceil(Math.sqrt(total)))))
  const max = total
  return Math.round(min + (max - min) * (density / 100))
}

export function filterMotifGraphByLimit(
  graph: MotifGraph,
  limit: number,
  preferredNodeId?: string | null,
): MotifGraph {
  if (limit <= 0 || graph.nodes.length <= limit) return graph

  const degreeByNode = new Map<string, number>()
  for (const edge of graph.edges) {
    degreeByNode.set(edge.source_id, (degreeByNode.get(edge.source_id) ?? 0) + edge.weight)
    degreeByNode.set(edge.target_id, (degreeByNode.get(edge.target_id) ?? 0) + edge.weight)
  }

  const ranked = [...graph.nodes].sort((a, b) => {
    if (a.id === preferredNodeId) return -1
    if (b.id === preferredNodeId) return 1
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
    const degreeDelta = (degreeByNode.get(b.id) ?? 0) - (degreeByNode.get(a.id) ?? 0)
    if (degreeDelta !== 0) return degreeDelta
    const excerptDelta = b.excerpt_count - a.excerpt_count
    if (excerptDelta !== 0) return excerptDelta
    return a.name.localeCompare(b.name)
  })

  const visibleIds = new Set(ranked.slice(0, limit).map((node) => node.id))
  return {
    nodes: graph.nodes.filter((node) => visibleIds.has(node.id)),
    edges: graph.edges.filter((edge) => visibleIds.has(edge.source_id) && visibleIds.has(edge.target_id)),
  }
}

function splitLabel(name: string): string[] {
  const parts = name
    .split(/[｜|/]/)
    .map((part) => part.trim())
    .filter(Boolean)
  if (parts.length > 1) {
    return parts.slice(0, 2).map((part) => {
      const chars = Array.from(part)
      return chars.length > 7 ? `${chars.slice(0, 7).join('')}…` : part
    })
  }
  const sourceLines = [name.trim()]
  const lines: string[] = []
  for (const source of sourceLines) {
    const chars = Array.from(source)
    if (chars.length <= 7) {
      lines.push(source)
    } else {
      lines.push(chars.slice(0, 7).join(''))
      if (chars.length > 7) lines.push(`${chars.slice(7, 13).join('')}${chars.length > 13 ? '…' : ''}`)
    }
    if (lines.length >= 2) break
  }
  return lines.length ? lines : ['未命名']
}

function estimateLabelWidth(lines: string[]): number {
  const maxChars = Math.max(1, ...lines.map((line) => Array.from(line).length))
  return clamp(maxChars * 13 + 22, 54, 152)
}

function labelConnector(
  x: number,
  y: number,
  radius: number,
  labelBoxX: number,
  labelBoxY: number,
  labelBoxWidth: number,
  labelBoxHeight: number,
) {
  const labelCenterX = labelBoxX + labelBoxWidth / 2
  const labelCenterY = labelBoxY + labelBoxHeight / 2
  const dx = labelCenterX - x
  const dy = labelCenterY - y
  const length = Math.hypot(dx, dy) || 1
  return {
    labelConnectorX1: x + (dx / length) * (radius + 2),
    labelConnectorY1: y + (dy / length) * (radius + 2),
    labelConnectorX2: clamp(x, labelBoxX, labelBoxX + labelBoxWidth),
    labelConnectorY2: clamp(y, labelBoxY, labelBoxY + labelBoxHeight),
  }
}

function rectIntersectsCircle(
  rectX: number,
  rectY: number,
  rectWidth: number,
  rectHeight: number,
  circleX: number,
  circleY: number,
  radius: number,
): boolean {
  const nearestX = clamp(circleX, rectX, rectX + rectWidth)
  const nearestY = clamp(circleY, rectY, rectY + rectHeight)
  return (circleX - nearestX) ** 2 + (circleY - nearestY) ** 2 < (radius + 7) ** 2
}

function rectsOverlap(
  aX: number,
  aY: number,
  aWidth: number,
  aHeight: number,
  bX: number,
  bY: number,
  bWidth: number,
  bHeight: number,
  padding = 4,
): boolean {
  return !(
    aX + aWidth + padding <= bX ||
    bX + bWidth + padding <= aX ||
    aY + aHeight + padding <= bY ||
    bY + bHeight + padding <= aY
  )
}

function moveLabel(node: PositionedMotifNode, dx: number, dy: number, width: number, height: number): PositionedMotifNode {
  const labelBoxX = clamp(node.labelBoxX + dx, 10, width - node.labelBoxWidth - 10)
  const labelBoxY = clamp(node.labelBoxY + dy, 10, height - node.labelBoxHeight - 10)
  return {
    ...node,
    labelBoxX,
    labelBoxY,
    labelTextX: labelBoxX + node.labelBoxWidth / 2,
    labelFirstLineY: labelBoxY + 18,
    ...labelConnector(node.x, node.y, node.radius, labelBoxX, labelBoxY, node.labelBoxWidth, node.labelBoxHeight),
  }
}

function preferredLabelSides(
  node: MotifGraphNode,
  x: number,
  y: number,
  radius: number,
  labelBoxWidth: number,
  width: number,
  centerX: number,
  centerY: number,
): LabelSide[] {
  const dx = x - centerX
  const dy = y - centerY
  let primary: LabelSide
  if (node.is_center) {
    primary = x + radius + 22 + labelBoxWidth <= width - 10 ? 'right' : 'bottom'
  } else if (Math.abs(dx) > Math.abs(dy)) {
    primary = dx >= 0 ? 'right' : 'left'
  } else {
    primary = dy >= 0 ? 'bottom' : 'top'
  }
  const sides: LabelSide[] = [primary, 'right', 'left', 'top', 'bottom']
  return sides
    .filter((side, index, sides) => sides.indexOf(side) === index)
}

function labelRawPosition(
  side: LabelSide,
  x: number,
  y: number,
  radius: number,
  labelBoxWidth: number,
  labelBoxHeight: number,
  gap: number,
) {
  if (side === 'right') {
    return { x: x + radius + gap, y: y - labelBoxHeight / 2 }
  }
  if (side === 'left') {
    return { x: x - radius - gap - labelBoxWidth, y: y - labelBoxHeight / 2 }
  }
  if (side === 'top') {
    return { x: x - labelBoxWidth / 2, y: y - radius - gap - labelBoxHeight }
  }
  return { x: x - labelBoxWidth / 2, y: y + radius + gap }
}

function withLabelLayout(
  node: MotifGraphNode,
  x: number,
  y: number,
  radius: number,
  width: number,
  height: number,
  centerX: number,
  centerY: number,
): PositionedMotifNode {
  const labelLines = splitLabel(node.name)
  const labelBoxWidth = estimateLabelWidth(labelLines)
  const labelBoxHeight = labelLines.length * 16 + 10
  const gap = node.is_center ? 24 : 18
  const preferredSides = preferredLabelSides(node, x, y, radius, labelBoxWidth, width, centerX, centerY)
  const candidates = preferredSides.map((side, index) => {
    const raw = labelRawPosition(side, x, y, radius, labelBoxWidth, labelBoxHeight, gap)
    const labelBoxX = clamp(raw.x, 10, width - labelBoxWidth - 10)
    const labelBoxY = clamp(raw.y, 10, height - labelBoxHeight - 10)
    const boundaryShift = Math.abs(labelBoxX - raw.x) + Math.abs(labelBoxY - raw.y)
    const ownOverlap = rectIntersectsCircle(
      labelBoxX,
      labelBoxY,
      labelBoxWidth,
      labelBoxHeight,
      x,
      y,
      radius + 5,
    )
    return {
      labelBoxX,
      labelBoxY,
      score: index * 26 + boundaryShift * 2 + (ownOverlap ? 10000 : 0),
    }
  }).sort((a, b) => a.score - b.score)

  const { labelBoxX, labelBoxY } = candidates[0]
  const labelTextX = labelBoxX + labelBoxWidth / 2
  const connector = labelConnector(x, y, radius, labelBoxX, labelBoxY, labelBoxWidth, labelBoxHeight)

  return {
    ...node,
    x,
    y,
    radius,
    labelLines,
    labelBoxX,
    labelBoxY,
    labelBoxWidth,
    labelBoxHeight,
    labelTextX,
    labelFirstLineY: labelBoxY + 18,
    ...connector,
  }
}

function avoidLabelCircleCollisions(nodes: PositionedMotifNode[], width: number, height: number, centerX: number, centerY: number): PositionedMotifNode[] {
  let adjusted = nodes
  for (let pass = 0; pass < 3; pass += 1) {
    adjusted = adjusted.map((node) => {
      let current = node
      for (const other of adjusted) {
        if (other.id === current.id) continue
        if (!rectIntersectsCircle(
          current.labelBoxX,
          current.labelBoxY,
          current.labelBoxWidth,
          current.labelBoxHeight,
          other.x,
          other.y,
          other.radius,
        )) continue
        const labelCenterX = current.labelBoxX + current.labelBoxWidth / 2
        const labelCenterY = current.labelBoxY + current.labelBoxHeight / 2
        const awayX = labelCenterX - other.x || current.x - centerX || 1
        const awayY = labelCenterY - other.y || current.y - centerY || 1
        if (Math.abs(awayX) >= Math.abs(awayY)) {
          current = moveLabel(current, awayX > 0 ? 18 : -18, 0, width, height)
        } else {
          current = moveLabel(current, 0, awayY > 0 ? 18 : -18, width, height)
        }
      }
      return current
    })
  }
  return adjusted
}

function avoidOwnLabelOverlaps(nodes: PositionedMotifNode[], width: number, height: number, centerX: number, centerY: number): PositionedMotifNode[] {
  return nodes.map((node) => {
    let current = node
    for (let pass = 0; pass < 6; pass += 1) {
      if (!rectIntersectsCircle(
        current.labelBoxX,
        current.labelBoxY,
        current.labelBoxWidth,
        current.labelBoxHeight,
        current.x,
        current.y,
        current.radius + 4,
      )) break
      const labelCenterX = current.labelBoxX + current.labelBoxWidth / 2
      const labelCenterY = current.labelBoxY + current.labelBoxHeight / 2
      const awayX = labelCenterX - current.x || current.x - centerX || 1
      const awayY = labelCenterY - current.y || current.y - centerY || 1
      if (Math.abs(awayX) >= Math.abs(awayY)) {
        current = moveLabel(current, awayX > 0 ? 16 : -16, 0, width, height)
      } else {
        current = moveLabel(current, 0, awayY > 0 ? 16 : -16, width, height)
      }
    }
    return current
  })
}

function avoidLabelBoxCollisions(nodes: PositionedMotifNode[], width: number, height: number, centerX: number, centerY: number): PositionedMotifNode[] {
  let adjusted = [...nodes]
  for (let pass = 0; pass < 5; pass += 1) {
    let moved = false
    for (let i = 0; i < adjusted.length; i += 1) {
      for (let j = i + 1; j < adjusted.length; j += 1) {
        const a = adjusted[i]
        const b = adjusted[j]
        if (!rectsOverlap(
          a.labelBoxX,
          a.labelBoxY,
          a.labelBoxWidth,
          a.labelBoxHeight,
          b.labelBoxX,
          b.labelBoxY,
          b.labelBoxWidth,
          b.labelBoxHeight,
          6,
        )) continue

        const aCenterX = a.labelBoxX + a.labelBoxWidth / 2
        const aCenterY = a.labelBoxY + a.labelBoxHeight / 2
        const bCenterX = b.labelBoxX + b.labelBoxWidth / 2
        const bCenterY = b.labelBoxY + b.labelBoxHeight / 2
        const dx = aCenterX - bCenterX || a.x - centerX || (i % 2 === 0 ? 1 : -1)
        const dy = aCenterY - bCenterY || a.y - centerY || (j % 2 === 0 ? 1 : -1)
        if (Math.abs(dx) >= Math.abs(dy)) {
          const shift = dx > 0 ? 12 : -12
          adjusted[i] = moveLabel(a, shift, 0, width, height)
          adjusted[j] = moveLabel(b, -shift, 0, width, height)
        } else {
          const shift = dy > 0 ? 12 : -12
          adjusted[i] = moveLabel(a, 0, shift, width, height)
          adjusted[j] = moveLabel(b, 0, -shift, width, height)
        }
        moved = true
      }
    }
    if (!moved) break
  }
  return adjusted
}

function refineLabelLayout(nodes: PositionedMotifNode[], width: number, height: number, centerX: number, centerY: number): PositionedMotifNode[] {
  let adjusted = nodes
  for (let pass = 0; pass < 4; pass += 1) {
    adjusted = avoidOwnLabelOverlaps(adjusted, width, height, centerX, centerY)
    adjusted = avoidLabelCircleCollisions(adjusted, width, height, centerX, centerY)
    adjusted = avoidLabelBoxCollisions(adjusted, width, height, centerX, centerY)
  }
  return adjusted
}

export function layoutMotifGraph(graph: MotifGraph, options: LayoutOptions): PositionedMotifGraph {
  const width = Math.max(320, options.width)
  const height = Math.max(260, options.height)
  const centerX = width / 2
  const centerY = height / 2
  const centerNode = graph.nodes.find((node) => node.is_center)
  const otherNodes = centerNode
    ? graph.nodes.filter((node) => node.id !== centerNode.id)
    : graph.nodes
  const orderedNodes = centerNode ? [centerNode, ...otherNodes] : otherNodes
  const maxRadius = Math.max(64, Math.min(width, height) * 0.38)
  const minRadius = Math.max(42, Math.min(width, height) * 0.18)
  const goldenAngle = Math.PI * (3 - Math.sqrt(5))
  const positioned = orderedNodes.map((node, index) => {
    if (node.is_center) {
      const radius = nodeRadius(node)
      return withLabelLayout(node, centerX, centerY, radius, width, height, centerX, centerY)
    }
    const ringIndex = centerNode ? index - 1 : index
    const spread = Math.sqrt((ringIndex + 1) / Math.max(1, otherNodes.length))
    const orbit = minRadius + (maxRadius - minRadius) * spread
    const angle = ringIndex * goldenAngle - Math.PI / 2
    const x = centerX + Math.cos(angle) * orbit * (width >= height ? 1.18 : 0.92)
    const y = centerY + Math.sin(angle) * orbit * (height >= width ? 1.08 : 0.86)
    const radius = nodeRadius(node)
    return withLabelLayout(
      node,
      clamp(x, 54, width - 54),
      clamp(y, 54, height - 54),
      radius,
      width,
      height,
      centerX,
      centerY,
    )
  })
  const adjusted = refineLabelLayout(positioned, width, height, centerX, centerY)
  const byId = new Map(adjusted.map((node) => [node.id, node]))
  const edges = graph.edges
    .map((edge) => {
      const source = byId.get(edge.source_id)
      const target = byId.get(edge.target_id)
      if (!source || !target) return null
      return {
        ...edge,
        x1: source.x,
        y1: source.y,
        x2: target.x,
        y2: target.y,
      }
    })
    .filter((edge): edge is PositionedMotifEdge => edge !== null)
  return { nodes: adjusted, edges }
}
