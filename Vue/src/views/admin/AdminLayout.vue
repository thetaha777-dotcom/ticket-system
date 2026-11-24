<script setup lang="ts">
/** Administrative portal for Platform Admins. */
import { RouterLink, RouterView } from 'vue-router'

const TABS = ['overview', 'users', 'events', 'orders', 'payments', 'activations', 'reports', 'support', 'promo', 'audit', 'settings'] as const
</script>

<template>
  <div class="page">
    <h1 class="mb-5">{{ $t('admin.title') }}</h1>
    <nav class="tabs mb-6" :aria-label="$t('admin.sections')">
      <RouterLink v-for="tab in TABS" :key="tab" :to="{ name: `admin-${tab}` }" class="tab" exact-active-class="tab-active">{{ $t(`admin.tab.${tab}`) }}</RouterLink>
    </nav>
    <RouterView />
  </div>
</template>
