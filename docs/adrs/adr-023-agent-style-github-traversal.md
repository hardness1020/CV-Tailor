# ADR: Implement Agent-Style GitHub Repository Traversal

**File:** docs/adrs/adr-023-agent-style-github-traversal.md
**Status:** Draft
**Date:** 2025-10-06
**Deciders:** Engineering Team
**Related:** ft-013-github-agent-traversal, spec-artifact-upload-enrichment-flow v1.3.0

---

## Context

### Problem Statement

Current GitHub repository enrichment suffers from significant quality and coverage gaps:

**Current Implementation (`document_loader_service.py:288-338`):**
- Fixed file selection: README + first 10 source files with path depth ≤ 3
- No config file parsing (misses `package.json`, `requirements.txt`, `Cargo.toml`)
- No CI/CD analysis (ignores `.github/workflows/`, test coverage configs)
- No documentation parsing (skips `docs/`, `CONTRIBUTING.md`, architecture docs)
- Arbitrary constraints prevent loading deeply nested important files

**Impact on Enrichment Quality:**
- **Technology extraction accuracy:** 60% (misses dependencies in config files)
- **Enrichment confidence:** 0.65 average (low due to limited context)
- **Enrichment failure rate:** 15% (quality validation rejects low-confidence results)
- **User satisfaction:** 7/10 (users report missing technologies and vague achievements)

**Quantitative Evidence:**
- 60-80% of repository context is **never analyzed** (only 10 files from 50-500 file repos)
- Config files like `package.json` contain **direct dependency listings** but are ignored
- CI/CD configs contain **quantifiable metrics** (test coverage, build times) but are skipped
- GitHub stars, contributors, and languages are extracted but **code patterns are not**

### Business Impact

Poor GitHub enrichment directly affects CV generation quality:
- Incomplete technology lists reduce ATS keyword matches
- Missing achievements weaken bullet point impact
- Low confidence triggers manual review workflows (adds 5-10 min/artifact)
- Users abandon artifact uploads after seeing poor enrichment previews (12% drop-off)

### Technical Constraints

1. **Token budget:** LangChain file loading averages 500 tokens/file (10 files = 5K tokens)
2. **LLM costs:** Current extraction costs $0.015/repo (GPT-5-mini for extraction)
3. **Processing latency:** GitHub enrichment takes 15-30 seconds (P95)
4. **API rate limits:** GitHub API allows 5K requests/hour (authenticated)

---

## Decision

Implement **agent-style GitHub repository traversal** with **4-phase intelligent analysis**:

### Phase 1: Reconnaissance
- Fetch repository metadata via GitHub API (languages, structure, file counts)
- Detect project type (web app, library, CLI tool, framework)
- Build file importance map based on project type

### Phase 2: Intelligent File Selection (LLM Agent)
- LLM-powered file prioritization using GPT-5
- Token-budget aware selection (target: 15-20 files within 8K tokens)
- Prioritize: config files > entry points > core modules > docs > infrastructure

### Phase 3: Hybrid File Analysis
- Multi-format specialized parsing:
  - **Config parser:** JSON/YAML/TOML for direct dependency extraction
  - **Source analyzer:** LLM-based pattern detection (architecture, APIs, DB usage)
  - **Infrastructure parser:** Docker, CI/CD workflow analysis
  - **Documentation analyzer:** Key features, quantitative metrics from docs
- Cross-reference findings for consistency validation

### Phase 4: Iterative Refinement (Optional)
- Agent evaluates: "Do we have enough context?" (confidence threshold: 0.75)
- If insufficient: request specific additional files
- Adaptive depth (stop when confidence threshold met or token budget exhausted)

### Implementation Architecture

**New Services:**
- `GitHubRepositoryAgent` (core layer): 4-phase orchestrator
- `HybridFileAnalyzer` (core layer): Multi-format parser
- Inherit from `BaseLLMService` for circuit breaker + performance tracking

**Integration Strategy: Direct Replacement (No Fallback)**

Replace existing `EvidenceContentExtractor.extract_github_content()` method entirely:

