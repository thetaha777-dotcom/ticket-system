<script setup lang="ts">
/** Create a new event or edit an existing one. Dates are typed in the event's own time zone. */
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'

import ModalDialog from '@/components/ModalDialog.vue'
import { api } from '@/lib/api'
import { errorText, fromLocalInput, toLocalInput } from '@/lib/format'
import { useToastStore } from '@/stores/toast'
import type { EventManage, Venue } from '@/types'

const props = defineProps<{ id?: string }>()
const router = useRouter()
const toasts = useToastStore()
const { t } = useI18n()

const TIMEZONES = ['Asia/Almaty', 'Asia/Aqtobe', 'Asia/Aqtau', 'Asia/Atyrau', 'Asia/Oral', 'Asia/Qostanay', 'Asia/Qyzylorda', 'Asia/Tashkent', 'Asia/Bishkek', 'Europe/Moscow', 'UTC']
const CATEGORIES = ['Music', 'Technology', 'Business', 'Education', 'Community', 'Sport', 'Film', 'Theatre', 'Food']

const venues = ref<Venue[]>([])
const form = reactive({
  title: '', category: '', description: '', venue_id: '', timezone: 'Asia/Almaty', start: '', end: '', regOpen: '', regClose: '',
  capacity: null as number | null, visibility: 'public', seating: 'general_admission', refund_policy: 'before_event',
  refund_policy_text: '', images: [] as string[],
})
const problem = ref('')
const busy = ref(false)
const uploading = ref(false)

const venueOpen = ref(false)
const venueForm = reactive({ name: '', city: '', address: '', capacity: null as number | null, use_predefined_layout: false })

const selectedVenue = computed(() => venues.value.find((venue) => venue.id === form.venue_id) ?? null)

async function loadVenues(): Promise<void> {
  venues.value = await api.get<Venue[]>('/venues')
}

async function createVenue(): Promise<void> {
  try {
    const venue = await api.post<Venue>('/venues', venueForm)
    await loadVenues()
    form.venue_id = venue.id
    venueOpen.value = false
    toasts.ok(t('eventForm.venueCreated'))
  } catch (error) {
    toasts.error(error)
  }
}

async function addImage(change: Event): Promise<void> {
  const input = change.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    form.images.push(await api.uploadImage(file))
  } catch (error) {
    toasts.error(error)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function save(): Promise<void> {
  busy.value = true
  problem.value = ''
  const body = {
    title: form.title, category: form.category, description: form.description || null, venue_id: form.venue_id, timezone: form.timezone,
    start_at: fromLocalInput(form.start, form.timezone), end_at: fromLocalInput(form.end, form.timezone),
    registration_open_at: fromLocalInput(form.regOpen, form.timezone), registration_close_at: fromLocalInput(form.regClose, form.timezone),
    capacity: form.capacity || null, visibility: form.visibility, seating: form.seating, refund_policy: form.refund_policy,
    refund_policy_text: form.refund_policy_text || null, images: form.images,
  }
  try {
    const saved = props.id ? await api.patch<EventManage>(`/organizer/events/${props.id}`, body) : await api.post<EventManage>('/organizer/events', body)
    toasts.ok(props.id ? t('eventForm.saved') : t('eventForm.created'))
    await router.push({ name: props.id ? 'manage-overview' : 'manage-tickets', params: { id: saved.id } })
  } catch (error) {
    problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    await loadVenues()
    if (props.id) {
      const event = await api.get<EventManage>(`/organizer/events/${props.id}`)
      Object.assign(form, {
        title: event.title, category: event.category, description: event.description ?? '', venue_id: event.venue.id, timezone: event.timezone,
        start: toLocalInput(event.start_at, event.timezone), end: toLocalInput(event.end_at, event.timezone),
        regOpen: toLocalInput(event.registration_open_at, event.timezone), regClose: toLocalInput(event.registration_close_at, event.timezone),
        capacity: event.capacity, visibility: event.visibility, seating: event.seating, refund_policy: event.refund_policy,
        refund_policy_text: event.refund_policy_text ?? '', images: [...event.images],
      })
    }
  } catch (error) {
    problem.value = errorText(error)
  }
})
</script>

