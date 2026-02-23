# PRD — CV & Cover-Letter Auto-Tailor

**Version:** v1.5.0
**File:** docs/prds/prd.md
**Owners:** Product (TBD), Engineering (TBD)
**Last_updated:** 2025-01-06

## Summary

Upload your work once with proof. For any job description + company, the app assembles a targeted, ATS-friendly CV and cover letter with quantified, defensible achievement bullets—grounded by linked evidence. Targeting job seekers from students to senior engineers/PMs/DS who need credible, consistent, reusable career documents with seamless authentication and comprehensive artifact management.

## Problem & Context

**Problem:** Tailoring CVs is slow, error-prone, and often unsubstantiated. Job seekers repeat vague claims that don't map tightly to job descriptions and fail automated ATS screens, leading to missed opportunities and prolonged job searches. Additionally, traditional authentication creates friction, and inflexible artifact management prevents users from maintaining accurate, up-to-date portfolios.

**Why now:** LLMs can parse job descriptions, map skills, and write strong bullets—but they need trusted, structured inputs and verifiable evidence to produce credible, consistent outputs that pass both ATS systems and human review. Modern users expect seamless social authentication and flexible content management.

**Evidence:** Manual CV tailoring takes 2-4 hours per application; 75% of resumes are filtered by ATS before human review; unsubstantiated claims reduce credibility with hiring managers; traditional registration creates 30-40% abandonment rates; users require artifact editing capabilities for portfolio maintenance.

## Users & Use Cases

**Primary persona:** Job seekers (student → senior engineer/PM/DS) actively applying for roles

**Key jobs-to-be-done:**
1. "Show me the best version of my CV for this role at this company, grounded in my real work"
2. "Draft a concise, specific cover letter that cites relevant proof"
3. "Keep versions for different roles without duplicating effort"
4. "Ensure my application passes ATS screening with proper keywords"
5. "Provide verifiable evidence for my achievements when requested"
6. "Sign in quickly without creating another password"
7. "Update my work samples and project descriptions as they evolve"
8. "Maintain accurate, current portfolio information"

## Scope (MoSCoW)

**Must:**
- **Core CV/Cover Letter Generation:**
  - Artifact ingestion (repos, papers, talks, datasets, dashboards, PRDs)
  - Evidence linking (GitHub PRs, live apps, arXiv, demo videos)
  - **Intelligent GitHub repository analysis with agent-based file selection**
  - **Multi-format artifact content extraction (config files, source code, CI/CD, documentation)**
  - **Evidence review & acceptance workflow with inline editing (blocking wizard step)**
  - **User verification of AI-extracted evidence content before artifact finalization**
  - **Re-unification of artifact content from user-edited evidence using LLM**
  - Role-based labeling system with skill taxonomy
  - Job description parsing and matching engine
  - **Artifact-based bullet point generation (3 bullets per selected artifact)**
  - ATS-optimized CV generation with keyword preservation
  - Cover letter generation with evidence citations
  - PDF/Docx export with clean formatting
  - Version tracking and evidence link management
- **Authentication & User Management:**
  - Google OAuth integration with one-click sign-in
  - Seamless profile creation from Google account information
  - Account linking for existing email/password users
  - Fallback email/password authentication option
- **Artifact Management:**
  - Comprehensive artifact editing capabilities
  - Metadata modification (title, description, dates, technologies, collaborators)
  - Evidence link management (add, edit, remove with validation)
  - File upload, replacement, and management
  - Data validation and integrity preservation

**Should:**
- QR code/footnote evidence linking in exports
- Reusable label templates for role families
- STAR/CAR achievement framework integration
- Company-specific customization signals
- Browser extension for job posting ingestion
- Bulk artifact editing operations
- Advanced form validation with real-time feedback

**Could:**
- Team/collaborative workspace features
- Interview preparation based on submitted evidence
- Performance analytics and application tracking
- Integration with job boards and LinkedIn
- Version history and change tracking for artifacts
- AI-powered content suggestions during editing

**Won't:**
- Social media profile optimization (future PRD)
- Salary negotiation tools (future PRD)
- Background check preparation (future PRD)
- Enterprise SSO integration (future PRD)
- Multi-provider social authentication beyond Google (future PRD)

## Success Metrics

**Primary:**
- Time to create tailored CV+cover letter: baseline 3 hours → target 15 minutes (90% reduction by 2025-12-31)
- ATS pass rate: baseline 25% → target 65% (40pp improvement by 2025-12-31)
- User retention: 70% monthly active users after 3 months
- Registration conversion rate: +25% with Google authentication
- Time-to-first-value: from 5 minutes → under 2 minutes

