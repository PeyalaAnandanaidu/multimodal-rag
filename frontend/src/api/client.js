import axios from 'axios'

// ============================================================
// Base URL Configuration
// Priority:
// 1. VITE_API_URL environment variable (set in Vercel dashboard)
// 2. Same origin (if frontend and backend on same domain)
// 3. Localhost for development
// ============================================================
const getBaseURL = () => {
  // Production: use environment variable
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  // Development fallback
  return 'http://localhost:8000'
}

const BASE_URL = getBaseURL()

console.log(`[API] Base URL: ${BASE_URL}`)

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 180000, // 3 min (LLM can be slow on free tier)
  headers: {
    'Content-Type': 'application/json',
  }
})

// Request interceptor
api.interceptors.request.use(
  config => {
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
    }
    return config
  },
  error => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  response => response,
  error => {
    const status  = error.response?.status
    const message = error.response?.data?.detail || error.message

    if (import.meta.env.DEV) {
      console.error(`[API Error] ${status}: ${message}`)
    }

    return Promise.reject(error)
  }
)

// ── PDF APIs ──────────────────────────────────────────────

export const uploadPDF = async (file, onProgress) => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/api/pdfs/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
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
  const response = await api.post(
    `/api/pdfs/${pdfId}/query`,
    { query }
  )
  return response.data
}

export const healthCheck = async () => {
  const response = await api.get('/health')
  return response.data
}

export { api }