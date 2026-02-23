# Feature — 024 cv-bullet-enhancements

**File:** docs/features/ft-024-cv-bullet-enhancements.md
**Owner:** Backend Team, Frontend Team
**TECH-SPECs:** `spec-api.md` (v4.3.0), `spec-frontend.md` (v2.7.0), `spec-cv-generation.md` (v1.0.0)
**Related ADRs:** [ADR-035-hybrid-bullet-refinement-strategy](../adrs/adr-035-hybrid-bullet-refinement-strategy.md), [ADR-036-refinement-prompt-lifecycle](../adrs/adr-036-refinement-prompt-lifecycle.md), [ADR-019-two-phase-cv-generation-workflow](../adrs/adr-019-two-phase-cv-generation-workflow.md)
**PRD Reference:** `prd.md` Section 2.2 (CV Generation with User Control)

## Existing Implementation Analysis

**Current Workflow (ft-009 Two-Phase):**
```
POST /api/v1/generation/cv/
  → prepare_cv_bullets_task()
    → CVGenerationService.prepare_bullets()
      → BulletGenerationService.generate_bullets()  # For each artifact
  → Status: bullets_ready

GET /api/v1/generation/cv/{id}/bullets/
  → Returns bullets grouped by artifact

PATCH /api/v1/generation/cv/{id}/bullets/{id}/
  → Edits individual bullet text

POST /api/v1/generation/cv/{id}/bullets/approve/
  → Approves ALL bullets (no individual approval)
  → Status: bullets_approved

POST /api/v1/generation/cv/{id}/assemble/
  → assemble_cv_task()
  → Status: completed
```

**Current Limitations:**
1. ❌ Bullet generation only uses `artifact.description` or `artifact.title`
2. ❌ Ignores `user_context`, `unified_description`, `enriched_achievements`
3. ❌ No bullet regeneration capability
4. ❌ Only "approve all" - cannot approve/reject individual bullets
5. ❌ No UI to review bullets after initial generation (must use Step 4)
6. ❌ No refinement prompts for iteration

**Files Affected:**
- ✅ `backend/generation/services/bullet_generation_service.py` (613 lines) - **ADD multi-source content**
- ✅ `backend/generation/services/cv_generation_service.py` (293 lines) - **ADD regeneration method**
- ✅ `backend/generation/views.py` (674 lines) - **ADD regeneration endpoint, enhance approval**
- ✅ `backend/generation/urls.py` - **ADD regeneration route**
- ✅ `frontend/src/pages/CVDetailPage.tsx` - **NEW PAGE**
- ✅ `frontend/src/components/BulletRegenerationModal.tsx` - **NEW COMPONENT**
- ✅ `frontend/src/components/BulletCard.tsx` - **ENHANCE with individual approval**
- ✅ `frontend/src/components/BulletReviewStep.tsx` - **ENHANCE with regeneration**
- ✅ `frontend/src/services/apiClient.ts` - **ADD regeneration methods**
- ✅ `frontend/src/stores/generationStore.ts` - **ENHANCE with regeneration state**

**Reusable Components:**
- ✅ `generation/services/bullet_generation_service.py` - **WILL ENHANCE**
  - `generate_bullets()` - Add multi-source content assembly
  - `_parse_bullet_response()` - Already exists
  - `_save_bullets()` - Already exists
- ✅ `generation/services/bullet_validation_service.py` (495 lines)
  - `validate_bullet_set()` - Already used
  - Multi-criteria quality validation
- ✅ `llm_services/services/core/tailored_content_service.py`
  - `generate_bullet_points()` - LLM generation
- ✅ Frontend components (existing):
  - `BulletReviewStep` - **REUSE in CVDetailPage**
  - `BulletCard` - **ENHANCE**
  - `BulletQualityBadge` - **REUSE as-is**

**Patterns to Follow:**
- **Service Layer Pattern:** Framework-agnostic services (ADR-018)
- **Multi-Source Content Assembly:** Pattern from ADR-035
- **Temporary Parameter Pattern:** refinement_prompt not persisted (ADR-036)
- **Component Reuse:** DRY principle - reuse BulletReviewStep in 2 places

**Dependencies:**
- `generation.services.BulletGenerationService` - **WILL ENHANCE**
- `generation.services.CVGenerationService` - **WILL ENHANCE**
- `llm_services.services.core.TailoredContentService` - Already used
- `artifacts.models.Artifact` - Read user_context, unified_description, enriched_achievements
- `generation.models.BulletPoint` - **WILL ADD user_approved, user_rejected fields**
- `generation.models.GeneratedDocument` - Already has job_description_data

