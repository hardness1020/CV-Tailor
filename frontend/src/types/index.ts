// Core API Types
export interface User {
  id: number;
  email: string;
  username: string;
  firstName: string;
  lastName: string;
  profileImage?: string;
  phone?: string;
  linkedinUrl?: string;
  githubUrl?: string;
  websiteUrl?: string;
  bio?: string;
  location?: string;
  preferredCvTemplate?: number;
  emailNotifications?: boolean;
  createdAt: string;
  updatedAt: string;
}

// Authentication Types
export interface AuthResponse {
  user: User;
  access: string;
  refresh: string;
}

export interface RegisterData {
  email: string;
  password: string;
  passwordConfirm: string;
  firstName: string;
  lastName: string;
}

// Artifact Types
export type ArtifactStatus = 'draft' | 'processing' | 'review_pending' | 'reunifying' | 'review_finalized' | 'complete' | 'abandoned';

export interface Artifact {
  id: number;
  title: string;
  description: string;
  userContext?: string; // NEW (ft-018): User-provided context for enrichment
  artifactType: 'project' | 'experience' | 'education' | 'certification' | 'publication' | 'presentation';
  startDate: string;
  endDate?: string;
  technologies: string[];
  evidenceLinks: EvidenceLink[];
  labels: Label[];
  // Wizard workflow status (6-step wizard)
  status: ArtifactStatus;
  lastWizardStep?: number; // Last step user reached (1-6) for resume capability
  wizardCompletedAt?: string; // Timestamp when user accepted artifact (Step 6)
  extractedMetadata?: Record<string, any>;
  // Enriched fields (AI-generated)
  unifiedDescription?: string;
  enrichedTechnologies?: string[];
  enrichedAchievements?: string[];
  processingConfidence?: number;
  createdAt: string;
  updatedAt: string;
}

export interface EvidenceLink {
  id: number;
  url: string;
  evidenceType: 'github' | 'document';
  description: string;
  filePath?: string;
  file_size?: number;
  mime_type?: string;
  mimeType?: string;
  isAccessible?: boolean;
  lastValidated?: string;
  validationMetadata?: Record<string, any>;
  createdAt?: string;
  updatedAt?: string;
}

export interface Label {
  id: number;
  name: string;
  color: string;
  description?: string;
}

export interface ArtifactCreateData {
  title: string;
  description?: string; // OPTIONAL (ft-018): AI will enhance this using evidence
  userContext?: string; // NEW (ft-018): Optional user-provided context
  artifactType?: 'project' | 'experience' | 'education' | 'certification' | 'publication' | 'presentation';
  startDate?: string;
  endDate?: string;
  technologies?: string[];
  evidenceLinks?: Omit<EvidenceLink, 'id' | 'isAccessible' | 'lastValidated' | 'validationMetadata'>[];
  labelIds?: number[];
  lastWizardStep?: number; // Resume capability: Track current wizard step
}

export interface ArtifactProcessingStatus {
  artifactId: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progressPercentage: number;
  errorMessage?: string;
  processedEvidenceCount: number;
  totalEvidenceCount: number;
  createdAt: string;
  completedAt?: string;
}

// Generation Types
export interface GenerationRequest {
  jobDescription: string;
  companyName: string;
  roleTitle: string;
  labelIds: number[];
  artifactIds?: number[]; // Manual artifact selection (ft-007)
  templateId?: number;
  customSections?: Record<string, any>;
  generationPreferences?: {
    tone: 'professional' | 'technical' | 'creative';
    length: 'concise' | 'detailed';
    focusAreas: string[];
  };
}

export interface GeneratedDocument {
  id: string;
  type: 'cv' | 'cover_letter';
  status: 'pending' | 'processing' | 'bullets_ready' | 'bullets_approved' | 'assembling' | 'completed' | 'failed';
  progressPercentage: number;
  content?: DocumentContent;
  metadata?: {
    artifactsUsed: number[];
    skillMatchScore: number;
    missingSkills: string[];
    generationTime: number;
    modelUsed: string;
  };
  createdAt: string;
  completedAt?: string;
  jobDescriptionHash: string;
  // Two-phase workflow fields (ft-009, ft-024)
  jobTitle?: string;
  companyName?: string;
  bulletsGeneratedAt?: string;
  bulletsCount?: number;
  assembledAt?: string;
  // Status polling fields (ft-026)
  currentPhase?: 'bullet_generation' | 'bullet_review' | 'assembly' | 'completed';
  errorMessage?: string;
  phaseDetails?: {
    bullet_generation?: {
      artifacts_processed: number;
      artifacts_total: number;
      bullets_generated: number;
    };
  };
}

