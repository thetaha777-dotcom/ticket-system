<script setup lang="ts">
/** Draws a QR code for `value`. Ticket codes are plain black on white so that scanners read them easily. */
import QRCode from 'qrcode'
import { onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ value: string; size?: number; label: string }>(), { size: 220 })
const canvas = ref<HTMLCanvasElement | null>(null)

async function draw(): Promise<void> {
  if (canvas.value) {
    await QRCode.toCanvas(canvas.value, props.value, { width: props.size, margin: 2, errorCorrectionLevel: 'Q' })
  }
}
onMounted(draw)
watch(() => props.value, draw)
</script>

<template>
  <canvas ref="canvas" role="img" :aria-label="label" class="h-auto max-w-full rounded-md bg-white" />
</template>
