import { describe, expect, it } from 'vitest'
import {
  APP_TOUR_STATE_KEY,
  COLLECTIONS_TOUR_DISMISSED_KEY,
  readAppTourStatuses,
} from './settings'

function storage(values: Record<string, string> = {}): Pick<Storage, 'getItem'> {
  return {
    getItem(key: string) {
      return Object.prototype.hasOwnProperty.call(values, key) ? values[key] : null
    },
  }
}

describe('guided tour preferences', () => {
  it('defaults every workspace tour to unseen', () => {
    expect(readAppTourStatuses(storage())).toEqual({
      collections: 'unseen',
      'ai-edit': 'unseen',
      agent: 'unseen',
      motifs: 'unseen',
    })
  })

  it('keeps valid independent statuses and ignores corrupt values', () => {
    expect(readAppTourStatuses(storage({
      [APP_TOUR_STATE_KEY]: JSON.stringify({
        collections: 'completed',
        'ai-edit': 'dismissed',
        agent: 'invalid',
        motifs: 'completed',
      }),
    }))).toEqual({
      collections: 'completed',
      'ai-edit': 'dismissed',
      agent: 'unseen',
      motifs: 'completed',
    })
  })

  it('migrates only the legacy collection dismissal without disturbing new tours', () => {
    expect(readAppTourStatuses(storage({
      [COLLECTIONS_TOUR_DISMISSED_KEY]: 'true',
    }))).toEqual({
      collections: 'dismissed',
      'ai-edit': 'unseen',
      agent: 'unseen',
      motifs: 'unseen',
    })
  })

  it('does not let the legacy flag overwrite an explicit completed state', () => {
    expect(readAppTourStatuses(storage({
      [COLLECTIONS_TOUR_DISMISSED_KEY]: 'true',
      [APP_TOUR_STATE_KEY]: JSON.stringify({ collections: 'completed' }),
    })).collections).toBe('completed')
  })
})
