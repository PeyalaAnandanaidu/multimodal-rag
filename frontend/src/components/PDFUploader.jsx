import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadPDF } from '../api/client'
import { Upload, Loader2, CheckCircle2, XCircle } from 'lucide-react'

export default function PDFUploader({ onUploaded }) {
  const [status, setStatus] = useState('idle') // idle | uploading | success | error
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [processingMsg, setProcessingMsg] = useState('')

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0]
    if (!file) return

    setStatus('uploading')
    setError('')
    setProgress(0)
    setProcessingMsg('Uploading PDF...')

    try {
      // Step 1: Upload
      setProcessingMsg('Uploading PDF...')
      const result = await uploadPDF(file, (pct) => {
        setProgress(pct)
        if (pct === 100) {
          setProcessingMsg('Extracting text & images...')
        }
      })

      setProcessingMsg('Building vector index...')
      await new Promise(r => setTimeout(r, 500)) // brief UX pause

      setStatus('success')
      setProcessingMsg('')

      onUploaded({
        pdf_id: result.pdf_id,
        filename: result.filename || file.name,
        page_count: result.page_count,
        doc_count: result.doc_count,
        image_count: result.image_count,
        created_at: new Date().toISOString()
      })

      // Reset after 3s
      setTimeout(() => {
        setStatus('idle')
        setProgress(0)
      }, 3000)

    } catch (err) {
      setStatus('error')
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Upload failed. Please try again.'
      )
      setTimeout(() => {
        setStatus('idle')
        setProgress(0)
        setError('')
      }, 5000)
    }
  }, [onUploaded])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: status === 'uploading'
  })

  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Upload PDF
      </h2>

      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-xl p-5 text-center cursor-pointer
          transition-all duration-200
          ${isDragActive
            ? 'border-indigo-500 bg-indigo-950/30'
            : status === 'uploading'
            ? 'border-blue-600 bg-blue-950/20 cursor-not-allowed'
            : status === 'success'
            ? 'border-green-600 bg-green-950/20'
            : status === 'error'
            ? 'border-red-600 bg-red-950/20'
            : 'border-gray-700 bg-gray-800/50 hover:border-indigo-600 hover:bg-gray-800'
          }
        `}
      >
        <input {...getInputProps()} />

        {status === 'idle' && (
          <>
            <Upload className={`
              w-8 h-8 mx-auto mb-2 transition-colors
              ${isDragActive ? 'text-indigo-400' : 'text-gray-500'}
            `} />
            <p className="text-sm font-medium text-gray-300">
              {isDragActive ? 'Drop PDF here' : 'Drop PDF or click to browse'}
            </p>
            <p className="text-xs text-gray-600 mt-1">Max 50MB</p>
          </>
        )}

        {status === 'uploading' && (
          <div className="py-1">
            <Loader2 className="w-8 h-8 mx-auto mb-2 text-blue-400 animate-spin" />
            <p className="text-sm font-medium text-blue-300">{processingMsg}</p>
            {progress > 0 && progress < 100 && (
              <div className="mt-3 bg-gray-700 rounded-full h-1.5">
                <div
                  className="bg-blue-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}
            {progress === 100 && (
              <div className="mt-3 bg-gray-700 rounded-full h-1.5">
                <div className="bg-yellow-500 h-1.5 rounded-full w-full animate-pulse" />
              </div>
            )}
          </div>
        )}

        {status === 'success' && (
          <>
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-green-400" />
            <p className="text-sm font-medium text-green-300">
              PDF processed successfully!
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-8 h-8 mx-auto mb-2 text-red-400" />
            <p className="text-sm font-medium text-red-300">Upload failed</p>
            <p className="text-xs text-red-400 mt-1 line-clamp-2">{error}</p>
          </>
        )}
      </div>
    </div>
  )
}