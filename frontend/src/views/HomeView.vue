<script setup lang="ts">
/** Event discovery: search, filters and the list of upcoming public events. */
import { onMounted, reactive, ref } from 'vue'

import EventTicketCard from '@/components/EventTicketCard.vue'
import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import type { EventCard, Page } from '@/types'

const PAGE_SIZE = 12
const filters = reactive({ q: '', city: '', category: '' })
const options = ref<{ categories: string[]; cities: string[] }>({ categories: [], cities: [] })
const events = ref<EventCard[]>([])
const total = ref(0)
const loading = ref(true)
const problem = ref('')

async function load(reset: boolean): Promise<void> {
  loading.value = true
  problem.value = ''
  try {
    const page = await api.get<Page<EventCard>>('/events', { ...filters, limit: PAGE_SIZE, offset: reset ? 0 : events.value.length })
    events.value = reset ? page.items : [...events.value, ...page.items]
    total.value = page.total
  } catch (error) {
    problem.value = errorText(error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  void load(true)
  try {
    options.value = await api.get('/events/filters')
  } catch {
    /* the filter lists stay empty; search still works */
  }
})
</script>

<template>
  <section class="border-b border-line bg-white">
    <div class="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <h1 class="max-w-[18ch] font-milker">{{ $t('home.title') }}</h1>
      <p class="mt-3 max-w-[60ch] text-lg text-ink-soft">{{ $t('home.lead') }}</p>

      <form class="mt-7 grid gap-3 sm:grid-cols-[2fr_1fr_1fr_auto]" role="search" @submit.prevent="load(true)">
        <div>
          <label class="label" for="search-q">{{ $t('home.search') }}</label>
          <input id="search-q" v-model="filters.q" type="search" class="input" :placeholder="$t('home.searchHint')" />
        </div>
        <div>
          <label class="label" for="search-city">{{ $t('home.city') }}</label>
          <select id="search-city" v-model="filters.city" class="input" @change="load(true)">
            <option value="">{{ $t('home.anyCity') }}</option>
            <option v-for="city in options.cities" :key="city">{{ city }}</option>
          </select>
        </div>
        <div>
          <label class="label" for="search-category">{{ $t('home.category') }}</label>
          <select id="search-category" v-model="filters.category" class="input" @change="load(true)">
            <option value="">{{ $t('home.anyCategory') }}</option>
            <option v-for="category in options.categories" :key="category">{{ category }}</option>
          </select>
        </div>
        <button type="submit" class="btn btn-primary self-end">{{ $t('home.find') }}</button>
      </form>
    </div>
  </section>

  <section class="page" aria-live="polite">
    <h2 class="mb-5">{{ $t('home.upcoming') }} <span v-if="total" class="text-ink-soft">{{ total }}</span></h2>
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <div v-else-if="events.length" class="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
      <EventTicketCard v-for="event in events" :key="event.id" :event="event" />
    </div>
    <p v-else-if="!loading" class="card text-ink-soft">{{ $t('home.empty') }}</p>
    <p v-if="loading" class="mt-4 text-ink-soft">{{ $t('common.loading') }}</p>
    <div v-if="events.length < total && !loading" class="mt-6 text-center">
      <button type="button" class="btn btn-secondary" @click="load(false)">{{ $t('home.more') }}</button>
    </div>
  </section>
</template>