<template>
  <div class="page max-w-3xl">
    <RouterLink class="text-sm font-semibold" :to="id ? { name: 'manage-overview', params: { id } } : { name: 'organizer' }">{{ $t('common.back') }}</RouterLink>
    <h1 class="mt-2 mb-6">{{ id ? $t('eventForm.editTitle') : $t('eventForm.newTitle') }}</h1>

    <form class="space-y-6" @submit.prevent="save">
      <section class="card space-y-4">
        <h2 class="card-title">{{ $t('eventForm.basics') }}</h2>
        <div><label class="label" for="ev-title">{{ $t('eventForm.title') }}</label><input id="ev-title" v-model="form.title" class="input" required maxlength="255" /></div>
        <div>
          <label class="label" for="ev-category">{{ $t('eventForm.category') }}</label>
          <input id="ev-category" v-model="form.category" class="input" list="category-list" required maxlength="255" />
          <datalist id="category-list"><option v-for="item in CATEGORIES" :key="item" :value="item" /></datalist>
        </div>
        <div><label class="label" for="ev-description">{{ $t('eventForm.description') }}</label><textarea id="ev-description" v-model="form.description" class="input" rows="6" /></div>
        <div>
          <span class="label">{{ $t('eventForm.images') }}</span>
          <ul v-if="form.images.length" class="mb-2 flex flex-wrap gap-3">
            <li v-for="(image, index) in form.images" :key="image" class="relative">
              <img :src="image" alt="" class="h-20 w-32 rounded-lg border border-line object-cover" />
              <button type="button" class="absolute -top-2 -right-2 h-7 w-7 cursor-pointer rounded-full bg-ink text-white" :aria-label="$t('eventForm.removeImage', { n: index + 1 })" @click="form.images.splice(index, 1)">✕</button>
            </li>
          </ul>
          <input type="file" accept="image/jpeg,image/png,image/webp" class="block text-sm" :aria-label="$t('eventForm.addImage')" :disabled="uploading || form.images.length >= 8" @change="addImage" />
          <p class="hint">{{ $t('eventForm.imagesHint') }}</p>
        </div>
      </section>

      <section class="card space-y-4">
        <h2 class="card-title">{{ $t('eventForm.whenWhere') }}</h2>
        <div>
          <label class="label" for="ev-venue">{{ $t('eventForm.venue') }}</label>
          <div class="flex gap-2">
            <select id="ev-venue" v-model="form.venue_id" class="input" required>
              <option value="" disabled>{{ $t('eventForm.chooseVenue') }}</option>
              <option v-for="venue in venues" :key="venue.id" :value="venue.id">{{ venue.name }}, {{ venue.city }}{{ venue.has_seat_map ? ` (${$t('eventForm.hasSeatMap')})` : '' }}</option>
            </select>
            <button type="button" class="btn btn-secondary shrink-0" @click="venueOpen = true">{{ $t('eventForm.newVenue') }}</button>
          </div>
        </div>
        <div>
          <label class="label" for="ev-tz">{{ $t('eventForm.timezone') }}</label>
          <select id="ev-tz" v-model="form.timezone" class="input"><option v-for="zone in TIMEZONES" :key="zone">{{ zone }}</option></select>
          <p class="hint">{{ $t('eventForm.timezoneHint') }}</p>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div><label class="label" for="ev-start">{{ $t('eventForm.start') }}</label><input id="ev-start" v-model="form.start" type="datetime-local" class="input" required /></div>
          <div><label class="label" for="ev-end">{{ $t('eventForm.end') }}</label><input id="ev-end" v-model="form.end" type="datetime-local" class="input" required :min="form.start" /></div>
          <div><label class="label" for="ev-reg-open">{{ $t('eventForm.regOpen') }}</label><input id="ev-reg-open" v-model="form.regOpen" type="datetime-local" class="input" /><p class="hint">{{ $t('eventForm.regOpenHint') }}</p></div>
          <div><label class="label" for="ev-reg-close">{{ $t('eventForm.regClose') }}</label><input id="ev-reg-close" v-model="form.regClose" type="datetime-local" class="input" /><p class="hint">{{ $t('eventForm.regCloseHint') }}</p></div>
        </div>
      </section>

      <section class="card space-y-4">
        <h2 class="card-title">{{ $t('eventForm.rules') }}</h2>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="label" for="ev-visibility">{{ $t('eventForm.visibility') }}</label>
            <select id="ev-visibility" v-model="form.visibility" class="input">
              <option value="public">{{ $t('visibility.public') }}</option><option value="unlisted">{{ $t('visibility.unlisted') }}</option><option value="private">{{ $t('visibility.private') }}</option>
            </select>
            <p class="hint">{{ $t(`eventForm.visibilityHint.${form.visibility}`) }}</p>
          </div>
          <div>
            <label class="label" for="ev-capacity">{{ $t('eventForm.capacity') }}</label>
            <input id="ev-capacity" v-model.number="form.capacity" type="number" min="1" class="input" />
            <p class="hint">{{ $t('eventForm.capacityHint') }}</p>
          </div>
          <div>
            <label class="label" for="ev-seating">{{ $t('eventForm.seating') }}</label>
            <select id="ev-seating" v-model="form.seating" class="input">
              <option value="general_admission">{{ $t('eventForm.general') }}</option>
              <option value="assigned_seating" :disabled="!selectedVenue?.has_seat_map">{{ $t('eventForm.assigned') }}</option>
            </select>
            <p class="hint">{{ $t('eventForm.seatingHint') }}</p>
          </div>
          <div>
            <label class="label" for="ev-refund">{{ $t('eventForm.refundPolicy') }}</label>
            <select id="ev-refund" v-model="form.refund_policy" class="input">
              <option value="before_event">{{ $t('refundPolicy.before_event') }}</option><option value="anytime">{{ $t('refundPolicy.anytime') }}</option><option value="none">{{ $t('refundPolicy.none') }}</option>
            </select>
          </div>
        </div>
        <div><label class="label" for="ev-refund-text">{{ $t('eventForm.refundText') }}</label><textarea id="ev-refund-text" v-model="form.refund_policy_text" class="input" rows="2" /></div>
      </section>

      <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
      <button type="submit" class="btn btn-primary" :disabled="busy">{{ id ? $t('common.save') : $t('eventForm.createDraft') }}</button>
    </form>

    <ModalDialog :open="venueOpen" :title="$t('eventForm.newVenue')" @close="venueOpen = false">
      <form class="space-y-4" @submit.prevent="createVenue">
        <div><label class="label" for="venue-name">{{ $t('eventForm.venueName') }}</label><input id="venue-name" v-model="venueForm.name" class="input" required /></div>
        <div class="grid gap-3 sm:grid-cols-2">
          <div><label class="label" for="venue-city">{{ $t('home.city') }}</label><input id="venue-city" v-model="venueForm.city" class="input" required /></div>
          <div><label class="label" for="venue-capacity">{{ $t('eventForm.capacity') }}</label><input id="venue-capacity" v-model.number="venueForm.capacity" type="number" min="1" class="input" :disabled="venueForm.use_predefined_layout" /></div>
        </div>
        <div><label class="label" for="venue-address">{{ $t('eventForm.address') }}</label><input id="venue-address" v-model="venueForm.address" class="input" required /></div>
        <label class="flex cursor-pointer items-start gap-2">
          <input v-model="venueForm.use_predefined_layout" type="checkbox" class="mt-1 h-4 w-4" />
          <span><strong class="block">{{ $t('eventForm.useLayout') }}</strong><span class="text-sm text-ink-soft">{{ $t('eventForm.useLayoutHint') }}</span></span>
        </label>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="venueOpen = false">{{ $t('common.cancel') }}</button>
          <button type="submit" class="btn btn-primary">{{ $t('eventForm.saveVenue') }}</button>
        </div>
      </form>
    </ModalDialog>
  </div>
</template>
