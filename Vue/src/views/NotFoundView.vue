<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="page-narrow">
    <h1 class="mb-3">{{ $t('notFound.title') }}</h1>
    <p class="mb-5 text-ink-soft">{{ $t('notFound.text') }}</p>
    <RouterLink class="btn btn-primary" :to="{ name: 'home' }">{{ $t('order.browse') }}</RouterLink>
  </div>
</template>
