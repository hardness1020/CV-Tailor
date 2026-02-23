/**
 * localStorage utilities for persisting user preferences
 */

const DISMISSED_PROMPTS_KEY = 'cv-tailor:dismissed-prompts'

interface DismissedPrompts {
  [artifactId: string]: {
    enrichmentPrompt?: boolean
  }
}

/**
 * Check if enrichment prompt has been dismissed for an artifact
 */
export function isEnrichmentPromptDismissed(artifactId: number): boolean {
  try {
    const stored = localStorage.getItem(DISMISSED_PROMPTS_KEY)
    if (!stored) return false

    const dismissed: DismissedPrompts = JSON.parse(stored)
    return dismissed[artifactId]?.enrichmentPrompt === true
  } catch (error) {
    console.error('Failed to read dismissed prompts from localStorage:', error)
    return false
  }
}

/**
 * Mark enrichment prompt as dismissed for an artifact
 */
export function dismissEnrichmentPrompt(artifactId: number): void {
  try {
    const stored = localStorage.getItem(DISMISSED_PROMPTS_KEY)
    const dismissed: DismissedPrompts = stored ? JSON.parse(stored) : {}

    dismissed[artifactId] = {
      ...dismissed[artifactId],
      enrichmentPrompt: true,
    }

    localStorage.setItem(DISMISSED_PROMPTS_KEY, JSON.stringify(dismissed))
  } catch (error) {
    console.error('Failed to save dismissed prompts to localStorage:', error)
  }
}

/**
 * Clear dismissal state for an artifact (useful when enrichment is re-run)
 */
export function clearEnrichmentPromptDismissal(artifactId: number): void {
  try {
    const stored = localStorage.getItem(DISMISSED_PROMPTS_KEY)
    if (!stored) return

    const dismissed: DismissedPrompts = JSON.parse(stored)
    if (dismissed[artifactId]) {
      delete dismissed[artifactId].enrichmentPrompt

      // Clean up empty artifact entries
      if (Object.keys(dismissed[artifactId]).length === 0) {
        delete dismissed[artifactId]
      }

      localStorage.setItem(DISMISSED_PROMPTS_KEY, JSON.stringify(dismissed))
    }
  } catch (error) {
    console.error('Failed to clear dismissed prompts from localStorage:', error)
  }
}
