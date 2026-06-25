import { useEffect, useMemo, useState } from 'react'
import { GlassCard } from '../components/GlassCard'
import { Icon } from '../components/Icon'
import {
  countByRating,
  loadProcessedReviews,
  type ProcessedReview,
  type ReviewsMetadata,
} from '../data/reviews'

const PAGE_SIZE = 50

function Stars({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Icon
          key={n}
          name="star"
          className={`text-sm ${n <= rating ? 'text-tertiary' : 'text-outline-variant/40'}`}
          filled={n <= rating}
        />
      ))}
    </div>
  )
}

export function ReviewExplorerPage() {
  const [reviews, setReviews] = useState<ProcessedReview[]>([])
  const [metadata, setMetadata] = useState<ReviewsMetadata | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [ratingFilter, setRatingFilter] = useState<number | null>(null)
  const [page, setPage] = useState(1)

  useEffect(() => {
    loadProcessedReviews()
      .then((payload) => {
        setReviews(payload.reviews)
        setMetadata(payload.metadata)
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const ratingCounts = useMemo(() => countByRating(reviews), [reviews])

  const filtered = useMemo(() => {
    return reviews.filter((r) => {
      const matchesQuery = !query || r.text.toLowerCase().includes(query.toLowerCase())
      const matchesRating = ratingFilter === null || r.rating === ratingFilter
      return matchesQuery && matchesRating
    })
  }, [reviews, query, ratingFilter])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageSafe = Math.min(page, totalPages)
  const pageRows = filtered.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE)

  useEffect(() => {
    setPage(1)
  }, [query, ratingFilter])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-on-surface-variant">
        Loading {metadata?.processedCount ?? '…'} processed reviews…
      </div>
    )
  }

  if (error) {
    return (
      <GlassCard className="p-8 text-center">
        <p className="text-error">{error}</p>
        <p className="mt-2 text-sm text-on-surface-variant">
          From project root: <code className="text-primary">python -m pulse ingest</code> then{' '}
          <code className="text-primary">cd frontend && npm run sync-reviews</code>
        </p>
      </GlassCard>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-2xl font-semibold">Review Explorer</h3>
          <p className="text-sm text-on-surface-variant">
            {metadata?.processedCount.toLocaleString()} processed reviews — PII scrubbed
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-xs text-primary">
          <Icon name="shield" className="text-sm" />
          PII scrubbed — no emails or phone numbers displayed
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-3">
          <GlassCard className="p-4">
            <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-on-surface-variant">Stats</h4>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Processed</span>
                <span className="font-bold tabular-nums">{metadata?.processedCount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Raw input</span>
                <span className="font-bold tabular-nums">{metadata?.inputCount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Matching filters</span>
                <span className="font-bold tabular-nums text-primary">{filtered.length.toLocaleString()}</span>
              </div>
            </div>
          </GlassCard>
          <GlassCard className="p-4">
            <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-on-surface-variant">
              Filter by Rating
            </h4>
            <div className="flex flex-col gap-2">
              <button
                type="button"
                onClick={() => setRatingFilter(null)}
                className={`flex items-center justify-between rounded-lg border px-3 py-2 text-xs ${
                  ratingFilter === null
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-outline-variant/20 hover:border-primary hover:text-primary'
                }`}
              >
                <span>All ratings</span>
                <span className="font-bold tabular-nums">{reviews.length.toLocaleString()}</span>
              </button>
              {[5, 4, 3, 2, 1].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setRatingFilter(n)}
                  className={`flex items-center justify-between rounded-lg border px-3 py-2 text-xs ${
                    ratingFilter === n
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-outline-variant/20 hover:border-primary hover:text-primary'
                  }`}
                >
                  <span>{n} ★</span>
                  <span className="font-bold tabular-nums">{ratingCounts[n].toLocaleString()}</span>
                </button>
              ))}
            </div>
          </GlassCard>
        </div>

        <div className="lg:col-span-9">
          <GlassCard className="overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-outline-variant/10 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative flex-1">
                <Icon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
                <input
                  type="search"
                  placeholder="Search review text..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full rounded-lg border border-outline-variant/20 bg-surface-container-lowest py-2 pl-10 pr-4 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
                />
              </div>
              <p className="shrink-0 text-xs text-on-surface-variant">
                Showing {(pageSafe - 1) * PAGE_SIZE + 1}–{Math.min(pageSafe * PAGE_SIZE, filtered.length)} of{' '}
                {filtered.length.toLocaleString()}
              </p>
            </div>
            <div className="custom-scrollbar max-h-[36rem] overflow-y-auto">
              {filtered.length === 0 ? (
                <p className="p-8 text-center text-sm text-on-surface-variant">No reviews match your filters.</p>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 z-10 bg-surface-container-low">
                    <tr>
                      {['Rating', 'Review', 'Version', 'Date'].map((h) => (
                        <th
                          key={h}
                          className="border-b border-outline-variant/10 p-4 text-xs font-medium text-on-surface-variant"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {pageRows.map((review) => (
                      <tr key={review.id} className="hover:bg-surface-container-highest/20">
                        <td className="border-b border-outline-variant/5 p-4">
                          <Stars rating={review.rating} />
                        </td>
                        <td className="max-w-md border-b border-outline-variant/5 p-4 text-on-surface-variant">
                          {review.text}
                        </td>
                        <td className="border-b border-outline-variant/5 p-4">
                          <span className="rounded bg-surface-container-high px-2 py-0.5 text-xs">{review.version}</span>
                        </td>
                        <td className="border-b border-outline-variant/5 p-4 text-xs text-on-surface-variant">
                          {review.date}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            {filtered.length > PAGE_SIZE && (
              <div className="flex items-center justify-between border-t border-outline-variant/10 px-4 py-3">
                <button
                  type="button"
                  disabled={pageSafe <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="rounded-lg border border-outline-variant/20 px-3 py-1.5 text-xs disabled:opacity-40 hover:border-primary hover:text-primary"
                >
                  Previous
                </button>
                <span className="text-xs text-on-surface-variant">
                  Page {pageSafe} of {totalPages}
                </span>
                <button
                  type="button"
                  disabled={pageSafe >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="rounded-lg border border-outline-variant/20 px-3 py-1.5 text-xs disabled:opacity-40 hover:border-primary hover:text-primary"
                >
                  Next
                </button>
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
