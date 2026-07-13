import { Zap, Database, Clock } from 'lucide-react'

export default function CacheIndicator({
  fromCache, similarity, fromExact, ageSeconds, latencyMs
}) {
  if (!fromCache) return null

  const formatAge = (seconds) => {
    if (seconds < 60)   return `${Math.round(seconds)}s ago`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`
    return `${Math.round(seconds / 3600)}h ago`
  }

  return (
    <div className="flex items-center gap-2 flex-wrap mt-1">
      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-900/30
                      border border-blue-800 rounded-full">
        <Zap className="w-3 h-3 text-blue-400" />
        <span className="text-xs text-blue-300 font-medium">
          {fromExact ? 'Exact Cache Hit' : `Semantic Cache ${Math.round(similarity * 100)}%`}
        </span>
      </div>

      {latencyMs !== undefined && (
        <div className="flex items-center gap-1 px-2 py-1 bg-gray-800
                        border border-gray-700 rounded-full">
          <Clock className="w-3 h-3 text-gray-500" />
          <span className="text-xs text-gray-400">{latencyMs}ms</span>
        </div>
      )}
    </div>
  )
}