export interface DocumentContent {
  professionalSummary: string;
  keySkills: string[];
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  education: EducationEntry[];
  certifications: CertificationEntry[];
}

export interface ExperienceEntry {
  title: string;
  organization: string;
  duration: string;
  achievements: string[];
  technologiesUsed: string[];
  evidenceReferences: string[];
}

export interface ProjectEntry {
  name: string;
  description: string;
  technologies: string[];
  evidenceUrl: string;
  impactMetrics: string;
}

export interface EducationEntry {
  institution: string;
  degree: string;
  field: string;
  year: string;
  gpa?: string;
}

export interface CertificationEntry {
  name: string;
  issuer: string;
  issueDate: string;
  expiryDate?: string;
  credentialId?: string;
}

// Export Types
export interface ExportRequest {
  format: 'pdf' | 'docx';
  templateId: number;
  options: {
    includeEvidence: boolean;
    evidenceFormat: 'hyperlinks' | 'footnotes' | 'qr_codes';
    pageMargins: 'narrow' | 'normal' | 'wide';
    fontSize: number;
    colorScheme: 'monochrome' | 'accent' | 'full_color';
  };
  sections: {
    includeProfessionalSummary: boolean;
    includeSkills: boolean;
    includeExperience: boolean;
    includeProjects: boolean;
    includeEducation: boolean;
    includeCertifications: boolean;
  };
  watermark?: {
    text: string;
    opacity: number;
  };
}

export interface ExportJob {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  progressPercentage: number;
  errorMessage?: string;
  fileSize?: number;
  downloadUrl?: string;
  expiresAt?: string;
}

// API Response Types
export interface PaginatedResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, any>;
}

// UI State Types
export interface ArtifactFilters {
  search?: string;
  technologies?: string[];
  labelIds?: number[];
  status?: 'active' | 'archived';
  dateRange?: {
    start: string;
    end: string;
  };
}

export interface UploadProgress {
  fileName: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  error?: string;
}

// LLM Services Types
export interface LLMModelStats {
  modelId: string;
  requestsCount: number;
  avgResponseTime: number;
  successRate: number;
  errorCount: number;
  totalTokensUsed: number;
  costUsd: number;
}

export interface LLMSystemHealth {
  status: 'healthy' | 'degraded' | 'down';
  models: {
    [modelId: string]: {
      status: 'available' | 'unavailable';
      responseTimeMs: number;
      lastCheck: string;
    };
  };
  circuitBreakers: {
    [modelId: string]: {
      state: 'closed' | 'open' | 'half-open';
      failureCount: number;
      lastFailure: string;
    };
  };
}

export interface LLMPerformanceMetric {
  id: number;
  modelId: string;
  requestType: string;
  responseTimeMs: number;
  tokensUsed: number;
  costUsd: number;
  success: boolean;
  errorMessage?: string;
  createdAt: string;
}

export interface LLMCostTracking {
  id: number;
  modelId: string;
  date: string;
  totalRequests: number;
  totalTokens: number;
  totalCostUsd: number;
  avgCostPerRequest: number;
}

export interface EnhancedArtifact {
  id: number;
  artifactId: number;
  enhancedDescription: string;
  extractedSkills: string[];
  impactMetrics: string[];
  relevanceScore: number;
  createdAt: string;
  updatedAt: string;
}

// Analytics Types
export interface GenerationAnalytics {
  totalGenerations: number;
  generationsByType: {
    cv: number;
    coverLetter: number;
  };
  avgGenerationTimeSeconds: number;
  successRate: number;
  mostUsedTemplates: Array<{
    templateId: number;
    usageCount: number;
  }>;
  artifactsUsage: Array<{
    artifactId: number;
    usageCount: number;
  }>;
}

export interface ExportAnalytics {
  totalExports: number;
  exportsByFormat: {
    pdf: number;
    docx: number;
  };
  avgExportTimeSeconds: number;
  successRate: number;
  mostUsedTemplates: Array<{
    templateId: number;
    usageCount: number;
  }>;
  fileSizeStats: {
    avgSizeMb: number;
    minSizeMb: number;
    maxSizeMb: number;
  };
}

