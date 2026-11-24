<script setup lang="ts">
/**
 * Column chart for one series (for example tickets sold per day).
 * Follows the project's chart rules: thin columns with a rounded top, quiet hairline grid,
 * text in text colours (never in the data colour), a tooltip on hover and keyboard focus,
 * a label only on the highest column, and a table view of the same numbers.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export interface ChartPoint { label: string; value: number; detail?: string }

const props = withDefaults(defineProps<{ points: ChartPoint[]; title: string; format?: (value: number) => string }>(), {
  format: (value: number) => new Intl.NumberFormat('ru-RU').format(value),
})

const box = ref<HTMLElement | null>(null)
const width = ref(640)
const active = ref<number | null>(null)
const showTable = ref(false)
let observer: ResizeObserver | null = null
onMounted(() => {
  if (!box.value) return
  observer = new ResizeObserver(([entry]) => (width.value = Math.max(280, entry.contentRect.width)))
  observer.observe(box.value)
})
onBeforeUnmount(() => observer?.disconnect())

const HEIGHT = 240
const PAD = { top: 22, right: 8, bottom: 28, left: 48 }

/** Round the axis maximum up to a clean number and split it into 4 steps. */
const axis = computed(() => {
  const max = Math.max(1, ...props.points.map((p) => p.value))
  const rough = max / 4
  const power = 10 ** Math.floor(Math.log10(rough))
  const step = Math.max(1, [1, 2, 2.5, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? rough)
  const ticks = [0, 1, 2, 3, 4].map((i) => Math.round(i * step))
  return { top: ticks[4], ticks }
})
const plot = computed(() => ({ w: width.value - PAD.left - PAD.right, h: HEIGHT - PAD.top - PAD.bottom }))
const band = computed(() => plot.value.w / Math.max(1, props.points.length))
const barWidth = computed(() => Math.min(24, Math.max(3, band.value - 2)))
const y = (value: number): number => PAD.top + plot.value.h * (1 - value / axis.value.top)
const xMid = (index: number): number => PAD.left + band.value * (index + 0.5)
const maxIndex = computed(() => props.points.reduce((best, p, i) => (p.value > props.points[best].value ? i : best), 0))
/** Show only as many date labels as fit side by side. */
const labelEvery = computed(() => Math.max(1, Math.ceil(props.points.length / Math.max(1, Math.floor(plot.value.w / 64)))))
const compact = (value: number): string => (value === 0 ? '0' : axis.value.top >= 10_000 ? `${value / 1000}K` : String(value))

/** Column with a 4px rounded top and a square foot on the baseline. */
function column(index: number): string {
  const value = props.points[index].value
  const left = xMid(index) - barWidth.value / 2
  const top = y(value)
  const bottom = y(0)
  const r = Math.min(4, barWidth.value / 2, Math.max(0, bottom - top))
  return `M${left},${bottom}V${top + r}Q${left},${top} ${left + r},${top}H${left + barWidth.value - r}Q${left + barWidth.value},${top} ${left + barWidth.value},${top + r}V${bottom}Z`
}
</script>

<template>
  <figure>
    <div class="mb-2 flex items-center justify-between gap-3">
      <figcaption class="font-semibold">{{ title }}</figcaption>
      <button type="button" class="btn btn-ghost btn-sm" :aria-pressed="showTable" @click="showTable = !showTable">
        {{ showTable ? $t('analytics.showChart') : $t('analytics.showTable') }}
      </button>
    </div>

    <p v-if="!points.length" class="py-10 text-center text-sm text-ink-soft">{{ $t('analytics.noSales') }}</p>

    <div v-else-if="!showTable" ref="box" class="relative" @mouseleave="active = null">
      <svg :width="width" :height="HEIGHT" role="img" :aria-label="title" class="block">
        <g v-for="tick in axis.ticks" :key="tick">
          <line :x1="PAD.left" :x2="width - PAD.right" :y1="y(tick)" :y2="y(tick)" stroke="var(--color-line)" stroke-width="1" />
          <text :x="PAD.left - 8" :y="y(tick) + 4" text-anchor="end" font-size="12" fill="var(--color-ink-soft)">{{ compact(tick) }}</text>
        </g>
        <g v-for="(point, index) in points" :key="point.label">
          <path :d="column(index)" :fill="active === index ? 'var(--color-sky)' : 'var(--color-chart)'" />
          <text v-if="index % labelEvery === 0" :x="xMid(index)" :y="HEIGHT - 8" text-anchor="middle" font-size="12" fill="var(--color-ink-soft)">{{ point.label }}</text>
          <text v-if="index === maxIndex && point.value > 0" :x="xMid(index)" :y="y(point.value) - 6" text-anchor="middle" font-size="12" font-weight="600" fill="var(--color-ink)">{{ format(point.value) }}</text>
          <!-- the hit area is the whole band, far bigger than the thin column -->
          <rect
            :x="PAD.left + band * index" :y="PAD.top" :width="band" :height="plot.h" fill="transparent" tabindex="0"
            :aria-label="`${point.label}: ${format(point.value)}`" @mouseenter="active = index" @focus="active = index" @blur="active = null"
          />
        </g>
      </svg>
      <div
        v-if="active !== null" class="pointer-events-none absolute z-10 -translate-x-1/2 rounded-lg bg-ink px-3 py-2 text-sm whitespace-nowrap text-white shadow-lg"
        :style="{ left: `${Math.min(width - 70, Math.max(70, xMid(active)))}px`, top: `${Math.max(0, y(points[active].value) - 58)}px` }"
      >
        <strong class="block text-base">{{ format(points[active].value) }}</strong>
        <span class="text-white/80">{{ points[active].label }}<template v-if="points[active].detail">, {{ points[active].detail }}</template></span>
      </div>
    </div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead><tr><th>{{ $t('analytics.day') }}</th><th class="num">{{ title }}</th><th>{{ $t('analytics.details') }}</th></tr></thead>
        <tbody>
          <tr v-for="point in points" :key="point.label"><td>{{ point.label }}</td><td class="num">{{ format(point.value) }}</td><td>{{ point.detail }}</td></tr>
        </tbody>
      </table>
    </div>
  </figure>
</template>
