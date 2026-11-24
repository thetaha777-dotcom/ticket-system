<script setup lang="ts">
/** Platform settings: activation fee, simulated processing fee and checkout hold time. */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import { useToastStore } from '@/stores/toast'
import type { PlatformSettings } from '@/types'

const toasts = useToastStore()
const { t } = useI18n()
const form = ref<PlatformSettings | null>(null)
const problem = ref('')

async function save(): Promise<void> {
  problem.value = ''
  try {
    form.value = await api.put<PlatformSettings>('/admin/settings', form.value)
    toasts.ok(t('admin.settingsSaved'))
  } catch (error) {
    problem.value = errorText(error)
  }
}

onMounted(async () => {
  try {
    form.value = await api.get<PlatformSettings>('/admin/settings')
  } catch (error) {
    problem.value = errorText(error)
  }
})
</script>

<template>
  <p v-if="problem" class="notice notice-bad mb-4" role="alert">{{ problem }}</p>
  <form v-if="form" class="card max-w-xl space-y-4" @submit.prevent="save">
    <div>
      <label class="label" for="set-fee">{{ $t('admin.setting.activationFee') }}</label>
      <input id="set-fee" v-model.number="form.activation_fee_kzt" type="number" min="0" class="input" required />
      <p class="hint">{{ $t('admin.setting.activationFeeHint') }}</p>
    </div>
    <div>
      <label class="label" for="set-processing">{{ $t('admin.setting.processingFee') }}</label>
      <input id="set-processing" v-model.number="form.processing_fee_percent" type="number" min="0" max="50" step="0.1" class="input" required />
      <p class="hint">{{ $t('admin.setting.processingFeeHint') }}</p>
    </div>
    <div>
      <label class="label" for="set-hold">{{ $t('admin.setting.hold') }}</label>
      <input id="set-hold" v-model.number="form.order_hold_minutes" type="number" min="1" max="120" class="input" required />
      <p class="hint">{{ $t('admin.setting.holdHint') }}</p>
    </div>
    <button type="submit" class="btn btn-primary">{{ $t('common.save') }}</button>
  </form>
</template>
