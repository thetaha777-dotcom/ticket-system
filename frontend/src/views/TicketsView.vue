<script setup lang="ts">
/** All tickets of the signed-in attendee. Usable tickets come first. */
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import TicketPass from '@/components/TicketPass.vue'
import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import type { Ticket } from '@/types'

const tickets = ref<Ticket[] | null>(null)
const problem = ref('')
const showAll = ref(false)

const usable = computed(() => (tickets.value ?? []).filter((ticket) => ticket.status === 'valid' && new Date(ticket.event.end_at) > new Date()))
const shown = computed(() => (showAll.value ? (tickets.value ?? []) : usable.value))

onMounted(async () => {
  try {
    tickets.value = await api.get<Ticket[]>('/tickets')
  } catch (error) {
    problem.value = errorText(error)
  }
})
</script>

<template>
  <div class="page">
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <h1>{{ $t('ticket.myTickets') }}</h1>
      <label v-if="tickets?.length" class="flex cursor-pointer items-center gap-2 text-sm font-semibold">
        <input v-model="showAll" type="checkbox" class="h-4 w-4" /> {{ $t('ticket.showAll') }}
      </label>
    </div>
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!tickets" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <div v-else-if="!shown.length" class="card">
      <p class="mb-3 text-ink-soft">{{ tickets.length ? $t('ticket.noneUpcoming') : $t('ticket.empty') }}</p>
      <RouterLink class="btn btn-primary" :to="{ name: 'home' }">{{ $t('order.browse') }}</RouterLink>
    </div>
    <div v-else class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <TicketPass v-for="ticket in shown" :key="ticket.id" :ticket="ticket" />
    </div>
  </div>
</template>