```python
# BEFORE (legacy fixed-file approach):
async def extract_github_content(repo_url, repo_stats, user_id) -> ExtractedContent:
    # Load README + first 10 source files (fixed selection)
    documents = await document_loader._process_github_repository(repo_url)
    # LLM extraction with limited context
    ...

# AFTER (agent-based replacement):
async def extract_github_content(repo_url, repo_stats, user_id) -> ExtractedContent:
    """
    Agent-based GitHub repository analysis with intelligent file selection.
    Replaced legacy fixed-file approach in v1.3.0.
    """
    agent = GitHubRepositoryAgent()
    return await agent.analyze_repository(
        repo_url=repo_url,
        user_id=user_id,
        token_budget=8000,
        repo_stats=repo_stats
    )
```

**Deployment Strategy: Canary Rollout (No Feature Flags)**
- Week 3: Deploy to 1 backend pod (canary), monitor 24 hours
- Week 4: Deploy to 25% of pods, monitor 48 hours
- Week 5: Deploy to 100% of pods (full rollout)
- Rollback via code revert if issues detected

**Database Schema:**
- New table: `github_repository_analysis` (stores 4-phase results)
- Extended table: `extracted_content` (add `agent_analysis_id` foreign key)

---

## Consequences

### Positive

1. **Quality Improvements (Expected):**
   - Technology extraction accuracy: **+40%** (60% → 85%)
   - Enrichment confidence: **+25%** (0.65 → 0.82 avg)
   - Enrichment failure rate: **-50%** (15% → 7.5%)
   - User satisfaction: **+2 points** (7/10 → 9/10)

2. **Feature Enhancements:**
   - Direct dependency extraction (e.g., "React 18.2.0" vs generic "React")
   - CI/CD metrics in achievements ("95% test coverage" from GitHub Actions config)
   - Architecture pattern detection (microservices, serverless, monolith)
   - Dependency version tracking for security/compatibility analysis

3. **Business Benefits:**
   - Reduced manual review time: **-5 min/artifact** (fewer low-confidence rejects)
   - Improved CV quality → **+10% ATS pass rate** (better keyword coverage)
   - Reduced upload abandonment: **-6%** (12% → 6% drop-off after preview)

4. **Technical Benefits:**
   - Adaptive to repo complexity (small repos: 5 files, large repos: 20 files)
   - Token-budget aware (prevents runaway costs)
   - Reuses existing infrastructure (BaseLLMService, DocumentLoader)
   - **Simpler codebase:** Single code path (~200 fewer lines vs dual-path)
   - **Cleaner API:** No `use_agent` parameter pollution
   - **Forces quality commitment:** Team fully owns agent implementation

### Negative

1. **Cost Increase:**
   - Token usage: **+100%** (5K → 10K tokens/repo)
   - LLM cost: **+$0.01/repo** (+67% from $0.015 → $0.025)
   - At 10K repos/month: **+$100/month** (acceptable for quality gains)

2. **Latency Increase:**
   - Processing time: **+10 seconds** (15-30s → 25-40s P95)
   - Still within 5-minute P95 target for overall enrichment
   - Async processing minimizes user-facing impact

3. **Complexity Increase:**
   - New services: **~900 lines** (GitHubRepositoryAgent + HybridFileAnalyzer)
   - New database table + migration
   - Additional test coverage needed (**~600 lines** of tests)
   - Maintenance overhead for agent prompts and logic

4. **Risk Factors (Replacement-Specific):**
   - **No automatic fallback:** If agent fails, entire GitHub enrichment breaks
   - **Slower rollback:** Requires code revert (5-10 min) instead of instant config change
   - **Higher pre-production burden:** Must validate on 50+ diverse repos before deploy
   - **No gradual sampling:** All-or-nothing deployment per pod (canary required)
   - Higher token usage increases OpenAI API costs (mitigation: token budget limits, caching)
   - Agent complexity may introduce bugs (mitigation: comprehensive tests, staged rollout)

### Neutral

- Database storage: **+5KB/repo** for `github_repository_analysis` records (negligible)
- Backward compatibility: **No breaking changes** to existing APIs (agent is opt-in)

