import { defineStore } from 'pinia'
import { ref } from 'vue'

import * as kbApi from '@/api/kb'
import type { DocumentItem, KnowledgeBase } from '@/api/types'

export const useKbStore = defineStore('kb', () => {
  const knowledgeBases = ref<KnowledgeBase[]>([])
  const current = ref<KnowledgeBase | null>(null)
  const documents = ref<DocumentItem[]>([])
  const loading = ref(false)
  const uploading = ref(false)
  const uploadPercent = ref(0)

  async function loadAdminList() {
    loading.value = true
    try {
      knowledgeBases.value = await kbApi.listAdminKnowledgeBases()
    } finally {
      loading.value = false
    }
  }

  async function loadKb(id: string) {
    loading.value = true
    try {
      current.value = await kbApi.getKnowledgeBase(id)
    } finally {
      loading.value = false
    }
  }

  async function loadDocuments(id: string) {
    const page = await kbApi.listDocuments(id, { page: 1, page_size: 100 })
    documents.value = page.items
  }

  async function create(payload: Parameters<typeof kbApi.createKnowledgeBase>[0]) {
    const kb = await kbApi.createKnowledgeBase(payload)
    knowledgeBases.value.unshift(kb)
    return kb
  }

  async function update(id: string, payload: Parameters<typeof kbApi.updateKnowledgeBase>[1]) {
    const kb = await kbApi.updateKnowledgeBase(id, payload)
    const index = knowledgeBases.value.findIndex((item) => item.id === id)
    if (index >= 0) knowledgeBases.value[index] = kb
    if (current.value?.id === id) current.value = kb
    return kb
  }

  async function remove(id: string) {
    await kbApi.deleteKnowledgeBase(id)
    knowledgeBases.value = knowledgeBases.value.filter((item) => item.id !== id)
    if (current.value?.id === id) current.value = null
  }

  async function upload(kbId: string, file: File, chunkSize: number, chunkOverlap: number) {
    uploading.value = true
    uploadPercent.value = 0
    try {
      const doc = await kbApi.uploadDocument(kbId, file, {
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
        onProgress: (percent) => {
          uploadPercent.value = percent
        },
      })
      documents.value.unshift(doc)
      return doc
    } finally {
      uploading.value = false
    }
  }

  async function deleteDocument(id: string) {
    await kbApi.deleteDocument(id)
    documents.value = documents.value.filter((item) => item.id !== id)
  }

  async function reparseDocument(id: string, payload: { chunk_size?: number; chunk_overlap?: number } = {}) {
    const doc = await kbApi.reparseDocument(id, payload)
    const index = documents.value.findIndex((item) => item.id === id)
    if (index >= 0) documents.value[index] = doc
    return doc
  }

  return {
    knowledgeBases,
    current,
    documents,
    loading,
    uploading,
    uploadPercent,
    loadAdminList,
    loadKb,
    loadDocuments,
    create,
    update,
    remove,
    upload,
    deleteDocument,
    reparseDocument,
  }
})
