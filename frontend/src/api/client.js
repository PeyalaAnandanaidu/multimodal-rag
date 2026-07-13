import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 min for LLM responses
})

// ── PDF APIs ──────────────────────────────────────────────

export const uploadPDF = async (file, onProgress) => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/api/pdfs/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress) {
        const pct = Math.round((e.loaded * 100) / e.total)
        onProgress(pct)
      }
    }
  })
  return response.data
}

export const listPDFs = async () => {
  const response = await api.get('/api/pdfs')
  return response.data
}

export const getPDFInfo = async (pdfId) => {
  const response = await api.get(`/api/pdfs/${pdfId}`)
  return response.data
}

export const deletePDF = async (pdfId) => {
  const response = await api.delete(`/api/pdfs/${pdfId}`)
  return response.data
}

export const queryPDF = async (pdfId, query) => {
  const response = await api.post(`/api/pdfs/${pdfId}/query`, { query })
  return response.data
}

export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}