## Architecture Conformance

**Layer Assignment:**
- **Service Layer:** `generation/services/bullet_generation_service.py`
  - `_build_comprehensive_content()` - NEW - Multi-source content assembly
  - `regenerate_bullets()` - NEW - Regeneration with refinement prompts
- **Service Layer:** `generation/services/cv_generation_service.py`
  - `regenerate_cv_bullets()` - NEW - Orchestrate bullet regeneration for CV
- **API Layer:** `generation/views.py`
  - `regenerate_cv_bullets()` - NEW - POST endpoint
  - `approve_cv_bullets()` - ENHANCE - Individual bullet actions
- **Frontend Pages:** `frontend/src/pages/`
  - `CVDetailPage.tsx` - NEW - `/cvs/:id` route
- **Frontend Components:** `frontend/src/components/`
  - `BulletRegenerationModal.tsx` - NEW
  - `BulletCard.tsx` - ENHANCE
  - `BulletReviewStep.tsx` - ENHANCE

**Pattern Compliance:**
- ✅ Framework-agnostic services (testable without Django)
- ✅ Multi-source content assembly (ADR-035 pattern)
- ✅ Temporary refinement prompts (ADR-036 pattern)
- ✅ Component reuse (BulletReviewStep in 2 places)
- ✅ Clean Architecture: app layer (generation) → infrastructure (llm_services)
- ✅ Circuit breaker for LLM calls (via BulletGenerationService)
- ✅ Retry logic with validation feedback (existing pattern)

**Test Coverage:**
- Current: 89.6% in generation/ app
- Target: Maintain ≥85% coverage after changes
- New tests needed:
  - Unit tests for `_build_comprehensive_content()`
  - Unit tests for `regenerate_bullets()` with refinement_prompt
  - Integration tests for regeneration endpoint
  - Frontend component tests for CVDetailPage
  - Frontend component tests for BulletRegenerationModal

## Acceptance Criteria

### Multi-Source Content Assembly
- [ ] `_build_comprehensive_content()` combines user_context + unified_description + enriched_achievements
- [ ] Falls back to description if enriched fields unavailable
- [ ] User context has highest priority in assembled content
- [ ] Multi-source content used in both initial generation AND regeneration
- [ ] Content sources logged in generation metadata

### Bullet Regeneration
- [ ] POST /api/v1/generation/cv/{generation_id}/bullets/regenerate/ endpoint works
- [ ] Accepts optional refinement_prompt parameter (max 500 chars)
- [ ] Accepts optional bullet_ids_to_regenerate (regenerate specific bullets)
- [ ] Accepts optional artifact_ids (regenerate bullets for specific artifacts)
- [ ] Inherits job_context from original CV generation
- [ ] refinement_prompt is NOT saved to database (ADR-036)
- [ ] Returns 202 Accepted with estimated_completion timestamp
- [ ] Updates BulletPoint records with new text
- [ ] Preserves original_text if user hasn't edited yet
- [ ] P95 latency ≤ 15 seconds for 3 bullets regeneration

### Individual Bullet Approval
- [ ] POST /api/v1/generation/cv/{generation_id}/bullets/approve/ accepts bullet_actions array
- [ ] Supports 'approve', 'reject', 'edit' actions per bullet
- [ ] Sets user_approved=true for approved bullets
- [ ] Sets user_approved=false for rejected bullets
- [ ] Preserves original_text when editing
- [ ] Status changes to 'bullets_approved' only if ALL bullets approved or rejected
- [ ] Returns count of approved/rejected/edited bullets
- [ ] Backward compatible (can still approve all by providing approve action for all)

### CV Detail Page (/cvs/:id)
- [ ] New route /cvs/:id renders CVDetailPage
- [ ] Displays CV generation metadata (job, company, status)
- [ ] Shows bullets grouped by artifact (reuses BulletReviewStep)
- [ ] "Regenerate Bullets" button opens BulletRegenerationModal
- [ ] Individual approve/reject buttons per bullet
- [ ] Edit bullet inline with 60-150 char validation
- [ ] Shows quality badges per bullet
- [ ] Shows user-edited vs. original LLM text
- [ ] "Assemble CV" button when all bullets approved
- [ ] Loading states during regeneration
- [ ] Error handling with retry capability

### Bullet Regeneration Modal
- [ ] Opens from "Regenerate Bullets" button
- [ ] Shows quick suggestions: "Add metrics", "Focus on leadership", etc.
- [ ] Custom refinement prompt textarea (max 500 chars)
- [ ] Clear messaging: "This prompt is temporary and won't be saved"
- [ ] Option to "Edit Artifact Context" for permanent improvements
- [ ] Shows which bullets will be regenerated (count)
- [ ] Can target specific bullets or all bullets
- [ ] Submit button triggers regeneration API call
- [ ] Closes modal on success, shows toast notification
- [ ] Shows error message if regeneration fails

