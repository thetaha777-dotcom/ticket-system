<script setup lang="ts">
/** Accessible modal built on the native <dialog>: focus is trapped and Esc closes it. */
import { ref, watch } from 'vue'

const props = defineProps<{ open: boolean; title: string }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement | null>(null)

watch(
  () => [props.open, dialog.value] as const,
  ([open, el]) => {
    if (!el) return
    if (open && !el.open) el.showModal()
    if (!open && el.open) el.close()
  },
  { immediate: true },
)
</script>

<template>
  <dialog
    ref="dialog" class="m-auto w-[min(34rem,92vw)] rounded-xl border border-line bg-white p-0 text-ink backdrop:bg-ink/50"
    @close="emit('close')" @click.self="emit('close')"
  >
    <div class="p-5 sm:p-6">
      <div class="mb-4 flex items-start justify-between gap-4">
        <h2 class="text-2xl">{{ title }}</h2>
        <button type="button" class="btn btn-ghost" :aria-label="$t('common.close')" @click="emit('close')">✕</button>
      </div>
      <slot />
    </div>
  </dialog>
</template>
