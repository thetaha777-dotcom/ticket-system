<script setup lang="ts">
/** A square event card with a photo background and the event's essential details. */
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { categoryColour, dayNumber, money, monthShort, timeOnly } from '@/lib/format'
import type { EventCard } from '@/types'

const props = defineProps<{ event: EventCard }>()
const colour = computed(() => categoryColour(props.event.category))
const cover = computed(() => props.event.images[0] ?? null)
</script>

<template>
  <article class="ticket-wrap">
    <RouterLink
      :to="{ name: 'event', params: { slug: event.slug } }"
      class="group relative flex aspect-square w-full flex-col justify-between overflow-hidden rounded-lg border border-line bg-ink text-white no-underline hover:text-white"
    >
      <img v-if="cover" :src="cover" alt="" class="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
      <div v-else class="absolute inset-0" :style="{ background: colour }" />
      <div class="absolute inset-0 bg-linear-to-t from-ink/95 via-ink/40 to-ink/10" aria-hidden="true" />

      <div class="relative flex items-start justify-between gap-2 p-3 sm:p-4">
        <div class="flex flex-col">
          <span class="font-display text-3xl leading-none font-semibold">{{ dayNumber(event.start_at, event.timezone) }}</span>
          <span class="mt-1 text-xs font-semibold uppercase">{{ monthShort(event.start_at, event.timezone) }} · {{ timeOnly(event.start_at, event.timezone) }}</span>
        </div>
        <span v-if="event.price_from === 0" class="badge shrink-0">{{ $t('event.free') }}</span>
        <span v-else-if="event.price_from !== null" class="badge shrink-0">{{ $t('event.from') }} {{ money(event.price_from) }}</span>
      </div>

      <div class="relative mt-auto p-3 sm:p-4">
        <p class="truncate text-xs text-white/80 sm:text-sm">{{ event.venue.name }}, {{ event.venue.city }}</p>
        <h3 class="mt-1 line-clamp-2 text-lg leading-tight font-semibold text-white sm:text-xl">{{ event.title }}</h3>
        <p class="mt-2 flex min-h-6 flex-wrap gap-1">
          <span class="badge">{{ event.category }}</span>
          <span v-if="event.status === 'cancelled'" class="badge badge-bad">{{ $t('status.cancelled') }}</span>
          <span v-else-if="!event.is_on_sale" class="badge badge-warn">{{ $t('event.salesClosed') }}</span>
        </p>
        <span class="mt-2 inline-flex text-sm font-semibold text-sun underline">{{ $t('event.details') }}</span>
      </div>
    </RouterLink>
  </article>
</template>