**Guardrails:**
- Evidence link accuracy ≥95% (verified working links)
- Generated content relevance score ≥8/10 (user-rated)
- **Content Quality & Anti-Hallucination:**
  - **Hallucination rate ≤5%** (false or unsupported claims in generated content)
  - **Source attribution accuracy ≥95%** (all claims traceable to source documents)
  - **Verification pass rate ≥90%** (generated content verified against sources)
  - **User acceptance rate ≥80%** (flagged low-confidence items approved by users)
- **Artifact enrichment quality: Technology extraction accuracy ≥85%**
- **Artifact enrichment confidence: Average ≥70% (minimum 60% threshold)**
- **GitHub repository analysis: Enrichment failure rate ≤10%**
- **Evidence Review & Acceptance:**
  - **Evidence acceptance rate: 100%** (all evidence reviewed before artifact finalization)
  - **Average review time per evidence: ≤3 minutes**
  - **Evidence edit rate: 40-60%** (users editing extracted content to improve accuracy)
  - **Re-unification success rate: ≥95%** (edited evidence successfully unified into artifact)
- Export formatting quality ≥95% ATS compatibility
- Response time ≤30 seconds for CV generation (including verification)
- Authentication flow completion ≤3 seconds
- Artifact edit operations complete ≤2 seconds for metadata changes
- Evidence review operations complete ≤5 seconds for re-unification
- Support ticket reduction: 60% decrease in authentication-related issues

## Non-Goals

This PRD explicitly excludes:
- Real-time collaboration features (v1)
- Advanced analytics dashboard (v1)
- Interview scheduling or tracking
- Salary benchmarking or negotiation
- Background verification services
- Social media optimization beyond LinkedIn basics
- Enterprise SSO for v1
- Multiple linked social accounts
- Advanced artifact workflow states (draft, review, published)

## Requirements

### Functional

**Core CV/Cover Letter Generation:**
- As a job seeker, I upload my projects/work history with supporting evidence links
- **As a job seeker with GitHub repositories, I receive comprehensive technology and achievement extraction from config files, source code, CI/CD configs, and documentation**
- **As a job seeker, my GitHub repositories are intelligently analyzed to identify the most relevant files automatically**
- **As a job seeker, I must review and accept all AI-extracted evidence before my artifact is finalized**
- **As a job seeker reviewing evidence, I can edit summaries, add/remove technologies, and modify achievements inline**
- **As a job seeker, I cannot proceed with bullet generation until all evidence is reviewed and accepted**
- **As a job seeker, my edits to evidence content are reflected in the final artifact description through LLM re-unification**
- **As a job seeker, I can see confidence scores for each extracted technology and achievement to guide my review**
- **As a job seeker, I receive clear visual indicators (color-coded badges) showing extraction confidence levels**
- **As a job seeker, I can re-edit evidence after initial acceptance and trigger re-unification of artifact content**
- As a job seeker, I paste a job description and get a relevance-ranked CV within 30 seconds
- **As a job seeker, I receive exactly 3 tailored bullet points for each selected artifact, optimized for the target role**
- As a job seeker, I receive a cover letter that specifically cites 2-3 pieces of evidence
- As a job seeker, I can export clean PDF/Docx that passes ATS parsing
- As a job seeker, I can track which evidence was included in each application version
- As a job seeker, I can reuse role labels for similar positions without re-uploading

**Authentication & User Management:**
- As a new user, I can sign in with my Google account in one click without creating passwords
- As an existing user, I can link my Google account to my current email/password account
- As a user without Google, I can still register with email/password as a fallback
- As a returning user, I am automatically logged in when I click Google sign-in

**Artifact Management:**
- As a user with uploaded artifacts, I can edit title, description, dates, technologies, and collaborators
- As a user maintaining my artifacts, I can add, edit, and remove evidence links with URL validation
- As a user with uploaded documents, I can replace files or add new files to existing artifacts
- As a user managing multiple artifacts, I can edit multiple artifacts efficiently with bulk operations
- As a user, all my edit operations are validated and provide clear error feedback

**Content Quality & Verification:**
- As a job seeker, I receive confidence scores for all generated content so I can assess quality
- As a job seeker, I can see which parts of generated content come from which source documents (source attribution)
- As a job seeker, low-confidence content is flagged for my review before finalization
- As a job seeker, I can approve or reject flagged content with clear indicators of potential quality issues
- As a job seeker, all generated claims are verified against my uploaded artifacts to prevent hallucinations
- As a job seeker, I can trace any bullet point or achievement back to its original source document

### Non-Functional
- **Availability:** ≥99.5% uptime during business hours
- **Performance:**
  - CV generation ≤30s, evidence verification ≤10s
  - Evidence extraction (wizard Step 5) ≤30 seconds for 3 sources
  - Evidence re-unification (after user edits) ≤5 seconds
  - Evidence content updates ≤2 seconds per edit
  - Authentication flow ≤3 seconds
  - Artifact metadata edits ≤2 seconds
  - File uploads with progress indicators
