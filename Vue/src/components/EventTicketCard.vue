<script setup lang="ts">
/** An event shown as a ticket: coloured date block, details, a perforation and a price stub. */
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { categoryColour, dayNumber, money, monthShort, timeOnly, weekday } from '@/lib/format'
import type { EventCard } from '@/types'

const props = defineProps<{ event: EventCard }>()
const colour = computed(() => categoryColour(props.event.category))
const cover = computed(() => props.event.images[0] ?? null)
</script>

<template>
  <article class="ticket-wrap">
    <RouterLink :to="{ name: 'event', params: { slug: event.slug } }" class="ticket flex min-h-36 text-ink no-underline hover:text-ink">
      <div class="ticket-main flex">
        <!-- date block: the big number is the day of the month -->
        <div class="flex w-16 shrink-0 flex-col items-center justify-center rounded-l-xl px-1 py-3 sm:w-24" :style="{ background: colour }">
          <span class="font-display text-3xl leading-none font-semibold sm:text-5xl">{{ dayNumber(event.start_at, event.timezone) }}</span>
          <span class="mt-1 font-display text-base leading-none sm:text-lg">{{ monthShort(event.start_at, event.timezone) }}</span>
          <span class="mt-2 text-xs font-semibold">{{ timeOnly(event.start_at, event.timezone) }}</span>
        </div>
        <div class="flex min-w-0 flex-1 flex-col justify-center gap-1 px-3 py-3 sm:px-4">
          <h3 class="line-clamp-2 text-lg sm:text-[1.4rem]">{{ event.title }}</h3>
          <p class="truncate text-sm text-ink-soft">{{ event.venue.name }}, {{ event.venue.city }}</p>
          <p class="text-sm text-ink-soft first-letter:uppercase">{{ weekday(event.start_at, event.timezone) }}</p>
          <p class="mt-1 flex flex-wrap gap-1.5">
            <span class="badge">{{ event.category }}</span>
            <span v-if="event.status === 'cancelled'" class="badge badge-bad">{{ $t('status.cancelled') }}</span>
            <span v-else-if="!event.is_on_sale" class="badge badge-warn">{{ $t('event.salesClosed') }}</span>
          </p>
        </div>
      </div>
      <div class="ticket-stub relative flex min-w-0 flex-col items-center justify-center gap-1 overflow-hidden px-1.5 py-3 text-center sm:px-2">
        <img v-if="cover" :src="cover" alt="" class="absolute inset-0 h-full w-full object-cover opacity-15" />
        <template v-if="event.price_from === 0">
          <span class="relative font-display text-base leading-tight font-semibold sm:text-2xl">{{ $t('event.free') }}</span>
        </template>
        <template v-else-if="event.price_from !== null">
          <span class="relative text-xs text-ink-soft">{{ $t('event.from') }}</span>
          <span class="relative font-display text-base leading-tight font-semibold whitespace-nowrap sm:text-2xl">{{ money(event.price_from) }}</span>
        </template>
        <span class="relative mt-1 text-xs font-semibold text-sky-deep underline sm:text-sm">{{ $t('event.details') }}</span>
      </div>
    </RouterLink>
  </article>
</template>
