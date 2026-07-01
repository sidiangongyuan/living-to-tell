import { describe, expect, it } from 'vitest'
import { toggleAiTaskProfileSelection } from './profileSelection'

describe('AI profile selection', () => {
  it('replaces the default profile when a specific profile is first selected', () => {
    expect(toggleAiTaskProfileSelection(['default'], 'gemini')).toEqual(['gemini'])
  })

  it('lets the user add the default profile back explicitly', () => {
    expect(toggleAiTaskProfileSelection(['gemini'], 'default')).toEqual(['gemini', 'default'])
  })

  it('does not impose a fixed comparison limit', () => {
    expect(toggleAiTaskProfileSelection(['a', 'b', 'c', 'd'], 'e')).toEqual(['a', 'b', 'c', 'd', 'e'])
  })

  it('allows an empty selection so the run action can show a clear prompt', () => {
    expect(toggleAiTaskProfileSelection(['default'], 'default')).toEqual([])
  })
})
