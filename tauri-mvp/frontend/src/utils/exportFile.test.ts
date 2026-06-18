import { describe, expect, it, vi } from 'vitest'
import { saveBlobWithDialog, type NativeInvoke } from './exportFile'

describe('saveBlobWithDialog', () => {
  it('uses native save dialog and writes blob bytes', async () => {
    const calls: Array<{ command: string; args?: Record<string, unknown> }> = []
    const invoke: NativeInvoke = vi.fn(async (command: string, args?: Record<string, unknown>) => {
      calls.push({ command, args })
      if (command === 'choose_export_file') return 'D:\\exports\\article.md'
      return undefined
    }) as NativeInvoke

    const result = await saveBlobWithDialog(
      new Blob(['hello']),
      'article.md',
      'md',
      { invoke }
    )

    expect(result).toEqual({ status: 'saved', path: 'D:\\exports\\article.md' })
    expect(calls[0]).toEqual({
      command: 'choose_export_file',
      args: { defaultFilename: 'article.md', format: 'md' },
    })
    expect(calls[1]).toEqual({
      command: 'write_export_file',
      args: { path: 'D:\\exports\\article.md', bytes: [104, 101, 108, 108, 111] },
    })
  })

  it('does not write when the native dialog is cancelled', async () => {
    const invoke = vi.fn(async (command: string) => {
      if (command === 'choose_export_file') return null
      throw new Error('write should not be called')
    }) as NativeInvoke

    await expect(saveBlobWithDialog(
      new Blob(['hello']),
      'article.md',
      'md',
      { invoke }
    )).resolves.toEqual({ status: 'cancelled' })
    expect(invoke).toHaveBeenCalledTimes(1)
  })
})