- **Security:**
  - Evidence links encrypted at rest, no credential storage
  - OAuth 2.0 compliance with PKCE
  - Secure token storage and refresh mechanisms
  - Server-side validation for all user inputs
- **Privacy:** User data isolated, GDPR/CCPA compliant deletion
- **Scalability:** Support 10,000 concurrent users, 1M+ artifacts stored
- **Usability:**
  - Intuitive editing interfaces with form validation
  - Clear authentication options presentation
  - Responsive design for mobile artifact editing

## Dependencies

**Data:**
- Skills taxonomy database (O*NET, LinkedIn Skills)
- ATS parsing validation dataset
- Company information database

**Services:**
- LLM API access (OpenAI/Anthropic) for content generation
- Document parsing service (PDF/Docx)
- URL validation and metadata extraction
- Email/authentication service
- Google Cloud Console OAuth credentials

**Legal/Policy:**
- Privacy policy review for evidence link handling and Google integration
- Terms of service for generated content liability
- GDPR compliance review for EU users

**3rd-party:**
- GitHub API for repository metadata
- Google Sign-In JavaScript SDK
- LinkedIn API for profile enhancement (future)
- Job board APIs for posting ingestion (future)

## Risks & Mitigations

**Top risks:**
1. **LLM hallucination/inaccuracy** →
   - **Detection:**
     - Source attribution tracking (all claims traced to source documents)
     - Post-generation verification service (LLM-based fact-checking)
     - Confidence scoring (flag items <0.7 for review)
     - Human review loops for flagged content
   - **Prevention:**
     - Enhanced extraction prompts with explicit "no inference" rules
     - Require source quotes in all extractions
     - Verification layer validates generated content against sources
     - GPT-5 reasoning mode for high-stakes accuracy tasks (extraction, verification)
     - Task-specific model configuration (reasoning_effort="high" for accuracy-critical tasks)
   - **Fallback:** Template-based generation, user review workflow for low-confidence items
   - **Monitoring:** Track hallucination rate (target ≤5%), verification pass rate (target ≥90%)
2. **Evidence link degradation** → Detection: Automated link checking; Fallback: Link validation warnings, archive.org fallbacks
3. **ATS compatibility issues** → Detection: Test suite against major ATS systems; Fallback: Multiple export format options
4. **User data privacy concerns** → Detection: Security audits, penetration testing; Fallback: Enhanced encryption, data minimization
5. **OAuth integration complexity** → Detection: Comprehensive testing; Fallback: Maintain email/password authentication
6. **Data corruption during editing** → Detection: Atomic transactions, validation; Fallback: File cleanup background jobs

## Analytics & Telemetry

**Events:**
- artifact_uploaded, artifact_edited, label_created, cv_generated, cover_letter_generated, document_exported, evidence_clicked
- google_signin_initiated, google_signin_completed, account_linked
- edit_initiated, edit_completed, bulk_edit_completed
- **content_verified, low_confidence_flagged, content_approved, content_rejected, hallucination_detected**
- **source_attribution_viewed, verification_passed, verification_failed**
- **evidence_review_started, evidence_accepted, evidence_rejected, evidence_edited, evidence_review_completed**
- **evidence_summary_edited, evidence_technology_added, evidence_technology_removed, evidence_achievement_edited**
- **artifact_reunification_triggered, artifact_reunification_completed, artifact_reunification_failed**
- error_generation_failed, link_validation_failed, export_failed, auth_failed, edit_failed, verification_error, reunification_error

**Dashboards:**
- User engagement: uploads, generations, exports per user
- Authentication: adoption rates, success rates, fallback usage
- Artifact management: edit frequency, bulk operation usage
- **Evidence Review: acceptance rates, average review time, edit rates per evidence type, confidence distribution**
- **Re-unification: success rates, latency, LLM cost per re-unification, user satisfaction**
- Performance: generation latency, success rates, error rates
- Quality: user ratings, ATS pass rates, evidence link health
- **Content Quality: hallucination rate, verification pass rate, confidence score distribution, user acceptance rate**
- **Source Attribution: attribution coverage, traceability accuracy, low-confidence item distribution**

**Alert thresholds:**
- Generation success rate <95%
- Average generation time >45s (including verification)
- Evidence link failure rate >10%
- User error rate >5%
- Authentication success rate <98%
- Edit operation failure rate >2%
- **Evidence review completion rate <95%** (users abandoning wizard at review step)
- **Average evidence review time >5 minutes** (review friction too high)
- **Re-unification failure rate >5%** (LLM integration issues)
- **Evidence edit rate <30%** (users not engaging with review, may indicate poor UX)
- **Evidence edit rate >70%** (extraction quality too low, needs prompt improvement)
- **Hallucination rate >5%** (immediate investigation required)
- **Verification pass rate <90%** (content quality degradation)
- **User acceptance rate <80%** (flagged content quality issues)
- **Low-confidence item rate >30%** (prompt quality degradation)