import { useState } from 'react'
import { deletePDF } from '../api/client'
import {
  FileText, Trash2, RefreshCw, Loader2,
  Image, BookOpen, ChevronRight
} from 'lucide-react'

export default function PDFList({
  pdfs, loading, selectedPDF,
  onSelect, onDelete, onRefresh
}) {

  const [deletingId, setDeletingId] = useState(null)

  const handleDelete = async (e, pdfId) => {
    e.stopPropagation()
    if (!confirm('Delete this PDF and all its data?')) return

    setDeletingId(pdfId)
    try {
      await deletePDF(pdfId)
      onDelete(pdfId)
    } catch (err) {
      alert('Failed to delete PDF')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Your PDFs ({pdfs.length})
        </h2>
        <button
          onClick={onRefresh}
          className="p-1.5 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded-lg transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 text-gray-600 animate-spin" />
        </div>
      ) : pdfs.length === 0 ? (
        <div className="text-center py-8">
          <FileText className="w-10 h-10 text-gray-700 mx-auto mb-2" />
          <p className="text-sm text-gray-600">No PDFs uploaded yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {pdfs.map((pdf) => (
            <PDFCard
              key={pdf.pdf_id}
              pdf={pdf}
              isSelected={selectedPDF?.pdf_id === pdf.pdf_id}
              isDeleting={deletingId === pdf.pdf_id}
              onSelect={() => onSelect(pdf)}
              onDelete={(e) => handleDelete(e, pdf.pdf_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function PDFCard({ pdf, isSelected, isDeleting, onSelect, onDelete }) {
  const date = pdf.created_at
    ? new Date(pdf.created_at).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric'
      })
    : ''

  return (
    <div
      onClick={onSelect}
      className={`
        group relative flex items-start gap-3 p-3 rounded-xl cursor-pointer
        border transition-all duration-150
        ${isSelected
          ? 'bg-indigo-900/30 border-indigo-600 shadow-md shadow-indigo-900/20'
          : 'bg-gray-800/50 border-gray-700/50 hover:bg-gray-800 hover:border-gray-600'
        }
      `}
    >
      {/* Icon */}
      <div className={`
        p-2 rounded-lg flex-shrink-0 transition-colors
        ${isSelected ? 'bg-indigo-600' : 'bg-gray-700 group-hover:bg-gray-600'}
      `}>
        <FileText className="w-4 h-4 text-white" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-200 truncate pr-6" title={pdf.filename}>
          {pdf.filename}
        </p>
        <div className="flex items-center gap-3 mt-1">
          <span className="flex items-center gap-1 text-xs text-gray-500">
            <BookOpen className="w-3 h-3" />
            {pdf.page_count} pages
          </span>
          {pdf.image_count > 0 && (
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <Image className="w-3 h-3" />
              {pdf.image_count} imgs
            </span>
          )}
          {date && (
            <span className="text-xs text-gray-600">{date}</span>
          )}
        </div>
      </div>

      {/* Selected Indicator */}
      {isSelected && (
        <ChevronRight className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-1" />
      )}

      {/* Delete Button */}
      <button
        onClick={onDelete}
        disabled={isDeleting}
        className={`
          absolute top-2 right-2 p-1 rounded-md opacity-0 group-hover:opacity-100
          transition-all hover:bg-red-900/50 hover:text-red-400
          ${isSelected ? 'text-indigo-400' : 'text-gray-500'}
          ${isDeleting ? 'opacity-100' : ''}
        `}
        title="Delete PDF"
      >
        {isDeleting
          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
          : <Trash2 className="w-3.5 h-3.5" />
        }
      </button>
    </div>
  )
}