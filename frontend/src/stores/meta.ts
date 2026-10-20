import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchMeta } from '@/api/meta'
import type { Meta } from '@/api/types'

export const useMetaStore = defineStore('meta', () => {
  const meta = ref<Meta | null>(null)
  const loading = ref(false)

  async function load() {
    if (meta.value || loading.value) return
    loading.value = true
    try {
      meta.value = await fetchMeta()
    } finally {
      loading.value = false
    }
  }

  return { meta, loading, load }
})
