# Feature — 003 Document Export System

**File:** docs/features/ft-003-document-export.md
**Owner:** Backend Team
**TECH-SPECs:** `spec-20250923-api.md`, `spec-20250923-frontend.md`, `spec-20250923-system.md`

## Acceptance Criteria

### Export Format Support
- [ ] Generate PDF documents with professional formatting and ATS-friendly layout
- [ ] Generate Microsoft Word (.docx) documents with editable formatting
- [ ] Maintain consistent styling across export formats (fonts, spacing, margins)
- [ ] Support multiple CV templates (modern, classic, technical, creative)
- [ ] Include optional QR codes linking to evidence URLs
- [ ] Generate cover letters in matching format to CV template

### Evidence Integration
- [ ] Embed clickable hyperlinks to evidence URLs in PDF exports
- [ ] Include optional footnote section with numbered evidence references
- [ ] Generate QR codes for evidence links when requested by user
- [ ] Validate evidence links are accessible before including in export
- [ ] Support evidence link customization (display text vs actual URL)
- [ ] Track which evidence links are included in each export for analytics

### Document Quality & ATS Optimization
- [ ] Generate documents that pass ATS parsing tests (Workday, Greenhouse, Lever)
- [ ] Maintain proper heading hierarchy and semantic structure
- [ ] Use ATS-friendly fonts (Arial, Calibri, Times New Roman)
- [ ] Ensure consistent formatting without tables or complex layouts
- [ ] Include proper metadata in PDF (title, author, keywords)
- [ ] Support accessibility features (screen reader compatibility)

### Performance & Reliability
- [ ] Document generation completes within 10 seconds (P95)
- [ ] Handle concurrent export requests (100+ simultaneous exports)
- [ ] Generate file sizes under 2MB for typical CVs
- [ ] Support documents up to 5 pages without performance degradation
- [ ] Graceful error handling with specific error messages
- [ ] Automatic retry for transient failures (network, service unavailable)

## Design Changes

### API Endpoints
```
POST /api/v1/export/{generation_id}
Headers: Authorization: Bearer <token>
Body: {
  format: "pdf" | "docx",
  template_id: number,
  options: {
    include_evidence: boolean,
    evidence_format: "hyperlinks" | "footnotes" | "qr_codes",
    page_margins: "narrow" | "normal" | "wide",
    font_size: number, // 10-14
    color_scheme: "monochrome" | "accent" | "full_color"
  },
  sections: {
    include_professional_summary: boolean,
    include_skills: boolean,
    include_experience: boolean,
    include_projects: boolean,
    include_education: boolean,
    include_certifications: boolean
  },
  watermark?: {
    text: string,
    opacity: number // 0.1-0.5
  }
}

Response: 202 {
  export_id: string,
  status: "processing",
  estimated_completion_time: timestamp,
  file_size_estimate: number
}

GET /api/v1/export/{export_id}/status
Response: 200 {
  export_id: string,
  status: "processing" | "completed" | "failed",
  progress_percentage: number,
  error_message?: string,
  file_size?: number,
  download_url?: string, // Temporary signed URL
  expires_at?: timestamp
}

GET /api/v1/export/{export_id}/download
Headers: Authorization: Bearer <token>
Response: 200
Content-Type: application/pdf | application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="cv_{{user_name}}_{{company}}.pdf"
Body: [Binary file data]
```

### Database Schema Updates
```sql
-- Export jobs tracking
CREATE TABLE export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES auth_user(id) ON DELETE CASCADE,
    generated_document_id UUID REFERENCES generated_documents(id),
    format VARCHAR(10) NOT NULL, -- pdf, docx
    template_id INTEGER,
    export_options JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'processing',
    progress_percentage INTEGER DEFAULT 0,
    file_path TEXT,
    file_size INTEGER,
    download_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Template definitions
CREATE TABLE export_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50), -- modern, classic, technical, creative
    description TEXT,
    preview_image_url TEXT,
    template_config JSONB NOT NULL,
    css_styles TEXT,
    is_premium BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Export analytics
CREATE TABLE export_analytics (
    id SERIAL PRIMARY KEY,
    export_id UUID REFERENCES export_jobs(id),
    event_type VARCHAR(50), -- created, downloaded, shared
    metadata JSONB DEFAULT '{}',
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Document Templates
```python
# PDF Generation with ReportLab
class PDFGenerator:
    def __init__(self, template_config):
        self.template = template_config
        self.page_width = letter[0]
        self.page_height = letter[1]

    def generate_cv(self, content, options):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []

        # Header section
        story.append(self._create_header(content['personal_info']))

        # Professional summary
        if options.get('include_professional_summary'):
            story.append(self._create_section(
                "Professional Summary",
                content['professional_summary']
            ))

        # Experience section
        story.append(self._create_experience_section(
            content['experience'],
            options.get('include_evidence', False)
        ))

        # Build PDF
        doc.build(story)
        return buffer.getvalue()

