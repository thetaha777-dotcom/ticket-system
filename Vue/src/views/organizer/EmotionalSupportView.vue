<script setup lang="ts">
import { RouterLink } from 'vue-router'

const catPhotos = [
  '02295-DIG-Ask-Woodgreen-May-26-A.png',
  '3e841a4b9dfb6d9abac377e684701c31.png',
  'are_siamese_cats_indoor_cats_fea.png',
  'avatars-000103501656-iji6a5-t108.png',
  'original.png',
  'white-cat-breeds-kitten-in-grass.png',
]
</script>

<template>
  <div class="page">
    <div class="mb-6 flex flex-wrap items-center justify-between gap-4">
      <h1>{{ $t('org.emotionalSupport') }}</h1>
      <RouterLink class="btn btn-secondary" :to="{ name: 'organizer-profile' }">{{ $t('common.back') }}</RouterLink>
    </div>
    <p class="mb-6 text-2xl font-semibold text-sky-deep">{{ $t('org.emotionalSupportMessage') }}</p>
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <img
        v-for="photo in catPhotos"
        :key="photo"
        :src="`/cats/${photo}`"
        :alt="$t('org.catPhotoAlt')"
        loading="lazy"
        decoding="async"
        class="aspect-[4/3] w-full border border-line bg-white object-cover"
      />
    </div>
  </div>
</template>
