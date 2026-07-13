import { useState, useEffect } from 'react'
import { listPDFs, healthCheck } from './api/client'
import PDFUploader from './components/PDFUploader'
import PDFList from './components/PDFList'
import ChatInterface from './components/ChatInterface'
import { FileText, Zap, AlertCircle } from 'lucide-react'

export default function App() {
  const [pdfs, setPdfs] = useState([])
  const [selectedPDF, setSelectedPDF] = useState(null)
  const [isOnline, setIsOnline] = useState(null)
  const [loading, setLoading] = useState(true)

  // Check API health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await healthCheck()
        setIsOnline(true)
      } catch {
        setIsOnline(false)
      }
    }
    checkHealth()
  }, [])

  // Load PDFs
  useEffect(() => {
    fetchPDFs()
  }, [])

  const fetchPDFs = async () => {
    try {
      setLoading(true)
      const data = await listPDFs()
      setPdfs(data.pdfs || [])
    } catch (err) {
      console.error('Failed to load PDFs:', err)
    } finally {
      setLoading(false)
    }
  }

  const handlePDFUploaded = (newPDF) => {
    setPdfs(prev => [newPDF, ...prev])
    setSelectedPDF(newPDF)
  }

  const handlePDFDeleted = (pdfId) => {
    setPdfs(prev => prev.filter(p => p.pdf_id !== pdfId))
    if (selectedPDF?.pdf_id === pdfId) {
      setSelectedPDF(null)
    }
  }

  const handleSelectPDF = (pdf) => {
    setSelectedPDF(pdf)
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950">

      {/* ── Header ── */}
      <header className="flex items-center justify-between px-6 py-4 bg-gray-900 border-b border-gray-800 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600 rounded-lg">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">
              Multimodal PDF RAG
            </h1>
            <p className="text-xs text-gray-400">
              Ask questions about your PDFs — text & images understood
            </p>
          </div>
        </div>

        {/* API Status Badge */}
        <div className="flex items-center gap-2">
          {isOnline === null ? (
            <span className="text-xs text-gray-500">Checking API...</span>
          ) : isOnline ? (
            <div className="flex items-center gap-1.5 px-3 py-1 bg-green-900/40 border border-green-700 rounded-full">
              <Zap className="w-3 h-3 text-green-400" />
              <span className="text-xs text-green-400 font-medium">API Online</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1 bg-red-900/40 border border-red-700 rounded-full">
              <AlertCircle className="w-3 h-3 text-red-400" />
              <span className="text-xs text-red-400 font-medium">API Offline</span>
            </div>
          )}
        </div>
      </header>

      {/* ── Main Layout ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Sidebar ── */}
        <aside className="w-80 flex flex-col bg-gray-900 border-r border-gray-800 overflow-hidden">

          {/* Upload Section */}
          <div className="p-4 border-b border-gray-800">
            <PDFUploader onUploaded={handlePDFUploaded} />
          </div>

          {/* PDF List */}
          <div className="flex-1 overflow-y-auto p-4">
            <PDFList
              pdfs={pdfs}
              loading={loading}
              selectedPDF={selectedPDF}
              onSelect={handleSelectPDF}
              onDelete={handlePDFDeleted}
              onRefresh={fetchPDFs}
            />
          </div>
        </aside>

        {/* ── Chat Area ── */}
        <main className="flex-1 overflow-hidden">
          {selectedPDF ? (
            <ChatInterface pdf={selectedPDF} />
          ) : (
            <EmptyState hasPDFs={pdfs.length > 0} />
          )}
        </main>
      </div>
    </div>
  )
}

function EmptyState({ hasPDFs }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      <div className="w-24 h-24 bg-gray-800 rounded-3xl flex items-center justify-center mb-6">
        <FileText className="w-12 h-12 text-gray-600" />
      </div>
      <h2 className="text-2xl font-semibold text-gray-300 mb-2">
        {hasPDFs ? 'Select a PDF to start' : 'Upload your first PDF'}
      </h2>
      <p className="text-gray-500 max-w-md">
        {hasPDFs
          ? 'Click on a PDF from the sidebar to start asking questions about it.'
          : 'Upload a PDF file using the sidebar. Once processed, you can ask questions about its text and images.'
        }
      </p>
    </div>
  )
}