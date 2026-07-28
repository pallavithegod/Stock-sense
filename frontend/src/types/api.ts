export type ApiEnvelope<T> = {
  success?: boolean
  status?: string
  data?: T
  error?: string
  message?: string
}

export type ApiError = {
  message: string
  status?: number
}

export type RequestOptions = {
  signal?: AbortSignal
  timeoutMs?: number
  unwrapData?: boolean
}
