import { useState, useRef, useEffect } from 'react'
import { queryPDF } from '../api/client'
import MessageBubble from './MessageBubble'
import {
  Send, Loader2, FileText, BookOpen,
  Image, Trash2, Sparkles, Shield,
  AlertTriangle, Zap
} from 'lucide-react'

const SUGGESTED_QUESTIONS = [
  "What is this document about?",
  "Summarize the main findings",
  "What charts or images are present?",
  "What are the key statistics mentioned?",
]

export default function ChatInterface({ pdf }) {
  const [chatHistories, setChatHistories] = useState({})
  const [input, setInput]                 = useState('')
  const [isLoading, setIsLoading]         = useState(false)
  const messagesEndRef                    = useRef(null)
  const inputRef                          = useRef(null)

  const messages = chatHistories[pdf.pdf_id] || []

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => {
    inputRef.current?.focus()
  }, [pdf.pdf_id])

  // ── Add message to this PDF's chat history ─────────────
  const addMessage = (pdfId, message) => {
    setChatHistories(prev => ({
      ...prev,
      [pdfId]: [...(prev[pdfId] || []), message]
    }))
  }

  // ── Main send handler ──────────────────────────────────
  const handleSend = async (queryText) => {
    const query = (queryText || input).trim()
    if (!query || isLoading) return

    setInput('')
    const pdfId = pdf.pdf_id

    // Always show user message in chat first
    const userMsgId = Date.now()
    addMessage(pdfId, {
      id:        userMsgId,
      role:      'user',
      content:   query,
      timestamp: new Date()
    })

    setIsLoading(true)

    try {
      const result = await queryPDF(pdfId, query)

      addMessage(pdfId, {
        id:               Date.now() + 1,
        role:             'assistant',
        content:          result.answer,
        sources:          result.sources   || [],
        from_cache:       result.from_cache,
        cache_similarity: result.cache_similarity,
        warnings:         result.warnings  || [],
        latency_ms:       result.latency_ms,
        timestamp:        new Date()
      })

    } catch (err) {
      const status  = err.response?.status
      const errData = err.response?.data

      // ── HTTP 400 — Guardrail blocked ─────────────────
      if (status === 400) {
        const detail     = errData?.detail
        const violations = detail?.violations || []
        const riskLevel  = detail?.risk_level || 'block'
        const hint       = detail?.hint || 'Please rephrase your question.'

        addMessage(pdfId, {
          id:         Date.now() + 1,
          role:       'blocked',
          content:    query,          // original query that was blocked
          violations: violations,
          risk_level: riskLevel,
          hint:       hint,
          timestamp:  new Date()
        })
      }

      // ── HTTP 429 — Rate limited ───────────────────────
      else if (status === 429) {
        const retryAfter = err.response?.headers?.['retry-after'] || '60'

        addMessage(pdfId, {
          id:          Date.now() + 1,
          role:        'rate_limit',
          content:     errData?.detail || 'Rate limit exceeded.',
          retry_after: retryAfter,
          timestamp:   new Date()
        })
      }

      // ── HTTP 500 — Output guardrail / server error ────
      else if (status === 500) {
        const detail     = errData?.detail
        const violations = typeof detail === 'object'
          ? detail?.violations
          : null

        if (violations) {
          // Output guardrail blocked
          addMessage(pdfId, {
            id:         Date.now() + 1,
            role:       'output_blocked',
            violations: violations,
            timestamp:  new Date()
          })
        } else {
          // Generic server error
          addMessage(pdfId, {
            id:        Date.now() + 1,
            role:      'error',
            content:   typeof detail === 'string'
              ? detail
              : 'Something went wrong. Please try again.',
            timestamp: new Date()
          })
        }
      }

      // ── Other errors ──────────────────────────────────
      else {
        addMessage(pdfId, {
          id:        Date.now() + 1,
          role:      'error',
          content:   err.message || 'Unexpected error. Please try again.',
          timestamp: new Date()
        })
      }

    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const clearChat = () => {
    setChatHistories(prev => ({ ...prev, [pdf.pdf_id]: [] }))
  }

  // ============================================================
  return (
    <div className="flex flex-col h-full bg-gray-950">

      {/* ── PDF Info Bar ── */}
      <div className="flex items-center justify-between px-6 py-3
                      bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600/20 rounded-lg">
            <FileText className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-200 truncate max-w-md">
              {pdf.filename}
            </h3>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <BookOpen className="w-3 h-3" />{pdf.page_count} pages
              </span>
              {pdf.image_count > 0 && (
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <Image className="w-3 h-3" />{pdf.image_count} images
                </span>
              )}
              <span className="flex items-center gap-1 text-xs text-green-600">
                <Shield className="w-3 h-3" />Guardrails
              </span>
              <span className="flex items-center gap-1 text-xs text-blue-600">
                <Zap className="w-3 h-3" />Cache
              </span>
            </div>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs
                       text-gray-500 hover:text-gray-300 hover:bg-gray-800
                       rounded-lg transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />Clear chat
          </button>
        )}
      </div>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 ? (
          <WelcomeScreen
            pdf={pdf}
            suggestions={SUGGESTED_QUESTIONS}
            onSuggest={handleSend}
          />
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* ── Input ── */}
      <div className="px-6 py-4 bg-gray-900 border-t border-gray-800">

        {/* Suggested questions when chat is fresh */}
        {messages.length > 0 && messages.length < 3 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {SUGGESTED_QUESTIONS.slice(0, 2).map((q, i) => (
              <button
                key={i}
                onClick={() => handleSend(q)}
                disabled={isLoading}
                className="px-3 py-1 text-xs bg-gray-800 text-gray-400
                           rounded-full hover:bg-gray-700 hover:text-gray-200
                           transition-colors disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask anything about "${pdf.filename}"...`}
            rows={1}
            disabled={isLoading}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-xl
                       px-4 py-3 text-gray-100 placeholder-gray-500 text-sm
                       resize-none focus:outline-none focus:ring-2
                       focus:ring-indigo-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed
                       max-h-32 overflow-y-auto"
            style={{ minHeight: '48px' }}
            onInput={(e) => {
              e.target.style.height = 'auto'
              e.target.style.height =
                Math.min(e.target.scrollHeight, 128) + 'px'
            }}
          />

          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="flex-shrink-0 p-3 bg-indigo-600 text-white rounded-xl
                       hover:bg-indigo-500 transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed
                       focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {isLoading
              ? <Loader2 className="w-5 h-5 animate-spin" />
              : <Send className="w-5 h-5" />
            }
          </button>
        </div>

        <p className="text-xs text-gray-600 mt-2 text-center">
          Protected by{' '}
          <span className="text-green-700">guardrails</span>
          {' · '}
          <span className="text-blue-700">semantic cache</span> enabled
        </p>
      </div>
    </div>
  )
}

// ── Welcome Screen ─────────────────────────────────────────
function WelcomeScreen({ pdf, suggestions, onSuggest }) {
  return (
    <div className="flex flex-col items-center justify-center h-full
                    text-center py-12">
      <div className="w-16 h-16 bg-indigo-900/40 rounded-2xl flex items-center
                      justify-center mb-4">
        <Sparkles className="w-8 h-8 text-indigo-400" />
      </div>
      <h3 className="text-xl font-semibold text-gray-200 mb-1">
        Ready to answer
      </h3>
      <p className="text-sm text-gray-500 mb-2 max-w-sm">
        Ask anything about{' '}
        <span className="text-indigo-400 font-medium">{pdf.filename}</span>
      </p>
      <div className="flex gap-4 mb-8 text-xs text-gray-600">
        <span className="flex items-center gap-1">
          <Shield className="w-3 h-3 text-green-600" />Guardrails active
        </span>
        <span className="flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-blue-600" />Cache active
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 w-full max-w-lg">
        {suggestions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSuggest(q)}
            className="p-3 text-left text-sm bg-gray-900 border border-gray-800
                       text-gray-400 rounded-xl hover:border-indigo-600
                       hover:text-gray-200 hover:bg-gray-800/50 transition-all"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Typing Indicator ───────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-full bg-indigo-700 flex items-center
                      justify-center flex-shrink-0">
        <Sparkles className="w-4 h-4 text-white" />
      </div>
      <div className="bg-gray-800 border border-gray-700 rounded-2xl
                      rounded-tl-sm px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className="typing-dot w-2 h-2 bg-indigo-400 rounded-full" />
          <span className="typing-dot w-2 h-2 bg-indigo-400 rounded-full" />
          <span className="typing-dot w-2 h-2 bg-indigo-400 rounded-full" />
        </div>
      </div>
    </div>
  )
}