---

## Alternatives Considered

### Alternative 1: Increase Fixed File Limit (10 → 50)

**Approach:** Simply load first 50 files instead of 10.

**Pros:**
- Minimal code changes (1-line config update)
- No LLM agent complexity
- Guaranteed to include more files

**Cons:**
- **Still arbitrary** (why 50? why not 100?)
- **Not adaptive** to repo size (small repos waste tokens, large repos still miss context)
- **No prioritization** (loads 50 random files, not important ones)
- **Token explosion:** 50 files × 500 tokens = **25K tokens** (+400% cost)
- **Rejected:** Doesn't solve root problem of intelligent file selection.

### Alternative 2: Load Entire Repository

**Approach:** Clone entire repo and load all files.

**Pros:**
- Complete context (0% missed files)
- No prioritization logic needed

**Cons:**
- **Prohibitively expensive:** Average repo = 200 files × 500 tokens = **100K tokens** (~$2/repo)
- **Massive latency:** Loading + processing 200 files = **5-10 minutes**
- **GitHub API abuse:** Cloning entire repos exceeds rate limits
- **Overkill:** Most enrichment value comes from top 20 files, not all 200
- **Rejected:** Cost and latency unacceptable.

### Alternative 3: Rule-Based File Prioritization

**Approach:** Hardcode priority rules (e.g., always load `package.json`, then `src/index.js`, etc.).

**Pros:**
- No LLM costs for file selection
- Deterministic behavior (easier to debug)
- Fast execution (no LLM call for Phase 2)

**Cons:**
- **Not adaptive** to different project types (React vs Django vs Rust have different important files)
- **Brittle:** Rules break when conventions change (e.g., `main.py` vs `app.py` vs `__init__.py`)
- **Manual maintenance:** Need separate rules for each language/framework
- **Partial solution:** Solves config file problem but not adaptive selection
- **Rejected:** Inflexible and high maintenance burden.

### Alternative 4: Agent-Style Traversal (CHOSEN)

**Approach:** LLM agent decides which files to load based on repo structure.

**Why chosen:**
- ✅ **Adaptive** to repo complexity and type
- ✅ **Token-budget aware** (stays within limits)
- ✅ **Prioritizes** intelligently (config > entry points > core modules)
- ✅ **Scales** to different project types (web apps, libraries, CLI tools)
- ✅ **Reasonable cost** (+$0.01/repo is acceptable)
- ✅ **Fallback safety** (legacy method still available)

---

## Rollback Plan

### Immediate Rollback (If Critical Issues)

**Trigger Conditions:**
- Agent failure rate >20% for 30 minutes
- LLM costs exceed +$0.10/repo for 1 hour
- Processing latency P95 >90 seconds for 15 minutes
- Multiple user complaints about enrichment quality
- Any 5xx errors from agent code

**Rollback Steps (Code Revert Required):**

```bash
# 1. Identify failing commit
git log --oneline backend/llm_services/services/core/

# 2. Create emergency revert branch
git checkout main
git checkout -b emergency/revert-github-agent
git revert <agent-commit-sha>

# 3. Create emergency PR
gh pr create --title "[EMERGENCY] Revert GitHub agent" \
             --body "Reverting due to: <reason>" \
             --base main

# 4. Merge and deploy (bypass normal review if critical)
gh pr merge --auto --squash

# 5. Deploy via CI/CD or manual
docker-compose up -d --build backend

# 6. Monitor for 30 minutes post-rollback
watch -n 10 'docker-compose logs backend --tail=100 | grep -i github'
```

**Estimated Rollback Time:** 5-10 minutes (code revert + deployment)

**Impact:**
- Brief service interruption during container restart (~30 seconds)
- All in-flight enrichments fail and must be retried
- Users see legacy GitHub extraction quality (pre-v1.3.0)
- No data loss (agent data remains in database for analysis)

### Gradual Rollback (If Partial Issues)

**Trigger Conditions:**
- Agent works for some repos but fails for specific patterns
- Certain project types (e.g., monorepos >1000 files) have high failure rates