// Bullet Generation Types (ft-006, ft-024, ft-030)
export interface BulletPoint {
  id: number;
  artifact: number;
  artifactTitle?: string; // Included in grouped responses
  cvGeneration: string | null;
  position: 1 | 2 | 3;
  bulletType: 'achievement' | 'technical' | 'impact';
  text: string;
  keywords: string[];
  metrics: Record<string, string>;
  confidenceScore: number;
  qualityScore: number;
  hasActionVerb: boolean;
  keywordRelevanceScore: number;
  userApproved: boolean;
  userRejected: boolean; // ft-024: Individual bullet rejection
  approvedAt?: string;
  approvedBy?: number;
  userEdited: boolean;
  originalText: string;
  createdAt: string;
  updatedAt: string;

  // ft-030: Anti-Hallucination Verification Fields
  confidence?: number; // Overall confidence score (0.0-1.0)
  confidence_tier?: ConfidenceTier;
  requires_review?: boolean;
  is_blocked?: boolean;
  verification_status?: VerificationStatus;
  verification_confidence?: number;
  hallucination_risk?: HallucinationRisk;
  source_attribution?: SourceAttribution[];
  claim_results?: VerifiedClaim[];
  confidence_breakdown?: ConfidenceBreakdown;
  is_approved?: boolean; // User approval after review
  approved_by_user?: number;
  approved_at_time?: string;
}

export interface BulletGenerationJob {
  id: string;
  artifact: number;
  cvGeneration: string | null;
  user: number;
  jobContext: Record<string, any>;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'needs_review';
  progressPercentage: number;
  generationAttempts: number;
  maxAttempts: number;
  generatedBullets: any[];
  validationResults: BulletValidationResult | null;
  errorMessage?: string;
  errorTraceback?: string;
  processingDurationMs?: number;
  llmCostUsd?: number;
  tokensUsed?: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

export interface BulletValidationResult {
  isValid: boolean;
  overallQualityScore: number;
  structureValid: boolean;
  bulletScores: number[];
  similarityPairs: Array<{ bullet1: number; bullet2: number; similarity: number }>;
  atsCompatibilityScore: number;
  issues: string[];
  suggestions: string[];
}

export interface BulletsByArtifact {
  artifactId: number;
  artifactTitle: string;
  bullets: BulletPoint[];
}

export interface GenerationBulletsResponse {
  generationId: string;
  status: string;
  bulletsCount: number;
  bulletsGeneratedAt: string;
  artifacts: BulletsByArtifact[];
}

export interface BulletGenerationRequest {
  jobContext: {
    roleTitle: string;
    keyRequirements: string[];
    preferredSkills?: string[];
    companyName?: string;
    seniorityLevel?: 'entry' | 'mid' | 'senior' | 'staff' | 'principal' | 'executive';
    industry?: string;
  };
  cvGenerationId?: string;
  regenerate?: boolean;
}

export interface BulletApprovalRequest {
  bulletIds: number[];
  action: 'approve' | 'reject' | 'edit';
  edits?: Record<string, string>; // bulletId -> newText
  feedback?: string;
}

// Enhanced Evidence Types (ft-015)
// ft-030: Source Attribution Types for Enhanced Evidence
export interface SourceAttributionMetadata {
  source_quote: string;
  source_file?: string;  // For GitHub: "README.md", "models.py"
  source_location: string;  // "README.md:## Features" or "models.py:15-23"
  confidence: number;  // 0.0-1.0
  reasoning?: string;
}

export interface AttributedTechnology {
  name: string;
  source_attribution: SourceAttributionMetadata;
}

export interface AttributedAchievement {
  text: string;
  source_attribution: SourceAttributionMetadata;
}

export interface AttributedFeature {
  text: string;
  source_attribution: SourceAttributionMetadata;
}

export interface AttributedPattern {
  name: string;
  source_attribution: SourceAttributionMetadata;
}

export interface AttributionQualityMetrics {
  coverage: number;  // 0.0-1.0 - percentage with source quotes
  inferred_ratio: number;  // 0.0-1.0 - percentage with low confidence
  total_items: number;
  attributed_items: number;
}

export interface EnhancedEvidenceResponse {
  id: string;
  evidenceId: number;
  evidence: number;
  title: string;
  contentType: 'pdf' | 'github' | 'linkedin' | 'web_profile' | 'markdown' | 'text';
  rawContent: string; // JSON string from backend
  processedContent: {
    // ft-030: Support both old format (strings) and new format (attributed objects)
    technologies?: string[] | AttributedTechnology[];
    achievements?: string[] | AttributedAchievement[];
    skills?: string[];
    metrics?: any[]; // Backend returns array, not Record
    summary?: string;
    description?: string;
    projectType?: string;
    patterns?: string[] | AttributedPattern[];
    key_features?: string[] | AttributedFeature[];  // ft-030: GitHub docs
    infrastructure?: {
      deployment?: string[];
      runtime?: string;
      services?: string[];
      webServer?: string;
      ciCd?: string;
      deploymentAutomation?: boolean;
      scaling?: string | null;
    };
    tokensUsed?: number;
    filesAnalyzed?: number;
    refinementIterations?: number;
    // ft-030: Attribution quality metrics
    attribution_coverage?: number;
    inferred_item_ratio?: number;
    documentation_attribution?: AttributionQualityMetrics;
    code_attribution?: AttributionQualityMetrics;
  };
  processingConfidence: number;
  langchainVersion?: string;
  processingStrategy?: string;
  totalChunks?: number;
  processingTimeMs?: number;
  llmModelUsed?: string;
  createdAt: string;
  updatedAt?: string;
  totalProcessingCost?: number;
  userEmail?: string;
}

// ft-026: Unified Generation Status Types (ADR-040)
export interface GenerationStatus {
  generation_id: string;
  status: 'pending' | 'processing' | 'bullets_ready' | 'bullets_approved' | 'assembling' | 'completed' | 'failed';
  progress_percentage: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;

