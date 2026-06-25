export async function openExternalUrl(url: string): Promise<void> {
  const target = url.trim()
  if (!target) throw new Error('URL is empty')

  try {
    const { open } = await import('@tauri-apps/plugin-shell')
    await open(target)
    return
  } catch {
    if (typeof window !== 'undefined' && typeof window.open === 'function') {
      window.open(target, '_blank', 'noopener,noreferrer')
      return
    }
  }

  throw new Error(`Unable to open URL: ${target}`)
}