**Mitigation Steps (Without Full Revert):**
1. Add defensive checks in agent code (deploy via hotfix):
   ```python
   # Emergency defensive wrapper
   async def extract_github_content(...):
       try:
           agent = GitHubRepositoryAgent()
           result = await agent.analyze_repository(...)

           # Quality gate: revert to simple extraction if low confidence
           if result.confidence < 0.4:
               return await self._simple_github_extraction(repo_url)
           return result
       except Exception as e:
           logger.error(f"Agent failed: {e}, using simple extraction")
           return await self._simple_github_extraction(repo_url)
   ```

2. Add timeout guards to prevent runaway costs:
   ```python
   result = await asyncio.wait_for(
       agent.analyze_repository(...),
       timeout=45  # 45s max per repo
   )
   ```

3. Improve agent prompts based on failure pattern analysis

**Impact:**
- Maintains agent for working cases
- Automatic fallback for problematic repos
- Data collection continues for debugging

### Long-Term Rollback (If Unsustainable)

**Trigger Conditions:**
- Cost increase unsustainable (consistently >+$0.05/repo)
- Agent bugs require constant hotfixes (>2 per week)
- User satisfaction does not improve after 60 days

**Deprecation Steps:**
1. Full code revert to pre-v1.3.0 GitHub extraction
2. Keep `github_repository_analysis` table for historical analysis
3. Extract learnings from agent data:
   - Which file types mattered most?
   - What patterns led to high confidence?
4. Implement simplified rule-based approach using agent insights:
   - Hardcode priority: `package.json` > `README.md` > `src/index.*`
   - Config-based file selection (no LLM for Phase 2)
5. Remove agent code after 3-month analysis period

**Impact:**
- Permanent return to simpler (but smarter) approach
- Retain valuable data for future improvements
- Knowledge transfer: Agent learnings inform v2.0 design

---

## Implementation Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Agent failure breaks all GitHub enrichment** | **Medium** | **Critical** | **Pre-prod validation on 50+ repos, canary deployment, emergency revert scripts** |
| LLM file selection misses critical files | Medium | High | File type whitelists, comprehensive test suite, post-deploy monitoring |
| GitHub API rate limit exceeded | Low | Medium | Request caching (24hr TTL), exponential backoff, rate limit monitoring |
| Agent cost explosion | Medium | High | Token budget limits (8K/repo), per-repo timeout (45s), cost alerts |
| Processing latency exceeds targets | Medium | Medium | Parallel phase execution, timeout enforcement, async processing |
| Agent introduces new bugs | High | Medium | Comprehensive tests (600+ lines), staged rollout, real-time error tracking |
| Database schema migration issues | Low | High | Test migrations in staging, backup before deploy, reversible migrations |
| **Rollback complexity** | **Low** | **Medium** | **Automated revert scripts, documented rollback procedure, on-call engineer** |

---

## Success Criteria

Implementation considered successful if (measured after 30 days at 100% rollout):

**Quality Metrics:**
- ✅ Technology extraction accuracy ≥85% (baseline: 60%)
- ✅ Enrichment confidence avg ≥0.80 (baseline: 0.65)
- ✅ Enrichment failure rate ≤10% (baseline: 15%)
- ✅ User satisfaction ≥8.5/10 (baseline: 7/10)

**Performance Metrics:**
- ✅ Agent success rate ≥90%
- ✅ Processing latency P95 ≤45 seconds (baseline: 30s)
- ✅ LLM cost ≤$0.03/repo (baseline: $0.015)

**Adoption Metrics:**
- ✅ Upload abandonment rate ≤8% (baseline: 12%)
- ✅ Manual review time -4 min/artifact (baseline: 5 min)

**System Health:**
- ✅ Agent failure rate <10%
- ✅ GitHub API errors <1%
- ✅ No regressions in non-GitHub evidence sources

---

## Monitoring & Evaluation

### Key Metrics to Track

**Agent Performance:**
- `github_agent_success_rate` (target: ≥90%)
- `github_agent_avg_files_loaded` (target: 15-20)
- `github_agent_avg_tokens_used` (target: 8K-10K)
- `github_agent_processing_time_ms` (target: ≤15s)

