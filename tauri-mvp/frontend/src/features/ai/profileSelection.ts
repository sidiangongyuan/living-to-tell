export function toggleAiTaskProfileSelection(
  selectedIds: string[],
  profileId: string,
  defaultProfileId = 'default',
): string[] {
  const normalizedProfileId = String(profileId || '').trim()
  const normalizedDefaultId = String(defaultProfileId || '').trim()
  if (!normalizedProfileId) return selectedIds

  if (selectedIds.includes(normalizedProfileId)) {
    return selectedIds.filter((id) => id !== normalizedProfileId)
  }

  if (
    normalizedDefaultId
    && normalizedProfileId !== normalizedDefaultId
    && selectedIds.length === 1
    && selectedIds[0] === normalizedDefaultId
  ) {
    return [normalizedProfileId]
  }

  return [...selectedIds, normalizedProfileId]
}