  // Phase tracking
  current_phase: 'bullet_generation' | 'bullet_review' | 'assembly' | 'completed';
  phase_details: {
    bullet_generation: {
      status: 'pending' | 'in_progress' | 'completed' | 'partial';
      artifacts_total: number;
      artifacts_processed: number;
      bullets_generated: number;
      started_at?: string;
      completed_at?: string;
    };
    assembly: {
      status: 'not_started' | 'in_progress' | 'completed' | 'failed';
      started_at?: string;
      completed_at?: string;
    };
  };

  // Sub-job aggregation
  bullet_generation_jobs: BulletGenerationJobStatus[];

  // Processing metrics
  processing_metrics: {
    total_duration_ms?: number;
    total_cost_usd?: number;
    total_tokens_used?: number;
    model_version?: string;
  };

  // Quality metrics
  quality_metrics: {
    average_bullet_quality?: number;
    average_keyword_relevance?: number;
    bullets_approved?: number;
    bullets_rejected?: number;
    bullets_edited?: number;
  };
}

export interface BulletGenerationJobStatus {
  job_id: string;
  artifact_id: number;
  artifact_title: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'needs_review';
  bullets_generated: number;
  processing_duration_ms?: number;
  error_message?: string;
}

// ft-030: Anti-Hallucination Verification Types (ADR-041, ADR-042, ADR-043)
export type ConfidenceTier = 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL'
export type VerificationStatus = 'VERIFIED' | 'INFERRED' | 'UNSUPPORTED' | 'PENDING' | 'ERROR'
export type HallucinationRisk = 'low' | 'medium' | 'high' | 'critical'

export interface SourceAttribution {
  quote: string;
  location: string; // e.g., "page 2, section 'Experience'"
  confidence: number; // 0.0-1.0
}

export interface VerifiedClaim {
  claim: string;
  classification: VerificationStatus;
  confidence: number;
  evidence: string;
  source_location?: string;
}

export interface ConfidenceBreakdown {
  base: number;
  after_verification_penalty: number;
  after_inferred_penalty: number;
  final: number;
}

export interface ConfidenceSignals {
  extraction: number; // 30% weight
  generation: number; // 20% weight
  verification: number; // 50% weight
}

export interface BulletVerificationData {
  // Overall confidence (ADR-043)
  confidence: number; // 0.0-1.0
  confidence_tier: ConfidenceTier;
  requires_review: boolean;
  is_blocked: boolean;

  // Verification status (ADR-042)
  verification_status: VerificationStatus;
  verification_confidence: number;
  hallucination_risk: HallucinationRisk;

  // Source attribution (ADR-041)
  source_attribution: SourceAttribution[];

  // Claim verification results (ADR-042)
  claim_results: VerifiedClaim[];

  // Confidence breakdown for debugging
  confidence_breakdown: ConfidenceBreakdown;
  signals?: ConfidenceSignals;
}

// Review workflow types (ADR-044)
export interface BulletReviewAction {
  bulletIds: number[];
  action: 'approve' | 'reject' | 'edit';
  edits?: Record<string, string>; // bulletId -> newText
  feedback?: string;
}

export interface BulletReviewResponse {
  approved_count?: number;
  rejected_count?: number;
  updated_bullets?: BulletPoint[];
  message?: string;
}