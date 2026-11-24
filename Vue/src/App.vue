<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { LOCALES, setLocale } from '@/i18n'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const auth = useAuthStore()
const toasts = useToastStore()
const router = useRouter()
const { locale } = useI18n()

function signOut(): void {
  auth.logout()
  void router.push({ name: 'home' })
}
</script>

<template>
  <a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-3">{{ $t('nav.skip') }}</a>

  <header class="no-print border-b border-line bg-white">
    <div class="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
      <RouterLink :to="{ name: 'home' }" class="flex items-center gap-2 text-ink no-underline hover:text-ink">
        <img src="/favicon.svg" alt="" class="h-8 w-8" />
        <span class="font-display text-2xl font-semibold tracking-wide">BiletFlow</span>
      </RouterLink>

      <nav :aria-label="$t('nav.main')" class="order-3 flex w-full gap-1 overflow-x-auto text-[0.95rem] font-semibold lg:order-none lg:w-auto lg:flex-1 lg:flex-wrap lg:overflow-visible">
        <RouterLink :to="{ name: 'home' }" class="nav-link">{{ $t('nav.events') }}</RouterLink>
        <template v-if="auth.isSignedIn">
          <RouterLink :to="{ name: 'tickets' }" class="nav-link">{{ $t('nav.tickets') }}</RouterLink>
          <RouterLink :to="{ name: 'orders' }" class="nav-link">{{ $t('nav.orders') }}</RouterLink>
          <RouterLink :to="{ name: 'support' }" class="nav-link">{{ $t('nav.support') }}</RouterLink>
        </template>
        <RouterLink :to="{ name: 'organizer' }" class="nav-link">{{ $t('nav.organizer') }}</RouterLink>
        <RouterLink v-if="auth.isAdmin" :to="{ name: 'admin-overview' }" class="nav-link">{{ $t('nav.admin') }}</RouterLink>
      </nav>

      <div class="ml-auto flex items-center gap-3">
        <div role="group" :aria-label="$t('nav.language')" class="flex rounded-lg border border-line p-0.5">
          <button
            v-for="item in LOCALES" :key="item.code" type="button" :lang="item.code" :aria-pressed="locale === item.code"
            class="cursor-pointer rounded-md px-2 py-1 text-sm font-semibold"
            :class="locale === item.code ? 'bg-ink text-white' : 'text-ink-soft hover:text-ink'"
            @click="setLocale(item.code)"
          >{{ item.label }}</button>
        </div>
        <template v-if="auth.isSignedIn">
          <RouterLink :to="{ name: 'account' }" class="max-w-36 truncate text-sm font-semibold text-ink">{{ auth.user?.name }}</RouterLink>
          <button type="button" class="btn btn-secondary btn-sm" @click="signOut">{{ $t('nav.signOut') }}</button>
        </template>
        <template v-else>
          <RouterLink :to="{ name: 'login' }" class="btn btn-secondary btn-sm">{{ $t('nav.signIn') }}</RouterLink>
          <RouterLink :to="{ name: 'register' }" class="btn btn-primary btn-sm hidden sm:inline-flex">{{ $t('nav.signUp') }}</RouterLink>
        </template>
      </div>
    </div>
  </header>

  <main id="main" tabindex="-1" class="min-h-[70vh] outline-none">
    <RouterView />
  </main>

  <footer class="no-print mt-12 border-t border-line bg-white">
    <div class="mx-auto max-w-6xl px-4 py-6 text-sm text-ink-soft sm:px-6">
      <p class="max-w-[70ch]">{{ $t('footer.demo') }}</p>
    </div>
  </footer>

  <!-- Toasts: announced to screen readers -->
  <div class="no-print fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4" role="status" aria-live="polite">
    <div
      v-for="toast in toasts.items" :key="toast.id"
      class="flex max-w-xl items-start gap-3 rounded-lg px-4 py-3 text-sm font-semibold text-white shadow-lg"
      :class="toast.kind === 'ok' ? 'bg-ink' : 'bg-bad'"
    >
      <span>{{ toast.text }}</span>
      <button type="button" class="cursor-pointer text-white/80 hover:text-white" :aria-label="$t('common.close')" @click="toasts.dismiss(toast.id)">✕</button>
    </div>
  </div>
</template>

<style scoped>
@reference "./styles.css";
.nav-link {
  @apply rounded-md px-2.5 py-1.5 whitespace-nowrap text-ink-soft no-underline hover:text-ink;
}
.nav-link.router-link-exact-active,
.nav-link.router-link-active:not([href="/"]) {
  @apply bg-mist text-ink;
}
</style>
