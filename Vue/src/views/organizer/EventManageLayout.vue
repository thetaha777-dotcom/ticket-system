<script setup lang="ts">
/** Shell of the event-management pages: loads the event once, shows its header and the tabs. */
import { onMounted, provide, ref, type Ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime, errorText } from '@/lib/format'
import { managedEventKey } from '@/lib/managed'
import type { EventManage } from '@/types'

const props = defineProps<{ id: string }>()
const event = ref<EventManage | null>(null)
const problem = ref('')

const TABS = [
  ['manage-overview', 'overview'], ['manage-tickets', 'tickets'], ['manage-seating', 'seating'], ['manage-orders', 'orders'],
  ['manage-attendees', 'attendees'], ['manage-promo', 'promo'], ['manage-staff', 'staff'], ['manage-activation', 'activation'],
  ['manage-analytics', 'analytics'], ['manage-history', 'history'], ['manage-support', 'support'],
] as const

async function reload(): Promise<void> {
  try {
    event.value = await api.get<EventManage>(`/organizer/events/${props.id}`)
  } catch (error) {
    problem.value = errorText(error)
  }
}
provide(managedEventKey, { event: event as Ref<EventManage>, reload })
onMounted(reload)
</script>

<template>
  <div class="page">
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!event" class="text-ink-soft">{{ $t('common.loading') }}</p>

    <template v-else>
      <RouterLink class="text-sm font-semibold" :to="{ name: 'organizer' }">{{ $t('manage.allEvents') }}</RouterLink>
      <div class="mt-2 mb-5">
        <p class="mb-1 flex flex-wrap items-center gap-2">
          <StatusBadge :status="event.status" />
          <StatusBadge v-if="event.status === 'published'" :status="event.event_class" />
          <span v-if="event.is_suspended" class="badge badge-bad">{{ $t('status.suspended') }}</span>
        </p>
        <h1 class="text-3xl sm:text-4xl">{{ event.title }}</h1>
        <p class="mt-1 text-ink-soft">{{ dateTime(event.start_at, event.timezone) }}, {{ event.venue.name }}, {{ event.venue.city }}</p>
      </div>
      <p v-if="event.is_suspended" class="notice notice-bad mb-5" role="status">{{ $t('manage.suspended', { reason: event.suspended_reason }) }}</p>

      <nav class="tabs mb-6" :aria-label="$t('manage.sections')">
        <RouterLink v-for="[name, key] in TABS" :key="name" :to="{ name, params: { id } }" class="tab" exact-active-class="tab-active">{{ $t(`manage.tab.${key}`) }}</RouterLink>
      </nav>
      <RouterView />
    </template>
  </div>
</template>
