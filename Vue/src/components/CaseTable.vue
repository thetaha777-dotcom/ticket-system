<script setup lang="ts">
/** List of support cases. Used by "My requests", the organizer's event tab and the admin queue. */
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/StatusBadge.vue'
import { dateTime } from '@/lib/format'
import type { SupportCase } from '@/types'

defineProps<{ cases: SupportCase[]; showRequester?: boolean }>()
</script>

<template>
  <p v-if="!cases.length" class="card text-ink-soft">{{ $t('support.empty') }}</p>
  <div v-else class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>{{ $t('support.request') }}</th>
          <th v-if="showRequester">{{ $t('support.from') }}</th>
          <th>{{ $t('support.category') }}</th>
          <th>{{ $t('support.about') }}</th>
          <th>{{ $t('common.status') }}</th>
          <th>{{ $t('support.updated') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in cases" :key="item.id">
          <td>
            <RouterLink :to="{ name: 'support-case', params: { id: item.id } }" class="font-semibold">{{ item.subject }}</RouterLink>
            <div class="text-ink-soft">{{ item.number }}, {{ $t('support.messages', item.message_count) }}</div>
          </td>
          <td v-if="showRequester">{{ item.requester.name }}<div class="text-ink-soft">{{ item.requester.email }}</div></td>
          <td>{{ $t(`supportCategory.${item.category}`) }}</td>
          <td>
            <div v-if="item.context.event_title">{{ item.context.event_title }}</div>
            <div v-if="item.context.order_number" class="text-ink-soft">{{ $t('order.number', { number: item.context.order_number }) }}</div>
            <div v-if="item.context.ticket_code" class="text-ink-soft">{{ $t('ticket.code', { code: item.context.ticket_code }) }}</div>
          </td>
          <td>
            <StatusBadge :status="item.status" />
            <span v-if="item.is_escalated" class="badge badge-bad mt-1">{{ $t('support.escalated') }}</span>
          </td>
          <td class="whitespace-nowrap">{{ dateTime(item.updated_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
