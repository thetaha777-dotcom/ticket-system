<script setup lang="ts">
/** Support requests that attendees opened about this event. */
import { onMounted, ref } from 'vue'

import CaseTable from '@/components/CaseTable.vue'
import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import type { SupportCase } from '@/types'

const { event } = useManagedEvent()
const cases = ref<SupportCase[] | null>(null)
const problem = ref('')

onMounted(async () => {
  try {
    cases.value = await api.get<SupportCase[]>('/support/cases', { scope: 'managed', event_id: event.value.id })
  } catch (error) {
    problem.value = errorText(error)
  }
})
</script>

<template>
  <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
  <p v-else-if="!cases" class="text-ink-soft">{{ $t('common.loading') }}</p>
  <CaseTable v-else :cases="cases" show-requester />
</template>
