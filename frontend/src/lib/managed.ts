/**
 * The organizer's event-management pages share one loaded event.
 * EventManageLayout.vue provides it; every tab reads it with useManagedEvent().
 */
import { inject, type InjectionKey, type Ref } from 'vue'

import type { EventManage } from '@/types'

export interface ManagedEvent {
  event: Ref<EventManage>
  /** Re-read the event from the server after something changed (status, ticket types, ...). */
  reload: () => Promise<void>
}
export const managedEventKey: InjectionKey<ManagedEvent> = Symbol('managedEvent')

export function useManagedEvent(): ManagedEvent {
  const value = inject(managedEventKey)
  if (!value) throw new Error('useManagedEvent() must be used inside EventManageLayout')
  return value
}
