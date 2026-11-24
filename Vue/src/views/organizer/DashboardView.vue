<script setup lang="ts">
/** Organizer dashboard: totals and all own events grouped as Upcoming / Active / Drafts / Completed / Cancelled. */
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import StatTile from '@/components/StatTile.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime, errorText, money } from '@/lib/format'
import type { EventManage, OrganizerSummary } from '@/types'

type Group = 'upcoming' | 'active' | 'draft' | 'completed' | 'cancelled'
const GROUPS: Group[] = ['upcoming', 'active', 'draft', 'completed', 'cancelled']

const events = ref<EventManage[] | null>(null)
const summary = ref<OrganizerSummary | null>(null)
const group = ref<Group>('upcoming')
const problem = ref('')

const groupOf = (event: EventManage): Group => (event.status === 'draft' || event.status === 'unpublished' ? 'draft' : event.event_class)
const counts = computed(() => Object.fromEntries(GROUPS.map((g) => [g, (events.value ?? []).filter((e) => groupOf(e) === g).length])))
const shown = computed(() => (events.value ?? []).filter((event) => groupOf(event) === group.value))

onMounted(async () => {
  try {
    ;[events.value, summary.value] = await Promise.all([api.get<EventManage[]>('/organizer/events'), api.get<OrganizerSummary>('/organizer/summary')])
    group.value = GROUPS.find((g) => counts.value[g] > 0) ?? 'upcoming'
  } catch (error) {
    problem.value = errorText(error)
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <h1>{{ $t('org.title') }}</h1>
      <div class="flex flex-wrap gap-2">
        <RouterLink class="btn btn-secondary" :to="{ name: 'organizer-profile' }">{{ $t('org.profile') }}</RouterLink>
        <RouterLink class="btn btn-primary" :to="{ name: 'event-new' }">{{ $t('org.createEvent') }}</RouterLink>
      </div>
    </div>

    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>

    <div v-if="summary" class="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatTile :label="$t('org.eventsTotal')" :value="String(summary.events)" :hint="$t('org.upcomingCount', summary.upcoming_events)" />
      <StatTile :label="$t('org.ticketsSold')" :value="String(summary.tickets_sold)" />
      <StatTile :label="$t('org.netRevenue')" :value="money(summary.net_revenue)" :hint="$t('common.demoMoney')" />
      <StatTile :label="$t('org.checkedIn')" :value="String(summary.checked_in)" />
    </div>

    <div class="tabs mb-5" role="tablist">
      <button
        v-for="item in GROUPS" :key="item" type="button" role="tab" class="tab cursor-pointer" :class="{ 'tab-active': group === item }"
        :aria-selected="group === item" @click="group = item"
      >{{ $t(`org.group.${item}`) }} <span class="text-ink-soft">{{ counts[item] }}</span></button>
    </div>

    <p v-if="!events" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <div v-else-if="!shown.length" class="card">
      <p class="mb-3 text-ink-soft">{{ $t(`org.empty.${group}`) }}</p>
      <RouterLink v-if="group === 'upcoming' || group === 'draft'" class="btn btn-primary" :to="{ name: 'event-new' }">{{ $t('org.createEvent') }}</RouterLink>
    </div>
    <ul v-else class="space-y-3">
      <li v-for="event in shown" :key="event.id" class="card flex flex-wrap items-center gap-4">
        <div class="min-w-0 flex-1">
          <p class="mb-1 flex flex-wrap items-center gap-2">
            <StatusBadge :status="event.status" />
            <span v-if="event.is_suspended" class="badge badge-bad">{{ $t('status.suspended') }}</span>
            <span v-if="event.visibility !== 'public'" class="badge">{{ $t(`visibility.${event.visibility}`) }}</span>
          </p>
          <h2 class="truncate text-2xl">
            <RouterLink class="text-ink no-underline hover:underline" :to="{ name: 'manage-overview', params: { id: event.id } }">{{ event.title }}</RouterLink>
          </h2>
          <p class="text-sm text-ink-soft">{{ dateTime(event.start_at, event.timezone) }}, {{ event.venue.name }}, {{ event.venue.city }}</p>
        </div>
        <div v-if="event.stats" class="w-44">
          <p class="text-sm"><strong class="tabular-nums">{{ event.stats.tickets_sold }}</strong> {{ $t('org.ofCapacity', { n: event.stats.capacity }) }}</p>
          <div class="mt-1 h-2 overflow-hidden rounded-full bg-sky-pale" role="meter" :aria-valuenow="event.stats.tickets_sold" aria-valuemin="0" :aria-valuemax="event.stats.capacity" :aria-label="$t('org.ticketsSold')">
            <div class="h-full rounded-full bg-chart" :style="{ width: `${event.stats.capacity ? (100 * event.stats.tickets_sold) / event.stats.capacity : 0}%` }" />
          </div>
        </div>
        <RouterLink class="btn btn-secondary btn-sm" :to="{ name: 'manage-overview', params: { id: event.id } }">{{ $t('event.manage') }}</RouterLink>
      </li>
    </ul>
  </div>
</template>
