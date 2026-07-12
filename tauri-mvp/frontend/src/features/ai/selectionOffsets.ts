export function utf16OffsetToCodePointOffset(text: string, offset: number): number {
  const safeOffset = Math.max(0, Math.min(Math.trunc(offset), text.length))
  return Array.from(text.slice(0, safeOffset)).length
}
