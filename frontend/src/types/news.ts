export type NewsArticle = {
  title: string
  url?: string
  link?: string
  source?: string
  publisher?: string
  sentiment?: string
  published_at?: string
  providerPublishTime?: string
}

export type NewsPayload = {
  articles?: NewsArticle[]
  sentiment?: Record<string, unknown>
  sectorwise?: Record<string, unknown>
}
