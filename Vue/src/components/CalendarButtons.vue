<script setup lang="ts">
/** "Add to calendar": one-click links for common services plus the .ics file. No calendar access is requested. */
import { onMounted, ref } from 'vue'

import { api } from '@/lib/api'

const props = defineProps<{ eventRef: string; accessKey?: string | null }>()
const links = ref<{ ics: string; google: string; outlook: string; office365: string; yahoo: string } | null>(null)

onMounted(async () => {
  try {
    links.value = await api.get(`/events/${props.eventRef}/calendar-links`, { access_key: props.accessKey })
  } catch {
    links.value = null // the buttons are simply not shown
  }
})
</script>

<template>
  <div v-if="links">
    <p class="mb-2 text-sm font-semibold">{{ $t('calendar.add') }}</p>
    <div class="flex flex-wrap gap-2">
      <a class="btn btn-secondary btn-sm" :href="links.google" target="_blank" rel="noopener">Google</a>
      <a class="btn btn-secondary btn-sm" :href="links.outlook" target="_blank" rel="noopener">Outlook</a>
      <a class="btn btn-secondary btn-sm" :href="links.office365" target="_blank" rel="noopener">Office 365</a>
      <a class="btn btn-secondary btn-sm" :href="links.yahoo" target="_blank" rel="noopener">Yahoo</a>
      <a class="btn btn-secondary btn-sm" :href="links.ics">{{ $t('calendar.file') }}</a>
    </div>
  </div>
</template>
