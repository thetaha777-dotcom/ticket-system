<script setup lang="ts">
/** Minutes and seconds left until `until` (the end of a checkout reservation). Emits `expired` once. */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{ until: string }>()
const emit = defineEmits<{ expired: [] }>()
const now = ref(Date.now())
let timer: number | undefined
let announced = false

const secondsLeft = computed(() => Math.max(0, Math.floor((new Date(props.until).getTime() - now.value) / 1000)))
const text = computed(() => `${String(Math.floor(secondsLeft.value / 60)).padStart(2, '0')}:${String(secondsLeft.value % 60).padStart(2, '0')}`)

onMounted(() => {
  timer = window.setInterval(() => {
    now.value = Date.now()
    if (secondsLeft.value === 0 && !announced) {
      announced = true
      emit('expired')
    }
  }, 1000)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <span role="timer" class="font-display text-2xl font-semibold tabular-nums" :class="secondsLeft < 60 ? 'text-bad' : ''">{{ text }}</span>
</template>
