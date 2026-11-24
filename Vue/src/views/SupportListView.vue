<script setup lang="ts">
/** Support requests: the ones I opened and, for organizers, the ones about my events. */
import { computed, onMounted, ref, watch } from 'vue'

import CaseTable from '@/components/CaseTable.vue'
import SupportRequestButton from '@/components/SupportRequestButton.vue'
import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'
import type { SupportCase } from '@/types'

const auth = useAuthStore()
const scope = ref<'mine' | 'managed'>('mine')
const cases = ref<SupportCase[] | null>(null)
const problem = ref('')
const canManage = computed(() => auth.isOrganizer || auth.user?.role === 'event_admin')

async function load(): Promise<void> {
  cases.value = null
  problem.value = ''
  try {
    cases.value = await api.get<SupportCase[]>('/support/cases', { scope: scope.value })
  } catch (error) {
    problem.value = errorText(error)
  }
}
watch(scope, load)
onMounted(load)
</script>

<template>
  <div class="page">
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1>{{ $t('support.title') }}</h1>
        <p class="mt-2 max-w-[60ch] text-ink-soft">{{ $t('support.lead') }}</p>
      </div>
      <SupportRequestButton v-if="auth.isOrganizer" kind="organizer" :label="$t('support.askPlatform')" />
    </div>

    <div v-if="canManage" class="tabs mb-5" role="tablist">
      <button type="button" role="tab" class="tab cursor-pointer" :class="{ 'tab-active': scope === 'mine' }" :aria-selected="scope === 'mine'" @click="scope = 'mine'">{{ $t('support.mine') }}</button>
      <button type="button" role="tab" class="tab cursor-pointer" :class="{ 'tab-active': scope === 'managed' }" :aria-selected="scope === 'managed'" @click="scope = 'managed'">{{ $t('support.managed') }}</button>
    </div>

    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!cases" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <CaseTable v-else :cases="cases" :show-requester="scope === 'managed'" />
  </div>
</template>
