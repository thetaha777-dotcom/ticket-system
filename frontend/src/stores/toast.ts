import { defineStore } from 'pinia'
import { ref } from 'vue'

import { errorText } from '@/lib/format'

export interface Toast { id: number; kind: 'ok' | 'bad'; text: string }

/** Short confirmation / error messages shown at the bottom of the screen. */
export const useToastStore = defineStore('toast', () => {
  const items = ref<Toast[]>([])
  let next = 1

  function push(kind: Toast['kind'], text: string): void {
    const id = next++
    items.value.push({ id, kind, text })
    setTimeout(() => dismiss(id), kind === 'bad' ? 8000 : 4000)
  }
  const ok = (text: string): void => push('ok', text)
  /** Show the translated message of a failed API call. */
  const error = (problem: unknown): void => push('bad', errorText(problem))
  function dismiss(id: number): void {
    items.value = items.value.filter((item) => item.id !== id)
  }
  return { items, ok, error, dismiss }
})
