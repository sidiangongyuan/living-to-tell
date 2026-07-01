const DEFAULT_PROFILE_ID = 'default'

export function toggleAiTaskProfileSelection(selectedIds: string[], profileId: string): string[] {
  const normalizedProfileId = String(profileId || '').trim()
  if (!normalizedProfileId) return selectedIds

  if (selectedIds.includes(normalizedProfileId)) {
    return selectedIds.filter((id) => id !== normalizedProfileId)
  }

  if (
    normalizedProfileId !== DEFAULT_PROFILE_ID
    && selectedIds.length === 1
    && selectedIds[0] === DEFAULT_PROFILE_ID
  ) {
    return [normalizedProfileId]
  }

  return [...selectedIds, normalizedProfileId]
}
