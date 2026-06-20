import { describe, expect, it } from 'vitest'
import { layoutMotifGraph } from './graphLayout'
import type { MotifGraph } from '../../api/motifs'

function rectIntersectsCircle(
  rectX: number,
  rectY: number,
  rectWidth: number,
  rectHeight: number,
  circleX: number,
  circleY: number,
  radius: number,
) {
  const nearestX = Math.max(rectX, Math.min(circleX, rectX + rectWidth))
  const nearestY = Math.max(rectY, Math.min(circleY, rectY + rectHeight))
  return (circleX - nearestX) ** 2 + (circleY - nearestY) ** 2 < radius ** 2
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
) {
  return !(
    aX + aWidth <= bX ||
    bX + bWidth <= aX ||
    aY + aHeight <= bY ||
    bY + bHeight <= aY
  )
}

describe('motif graph layout', () => {
  it('keeps local graph labels outside their node circles and within the viewport', () => {
    const graph: MotifGraph = {
      nodes: [
        { id: 'center', name: '测试意象｜岁月', excerpt_count: 3, pinned: false, is_center: true },
        { id: 'city', name: '测试意象｜城市', excerpt_count: 2, pinned: false, is_center: false },
        { id: 'message', name: '测试意象｜很长很长的消息名字', excerpt_count: 1, pinned: false, is_center: false },
      ],
      edges: [
        { source_id: 'center', target_id: 'city', weight: 3, shared_excerpts: 1, shared_sources: 1 },
        { source_id: 'center', target_id: 'message', weight: 2, shared_excerpts: 1, shared_sources: 0 },
      ],
    }

    const positioned = layoutMotifGraph(graph, { width: 560, height: 360 })

    for (const node of positioned.nodes) {
      expect(node.labelLines.length).toBeGreaterThan(0)
      expect(node.labelLines.length).toBeLessThanOrEqual(2)
      expect(node.labelBoxX).toBeGreaterThanOrEqual(10)
      expect(node.labelBoxY).toBeGreaterThanOrEqual(10)
      expect(node.labelBoxX + node.labelBoxWidth).toBeLessThanOrEqual(550)
      expect(node.labelBoxY + node.labelBoxHeight).toBeLessThanOrEqual(350)
      expect(rectIntersectsCircle(
        node.labelBoxX,
        node.labelBoxY,
        node.labelBoxWidth,
        node.labelBoxHeight,
        node.x,
        node.y,
        node.radius + 4,
      )).toBe(false)
    }
  })

  it('keeps screenshot-sized local labels from covering nearby nodes or each other', () => {
    const graph: MotifGraph = {
      nodes: [
        { id: 'years', name: '测试意象｜岁月', excerpt_count: 4, pinned: false, is_center: true },
        { id: 'city', name: '测试意象｜城市', excerpt_count: 2, pinned: false, is_center: false },
        { id: 'message', name: '测试意象｜消息', excerpt_count: 1, pinned: false, is_center: false },
        { id: 'gate', name: '测试意象｜门口', excerpt_count: 1, pinned: false, is_center: false },
      ],
      edges: [
        { source_id: 'years', target_id: 'city', weight: 3, shared_excerpts: 1, shared_sources: 1 },
        { source_id: 'years', target_id: 'message', weight: 2, shared_excerpts: 1, shared_sources: 0 },
        { source_id: 'years', target_id: 'gate', weight: 2, shared_excerpts: 1, shared_sources: 0 },
      ],
    }

    const positioned = layoutMotifGraph(graph, { width: 620, height: 440 })

    for (const labelOwner of positioned.nodes) {
      for (const node of positioned.nodes) {
        expect(rectIntersectsCircle(
          labelOwner.labelBoxX,
          labelOwner.labelBoxY,
          labelOwner.labelBoxWidth,
          labelOwner.labelBoxHeight,
          node.x,
          node.y,
          node.radius + 4,
        )).toBe(false)
      }
    }

    for (let i = 0; i < positioned.nodes.length; i += 1) {
      for (let j = i + 1; j < positioned.nodes.length; j += 1) {
        const a = positioned.nodes[i]
        const b = positioned.nodes[j]
        expect(rectsOverlap(
          a.labelBoxX,
          a.labelBoxY,
          a.labelBoxWidth,
          a.labelBoxHeight,
          b.labelBoxX,
          b.labelBoxY,
          b.labelBoxWidth,
          b.labelBoxHeight,
        )).toBe(false)
      }
    }
  })
})
