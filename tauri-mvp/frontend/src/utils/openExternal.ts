export async function openExternalUrl(url: string): Promise<void> {
  const target = url.trim()
  if (!target) throw new Error('URL is empty')

  try {
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('open_external_url', { url: target })
    return
  } catch {
    if (typeof window !== 'undefined' && typeof window.open === 'function') {
      window.open(target, '_blank', 'noopener,noreferrer')
      return
    }
  }

  throw new Error(`Unable to open URL: ${target}`)
}