# Word Document Generation with python-docx
class DocxGenerator:
    def __init__(self, template_path):
        self.template = Document(template_path)

    def generate_cv(self, content, options):
        doc = Document()

        # Set document properties
        doc.core_properties.title = f"CV - {content['personal_info']['name']}"
        doc.core_properties.author = content['personal_info']['name']

        # Add sections
        self._add_header(doc, content['personal_info'])
        self._add_summary(doc, content['professional_summary'])
        self._add_experience(doc, content['experience'], options)

        return self._save_to_buffer(doc)
```

### Frontend Components
```tsx
// Export configuration dialog
<ExportDialog
  generationId={currentGeneration.id}
  onExportStart={handleExportStart}
  onClose={handleClose}
>
  <TemplateSelector
    templates={availableTemplates}
    selectedTemplate={selectedTemplate}
    onSelect={setSelectedTemplate}
  />

  <ExportOptions
    options={exportOptions}
    onChange={setExportOptions}
  />

  <EvidenceSettings
    evidenceLinks={availableEvidence}
    format={evidenceFormat}
    onChange={setEvidenceFormat}
  />
</ExportDialog>

// Export progress and download
<ExportProgress
  exportId={currentExport.id}
  onComplete={handleExportComplete}
  onError={handleExportError}
/>

<DownloadButton
  exportId={completedExport.id}
  filename={downloadFilename}
  onDownload={trackDownload}
