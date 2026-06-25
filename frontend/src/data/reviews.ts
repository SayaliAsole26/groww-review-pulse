export type ProcessedReview = {
  id: string
  text: string
  rating: number
  version: string
  date: string
}

export type ReviewsMetadata = {
  runId: string
  inputCount: number
  processedCount: number
  processedAt: string
}

export type ReviewsPayload = {
  metadata: ReviewsMetadata
  reviews: ProcessedReview[]
}

type RawReview = {
  review_id: string
  text: string
  rating: number
  timestamp: string
  version: string | null
}

type RawFile = {
  metadata: {
    run_id: string
    input_count: number
    count: number
    processed_at: string
  }
  reviews: RawReview[]
}

export function parseReviewsFile(data: RawFile): ReviewsPayload {
  return {
    metadata: {
      runId: data.metadata.run_id,
      inputCount: data.metadata.input_count,
      processedCount: data.metadata.count,
      processedAt: data.metadata.processed_at,
    },
    reviews: data.reviews.map((r) => ({
      id: r.review_id,
      text: r.text,
      rating: r.rating,
      version: r.version ?? '—',
      date: new Date(r.timestamp).toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }),
    })),
  }
}

export async function loadProcessedReviews(): Promise<ReviewsPayload> {
  const response = await fetch('/data/reviews_normalized.json')
  if (!response.ok) {
    throw new Error('Processed reviews not found. Run: cd frontend && npm run sync-reviews')
  }
  const data = (await response.json()) as RawFile
  return parseReviewsFile(data)
}

export function countByRating(reviews: ProcessedReview[]): Record<number, number> {
  const counts: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 }
  for (const review of reviews) {
    if (review.rating >= 1 && review.rating <= 5) {
      counts[review.rating] += 1
    }
  }
  return counts
}
