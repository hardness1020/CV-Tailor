/**
 * ReviewModal component (ft-030 - Anti-Hallucination Improvements)
 *
 * Comprehensive review interface for flagged bullet points.
 * Implements ADR-044: Review Workflow UX.
 *
 * Features:
 * - Confidence tier visualization
 * - Source attribution display
 * - Verified claims breakdown
 * - Approve/Edit/Reject actions
 * - Confidence breakdown for debugging
 */

import { AlertCircle, CheckCircle2, XCircle, Shield } from 'lucide-react'
import type { BulletPoint } from '@/types'
import ConfidenceBadge from './ConfidenceBadge'
import SourceAttributionCard from './SourceAttributionCard'
import ReviewActionBar from './ReviewActionBar'
import { Modal } from './ui/Modal'

interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  bullet: BulletPoint;
  onApprove: (bulletId: number) => void | Promise<void>;
  onReject: (bulletId: number, regenerate?: boolean) => void | Promise<void>;
  onEdit: (bulletId: number, newText: string) => void | Promise<void>;
  isLoading?: boolean;
}

export default function ReviewModal({
  isOpen,
  onClose,
  bullet,
  onApprove,
  onReject,
  onEdit,
  isLoading = false
}: ReviewModalProps) {
  const verifiedClaims = bullet.claim_results?.filter(c => c.classification === 'VERIFIED') || []
  const inferredClaims = bullet.claim_results?.filter(c => c.classification === 'INFERRED') || []
  const unsupportedClaims = bullet.claim_results?.filter(c => c.classification === 'UNSUPPORTED') || []

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Review Bullet Point"
      size="xl"
    >
      <div className="space-y-6">
        {/* Header: Confidence Overview */}
        <div className="flex items-start justify-between gap-4 p-4 bg-gradient-to-r from-gray-50 to-slate-50 rounded-xl border-2 border-gray-200">
          <div className="flex-1">
            <h3 className="text-lg font-bold text-gray-900 mb-1">
              Confidence Assessment
            </h3>
            <p className="text-sm text-gray-600">
              Review the evidence and take action on this bullet point
            </p>
          </div>
          {bullet.confidence_tier && (
            <ConfidenceBadge
              confidence={bullet.confidence || 0}
              tier={bullet.confidence_tier}
              requiresReview={bullet.requires_review}
              isBlocked={bullet.is_blocked}
              showDetailed={false}
            />
          )}
        </div>

        {/* Bullet Text */}
        <div className="space-y-2">
          <label className="block text-sm font-bold text-gray-700">
            Bullet Point Text
          </label>
          <div className="p-4 bg-white rounded-lg border-2 border-gray-200">
            <p className="text-sm text-gray-800 leading-relaxed">
              {bullet.text}
            </p>
          </div>
        </div>

        {/* Detailed Confidence Breakdown */}
        {bullet.confidence_tier && (
          <div>
            <ConfidenceBadge
              confidence={bullet.confidence || 0}
              tier={bullet.confidence_tier}
              requiresReview={bullet.requires_review}
              isBlocked={bullet.is_blocked}
              showDetailed={true}
            />
          </div>
        )}

        {/* Source Attribution */}
        {bullet.source_attribution && bullet.source_attribution.length > 0 && (
          <div>
            <SourceAttributionCard attributions={bullet.source_attribution} />
          </div>
        )}

        {/* Verified Claims Breakdown */}
        {bullet.claim_results && bullet.claim_results.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-blue-600" />
              <h4 className="text-sm font-bold text-gray-900">
                Claim Verification Results
              </h4>
            </div>

            <div className="space-y-2">
              {/* Verified Claims */}
              {verifiedClaims.length > 0 && (
                <details open className="group">
                  <summary className="flex items-center gap-2 p-2 rounded-lg bg-green-50 border border-green-200 cursor-pointer hover:bg-green-100 transition-colors">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-bold text-green-800">
                      {verifiedClaims.length} Verified {verifiedClaims.length === 1 ? 'Claim' : 'Claims'}
                    </span>
                  </summary>
                  <div className="mt-2 pl-6 space-y-2">
                    {verifiedClaims.map((claim, idx) => (
                      <div key={idx} className="p-2 bg-white rounded border border-green-200">
                        <p className="text-xs text-gray-700">
                          <span className="font-bold">Claim:</span> {claim.claim}
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          <span className="font-bold">Evidence:</span> {claim.evidence}
                        </p>
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {/* Inferred Claims */}
              {inferredClaims.length > 0 && (
                <details className="group">
                  <summary className="flex items-center gap-2 p-2 rounded-lg bg-blue-50 border border-blue-200 cursor-pointer hover:bg-blue-100 transition-colors">
                    <AlertCircle className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-bold text-blue-800">
                      {inferredClaims.length} Inferred {inferredClaims.length === 1 ? 'Claim' : 'Claims'}
                    </span>
                  </summary>
                  <div className="mt-2 pl-6 space-y-2">
                    {inferredClaims.map((claim, idx) => (
                      <div key={idx} className="p-2 bg-white rounded border border-blue-200">
                        <p className="text-xs text-gray-700">
                          <span className="font-bold">Claim:</span> {claim.claim}
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          <span className="font-bold">Note:</span> Could not find direct supporting evidence
                        </p>
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {/* Unsupported Claims */}
              {unsupportedClaims.length > 0 && (
                <details open className="group">
                  <summary className="flex items-center gap-2 p-2 rounded-lg bg-red-50 border border-red-200 cursor-pointer hover:bg-red-100 transition-colors">
                    <XCircle className="h-4 w-4 text-red-600" />
                    <span className="text-sm font-bold text-red-800">
                      {unsupportedClaims.length} Unsupported {unsupportedClaims.length === 1 ? 'Claim' : 'Claims'}
                    </span>
                  </summary>
                  <div className="mt-2 pl-6 space-y-2">
                    {unsupportedClaims.map((claim, idx) => (
                      <div key={idx} className="p-2 bg-white rounded border border-red-200">
                        <p className="text-xs text-gray-700">
                          <span className="font-bold">Claim:</span> {claim.claim}
                        </p>
                        <p className="text-xs text-red-600 mt-1">
                          <span className="font-bold">Warning:</span> No supporting evidence found in source documents
                        </p>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        )}

        {/* Confidence Breakdown (Debug Info) */}
        {bullet.confidence_breakdown && (
          <details className="group">
            <summary className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 border border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors">
              <span className="text-xs font-bold text-gray-600">
                ⚙️ Technical Details
              </span>
            </summary>
            <div className="mt-2 p-3 bg-white rounded-lg border border-gray-200 space-y-2">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="font-bold text-gray-700">Base Confidence:</span>
                  <span className="ml-2 text-gray-600">{(bullet.confidence_breakdown.base * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="font-bold text-gray-700">After Verification Penalty:</span>
                  <span className="ml-2 text-gray-600">{(bullet.confidence_breakdown.after_verification_penalty * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="font-bold text-gray-700">After Inferred Penalty:</span>
                  <span className="ml-2 text-gray-600">{(bullet.confidence_breakdown.after_inferred_penalty * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="font-bold text-gray-700">Final Confidence:</span>
                  <span className="ml-2 text-gray-600">{(bullet.confidence_breakdown.final * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
          </details>
        )}

        {/* Action Bar */}
        <div className="pt-4 border-t-2 border-gray-200">
          <ReviewActionBar
            bulletId={bullet.id}
            bulletText={bullet.text}
            isBlocked={bullet.is_blocked}
            onApprove={onApprove}
            onReject={onReject}
            onEdit={onEdit}
            isLoading={isLoading}
          />
        </div>
      </div>
    </Modal>
  )
}