/>
```

## Test & Eval Plan

### Unit Tests
- [ ] PDF generation with various content lengths and structures
- [ ] Word document formatting and styling consistency
- [ ] Template rendering with different data configurations
- [ ] Evidence link formatting (hyperlinks, footnotes, QR codes)
- [ ] Error handling for malformed content data
- [ ] File size optimization and compression

### Integration Tests
- [ ] End-to-end export workflow from generation to download
- [ ] ATS compatibility testing with major platforms
- [ ] Template switching and formatting consistency
- [ ] Concurrent export processing under load
- [ ] File storage and retrieval operations
- [ ] Email delivery for completed exports (future feature)

### Quality Assurance Tests
- [ ] Visual regression testing for template layouts
- [ ] Cross-platform compatibility (Windows, Mac, Linux)
- [ ] Mobile browser download functionality
- [ ] Accessibility compliance (WCAG 2.1 AA)
- [ ] Print quality testing for physical documents
- [ ] Evidence link verification and clickability

### ATS Compatibility Testing
- [ ] Workday ATS parsing accuracy ≥95%
- [ ] Greenhouse resume parsing validation
- [ ] Lever applicant tracking system compatibility
- [ ] BambooHR resume processing
- [ ] SmartRecruiters parsing verification
- [ ] Generic ATS parsing with resume-parser libraries

### Performance Benchmarks
- **Generation Time**: P95 ≤10s, P50 ≤5s
- **File Size**: ≤2MB for typical 2-page CV
- **Concurrent Processing**: 100 simultaneous exports without degradation
- **Memory Usage**: ≤256MB per export process
- **Storage Efficiency**: Automatic cleanup of expired files

## Telemetry & Metrics to Watch

### User Engagement Metrics
- **Export Conversion Rate**: % of CV generations that lead to export
- **Format Preference**: Distribution of PDF vs DOCX exports
- **Template Usage**: Most popular templates and customization options
- **Download Completion**: % of exports that are successfully downloaded
- **Re-export Rate**: % of users who export multiple versions

### Quality Metrics
- **ATS Pass Rate**: % of exported documents that pass ATS parsing
- **Template Rendering Success**: % of exports without formatting errors
- **Evidence Link Validity**: % of included evidence links that are accessible
- **File Size Distribution**: Average and P95 file sizes by template
- **User Satisfaction**: Ratings for export quality and formatting

### System Performance Metrics
- **Export Processing Time**: P50, P95, P99 generation times
- **Queue Depth**: Background export job backlog
- **Error Rate**: Failed exports by error type and frequency
- **Storage Usage**: Total storage consumed by exported files
- **Bandwidth Usage**: Download traffic and CDN costs

### Business Intelligence
- **Premium Template Usage**: Adoption of paid template features
- **Evidence Feature Adoption**: Usage of QR codes and footnotes
- **Mobile Export Usage**: Export behavior on mobile devices
- **Sharing Behavior**: How users share exported documents
- **Repeat Usage**: User retention and export frequency

## Rollout/Canary & Rollback

### Rollout Strategy
**Phase 1 (10% Beta Users - 1 week)**
- Limited to PDF export only
- Basic templates without advanced formatting
- Enhanced error logging and user feedback collection
- Manual quality review of exported documents

**Phase 2 (50% Users - 1 week)**
- Enable DOCX export functionality
- Add premium templates and formatting options
- Automated quality monitoring implementation
- A/B testing of different template designs

**Phase 3 (100% Users)**
- Full feature rollout with all templates
- Evidence integration features (QR codes, footnotes)
- Performance optimization and CDN integration
- Real-time quality monitoring and alerts

### Feature Flags
- `feature.export.enabled` - Master export functionality
- `feature.export.docx_enabled` - Word document generation
- `feature.export.premium_templates` - Advanced template access
- `feature.export.evidence_integration` - QR codes and footnotes
- `feature.export.bulk_download` - Multiple document export

### Rollback Plan
**Critical Rollback Triggers**:
- Export success rate drops below 90%
- File generation time P95 exceeds 30 seconds
- ATS compatibility drops below 85%
- Storage costs exceed budget by 200%
- User complaints about document quality >5% of exports

**Rollback Steps**:
1. Disable new export requests via feature flag
2. Complete in-progress export jobs
3. Switch to basic template-only exports
4. Notify users of temporary reduced functionality
5. Debug and optimize in development environment
6. Gradual re-enablement with monitoring

## Edge Cases & Risks

### Document Quality Risks
- **Formatting Corruption**: Complex layouts may break during PDF generation
  - *Mitigation*: Template validation, fallback to simpler layouts
- **Evidence Link Failures**: URLs become inaccessible after document creation
  - *Mitigation*: Link validation before export, archive.org fallbacks
- **Font Rendering Issues**: Custom fonts may not display correctly across platforms
  - *Mitigation*: Stick to web-safe fonts, font fallback chains

### Technical Risks
- **Memory Exhaustion**: Large documents or concurrent exports exhaust server memory
  - *Mitigation*: Process limits, memory monitoring, queue management
- **Storage Costs**: Users downloading large numbers of documents increases storage costs
  - *Mitigation*: File lifecycle management, storage quotas, cost monitoring
- **CDN Performance**: Slow download speeds frustrate users
  - *Mitigation*: Multiple CDN regions, bandwidth monitoring

### Security Risks
- **Information Leakage**: Temporary download URLs accessible without authentication
  - *Mitigation*: Short-lived signed URLs, access logging
- **Malicious Content**: User-generated content includes inappropriate material
  - *Mitigation*: Content validation, terms of service enforcement
- **File System Attacks**: File path manipulation attempts
  - *Mitigation*: Secure file naming, sandboxed storage

### User Experience Risks
- **Download Failures**: Network issues prevent successful file downloads
  - *Mitigation*: Resume-capable downloads, multiple download attempts
- **Format Compatibility**: Generated documents don't open properly on user devices
  - *Mitigation*: Standard format compliance, compatibility testing
- **Template Confusion**: Too many template options overwhelm users
  - *Mitigation*: Guided template selection, preview functionality

### Business Risks
- **Support Burden**: Document formatting issues generate customer support tickets
  - *Mitigation*: Comprehensive FAQ, template preview, user education
- **Legal Issues**: Exported documents used inappropriately in job applications
  - *Mitigation*: Clear disclaimers, terms of service, user responsibility

## Dependencies

### External Services
- ReportLab for PDF generation
- python-docx for Word document creation
- QR code generation library (qrcode)
- File storage service (AWS S3/Azure Blob)
- CDN for fast file delivery

### Internal Components
- CV generation system (ft-002) for content input
- User authentication for download access control
- Celery task queue for async export processing
- Redis for temporary file URL caching
- PostgreSQL for export job tracking

### Team Dependencies
- Backend team for export API and processing logic
- Frontend team for export UI and download experience
- DevOps team for file storage and CDN infrastructure
- Design team for template creation and visual quality
- QA team for ATS compatibility testing