### CVGenerationFlow Enhancement
- [ ] Step 4 (Bullet Review) shows individual approve/reject buttons
- [ ] Step 4 has "Regenerate Bullets" button
- [ ] BulletRegenerationModal works in Step 4
- [ ] Multi-source content assembly applied automatically
- [ ] User can proceed to Step 5 after approving all bullets

### Data Integrity
- [ ] user_approved and user_rejected are mutually exclusive
- [ ] original_text preserved across regenerations
- [ ] refinement_prompt NEVER saved to database
- [ ] Multi-source content assembly doesn't modify artifact data
- [ ] Bullet quality scores recalculated after regeneration

## Design Changes

### Backend Model Changes

**BulletPoint (models.py):**
```python
class BulletPoint(models.Model):
    # ... existing fields ...

    # ENHANCED APPROVAL TRACKING
    user_approved = models.BooleanField(
        default=False,
        help_text='True if user explicitly approved this bullet'
    )
    user_rejected = models.BooleanField(
        default=False,
        help_text='True if user explicitly rejected this bullet'
    )

    # Already exists from ft-009:
    # approved_at, approved_by, original_text, edited, user_edited

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~models.Q(user_approved=True, user_rejected=True),
                name='user_approved_rejected_mutually_exclusive'
            )
        ]
```

### Backend Service Changes

**BulletGenerationService (services/bullet_generation_service.py):**
```python
class BulletGenerationService:
    """Enhanced with multi-source content assembly."""

    def _build_comprehensive_content(self, artifact: Artifact) -> str:
        """
        Build comprehensive content from multiple artifact sources.

        Priority:
        1. user_context (HIGHEST - user facts)
        2. unified_description (AI-enhanced from evidence)
        3. enriched_achievements (extracted metrics)
        4. description (fallback)

        Returns:
            Assembled content string with clear section headers
        """
        parts = []
        sources_used = []

        # 1. User context (HIGHEST PRIORITY)
        if artifact.user_context:
            parts.append(f"User-Provided Context (PRIORITIZE):\n{artifact.user_context}")
            sources_used.append('user_context')

        # 2. AI-enhanced description
        if artifact.unified_description:
            parts.append(f"Enhanced Description:\n{artifact.unified_description}")
            sources_used.append('unified_description')
        elif artifact.description:
            parts.append(f"Description:\n{artifact.description}")
            sources_used.append('description')

        # 3. Extracted achievements with metrics
        if artifact.enriched_achievements:
            achievements_text = "\n".join([f"- {ach}" for ach in artifact.enriched_achievements])
            parts.append(f"Key Achievements:\n{achievements_text}")
            sources_used.append('enriched_achievements')

        logger.info(f"Built content for artifact {artifact.id} using sources: {sources_used}")

        return {
            'content': "\n\n".join(parts),
            'sources_used': sources_used
        }

    async def generate_bullets(
        self,
        artifact_id: int,
        job_context: Dict[str, Any],
        cv_generation_id: Optional[str] = None,
        regenerate: bool = False
    ) -> GeneratedBulletSet:
        """
        Generate bullets with multi-source content assembly.

        ENHANCED: Now uses _build_comprehensive_content() instead of just description.
        """
        artifact = await self._get_artifact(artifact_id)

        # CHANGE: Use multi-source content instead of just description
        content_data = self._build_comprehensive_content(artifact)
        artifact_content = content_data['content']
        sources_used = content_data['sources_used']

        # Call LLM with comprehensive content
        llm_response = await self.tailored_content_service.generate_bullet_points(
            artifact_content=artifact_content,  # Multi-source assembly
            job_requirements=job_context.get('key_requirements', []),
            user_id=artifact.user.id,
            target_count=3,
            job_context=job_context
        )

        # Parse and validate bullets (existing logic)
        bullets = self._parse_bullet_response(llm_response)
        validation_result = await self.validation_service.validate_bullet_set(bullets, job_context)

        # Save with metadata
        saved_bullets = self._save_bullets(
            bullets,
            artifact,
            cv_generation_id,
            metadata={'content_sources_used': sources_used}  # Track sources
        )

        return GeneratedBulletSet(
            bullets=saved_bullets,
            quality_score=validation_result.overall_quality_score,
            content_sources_used=sources_used  # Return to caller
        )
```

