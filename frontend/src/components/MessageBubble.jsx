import ReactMarkdown from 'react-markdown'
import {
  BookOpen, Image, AlertCircle, User,
  Sparkles, Clock, AlertTriangle,
  ShieldX, ShieldAlert, Timer, Zap, Database
} from 'lucide-react'

export default function MessageBubble({ message }) {
  const time = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit'
      })
    : ''

  // ── User Message ─────────────────────────────────────
  if (message.role === 'user') {
    return (
      <div className="flex items-start gap-3 flex-row-reverse">
        <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center
                        justify-center flex-shrink-0">
          <User className="w-4 h-4 text-gray-300" />
        </div>
        <div className="flex flex-col items-end max-w-2xl">
          <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-sm
                          px-4 py-3">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
          {time && (
            <span className="text-xs text-gray-600 mt-1">{time}</span>
          )}
        </div>
      </div>
    )
  }

  // ── Input Guardrail Blocked ───────────────────────────
  if (message.role === 'blocked') {
    return (
      <div className="flex items-start gap-3">

        {/* Shield Icon */}
        <div className="w-8 h-8 rounded-full bg-red-800 flex items-center
                        justify-center flex-shrink-0 mt-0.5">
          <ShieldX className="w-4 h-4 text-white" />
        </div>

        <div className="flex flex-col max-w-2xl flex-1">

          {/* Main blocked card */}
          <div className="bg-red-950/40 border border-red-700/60
                          rounded-2xl rounded-tl-sm overflow-hidden">

            {/* Header */}
            <div className="flex items-center gap-2 px-4 py-3
                            bg-red-900/30 border-b border-red-800/50">
              <ShieldX className="w-4 h-4 text-red-400" />
              <span className="text-sm font-semibold text-red-300">
                Query Blocked by Guardrails
              </span>
              <RiskBadge level={message.risk_level} />
            </div>

            {/* Blocked query */}
            <div className="px-4 py-3 border-b border-red-900/30">
              <p className="text-xs text-red-500 font-medium mb-1">
                Blocked query:
              </p>
              <code className="text-xs text-red-300 bg-red-950/50
                               px-2 py-1 rounded font-mono block">
                "{message.content}"
              </code>
            </div>

            {/* Violations list */}
            {message.violations?.length > 0 && (
              <div className="px-4 py-3 border-b border-red-900/30">
                <p className="text-xs text-red-400 font-semibold mb-2 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  Violations detected:
                </p>
                <ul className="space-y-1">
                  {message.violations.map((v, i) => (
                    <li key={i}
                        className="flex items-start gap-2 text-xs text-red-300">
                      <span className="text-red-500 mt-0.5 flex-shrink-0">•</span>
                      {v}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Hint */}
            {message.hint && (
              <div className="px-4 py-3">
                <p className="text-xs text-red-400/80 flex items-start gap-1.5">
                  <AlertCircle className="w-3 h-3 flex-shrink-0 mt-0.5" />
                  <span>{message.hint}</span>
                </p>
              </div>
            )}
          </div>

          {time && (
            <span className="text-xs text-gray-600 mt-1">{time}</span>
          )}
        </div>
      </div>
    )
  }

  // ── Output Guardrail Blocked ──────────────────────────
  if (message.role === 'output_blocked') {
    return (
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-orange-800 flex items-center
                        justify-center flex-shrink-0">
          <ShieldAlert className="w-4 h-4 text-white" />
        </div>

        <div className="flex flex-col max-w-2xl flex-1">
          <div className="bg-orange-950/40 border border-orange-700/60
                          rounded-2xl rounded-tl-sm overflow-hidden">

            <div className="flex items-center gap-2 px-4 py-3
                            bg-orange-900/30 border-b border-orange-800/50">
              <ShieldAlert className="w-4 h-4 text-orange-400" />
              <span className="text-sm font-semibold text-orange-300">
                Response Blocked by Output Guardrails
              </span>
            </div>

            <div className="px-4 py-3">
              <p className="text-xs text-orange-300">
                The generated response was flagged as unsafe and could not
                be shown. Please rephrase your question.
              </p>

              {message.violations?.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {message.violations.map((v, i) => (
                    <li key={i} className="text-xs text-orange-400">• {v}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          {time && (
            <span className="text-xs text-gray-600 mt-1">{time}</span>
          )}
        </div>
      </div>
    )
  }

  // ── Rate Limit ────────────────────────────────────────
  if (message.role === 'rate_limit') {
    return (
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-yellow-800 flex items-center
                        justify-center flex-shrink-0">
          <Timer className="w-4 h-4 text-white" />
        </div>

        <div className="flex flex-col max-w-2xl flex-1">
          <div className="bg-yellow-950/40 border border-yellow-700/60
                          rounded-2xl rounded-tl-sm overflow-hidden">

            <div className="flex items-center gap-2 px-4 py-3
                            bg-yellow-900/30 border-b border-yellow-800/50">
              <Timer className="w-4 h-4 text-yellow-400" />
              <span className="text-sm font-semibold text-yellow-300">
                Rate Limit Reached
              </span>
            </div>

            <div className="px-4 py-3">
              <p className="text-xs text-yellow-300">{message.content}</p>
              {message.retry_after && (
                <p className="text-xs text-yellow-500 mt-1">
                  ⏱ Retry after: {message.retry_after}s
                </p>
              )}
            </div>
          </div>
          {time && (
            <span className="text-xs text-gray-600 mt-1">{time}</span>
          )}
        </div>
      </div>
    )
  }

  // ── Generic Error ─────────────────────────────────────
  if (message.role === 'error') {
    return (
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-red-900 flex items-center
                        justify-center flex-shrink-0">
          <AlertCircle className="w-4 h-4 text-white" />
        </div>

        <div className="flex flex-col max-w-2xl flex-1">
          <div className="bg-red-950/30 border border-red-800/50
                          rounded-2xl rounded-tl-sm px-4 py-3">
            <p className="text-sm text-red-300">{message.content}</p>
          </div>
          {time && (
            <span className="text-xs text-gray-600 mt-1">{time}</span>
          )}
        </div>
      </div>
    )
  }

  // ── Assistant (normal answer) ─────────────────────────
  return (
    <div className="flex items-start gap-3">

      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-indigo-700 flex items-center
                      justify-center flex-shrink-0">
        <Sparkles className="w-4 h-4 text-white" />
      </div>

      <div className="flex flex-col max-w-3xl flex-1">

        {/* Cache + latency badges */}
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          {message.from_cache && (
            <div className="flex items-center gap-1.5 px-2.5 py-1
                            bg-blue-900/30 border border-blue-800
                            rounded-full">
              <Zap className="w-3 h-3 text-blue-400" />
              <span className="text-xs text-blue-300 font-medium">
                {message.cache_similarity === 1.0
                  ? 'Exact Cache Hit'
                  : `Semantic Cache ${(message.cache_similarity * 100).toFixed(1)}%`
                }
              </span>
            </div>
          )}

          {message.latency_ms !== undefined && (
            <div className="flex items-center gap-1 px-2 py-1
                            bg-gray-800 border border-gray-700 rounded-full">
              <Clock className="w-3 h-3 text-gray-500" />
              <span className="text-xs text-gray-400 font-mono">
                {message.latency_ms}ms
              </span>
            </div>
          )}
        </div>

        {/* Answer bubble */}
        <div className="bg-gray-800 border border-gray-700 rounded-2xl
                        rounded-tl-sm px-5 py-4">
          <div className="prose prose-invert prose-sm max-w-none
                          prose-p:leading-relaxed prose-p:my-2
                          prose-headings:text-gray-200
                          prose-strong:text-gray-100
                          prose-code:text-indigo-300 prose-code:bg-gray-900
                          prose-code:px-1 prose-code:rounded
                          prose-ul:my-2 prose-li:my-0.5
                          prose-blockquote:border-indigo-500
                          prose-blockquote:text-gray-400">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>

        {/* Warnings */}
        {message.warnings?.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.warnings.map((w, i) => (
              <div key={i}
                   className="flex items-start gap-2 px-3 py-1.5
                              bg-yellow-900/20 border border-yellow-800/50
                              rounded-lg">
                <AlertTriangle className="w-3 h-3 text-yellow-500
                                          flex-shrink-0 mt-0.5" />
                <p className="text-xs text-yellow-400">{w}</p>
              </div>
            ))}
          </div>
        )}

        {/* Sources */}
        {message.sources?.length > 0 && (
          <div className="mt-2 ml-1">
            <p className="text-xs text-gray-600 mb-1.5 font-medium
                          uppercase tracking-wider">
              Sources
            </p>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((src, i) => (
                <SourceBadge key={i} source={src} />
              ))}
            </div>
          </div>
        )}

        {time && (
          <span className="text-xs text-gray-600 mt-1 ml-1">{time}</span>
        )}
      </div>
    </div>
  )
}

// ── Risk Level Badge ────────────────────────────────────────
function RiskBadge({ level }) {
  if (!level) return null

  const configs = {
    block:  'bg-red-900/50 border-red-700 text-red-300',
    high:   'bg-orange-900/50 border-orange-700 text-orange-300',
    medium: 'bg-yellow-900/50 border-yellow-700 text-yellow-300',
    low:    'bg-green-900/50 border-green-700 text-green-300',
  }

  return (
    <span className={`
      px-2 py-0.5 rounded-full text-xs font-mono border ml-auto
      ${configs[level] || configs.block}
    `}>
      risk: {level}
    </span>
  )
}

// ── Source Badge ────────────────────────────────────────────
function SourceBadge({ source }) {
  const isImage = source.type === 'image'
  return (
    <div className={`
      flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border
      ${isImage
        ? 'bg-purple-900/30 border-purple-800 text-purple-300'
        : 'bg-blue-900/30 border-blue-800 text-blue-300'
      }
    `}>
      {isImage
        ? <Image className="w-3 h-3" />
        : <BookOpen className="w-3 h-3" />
      }
      <span>
        {isImage ? 'Image' : 'Text'} — Page {source.page}
      </span>
    </div>
  )
}