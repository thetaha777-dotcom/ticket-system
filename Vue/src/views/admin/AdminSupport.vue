<script setup lang="ts">
/** Platform support queue: organizer requests and attendee cases that were escalated. */
import { onMounted, ref } from 'vue'

import CaseTable from '@/components/CaseTable.vue'
import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import type { SupportCase } from '@/types'

const cases = ref<SupportCase[] | null>(null)
const problem = ref('')

onMounted(async () => {
  try {
    cases.value = await api.get<SupportCase[]>('/support/cases', { scope: 'platform' })
  } catch (error) {
    problem.value = errorText(error)
  }
})
</script>

<template>
  <p class="mb-4 max-w-[65ch] text-sm text-ink-soft">{{ $t('admin.supportLead') }}</p>
  <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
  <p v-else-if="!cases" class="text-ink-soft">{{ $t('common.loading') }}</p>
  <CaseTable v-else :cases="cases" show-requester />
</template>