**Quality Indicators:**
- `technology_extraction_accuracy` (manual validation sample)
- `enrichment_confidence_distribution` (histogram)
- `quality_validation_pass_rate` (target: ≥90%)

**Cost Metrics:**
- `llm_cost_per_repo` (target: ≤$0.03)
- `monthly_agent_cost` (alert if >$500)

**User Experience:**
- `enrichment_failure_rate` (target: ≤10%)
- `user_satisfaction_rating` (post-enrichment survey)
- `upload_abandonment_rate` (target: ≤8%)

### Dashboards

**Grafana Dashboard: GitHub Agent Health**
- Success rate trends (7-day moving average)
- Cost per repo breakdown (by project type)
- Processing latency percentiles (P50, P95, P99)
- File selection distribution (config vs source vs docs)

**Alerts:**
- Agent success rate <85% for 10 minutes → P2 alert
- LLM cost >$0.05/repo for 1 hour → P1 alert
- Processing latency P95 >60s for 15 minutes → P2 alert
- GitHub API error rate >5% for 5 minutes → P1 alert

---

## Timeline & Phasing

### Phase 1: Development (Week 1-2)
- Implement `GitHubRepositoryAgent` (Phases 1-3 only)
- Implement `HybridFileAnalyzer`
- Write comprehensive tests (unit + integration)
- Database migration
- **Pre-production validation:** Test on 50+ diverse repos locally

**Validation Repos (Examples):**
- Python: Django, Flask, FastAPI (frameworks + libs)
- JavaScript: Next.js, React, Vue (different structures)
- Go: Kubernetes, Docker (large monorepos)
- Rust: Tokio, Serde (systems programming)
- Small libs: <50 files
- Large monorepos: >500 files

### Phase 2: Staging Deployment (Week 3)
- Deploy to staging environment (isolated from production)
- Run full enrichment test suite (all GitHub repos in test data)
- Load test: 100 concurrent enrichments
- Validate quality metrics meet targets:
  - ✅ Technology extraction accuracy ≥85%
  - ✅ Enrichment confidence avg ≥0.80
  - ✅ Agent success rate ≥90%
- Fix critical bugs before production

### Phase 3: Canary Production (Week 4)
**Day 1-2:** Deploy to **1 backend pod** (out of N pods)
- Monitor agent metrics 24/7
- Alert on-call engineer if failure rate >10%
- If stable for 48 hours → proceed

**Day 3-5:** Deploy to **25% of backend pods**
- Continue monitoring
- Gather user feedback on enrichment quality
- If stable for 72 hours → proceed

**Day 6-7:** Deploy to **100% of backend pods**
- Monitor for 7 days
- Validate cost projections ($0.025/repo actual vs estimated)
- Mark as stable if all success criteria met

### Phase 4: Optimization (Week 5+)
- Implement Phase 4 (iterative refinement) if Phase 1-3 performs well
- Add advanced features (dependency security analysis, license detection)
- Optimize costs (model selection, caching improvements, token budget tuning)

---

## Links

**PRD:**
- `docs/prds/prd.md` (v1.3.0)

**TECH-SPECs:**
- `docs/specs/spec-artifact-upload-enrichment-flow.md` (v1.3.0)
- `docs/specs/spec-llm.md` (v3.1.0)

**FEATUREs:**
- `docs/features/ft-013-github-agent-traversal.md` (to be created)

**Discovery:**
- `docs/discovery/ft-013-github-agent-codebase-discovery.md`

**Related ADRs:**
- `adr-015-multi-source-artifact-preprocessing.md` (original enrichment decision)
- `adr-022-gpt5-model-migration.md` (LLM model choice)

**Related Issues/PRs:**
- (To be linked when PR created)

---

## Approval

**Status:** Draft (pending human review at CHECKPOINT #1)

**Approvers:**
- [ ] Engineering Lead
- [ ] Product Manager
- [ ] Senior Backend Engineer

**Approval Date:** (To be filled after review)

---

**Last Updated:** 2025-10-06
**Next Review:** After CHECKPOINT #1 (Planning Complete)
