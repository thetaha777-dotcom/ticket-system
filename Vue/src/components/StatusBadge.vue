<script setup lang="ts">
/** A status word with a colour AND a symbol, so the meaning never depends on colour alone. */
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const LOOK: Record<string, [string, string]> = {
  // status: [css class, symbol]
  published: ['badge-ok', '●'], completed: ['badge-ok', '✓'], valid: ['badge-ok', '✓'], succeeded: ['badge-ok', '✓'],
  active: ['badge-ok', '●'], resolved: ['badge-ok', '✓'], verified: ['badge-ok', '✓'], checked_in: ['badge-sky', '✓'],
  upcoming: ['badge-sky', '◷'], in_progress: ['badge-sky', '◷'], reviewed: ['badge-sky', '✓'],
  pending: ['badge-warn', '◷'], draft: ['badge-warn', '✎'], unpublished: ['badge-warn', '◌'], open: ['badge-warn', '●'],
  waiting_for_customer: ['badge-warn', '◷'], not_started: ['badge-warn', '◌'], suspended: ['badge-bad', '!'],
  cancelled: ['badge-bad', '✕'], refunded: ['badge-bad', '↩'], failed: ['badge-bad', '✕'], expired: ['', '◌'], dismissed: ['', '◌'],
}
const look = computed(() => LOOK[props.status] ?? ['', '•'])
</script>

<template>
  <span class="badge" :class="look[0]"><span aria-hidden="true">{{ look[1] }}</span>{{ $t(`status.${status}`) }}</span>
</template>
