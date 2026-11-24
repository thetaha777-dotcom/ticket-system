<script setup lang="ts">
/** Promo-code activity across all events. */
import { onMounted, ref } from 'vue'

import { api } from '@/lib/api'
import { errorText, money } from '@/lib/format'
import type { PromoActivityRow } from '@/types'

const rows = ref<PromoActivityRow[] | null>(null)
const problem = ref('')

onMounted(async () => {
  try {
    rows.value = await api.get<PromoActivityRow[]>('/admin/promo-activity')
  } catch (error) {
    problem.value = errorText(error)
  }
})
</script>

<template>
  <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
  <p v-else-if="!rows" class="text-ink-soft">{{ $t('common.loading') }}</p>
  <p v-else-if="!rows.length" class="card text-ink-soft">{{ $t('promo.empty') }}</p>
  <div v-else class="table-wrap">
    <table class="table">
      <thead><tr><th>{{ $t('promo.name') }}</th><th>{{ $t('order.event') }}</th><th>{{ $t('promo.code') }}</th><th class="num">{{ $t('promo.redemptions') }}</th><th class="num">{{ $t('analytics.discounts') }}</th><th class="num">{{ $t('analytics.net') }}</th></tr></thead>
      <tbody>
        <tr v-for="row in rows" :key="row.campaign_id">
          <td class="font-semibold">{{ row.name }}<span v-if="!row.is_active" class="badge badge-bad ml-2">{{ $t('promo.disabled') }}</span></td>
          <td>{{ row.event_title }}</td><td>{{ row.code }}</td>
          <td class="num">{{ row.redemptions }}<span v-if="row.max_redemptions" class="text-ink-soft"> / {{ row.max_redemptions }}</span></td>
          <td class="num">{{ money(row.discount_amount) }}</td><td class="num">{{ money(row.net_revenue) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
