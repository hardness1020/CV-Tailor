/**
 * useArtifactNavigation - Centralized artifact routing logic
 *
 * Determines where to navigate when user clicks an artifact based on:
 * - Artifact status (complete, draft, processing, etc.)
 * - Last wizard step (for resume capability)
 * - Query parameter overrides (for re-enrich flows)
 *
 * Supports backward compatibility with old 9-step wizard artifacts
 */

import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Artifact, ArtifactStatus } from '@/types'

/**
 * Maps old 9-step wizard steps to new 6-step wizard steps
 * Used for backward compatibility when resuming old artifacts
 */
function mapOldStepToNewStep(oldStep: number): number {
  if (oldStep <= 2) return oldStep          // Steps 1-2 unchanged (Basic Info, Context)
  if (oldStep === 3) return 3               // Old Technologies → New Evidence
  if (oldStep === 4) return 3               // Old Evidence → New Evidence
  if (oldStep === 5) return 4               // Old Confirmation → New Confirmation
  if (oldStep >= 6 && oldStep <= 7) return 5 // Old Processing/Review → New Processing & Review
  if (oldStep >= 8 && oldStep <= 9) return 6 // Old Reunification/Acceptance → New Reunification & Acceptance
  return 1                                   // Fallback to Step 1
}

/**
 * Determines the wizard step to resume based on artifact status and lastWizardStep
 */
function getResumeStep(artifact: Artifact, explicitStep?: number): number {
  // Priority 1: Explicit step override (from query params, e.g., re-enrich flows)
  if (explicitStep !== undefined && explicitStep >= 1 && explicitStep <= 6) {
    return explicitStep
  }

  // Priority 2: Status-based step mapping (post-wizard statuses)
  switch (artifact.status) {
    case 'processing':
    case 'review_pending':
      // Processing & Evidence Review step (consolidated)
      return 5

    case 'reunifying':
    case 'review_finalized':
      // Reunification & Acceptance step (consolidated)
      return 6

    case 'complete':
      // Completed artifacts shouldn't resume wizard (should go to detail page)
      // But if explicitly resuming, go to last step
      return 6

    case 'abandoned':
      // Always start from beginning for abandoned artifacts
      return 1

    case 'draft':
      // Priority 3: Use lastWizardStep if available
      if (artifact.lastWizardStep) {
        // Map old step numbers (1-9) to new step numbers (1-6)
        return mapOldStepToNewStep(artifact.lastWizardStep)
      }
      // Fallback: Resume at Step 3 (Evidence) for drafts without step history
      return 3

    default:
      // Unknown status - start from beginning
      return 1
  }
}

/**
 * Determines if artifact should go to detail page or resume wizard
 */
function shouldGoToDetailPage(status: ArtifactStatus): boolean {
  return status === 'complete'
}

export interface ArtifactNavigationOptions {
  /** Explicit step to navigate to (overrides status-based logic) */
  startStep?: number
  /** Whether to replace history instead of push */
  replace?: boolean
}

export function useArtifactNavigation() {
  const navigate = useNavigate()

  /**
   * Navigate to the appropriate page for an artifact
   *
   * @param artifact - The artifact to navigate to
   * @param options - Navigation options
   */
  const navigateToArtifact = useCallback(
    (artifact: Artifact, options?: ArtifactNavigationOptions) => {
      const { startStep, replace = false } = options || {}

      // Complete artifacts go to detail page
      if (shouldGoToDetailPage(artifact.status) && !startStep) {
        navigate(`/artifacts/${artifact.id}`, { replace })
        return
      }

      // All other statuses resume wizard
      const resumeStep = getResumeStep(artifact, startStep)

      // Build query string
      const params = new URLSearchParams()
      if (startStep !== undefined) {
        params.append('startStep', startStep.toString())
      }

      const queryString = params.toString()
      const url = queryString
        ? `/artifacts/upload/${artifact.id}?${queryString}`
        : `/artifacts/upload/${artifact.id}`

      navigate(url, { replace, state: { resumeStep } })
    },
    [navigate]
  )

  /**
   * Navigate to wizard for re-enrichment flows
   *
   * @param artifactId - The artifact ID
   * @param step - The wizard step to navigate to
   */
  const navigateToWizardStep = useCallback(
    (artifactId: number, step: number) => {
      navigate(`/artifacts/upload?artifactId=${artifactId}&startStep=${step}`)
    },
    [navigate]
  )

  return {
    navigateToArtifact,
    navigateToWizardStep,
    getResumeStep,
    mapOldStepToNewStep,
  }
}
