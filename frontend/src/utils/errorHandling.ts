import toast from 'react-hot-toast'

export interface APIError {
  message: string
  code?: string
  details?: Record<string, any>
  status?: number
}

export class ErrorHandler {
  static handleAPIError(error: any): APIError {
    // Handle axios errors
    if (error.response) {
      const status = error.response.status
      const data = error.response.data

      // Common error patterns
      if (status === 400) {
        return {
          message: data?.detail || data?.error || 'Invalid request data',
          code: 'BAD_REQUEST',
          details: data,
          status,
        }
      }

      if (status === 401) {
        return {
          message: 'Authentication required. Please log in again.',
          code: 'UNAUTHORIZED',
          details: data,
          status,
        }
      }

      if (status === 403) {
        return {
          message: 'You do not have permission to perform this action.',
          code: 'FORBIDDEN',
          details: data,
          status,
        }
      }

      if (status === 404) {
        return {
          message: 'The requested resource was not found.',
          code: 'NOT_FOUND',
          details: data,
          status,
        }
      }

      if (status === 422) {
        // Validation errors
        const fieldErrors = data?.errors || data?.detail || {}
        const firstError = Object.values(fieldErrors)[0]
        return {
          message: Array.isArray(firstError) ? firstError[0] : (firstError as string) || 'Validation error',
          code: 'VALIDATION_ERROR',
          details: fieldErrors,
          status,
        }
      }

      if (status === 429) {
        return {
          message: 'Too many requests. Please try again later.',
          code: 'RATE_LIMITED',
          details: data,
          status,
        }
      }

      if (status >= 500) {
        return {
          message: 'A server error occurred. Please try again later.',
          code: 'SERVER_ERROR',
          details: data,
          status,
        }
      }

      return {
        message: data?.detail || data?.error || 'An unexpected error occurred',
        code: 'UNKNOWN_API_ERROR',
        details: data,
        status,
      }
    }

    // Handle network errors
    if (error.request) {
      return {
        message: 'Network error. Please check your internet connection.',
        code: 'NETWORK_ERROR',
        details: { originalError: error.message },
      }
    }

    // Handle other errors
    return {
      message: error.message || 'An unexpected error occurred',
      code: 'UNKNOWN_ERROR',
      details: { originalError: error },
    }
  }

  static showErrorToast(error: any, fallbackMessage?: string): void {
    const apiError = this.handleAPIError(error)
    toast.error(fallbackMessage || apiError.message)
  }

  static showValidationErrors(error: any): void {
    const apiError = this.handleAPIError(error)

    if (apiError.code === 'VALIDATION_ERROR' && apiError.details) {
      // Show multiple validation errors
      Object.entries(apiError.details).forEach(([field, messages]) => {
        const errorMessage = Array.isArray(messages) ? messages[0] : messages
        toast.error(`${field}: ${errorMessage}`)
      })
    } else {
      toast.error(apiError.message)
    }
  }

  static getFieldError(error: any, fieldName: string): string | null {
    const apiError = this.handleAPIError(error)

    if (apiError.details && apiError.details[fieldName]) {
      const fieldError = apiError.details[fieldName]
      return Array.isArray(fieldError) ? fieldError[0] : fieldError
    }

    return null
  }

  static shouldRetry(error: any): boolean {
    const apiError = this.handleAPIError(error)

    // Retry on network errors and certain server errors
    return (
      apiError.code === 'NETWORK_ERROR' ||
      (!!apiError.status && apiError.status >= 500 && apiError.status !== 501)
    )
  }

  static getRetryDelay(attempt: number): number {
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s (max)
    return Math.min(1000 * Math.pow(2, attempt), 16000)
  }
}

export class RetryableOperation {
  private maxRetries: number

  constructor(maxRetries: number = 3) {
    this.maxRetries = maxRetries
  }

  async execute<T>(
    operation: () => Promise<T>,
    onRetry?: (attempt: number, error: any) => void
  ): Promise<T> {
    let lastError: any

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        return await operation()
      } catch (error) {
        lastError = error

        if (attempt === this.maxRetries || !ErrorHandler.shouldRetry(error)) {
          throw error
        }

        const retryDelay = ErrorHandler.getRetryDelay(attempt)
        onRetry?.(attempt + 1, error)

        await new Promise(resolve => setTimeout(resolve, retryDelay))
      }
    }

    throw lastError
  }
}

// Utility hook for error handling
export function useErrorHandler() {
  const handleError = (error: any, fallbackMessage?: string) => {
    console.error('Handled error:', error)
    ErrorHandler.showErrorToast(error, fallbackMessage)
    return ErrorHandler.handleAPIError(error)
  }

  const handleValidationError = (error: any) => {
    console.error('Validation error:', error)
    ErrorHandler.showValidationErrors(error)
    return ErrorHandler.handleAPIError(error)
  }

  const withRetry = <T>(
    operation: () => Promise<T>,
    options?: { maxRetries?: number; onRetry?: (attempt: number, error: any) => void }
  ) => {
    const retryable = new RetryableOperation(options?.maxRetries)
    return retryable.execute(operation, options?.onRetry)
  }

  return {
    handleError,
    handleValidationError,
    withRetry,
    shouldRetry: ErrorHandler.shouldRetry,
    getFieldError: ErrorHandler.getFieldError,
  }
}