<script setup lang="ts">
/** Event Admins: people who may scan tickets for this event in the mobile check-in app. */
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { api } from '@/lib/api'
import { dateOnly, errorText } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import { useToastStore } from '@/stores/toast'
import type { StaffAssignment } from '@/types'

const { event } = useManagedEvent()
const toasts = useToastStore()
const { t } = useI18n()

const staff = ref<StaffAssignment[] | null>(null)
const form = reactive({ email: '', can_undo: true })
const problem = ref('')
const base = (): string => `/organizer/events/${event.value.id}/staff`

async function load(): Promise<void> {
  try {
    staff.value = await api.get<StaffAssignment[]>(base())
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function add(): Promise<void> {
  problem.value = ''
  try {
    await api.post(base(), form)
    form.email = ''
    await load()
    toasts.ok(t('staff.added'))
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function remove(assignment: StaffAssignment): Promise<void> {
  if (!window.confirm(t('staff.removeConfirm', { name: assignment.user.name }))) return
  try {
    await api.delete(`${base()}/${assignment.id}`)
    await load()
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(load)
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-[1fr_22rem]">
    <section>
      <p class="mb-4 max-w-[65ch] text-sm text-ink-soft">{{ $t('staff.lead') }}</p>
      <p v-if="!staff" class="text-ink-soft">{{ $t('common.loading') }}</p>
      <p v-else-if="!staff.length" class="card text-ink-soft">{{ $t('staff.empty') }}</p>
      <div v-else class="table-wrap">
        <table class="table">
          <thead><tr><th>{{ $t('staff.person') }}</th><th>{{ $t('staff.undo') }}</th><th>{{ $t('staff.since') }}</th><th><span class="sr-only">{{ $t('common.actions') }}</span></th></tr></thead>
          <tbody>
            <tr v-for="assignment in staff" :key="assignment.id">
              <td>{{ assignment.user.name }}<div class="text-ink-soft">{{ assignment.user.email }}</div></td>
              <td>{{ assignment.can_undo ? $t('common.yes') : $t('common.no') }}</td>
              <td>{{ dateOnly(assignment.created_at) }}</td>
              <td><button type="button" class="btn btn-ghost btn-sm text-bad" @click="remove(assignment)">{{ $t('staff.remove') }}</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <form class="card space-y-4 self-start" @submit.prevent="add">
      <h2 class="card-title">{{ $t('staff.add') }}</h2>
      <div>
        <label class="label" for="staff-email">{{ $t('auth.email') }}</label>
        <input id="staff-email" v-model="form.email" type="email" class="input" required />
        <p class="hint">{{ $t('staff.emailHint') }}</p>
      </div>
      <label class="flex cursor-pointer items-center gap-2"><input v-model="form.can_undo" type="checkbox" class="h-4 w-4" /> {{ $t('staff.canUndo') }}</label>
      <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
      <button type="submit" class="btn btn-primary">{{ $t('staff.assign') }}</button>
    </form>
  </div>
</template>