**CVGenerationService (services/cv_generation_service.py):**
```python
class CVGenerationService:
    """Enhanced with bullet regeneration capability."""

    async def regenerate_cv_bullets(
        self,
        generation_id: str,
        refinement_prompt: Optional[str] = None,
        bullet_ids: Optional[List[int]] = None,
        artifact_ids: Optional[List[int]] = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> BulletRegenerationResult:
        """
        Regenerate bullets for CV generation with optional refinement prompt.

        Args:
            generation_id: CV generation ID (contains job_context)
            refinement_prompt: Temporary hint for LLM (NOT persisted per ADR-036)
            bullet_ids: Specific bullets to regenerate (or all if None)
            artifact_ids: Specific artifacts to regenerate bullets for (or all if None)
            progress_callback: Progress updates 0-100%

        Returns:
            BulletRegenerationResult with regenerated bullets and metadata
        """
        generation = await self._get_generation(generation_id)
        job_context = generation.job_description_data  # Inherit from CV generation

        # Add refinement prompt to job_context (temporary, not persisted)
        refined_context = job_context.copy()
        if refinement_prompt:
            refined_context['_refinement_prompt'] = refinement_prompt
            logger.info(f"Refinement prompt provided (length: {len(refinement_prompt)} chars)")

        # Determine which artifacts to regenerate
        if artifact_ids:
            artifacts = generation.artifacts_used.filter(id__in=artifact_ids)
        else:
            artifacts = generation.artifacts_used.all()

        regenerated_count = 0
        total_to_regenerate = len(artifacts) * 3  # 3 bullets per artifact

        for i, artifact in enumerate(artifacts):
            if progress_callback:
                progress = int((i / len(artifacts)) * 100)
                progress_callback(progress)

            # Regenerate bullets for this artifact
            result = await self.bullet_service.generate_bullets(
                artifact_id=artifact.id,
                job_context=refined_context,  # Contains temporary refinement_prompt
                cv_generation_id=generation_id,
                regenerate=True  # Force regeneration
            )

            regenerated_count += len(result.bullets)

        if progress_callback:
            progress_callback(100)

        return BulletRegenerationResult(
            success=True,
            bullets_regenerated=regenerated_count,
            content_sources_used=result.content_sources_used,
            refinement_prompt_used=refinement_prompt is not None
        )
```

### API Changes

**views.py:**
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def regenerate_cv_bullets(request, generation_id):
    """
    Regenerate bullets for CV generation with optional refinement prompt.

    NEW ENDPOINT (ft-024)

    Body:
        refinement_prompt (optional): Temporary hint for LLM (max 500 chars)
        bullet_ids_to_regenerate (optional): List of bullet IDs to regenerate
        artifact_ids (optional): List of artifact IDs to regenerate bullets for

    Returns:
        202 Accepted with job status
    """
    generation = await sync_to_async(GeneratedDocument.objects.get)(id=generation_id)

    # Verify ownership
    if generation.user != request.user:
        return Response({'error': 'Unauthorized'}, status=403)

    # Validate refinement_prompt length
    refinement_prompt = request.data.get('refinement_prompt')
    if refinement_prompt and len(refinement_prompt) > 500:
        return Response(
            {'error': 'Refinement prompt must be 500 characters or less'},
            status=400
        )

    bullet_ids = request.data.get('bullet_ids_to_regenerate')
    artifact_ids = request.data.get('artifact_ids')

    # Trigger async regeneration
    regenerate_bullets_task.delay(
        generation_id=str(generation_id),
        refinement_prompt=refinement_prompt,  # Temporary only, not saved
        bullet_ids=bullet_ids,
        artifact_ids=artifact_ids
    )

    return Response({
        'generation_id': str(generation_id),
        'status': 'processing',
        'message': 'Bullet regeneration started',
        'bullets_to_regenerate': len(bullet_ids) if bullet_ids else 'all',
        'estimated_completion': timezone.now() + timedelta(seconds=15)
    }, status=202)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def approve_cv_bullets(request, generation_id):
    """
    Approve/reject/edit individual bullets.

    ENHANCED (ft-024): Now supports individual bullet actions instead of just "approve all".

    Body:
        bullet_actions: [
            {bullet_id: int, action: 'approve' | 'reject' | 'edit', edited_text?: string}
        ]

    Returns:
        200 OK with updated bullets and counts
    """
    generation = await sync_to_async(GeneratedDocument.objects.get)(id=generation_id)

    bullet_actions = request.data.get('bullet_actions', [])

    approved_count = 0
    rejected_count = 0
    edited_count = 0
    updated_bullets = []

    for action_data in bullet_actions:
        bullet = await sync_to_async(BulletPoint.objects.get)(
            id=action_data['bullet_id'],
            cv_generation_id=generation_id
        )

        action = action_data['action']

        if action == 'approve':
            bullet.user_approved = True
            bullet.user_rejected = False
            bullet.approved_at = timezone.now()
            bullet.approved_by = request.user
            approved_count += 1

        elif action == 'reject':
            bullet.user_approved = False
            bullet.user_rejected = True
            rejected_count += 1

        elif action == 'edit':
            if not bullet.original_text:
                bullet.original_text = bullet.text  # Preserve LLM text
            bullet.text = action_data['edited_text']
            bullet.edited = True
            bullet.user_edited = True
            edited_count += 1

        await sync_to_async(bullet.save)()
        updated_bullets.append(bullet)

    # Check if all bullets are approved or rejected
    all_bullets = await sync_to_async(list)(
        BulletPoint.objects.filter(cv_generation_id=generation_id)
    )

    if all(b.user_approved or b.user_rejected for b in all_bullets):
        generation.status = 'bullets_approved'
        await sync_to_async(generation.save)()

    serializer = BulletPointSerializer(updated_bullets, many=True)

    return Response({
        'generation_id': str(generation_id),
        'status': generation.status,
        'bullets_approved': approved_count,
        'bullets_rejected': rejected_count,
        'bullets_edited': edited_count,
        'updated_bullets': serializer.data
    })
