import axios, { AxiosInstance } from 'axios'
import { useAuthStore } from '@/stores/authStore'
import type {
  User,
  AuthResponse,
  RegisterData,
  Artifact,
  ArtifactCreateData,
  ArtifactFilters,
  PaginatedResponse,
  GenerationRequest,
  GeneratedDocument,
  GenerationStatus,
  ExportRequest,
  ExportJob,
  Label,
  ArtifactProcessingStatus,
  LLMModelStats,
  LLMSystemHealth,
  LLMPerformanceMetric,
  LLMCostTracking,
  EnhancedArtifact,
  EnhancedEvidenceResponse,
  GenerationAnalytics,
  ExportAnalytics,
  BulletPoint,
  BulletValidationResult,
  GenerationBulletsResponse,
  BulletGenerationRequest,
  BulletApprovalRequest
} from '@/types'

class ApiClient {
  public client: AxiosInstance

  constructor() {
    // Use environment variable for base URL, fallback to /api for development with Vite proxy
    const baseURL = import.meta.env.VITE_API_BASE_URL
      ? `${import.meta.env.VITE_API_BASE_URL}/api`
      : '/api'

    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  /**
   * Extract CSRF token from browser cookies
   * Django sets this as 'csrftoken' cookie when CSRF middleware is active
   */
  private getCsrfTokenFromCookie(): string | null {
    const name = 'csrftoken'
    const value = `; ${document.cookie}`
    const parts = value.split(`; ${name}=`)
    if (parts.length === 2) {
      return parts.pop()?.split(';').shift() || null
    }
    return null
  }

  private setupInterceptors() {
    // Request interceptor to add auth token and CSRF token
    this.client.interceptors.request.use(
      (config) => {
        // Add JWT authorization token
        const token = useAuthStore.getState().accessToken
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }

        // Add CSRF token from cookie for state-changing requests
        if (config.method && ['post', 'put', 'patch', 'delete'].includes(config.method.toLowerCase())) {
          const csrfToken = this.getCsrfTokenFromCookie()
          if (csrfToken) {
            config.headers['X-CSRFToken'] = csrfToken
          }
        }

        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          try {
            const refreshToken = useAuthStore.getState().refreshToken
            if (refreshToken) {
              const response = await this.refreshToken()
              useAuthStore.getState().setTokens(response.access, response.refresh)
              return this.client(originalRequest)
            }
          } catch (refreshError) {
            useAuthStore.getState().clearAuth()
            window.location.href = '/login'
            return Promise.reject(refreshError)
          }
        }

        // Don't automatically show error toasts - let components handle error display

        return Promise.reject(error)
      }
    )
  }

  // Authentication endpoints
  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/v1/auth/login/', {
      email,
      password,
    })
    return response.data
  }

  async register(userData: RegisterData): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/v1/auth/register/', userData)
    return response.data
  }

  async refreshToken(): Promise<{ access: string; refresh: string }> {
    const refreshToken = useAuthStore.getState().refreshToken
    const response = await this.client.post<{ access: string; refresh: string }>(
      '/v1/auth/token/refresh/',
      { refresh: refreshToken }
    )
    return response.data
  }

  async logout(): Promise<void> {
    const refreshToken = useAuthStore.getState().refreshToken
    try {
      await this.client.post('/v1/auth/logout/', { refresh: refreshToken })
    } catch (error) {
      // Continue with logout even if server request fails
      console.warn('Logout request failed:', error)
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/v1/auth/profile/')
    return response.data
  }

  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await this.client.patch<User>('/v1/auth/profile/', data)
    return response.data
  }

  async changePassword(data: {
    currentPassword: string;
    newPassword: string;
    newPasswordConfirm: string;
  }): Promise<void> {
    await this.client.post('/v1/auth/change-password/', data)
  }

  async requestPasswordReset(email: string): Promise<void> {
    await this.client.post('/v1/auth/password-reset/', { email })
  }

  // Artifact endpoints
  async getArtifacts(filters?: ArtifactFilters): Promise<PaginatedResponse<Artifact>> {
    const params = new URLSearchParams()

    if (filters?.search) params.append('search', filters.search)
    if (filters?.technologies?.length) {
      filters.technologies.forEach(tech => params.append('technologies', tech))
    }
    if (filters?.labelIds?.length) {
      filters.labelIds.forEach(id => params.append('labels', id.toString()))
    }
    if (filters?.status) params.append('status', filters.status)
    if (filters?.dateRange?.start) params.append('startDate', filters.dateRange.start)
    if (filters?.dateRange?.end) params.append('endDate', filters.dateRange.end)

    const response = await this.client.get<PaginatedResponse<Artifact>>(
      `/v1/artifacts/?${params.toString()}`
    )
    return response.data
  }

  async createArtifact(data: ArtifactCreateData): Promise<Artifact> {
    const response = await this.client.post<Artifact>('/v1/artifacts/', data)
    return response.data
  }

  async updateArtifact(id: number, data: Partial<ArtifactCreateData>): Promise<Artifact> {
    const response = await this.client.patch<Artifact>(`/v1/artifacts/${id}/`, data)
    return response.data
  }

  async deleteArtifact(id: number): Promise<void> {
    await this.client.delete(`/v1/artifacts/${id}/`)
  }

  async getArtifact(id: number): Promise<Artifact> {
    const response = await this.client.get<Artifact>(`/v1/artifacts/${id}/`)
    return response.data
  }

  async uploadArtifactFiles(artifactId: number, files: File[]): Promise<void> {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append(`files`, file)
    })

    await this.client.post(`/v1/artifacts/${artifactId}/upload/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  }

  async getArtifactProcessingStatus(artifactId: number): Promise<ArtifactProcessingStatus> {
    const response = await this.client.get(`/v1/artifacts/${artifactId}/status/`)
    return response.data
  }

  async getTechnologySuggestions(query?: string): Promise<string[]> {
    const params = new URLSearchParams()
    if (query) params.append('q', query)

    const response = await this.client.get<{ suggestions: string[] }>(
      `/v1/artifacts/suggestions/?${params.toString()}`
    )
    return response.data.suggestions
  }

  async getEnhancedEvidence(evidenceId: number): Promise<EnhancedEvidenceResponse> {
    const response = await this.client.get<EnhancedEvidenceResponse>(
      `/v1/llm/enhanced-artifacts/by-evidence/${evidenceId}/`
    )
    return response.data
  }

  async updateEnhancedEvidence(
    enhancedEvidenceId: string,
    data: {
      processedContent: {
        summary?: string;
        description?: string;
        technologies?: string[];
        achievements?: string[];
        skills?: string[];
      }
    }
  ): Promise<EnhancedEvidenceResponse> {
    const response = await this.client.patch<EnhancedEvidenceResponse>(
      `/v1/llm/enhanced-artifacts/${enhancedEvidenceId}/`,
      { processed_content: data.processedContent }
    )
    return response.data
  }

  // Artifact suggestion endpoint (ft-007)
  async suggestArtifactsForJob(
    jobDescription: string,
    limit: number = 10
  ): Promise<{
    artifacts: Array<{
      id: number;
      title: string;
      description: string;
      technologies: string[];
      enriched_technologies: string[];
      relevance_score: number;
      exact_matches: number;
      partial_matches: number;
      fuzzy_matches: number;
      matched_keywords: string[];
      start_date?: string;
      end_date?: string;
      artifact_type: string;
    }>;
    total_artifacts: number;
    returned_count: number;
  }> {
    const response = await this.client.post('/v1/artifacts/suggest-for-job/', {
      job_description: jobDescription,
      limit
    })
    return response.data
  }

  // Generation endpoints
  async createGeneration(
    request: GenerationRequest & { artifactIds?: number[] }
  ): Promise<{ generationId: string }> {
    const response = await this.client.post<{ generationId: string }>(
      '/v1/generations/create/',
      {
        ...request,
        artifact_ids: request.artifactIds  // ft-007: Convert camelCase to snake_case
      }
    )
    return response.data
  }

  async getGeneration(id: string): Promise<GeneratedDocument> {
    const response = await this.client.get<GeneratedDocument>(`/v1/generations/${id}/`)
    return response.data
  }

  /**
   * Get comprehensive unified status for generation and all related jobs.
   * ft-026: Unified Generation Status Endpoint (ADR-040)
   *
   * This endpoint should be used for polling during generation.
   * Use getGeneration() for retrieving final document content.
   */
  async getGenerationStatus(id: string): Promise<GenerationStatus> {
    const response = await this.client.get<GenerationStatus>(
      `/v1/generations/${id}/generation-status/`
    )
    return response.data
  }

  async updateGeneration(
    id: string,
    data: {
      templateId?: number;
      customSections?: Record<string, any>;
      generationPreferences?: {
        tone?: 'professional' | 'technical' | 'creative';
        length?: 'concise' | 'detailed';
      };
    }
  ): Promise<GeneratedDocument> {
    const response = await this.client.patch<GeneratedDocument>(
      `/v1/generations/${id}/`,
      {
        template_id: data.templateId,
        custom_sections: data.customSections,
        generation_preferences: data.generationPreferences,
      }
    )
    return response.data
  }

  async deleteGeneration(id: string): Promise<void> {
    await this.client.delete(`/v1/generations/${id}/`)
  }

  async bulkDeleteGenerations(ids: string[]): Promise<void> {
    // Backend doesn't have bulk delete endpoint, delete one by one
    await Promise.all(ids.map(id => this.deleteGeneration(id)))
  }

  async generateCoverLetter(request: Omit<GenerationRequest, 'templateId'>): Promise<{ generationId: string }> {
    const response = await this.client.post<{ generationId: string }>(
      '/v1/generations/cover-letter/',
      request
    )
    return response.data
  }

  // Export endpoints
  async exportDocument(generationId: string, exportRequest: ExportRequest): Promise<{ exportId: string }> {
    const response = await this.client.post<{ exportId: string }>(
      `/v1/export/create/${generationId}/`,  // ADR-039: Explicit /create/ path with trailing slash
      exportRequest
    )
    return response.data
  }

  async getExportStatus(exportId: string): Promise<ExportJob> {
    const response = await this.client.get<ExportJob>(`/v1/export/${exportId}/status/`)
    return response.data
  }

  async downloadExport(exportId: string): Promise<Blob> {
    const response = await this.client.get(`/v1/export/${exportId}/download/`, {
      responseType: 'blob',
    })
    return response.data
  }

  // Labels and metadata endpoints
  async getLabels(): Promise<Label[]> {
    const response = await this.client.get<Label[]>('/v1/labels/')
    return response.data
  }

  async createLabel(data: { name: string; color: string; description?: string }): Promise<Label> {
    const response = await this.client.post<Label>('/v1/labels/', data)
    return response.data
  }

  async suggestSkills(query: string): Promise<string[]> {
    const response = await this.client.get<{ suggestions: string[] }>(
      `/v1/artifacts/suggestions/?q=${encodeURIComponent(query)}`
    )
    return response.data.suggestions
  }

  // Artifact editing endpoints
  async addEvidenceLink(artifactId: number, linkData: {
    url: string;
    evidenceType: string;
    description?: string;
  }): Promise<{
    id: number;
    url: string;
    evidenceType: string;
    description: string;
    createdAt: string;
  }> {
    const response = await this.client.post(`/v1/artifacts/${artifactId}/evidence-links/`, linkData)
    return response.data
  }

  async updateEvidenceLink(linkId: number, linkData: {
    url?: string;
    evidenceType?: string;
    description?: string;
  }): Promise<{
    id: number;
    url: string;
    evidenceType: string;
    description: string;
    updatedAt: string;
  }> {
    const response = await this.client.put(`/v1/artifacts/evidence-links/${linkId}/`, linkData)
    return response.data
  }

  async deleteEvidenceLink(linkId: number): Promise<void> {
    await this.client.delete(`/v1/artifacts/evidence-links/${linkId}/`)
  }

  async deleteArtifactFile(fileId: string): Promise<void> {
    await this.client.delete(`/v1/artifacts/files/${fileId}/`)
  }

  // Artifact Enrichment endpoints
  async triggerEnrichment(artifactId: number): Promise<{
    status: string;
    artifactId: number;
    taskId: string;
    message: string;
  }> {
    const response = await this.client.post(`/v1/artifacts/${artifactId}/enrich/`)
    return response.data
  }

  async getEnrichmentStatus(artifactId: number): Promise<{
    artifactId: number;
    status: 'not_started' | 'pending' | 'processing' | 'completed' | 'failed';
    progressPercentage: number;
    errorMessage?: string;
    hasEnrichment: boolean;
    enrichment?: {
      sourcesProcessed: number;
      sourcesSuccessful: number;
      processingConfidence: number;
      totalCostUsd: number;
      processingTimeMs: number;
      technologiesCount: number;
      achievementsCount: number;
    };
    createdAt?: string;
    completedAt?: string;
  }> {
    const response = await this.client.get(`/v1/artifacts/${artifactId}/enrichment-status/`)
    return response.data
  }

  async updateEnrichedContent(artifactId: number, data: {
    unifiedDescription?: string;
    enrichedTechnologies?: string[];
    enrichedAchievements?: string[];
  }): Promise<{
    message: string;
    artifactId: number;
    updatedFields: string[];
    enrichedContent: {
      unifiedDescription?: string;
      enrichedTechnologies?: string[];
      enrichedAchievements?: string[];
      processingConfidence?: number;
    };
  }> {
    const response = await this.client.patch(`/v1/artifacts/${artifactId}/enriched-content/`, data)
    return response.data
  }

  // Evidence validation endpoints (Layer 2 validation from ft-010)
  async validateEvidenceLinks(evidenceLinks: Array<{
    url: string;
    evidence_type: string;
  }>): Promise<{
    results: Array<{
      url: string;
      evidence_type: string;
      valid: boolean;
      accessible: boolean;
      status: 'success' | 'warning' | 'error';
      message: string | null;
    }>;
  }> {
    const response = await this.client.post('/v1/artifacts/validate-evidence-links/', {
      evidence_links: evidenceLinks
    })
    return response.data
  }

  // Additional generation endpoints
  async getUserGenerations(): Promise<GeneratedDocument[]> {
    const response = await this.client.get<PaginatedResponse<GeneratedDocument>>('/v1/generations/')
    return response.data.results
  }

  async rateGeneration(generationId: string, rating: number, feedback?: string): Promise<void> {
    await this.client.post(`/v1/generations/${generationId}/rate/`, {
      rating,
      feedback,
    })
  }

  async getGenerationTemplates(): Promise<any[]> {
    const response = await this.client.get<any[]>('/v1/generations/templates/')
    return response.data
  }

  // Additional export endpoints
  async getUserExports(): Promise<ExportJob[]> {
    const response = await this.client.get<PaginatedResponse<ExportJob>>('/v1/export/')
    return response.data.results
  }

  async getExportTemplates(): Promise<any[]> {
    const response = await this.client.get<any[]>('/v1/export/templates/')
    return response.data
  }

  async getExportAnalytics(): Promise<ExportAnalytics> {
    const response = await this.client.get<ExportAnalytics>('/v1/export/analytics/')
    return response.data
  }

  // Analytics endpoints
  async getGenerationAnalytics(): Promise<GenerationAnalytics> {
    const response = await this.client.get<GenerationAnalytics>('/v1/generations/analytics/')
    return response.data
  }

  // LLM Services endpoints
  async getLLMModelStats(): Promise<LLMModelStats[]> {
    const response = await this.client.get<LLMModelStats[]>('/v1/llm/model-stats/')
    return response.data
  }

  async selectLLMModel(modelId: string): Promise<{ message: string; selectedModel: string }> {
    const response = await this.client.post<{ message: string; selectedModel: string }>('/v1/llm/select-model/', { modelId })
    return response.data
  }

  async getLLMSystemHealth(): Promise<LLMSystemHealth> {
    const response = await this.client.get<LLMSystemHealth>('/v1/llm/system-health/')
    return response.data
  }

  async getAvailableLLMModels(): Promise<string[]> {
    const response = await this.client.get<{ models: string[] }>('/v1/llm/available-models/')
    return response.data.models
  }

  async getLLMPerformanceMetrics(params?: Record<string, string>): Promise<PaginatedResponse<LLMPerformanceMetric>> {
    const queryString = params ? `?${new URLSearchParams(params).toString()}` : ''
    const response = await this.client.get<PaginatedResponse<LLMPerformanceMetric>>(`/v1/llm/performance-metrics/${queryString}`)
    return response.data
  }

  async getLLMCircuitBreakers(): Promise<any> {
    const response = await this.client.get('/v1/llm/circuit-breakers/')
    return response.data
  }

  async getLLMCostTracking(params?: Record<string, string>): Promise<PaginatedResponse<LLMCostTracking>> {
    const queryString = params ? `?${new URLSearchParams(params).toString()}` : ''
    const response = await this.client.get<PaginatedResponse<LLMCostTracking>>(`/v1/llm/cost-tracking/${queryString}`)
    return response.data
  }

  async getLLMEnhancedArtifacts(params?: Record<string, string>): Promise<PaginatedResponse<EnhancedArtifact>> {
    const queryString = params ? `?${new URLSearchParams(params).toString()}` : ''
    const response = await this.client.get<PaginatedResponse<EnhancedArtifact>>(`/v1/llm/enhanced-artifacts/${queryString}`)
    return response.data
  }

  // Two-Phase Generation Workflow Endpoints (ft-009, ADR-038: added artifact filter)
  async getGenerationBullets(
    generationId: string,
    artifactId?: number
  ): Promise<GenerationBulletsResponse> {
    const queryParams = artifactId ? `?artifact_id=${artifactId}` : ''
    const response = await this.client.get<GenerationBulletsResponse>(
      `/v1/generations/${generationId}/bullets/${queryParams}`
    )
    return response.data
  }

  async editGenerationBullet(generationId: string, bulletId: number, text: string): Promise<{ message: string; bullet: BulletPoint }> {
    const response = await this.client.patch<{ message: string; bullet: BulletPoint }>(
      `/v1/generations/${generationId}/bullets/${bulletId}/`,
      { text }
    )
    return response.data
  }

  async approveGenerationBullets(generationId: string): Promise<{
    message: string;
    generationId: string;
    status: string;
    bulletsApprovedCount: number;
    nextStep: string;
  }> {
    const response = await this.client.post(
      `/v1/generations/${generationId}/bullets/approve/`
    )
    return response.data
  }

  // ft-024: Individual bullet actions (approve/reject/edit)
  async approveBulletActions(
    generationId: string,
    bulletActions: Array<{
      bullet_id: number
      action: 'approve' | 'reject' | 'edit'
      edited_text?: string
    }>
  ): Promise<{
    generation_id: string
    status: string
    bullets_approved: number
    bullets_rejected: number
    bullets_edited: number
    all_bullets_decided: boolean
    updated_bullets: BulletPoint[]
  }> {
    const response = await this.client.post(
      `/v1/generations/${generationId}/bullets/approve/`,
      { bullet_actions: bulletActions }
    )
    return response.data
  }

  // ft-024: Regenerate bullets with optional refinement prompt
  async regenerateGenerationBullets(
    generationId: string,
    options?: {
      refinementPrompt?: string
      bulletIdsToRegenerate?: number[]
      artifactIds?: number[]
    }
  ): Promise<{
    generation_id: string
    status: string
    message: string
    bullets_regenerated: number
    content_sources_used: string[]
    refinement_prompt_used: boolean
  }> {
    const response = await this.client.post(
      `/v1/generations/${generationId}/bullets/regenerate/`,
      {
        refinement_prompt: options?.refinementPrompt,
        bullet_ids_to_regenerate: options?.bulletIdsToRegenerate,
        artifact_ids: options?.artifactIds
      }
    )
    return response.data
  }

  async assembleGeneration(generationId: string): Promise<{
    generationId: string;
    status: string;
    message: string;
    estimatedCompletion: string;
    pollStatusAt: string;
  }> {
    const response = await this.client.post(
      `/v1/generations/${generationId}/assemble/`
    )
    return response.data
  }

  // Bullet Generation Endpoints (ft-006, ADR-038: generation-scoped)
  async generateBulletsForArtifact(
    generationId: string,
    artifactId: number,
    request: BulletGenerationRequest
  ): Promise<{
    status: string;
    artifactId: number;
    generationId: string;
    estimatedCompletionTime: string;
    statusEndpoint: string;
  }> {
    const response = await this.client.post(
      `/v1/generations/${generationId}/bullets/`,
      {
        artifact_id: artifactId,  // ADR-038: artifact_id in body
        ...request
      }
    )
    return response.data
  }

  // DEPRECATED (ADR-038): Use getGenerationBullets instead
  // Kept for backward compatibility, will be removed in future version
  async previewArtifactBullets(
    artifactId: number,
    params?: {
      includeQualityMetrics?: boolean;
      cvGenerationId?: string;
    }
  ): Promise<{
    bulletPoints: BulletPoint[];
    approvalStatus: {
      allApproved: boolean;
      approvedCount: number;
      totalCount: number;
    };
    qualityAnalysis?: {
      overallQualityScore: number;
      structureValid: boolean;
      bulletScores: number[];
      hasActionVerbs: boolean[];
      keywordRelevance: number[];
    };
  }> {
    // ADR-038: Redirect to generation-scoped endpoint if generation ID provided
    if (params?.cvGenerationId) {
      const response = await this.getGenerationBullets(params.cvGenerationId, artifactId)
      // Transform response to match old format
      const artifact = response.artifacts.find(a => a.artifactId === artifactId)
      return {
        bulletPoints: artifact?.bullets || [],
        approvalStatus: {
          allApproved: false,
          approvedCount: 0,
          totalCount: artifact?.bullets.length || 0
        }
      }
    }
    throw new Error('cvGenerationId is required (ADR-038)')
  }

  // DEPRECATED (ADR-038): Use approveGenerationBullets instead
  // This method now throws an error to force migration
  async approveArtifactBullets(
    _artifactId: number,
    _request: BulletApprovalRequest
  ): Promise<{
    success: boolean;
    action: string;
    bulletPoints?: BulletPoint[];
    message: string;
    feedback?: string;
  }> {
    throw new Error(
      'approveArtifactBullets is deprecated (ADR-038). Use approveGenerationBullets instead.'
    )
  }

  async validateBullets(
    bullets: Array<{ text: string; position: number; bulletType: string }>,
    jobContext: {
      roleTitle: string;
      keyRequirements: string[];
      preferredSkills?: string[];
      companyName?: string;
      seniorityLevel?: 'entry' | 'mid' | 'senior' | 'staff' | 'principal' | 'executive';
      industry?: string;
    }
  ): Promise<{
    validationResults: BulletValidationResult;
  }> {
    const response = await this.client.post(
      '/v1/generations/bullets/validate/',
      { bullets, jobContext }
    )
    return response.data
  }

  // ft-030: Review Workflow Endpoints (Anti-Hallucination Improvements)
  // These endpoints handle approve/reject/edit actions for flagged bullets

  /**
   * Approve a single bullet point after review
   */
  async approveBullet(bulletId: number): Promise<BulletPoint> {
    const response = await this.client.post(
      `/v1/bullets/${bulletId}/approve/`
    )
    return response.data
  }

  /**
   * Reject a single bullet point
   * @param regenerate - Whether to trigger automatic regeneration
   */
  async rejectBullet(
    bulletId: number,
    regenerate: boolean = false
  ): Promise<{ status: string; regenerate: boolean }> {
    const response = await this.client.post(
      `/v1/bullets/${bulletId}/reject/`,
      { regenerate }
    )
    return response.data
  }

  /**
   * Update bullet text after manual editing
   */
  async updateBullet(
    bulletId: number,
    text: string
  ): Promise<BulletPoint> {
    const response = await this.client.put(
      `/v1/bullets/${bulletId}/update/`,
      { text }
    )
    return response.data
  }

  /**
   * Bulk approve multiple bullets
   */
  async bulkApproveBullets(
    bulletIds: number[]
  ): Promise<{ approved_count: number }> {
    const response = await this.client.post(
      '/v1/bullets/bulk-approve/',
      { bullet_ids: bulletIds }
    )
    return response.data
  }

  /**
   * Bulk reject multiple bullets
   */
  async bulkRejectBullets(
    bulletIds: number[]
  ): Promise<{ rejected_count: number }> {
    const response = await this.client.post(
      '/v1/bullets/bulk-reject/',
      { bullet_ids: bulletIds }
    )
    return response.data
  }

  // ft-045: Evidence Review & Acceptance API (Anti-Hallucination Workflow)

  /**
   * Get evidence acceptance status for an artifact
   */
  async getEvidenceAcceptanceStatus(artifactId: number): Promise<{
    canFinalize: boolean;
    totalEvidence: number;
    accepted: number;
    rejected: number;
    pending: number;
    evidenceDetails: EnhancedEvidenceResponse[];
  }> {
    const response = await this.client.get(
      `/v1/artifacts/${artifactId}/evidence-acceptance-status/`
    )
    return response.data
  }

  /**
   * Accept a single evidence item
   */
  async acceptEvidence(
    artifactId: number,
    evidenceId: string,
    reviewNotes?: string
  ): Promise<EnhancedEvidenceResponse> {
    const response = await this.client.post(
      `/v1/artifacts/${artifactId}/evidence/${evidenceId}/accept/`,
      { review_notes: reviewNotes }
    )
    return response.data
  }

  /**
   * Reject a single evidence item
   */
  async rejectEvidence(
    artifactId: number,
    evidenceId: string
  ): Promise<EnhancedEvidenceResponse> {
    const response = await this.client.post(
      `/v1/artifacts/${artifactId}/evidence/${evidenceId}/reject/`
    )
    return response.data
  }

  /**
   * Edit evidence processed content (inline editing)
   */
  async editEvidenceContent(
    artifactId: number,
    evidenceId: string,
    processedContent: any
  ): Promise<EnhancedEvidenceResponse> {
    const response = await this.client.patch(
      `/v1/artifacts/${artifactId}/evidence/${evidenceId}/content/`,
      { processed_content: processedContent }
    )
    return response.data
  }

  /**
   * Finalize evidence review and trigger async LLM reunification
   */
  async finalizeEvidenceReview(artifactId: number): Promise<{
    message: string;
    artifactId: number;
    processingJobId: string;
    phase: number;
  }> {
    const response = await this.client.post(
      `/v1/artifacts/${artifactId}/finalize-evidence-review/`
    )
    return response.data
  }

  /**
   * Accept artifact after reunification (Step 9 of wizard)
   * Sets artifact status to 'complete'
   */
  async acceptArtifact(artifactId: number): Promise<{
    message: string;
    artifactId: number;
    status: string;
  }> {
    const response = await this.client.post(
      `/v1/artifacts/${artifactId}/accept-artifact/`
    )
    return response.data
  }
}

// Create singleton instance
export const apiClient = new ApiClient()
export default apiClient