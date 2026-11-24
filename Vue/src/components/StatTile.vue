<script setup lang="ts">
/** One headline number with a label, and optionally a meter (share of a whole) under it. */
import { computed } from 'vue'

const props = defineProps<{ label: string; value: string; hint?: string; meter?: number }>()
const percent = computed(() => Math.min(100, Math.max(0, props.meter ?? 0)))
</script>

<template>
  <div class="card">
    <p class="text-sm text-ink-soft">{{ label }}</p>
    <p class="mt-1 font-display text-3xl font-semibold tabular-nums">{{ value }}</p>
    <div
      v-if="meter !== undefined" class="mt-3 h-2 overflow-hidden rounded-full bg-sky-pale" role="meter"
      :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100" :aria-label="label"
    >
      <div class="h-full rounded-full bg-chart" :style="{ width: `${percent}%` }" />
    </div>
    <p v-if="hint" class="mt-2 text-sm text-ink-soft">{{ hint }}</p>
  </div>
</template>