```

**urls.py:**
```python
urlpatterns = [
    # ... existing routes ...

    # NEW: Bullet regeneration
    path(
        'cv/<uuid:generation_id>/bullets/regenerate/',
        views.regenerate_cv_bullets,
        name='regenerate-cv-bullets'
    ),

    # ENHANCED: Individual bullet approval
    path(
        'cv/<uuid:generation_id>/bullets/approve/',
        views.approve_cv_bullets,  # Enhanced to support individual actions
        name='approve-cv-bullets'
    ),
]
```

### Frontend Changes

**New Page: CVDetailPage.tsx**
```typescript
// frontend/src/pages/CVDetailPage.tsx
export default function CVDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [generation, setGeneration] = useState<GeneratedDocument | null>(null)
  const [bullets, setBullets] = useState<BulletsByArtifact[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showRegenerationModal, setShowRegenerationModal] = useState(false)

  useEffect(() => {
    loadCVDetails()
  }, [id])

  const loadCVDetails = async () => {
    const [genData, bulletsData] = await Promise.all([
      apiClient.getGeneration(id),
      apiClient.getCVBullets(id)
    ])
    setGeneration(genData)
    setBullets(bulletsData.artifacts)
    setIsLoading(false)
  }

  const handleRegenerateBullets = async (refinementPrompt?: string) => {
    await apiClient.regenerateCVBullets(id, refinementPrompt)
    setShowRegenerationModal(false)
    toast.success('Bullets are being regenerated...')
    // Poll for updates
    pollForBulletUpdates()
  }

  const handleBulletAction = async (bulletId: number, action: BulletAction) => {
    await apiClient.approveBulletActions(id, [{
      bullet_id: bulletId,
      action: action.type,
      edited_text: action.editedText
    }])
    await loadCVDetails()  // Reload bullets
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* CV Metadata Header */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h1 className="text-2xl font-bold">{generation?.job_title}</h1>
        <p className="text-gray-600">{generation?.company_name}</p>
        <div className="mt-4 flex gap-4">
          <StatusBadge status={generation?.status} />
          <span>Generated: {formatDate(generation?.created_at)}</span>
        </div>
      </div>

      {/* Bullet Review Section */}
      <BulletReviewStep
        generationId={id!}
        bullets={bullets}
        onBulletEdit={handleBulletAction}
        onBulletApprove={handleBulletAction}
        onRegenerateClick={() => setShowRegenerationModal(true)}
      />

      {/* Regeneration Modal */}
      {showRegenerationModal && (
        <BulletRegenerationModal
          onClose={() => setShowRegenerationModal(false)}
          onRegenerate={handleRegenerateBullets}
          artifactCount={bullets.length}
        />
      )}
    </div>
  )
}
```

**New Component: BulletRegenerationModal.tsx**
```typescript
// frontend/src/components/BulletRegenerationModal.tsx
export function BulletRegenerationModal({
  onClose,
  onRegenerate,
  artifactCount
}: Props) {
  const [refinementPrompt, setRefinementPrompt] = useState('')
  const [selectedSuggestion, setSelectedSuggestion] = useState<string | null>(null)

  const quickSuggestions = [
    { label: 'Add more metrics', prompt: 'Add specific metrics and quantifiable achievements' },
    { label: 'Focus on leadership', prompt: 'Focus more on leadership and team management' },
    { label: 'More technical detail', prompt: 'Emphasize technical depth over business impact' },
    { label: 'Use action verbs', prompt: 'Use more action verbs and reduce generic language' }
  ]

  const handleSuggestionClick = (prompt: string) => {
    setRefinementPrompt(prompt)
    setSelectedSuggestion(prompt)
  }

  return (
    <Dialog open onClose={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Regenerate Bullets</DialogTitle>
          <DialogDescription>
            Provide hints to improve your bullet points. This prompt is temporary and won't be saved.
          </DialogDescription>
        </DialogHeader>

        <Alert variant="info" className="my-4">
          💡 Refinement prompts are temporary. To make permanent improvements,
          <Link className="underline">edit your artifact context</Link>.
        </Alert>

        {/* Quick Suggestions */}
        <div className="space-y-2">
          <Label>Quick Suggestions</Label>
          <div className="flex flex-wrap gap-2">
            {quickSuggestions.map((suggestion) => (
              <Button
                key={suggestion.label}
                variant={selectedSuggestion === suggestion.prompt ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleSuggestionClick(suggestion.prompt)}
              >
                {suggestion.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Custom Prompt */}
        <div className="space-y-2">
          <Label htmlFor="refinement">Custom Refinement Prompt (Optional)</Label>
          <Textarea
            id="refinement"
            value={refinementPrompt}
            onChange={(e) => setRefinementPrompt(e.target.value)}
            placeholder="Describe how to improve these bullets..."
            rows={4}
            maxLength={500}
          />
          <p className="text-sm text-gray-500">
            {refinementPrompt.length}/500 characters
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => onRegenerate(refinementPrompt || undefined)}>
            Regenerate {artifactCount * 3} Bullets
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**Enhanced: BulletCard.tsx**
```typescript
// frontend/src/components/BulletCard.tsx
export function BulletCard({
  bullet,
  onApprove,
  onReject,
  onEdit
}: Props) {
  const [isEditing, setIsEditing] = useState(false)
  const [editedText, setEditedText] = useState(bullet.text)

  const handleApprove = () => {
    onApprove?.(bullet.id)
  }

  const handleReject = () => {
    onReject?.(bullet.id)
  }

  const handleSaveEdit = () => {
    if (editedText.length >= 60 && editedText.length <= 150) {
      onEdit?.(bullet.id, editedText)
      setIsEditing(false)
    }
  }

  return (
    <div className={cn(
      "p-4 rounded-lg border",
      bullet.user_approved && "bg-green-50 border-green-200",
      bullet.user_rejected && "bg-red-50 border-red-200",
      !bullet.user_approved && !bullet.user_rejected && "bg-white border-gray-200"
    )}>
      {/* Bullet Type Badge */}
      <div className="flex items-center justify-between mb-2">
        <Badge variant={getBulletTypeVariant(bullet.bullet_type)}>
          {bullet.bullet_type}
        </Badge>
        <BulletQualityBadge score={bullet.quality_score} compact />
      </div>

      {/* Bullet Text */}
      {isEditing ? (
        <div>
          <Textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            className="mb-2"
          />
          <p className="text-sm text-gray-500">
            {editedText.length}/150 characters (min: 60)
          </p>
          <div className="flex gap-2 mt-2">
            <Button size="sm" onClick={handleSaveEdit}>Save</Button>
            <Button size="sm" variant="outline" onClick={() => setIsEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div>
          <p className="text-gray-800">{bullet.text}</p>
          {bullet.user_edited && bullet.original_text && (
            <details className="mt-2 text-sm text-gray-600">
              <summary className="cursor-pointer">Show original LLM text</summary>
              <p className="mt-1 italic">{bullet.original_text}</p>
            </details>
          )}
        </div>
      )}

      {/* Action Buttons */}
      {!bullet.user_approved && !bullet.user_rejected && (
        <div className="flex gap-2 mt-4">
          <Button size="sm" variant="default" onClick={handleApprove}>
            ✓ Approve
          </Button>
          <Button size="sm" variant="destructive" onClick={handleReject}>
            ✗ Reject
          </Button>
          <Button size="sm" variant="outline" onClick={() => setIsEditing(true)}>
            Edit
          </Button>
        </div>
      )}

      {bullet.user_approved && (
        <div className="flex items-center gap-2 mt-2 text-green-700">
          <CheckCircle className="w-4 h-4" />
          <span className="text-sm font-medium">Approved</span>
        </div>
      )}

      {bullet.user_rejected && (
        <div className="flex items-center gap-2 mt-2 text-red-700">
          <XCircle className="w-4 h-4" />
          <span className="text-sm font-medium">Rejected</span>
        </div>
      )}
    </div>
  )
}
```

## Migration Strategy

### Database Migration

**Migration: Add user_approved and user_rejected fields**
```python
# generation/migrations/00XX_add_individual_bullet_approval.py
operations = [
    migrations.AddField(
        model_name='bulletpoint',
        name='user_approved',
        field=models.BooleanField(default=False),
    ),
    migrations.AddField(
        model_name='bulletpoint',
        name='user_rejected',
        field=models.BooleanField(default=False),
    ),
    migrations.AddConstraint(
        model_name='bulletpoint',
        constraint=models.CheckConstraint(
            check=~models.Q(user_approved=True, user_rejected=True),
            name='user_approved_rejected_mutually_exclusive'
        ),
    ),
]
```

**Existing Data:**
- All existing bullets default to user_approved=false, user_rejected=false
- No data loss
- Backward compatible

## Testing Strategy

### Unit Tests

**backend/generation/tests/test_bullet_generation_service.py:**
```python
class TestMultiSourceContent:
    def test_build_comprehensive_content_with_all_sources()
    def test_build_comprehensive_content_user_context_priority()
    def test_build_comprehensive_content_fallback_to_description()
    def test_build_comprehensive_content_tracks_sources_used()

class TestBulletRegeneration:
    async def test_regenerate_bullets_with_refinement_prompt()
    async def test_regenerate_bullets_without_prompt()
    async def test_regenerate_specific_bullets()
    async def test_regenerate_specific_artifacts()
    async def test_refinement_prompt_not_saved()
```

**backend/generation/tests/test_cv_generation_service.py:**
```python
class TestCVBulletRegeneration:
    async def test_regenerate_cv_bullets_success()
    async def test_regenerate_inherits_job_context()
    async def test_regenerate_with_refinement_prompt()
    async def test_regenerate_progress_callback()
```

**backend/generation/tests/test_views.py:**
```python
class TestRegenerationAPI:
    def test_regenerate_endpoint_accepts_refinement_prompt()
    def test_regenerate_endpoint_validates_prompt_length()
    def test_regenerate_endpoint_accepts_bullet_ids()
    def test_regenerate_endpoint_returns_202()

class TestIndividualApproval:
    def test_approve_individual_bullet()
    def test_reject_individual_bullet()
    def test_edit_bullet_action()
    def test_approve_reject_mutually_exclusive()
    def test_status_changes_when_all_decided()
```

### Integration Tests

**backend/generation/tests/test_regeneration_integration.py:**
```python
class TestRegenerationWorkflow:
    async def test_end_to_end_regeneration()
    async def test_multi_source_content_in_bullets()
    async def test_refinement_prompt_affects_output()
    async def test_regeneration_preserves_metadata()
```

### Frontend Tests

**frontend/src/pages/__tests__/CVDetailPage.test.tsx:**
```python
describe('CVDetailPage', () => {
  it('renders CV metadata correctly')
  it('displays bullets grouped by artifact')
  it('opens regeneration modal on button click')
  it('handles bullet approval')
  it('handles bullet rejection')
  it('handles bullet editing')
  it('polls for updates after regeneration')
})
```

**frontend/src/components/__tests__/BulletRegenerationModal.test.tsx:**
```python
describe('BulletRegenerationModal', () => {
  it('renders quick suggestions')
  it('allows custom refinement prompt input')
  it('validates prompt length (500 chars max)')
  it('calls onRegenerate with prompt')
  it('shows temporary prompt warning message')
  it('provides link to edit artifact context')
})
```

## Rollout Plan

### Phase A: Backend Multi-Source Content (Week 1)
- [ ] Write tests for `_build_comprehensive_content()` (TDD RED)
- [ ] Implement `_build_comprehensive_content()` (TDD GREEN)
- [ ] Update `generate_bullets()` to use multi-source content (TDD GREEN)
- [ ] Refactor for code quality (TDD REFACTOR)
- [ ] Run tests, ensure 158 tests still pass

### Phase B: Backend Regeneration (Week 1-2)
- [ ] Write tests for `regenerate_cv_bullets()` service method (TDD RED)
- [ ] Implement `regenerate_cv_bullets()` (TDD GREEN)
- [ ] Write tests for regeneration API endpoint (TDD RED)
- [ ] Implement regeneration endpoint (TDD GREEN)
- [ ] Create Celery task for async regeneration
- [ ] Add URL routing

### Phase C: Individual Approval (Week 2)
- [ ] Create database migration for user_approved/user_rejected
- [ ] Run migration in development
- [ ] Write tests for enhanced approval endpoint (TDD RED)
- [ ] Implement enhanced approval logic (TDD GREEN)
- [ ] Update BulletPoint model with constraint

### Phase D: Frontend CVDetailPage (Week 3)
- [ ] Create CVDetailPage component
- [ ] Add route /cvs/:id to App.tsx
- [ ] Implement CV metadata display
- [ ] Integrate BulletReviewStep (reuse)
- [ ] Add loading and error states
- [ ] Wire up regeneration trigger

### Phase E: Frontend Regeneration Modal (Week 3)
- [ ] Create BulletRegenerationModal component
- [ ] Implement quick suggestions
- [ ] Implement custom prompt textarea
- [ ] Add character validation (500 max)
- [ ] Add temporary prompt warning
- [ ] Link to artifact edit page

### Phase F: Enhanced Components (Week 4)
- [ ] Enhance BulletCard with individual approval
- [ ] Add approve/reject buttons
- [ ] Add visual states (approved/rejected/pending)
- [ ] Enhance BulletReviewStep with regeneration button
- [ ] Update CVGenerationFlow Step 4

### Phase G: Integration & Testing (Week 4)
- [ ] Run full test suite (backend + frontend)
- [ ] Fix integration issues
- [ ] Performance testing (P95 targets)
- [ ] User acceptance testing

### Phase H: Deployment (Week 5)
- [ ] Create operation note (op-025)
- [ ] Deploy to staging
- [ ] Smoke tests
- [ ] Deploy to production
- [ ] Monitor metrics

## Performance Targets

- **Multi-Source Content Assembly:** <50ms overhead per artifact
- **Bullet Regeneration:** P95 ≤ 15 seconds for 3 bullets
- **Individual Approval:** <200ms per action
- **CVDetailPage Load:** P95 ≤ 1 second
- **Success Rate:** ≥ 95% for regeneration
- **Quality Improvement:** ≥ 10% increase in bullet quality with multi-source content

## Risk Mitigation

**Risk 1: Multi-Source Content Increases LLM Token Usage**
- Mitigation: Monitor token usage, set max content length
- Fallback: Use only unified_description if token budget exceeded

**Risk 2: Users Overuse Regeneration (Cost)**
- Mitigation: Rate limit to 10 regenerations per CV generation
- Tracking: Monitor regeneration frequency per user

**Risk 3: Refinement Prompts Not Effective**
- Mitigation: A/B test with and without refinement prompts
- Tracking: Compare bullet quality scores with/without prompts

**Risk 4: Frontend Performance Degradation**
- Mitigation: Lazy load BulletRegenerationModal, memoize components
- Tracking: Monitor page load times

## Success Metrics

- **Adoption:** ≥ 40% of users visit /cvs/:id page within 30 days
- **Regeneration Usage:** ≥ 25% of CV generations use regeneration at least once
- **Individual Approval:** ≥ 50% of users approve/reject individual bullets (not just "approve all")
- **Quality Improvement:** ≥ 10% increase in bullet quality scores with multi-source content
- **User Satisfaction:** ≥ 80% positive feedback on bullet quality in surveys
- **Performance:** P95 ≤ 15s for regeneration, zero timeout errors

## Related Documents

- `docs/specs/spec-api.md` (v4.3.0) - API specification with regeneration endpoint
- `docs/specs/spec-frontend.md` (v2.7.0) - Frontend specification with CVDetailPage
- `docs/adrs/adr-035-hybrid-bullet-refinement-strategy.md` - Multi-source content decision
- `docs/adrs/adr-036-refinement-prompt-lifecycle.md` - Don't persist prompts decision
- `docs/adrs/adr-019-two-phase-cv-generation-workflow.md` - Two-phase workflow context
- `docs/adrs/adr-027-user-context-field.md` - User context field design
- `docs/features/ft-009-two-phase-cv-workflow.md` - Base two-phase workflow
- `docs/features/ft-006-three-bullets-per-artifact.md` - Bullet generation base feature

## Notes

- **Track:** MEDIUM feature (multi-component, existing services enhanced, new page)
- **Estimated Effort:** 5 weeks (2 backend + 2 frontend + 1 testing/deployment)
- **Team Size:** 2 backend engineers, 1 frontend engineer
- **Priority:** High (improves core product value)
- **User Impact:** All CV generation users
- **Breaking Change:** No - extends existing two-phase workflow
