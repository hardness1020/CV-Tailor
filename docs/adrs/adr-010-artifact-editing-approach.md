# ADR: Artifact Editing Implementation Approach

**Document ID:** ADR-010
**Date:** 2024-09-24
**Status:** Accepted
**Author:** Claude Code
**Related:** PRD-20250924-02, SPEC-20250924-02-SYSTEM

## Context

The CV Tailor system currently allows users to create and upload artifacts but provides no mechanism to modify them after creation. Users must delete and recreate entire artifacts for any changes, creating significant friction and potential data loss. We need to implement comprehensive artifact editing capabilities while maintaining data integrity, user experience, and system performance.

The decision involves multiple architectural considerations including API design patterns, validation strategies, file management approaches, and state management patterns.

## Decision Drivers

### Functional Requirements
- **Data Integrity**: Ensure atomic updates across related models (Artifact, EvidenceLink, UploadedFile)
- **User Experience**: Provide intuitive editing with real-time validation and optimistic updates
- **File Management**: Handle file uploads, replacements, and cleanup safely
- **Scalability**: Support bulk operations and concurrent editing scenarios
- **Security**: Maintain proper authorization and input validation

### Technical Constraints
- **Existing Architecture**: Must work with current Django/DRF backend and React/TypeScript frontend
- **Database Design**: Work within existing model relationships and constraints
- **Authentication**: Integrate with current JWT-based authentication system
- **File Storage**: Work with current file upload and storage mechanisms

### Business Priorities
- **Time to Market**: Leverage existing components and patterns where possible
- **Risk Mitigation**: Minimize breaking changes to existing functionality
- **User Adoption**: Ensure feature discoverability and ease of use
- **Data Quality**: Improve overall artifact data quality through easier editing

## Options Considered

### Option 1: Full REST CRUD with Separate Endpoints
**Architecture**: Implement full CRUD operations with dedicated endpoints for each entity type.

**API Design**:
- `PATCH/PUT /api/artifacts/{id}/` - Artifact updates
- `POST/PUT/DELETE /api/artifacts/{id}/evidence-links/` - Evidence management
- `POST/DELETE /api/artifacts/{id}/files/` - File operations
- `PATCH /api/artifacts/bulk/` - Bulk operations

**Pros**:
- Clear separation of concerns
- Fine-grained control over operations
- Easy to implement incremental features
- Standard REST patterns
- Good for API documentation and testing

**Cons**:
- Multiple API calls for complex updates
- Potential consistency issues between calls
- More complex frontend state management
- Higher network overhead for related updates

### Option 2: GraphQL Mutations with Nested Updates
**Architecture**: Use GraphQL mutations to handle complex nested updates in single operations.

**Schema Example**:
```graphql
mutation UpdateArtifact($input: ArtifactUpdateInput!) {
  updateArtifact(input: $input) {
    artifact { ... }
    evidenceLinks { ... }
    files { ... }
  }
}
```

**Pros**:
- Single operation for complex updates
- Strong typing and validation
- Efficient data fetching
- Atomic operations
- Excellent developer experience

**Cons**:
- Significant architecture change required
- Learning curve for existing team
- Additional complexity in backend implementation
- Not consistent with existing REST API

### Option 3: Hybrid REST with Transaction Endpoints
**Architecture**: Combine traditional REST with special transaction endpoints for complex operations.

**API Design**:
- `PATCH /api/artifacts/{id}/` - Simple metadata updates
- `POST /api/artifacts/{id}/transaction/` - Complex multi-entity updates
- Individual CRUD endpoints for granular operations
- Bulk endpoints for mass operations

**Pros**:
- Best of both worlds approach
- Maintains REST compatibility
- Atomic operations when needed
- Gradual complexity scaling
- Backward compatibility

**Cons**:
- Mixed patterns may confuse developers
- Additional endpoint maintenance
- Transaction complexity in implementation

### Option 4: Event-Sourced Updates
**Architecture**: Implement editing as a series of events that modify artifact state.

**Event Types**: ArtifactUpdated, EvidenceLinkAdded, FileReplaced, etc.

**Pros**:
- Complete audit trail
- Easy rollback capabilities
- Eventual consistency support
- Excellent for analytics

**Cons**:
- Over-engineering for current requirements
- Significant architectural changes required
- Complex implementation
- May impact performance

## Decision

**Selected Option: Option 1 - Full REST CRUD with Separate Endpoints**

We will implement comprehensive CRUD operations using separate, well-defined REST endpoints for each entity type, with atomic transaction support at the service layer.

### Rationale

1. **Consistency with Existing Architecture**: Maintains compatibility with our current Django REST Framework implementation and established patterns.

2. **Incremental Implementation**: Allows us to roll out editing features progressively - start with basic metadata editing, then add evidence management, file operations, and bulk operations.

3. **Clear Separation of Concerns**: Each endpoint has a single responsibility, making testing, documentation, and maintenance straightforward.

4. **Frontend Flexibility**: Enables both simple single-field updates and complex multi-step editing workflows based on UI requirements.

5. **Performance Optimization**: Individual endpoints can be optimized independently, and clients can choose the most efficient update pattern for their use case.

6. **Error Handling**: Granular error reporting for specific operations, improving user experience and debugging.

## Implementation Details

### Backend Architecture

#### API Endpoints
```python
# Artifact metadata editing
PATCH /api/v1/artifacts/{artifact_id}/          # Partial updates
PUT /api/v1/artifacts/{artifact_id}/            # Full replacement

# Evidence link management
POST /api/v1/artifacts/{artifact_id}/evidence-links/        # Add link
PUT /api/v1/evidence-links/{link_id}/                       # Update link
DELETE /api/v1/evidence-links/{link_id}/                    # Remove link

# File operations
POST /api/v1/artifacts/{artifact_id}/files/                 # Add files
DELETE /api/v1/files/{file_id}/                             # Remove file

# Bulk operations
PATCH /api/v1/artifacts/bulk/                               # Bulk updates
```

#### Service Layer
```python
class ArtifactEditService:
    @transaction.atomic
    def update_artifact(self, artifact_id, user, updates):
        # Validate ownership and permissions
        # Apply updates atomically
        # Handle related model updates
        # Return updated artifact with related data

class EvidenceManagerService:
    def add_evidence_link(self, artifact_id, user, link_data):
        # Validate artifact ownership
        # Validate URL and link data
        # Create evidence link
        # Update artifact metadata if needed

class FileManagerService:
    @transaction.atomic
    def add_files(self, artifact_id, user, files):
        # Validate file types and sizes
        # Upload files to storage
        # Create UploadedFile records
        # Create EvidenceLink records
        # Clean up on failure
```

#### Validation Strategy
```python
class ArtifactUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artifact
        fields = ['title', 'description', 'artifact_type', 'start_date',
                 'end_date', 'technologies', 'collaborators']

    def validate(self, data):
        # Cross-field validation
        # Business rule validation
        # Return validated data

class EvidenceLinkUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceLink
        fields = ['url', 'link_type', 'description']

    def validate_url(self, value):
        # URL accessibility validation
        # Security checks
        # Return validated URL
```

### Frontend Architecture

#### State Management
```typescript
interface ArtifactEditStore {
  // Current editing state
  editingArtifact: Artifact | null;
  isDirty: boolean;
  validationErrors: ValidationErrors;

  // Operations
  updateArtifact: (updates: Partial<Artifact>) => Promise<void>;
  addEvidenceLink: (link: EvidenceLink) => Promise<void>;
  updateEvidenceLink: (id: string, updates: Partial<EvidenceLink>) => Promise<void>;
  removeEvidenceLink: (id: string) => Promise<void>;
  addFiles: (files: File[]) => Promise<void>;
  removeFile: (fileId: string) => Promise<void>;

  // Validation and persistence
  validateChanges: () => ValidationResult;
  saveChanges: () => Promise<void>;
  discardChanges: () => void;
}
```

#### Component Structure
```tsx
// Main editing interface
<ArtifactEditForm>
  <MetadataSection />
  <EvidenceLinksSection />
  <FilesSection />
  <ActionButtons />
</ArtifactEditForm>

// Evidence management
<EvidenceLinksManager>
  <EvidenceLinksList />
  <AddEvidenceLinkForm />
</EvidenceLinksManager>

// File management
<FileManager>
  <FileUploadZone />
  <FileList />
</FileManager>
```

## Security Considerations

### Authorization
- Users can only edit their own artifacts
- Permission checks at both API and service layer
- JWT token validation for all operations

### Input Validation
- Server-side validation for all user inputs
- File type and size restrictions
- URL validation and sanitization
- XSS protection through proper encoding

### Data Integrity
- Database transactions for multi-model updates
- Foreign key constraint validation
- Concurrent edit detection using optimistic locking

## Performance Implications

### Positive Impacts
- Granular updates reduce unnecessary data transfer
- Individual endpoint optimization
- Caching opportunities for frequently accessed data

### Potential Concerns
- Multiple API calls for complex updates
- Increased database connections for related operations

### Mitigation Strategies
- Implement request coalescing for rapid successive updates
- Use database connection pooling
- Add caching layers for expensive operations
- Monitor and optimize N+1 query patterns

## Migration Strategy

### Phase 1: Basic Metadata Editing
- Implement PATCH/PUT endpoints for Artifact model
- Add basic frontend editing form
- Comprehensive validation and error handling

### Phase 2: Evidence Link Management
- Add evidence link CRUD endpoints
- Implement evidence management UI
- URL validation and accessibility checking

### Phase 3: File Operations
- File upload/replacement endpoints
- File management UI components
- Orphaned file cleanup processes

### Phase 4: Bulk Operations
- Bulk update endpoints
- Multi-artifact selection UI
- Performance optimization and monitoring

## Monitoring and Success Metrics

### Technical Metrics
- API response times (target: <200ms for metadata updates)
- Error rates (target: <1% for edit operations)
- Database query efficiency
- File operation success rates

### User Experience Metrics
- Feature adoption rates
- Edit completion rates
- User satisfaction scores
- Support ticket volume

### Business Metrics
- Reduction in artifact duplication
- Improvement in data quality
- User retention and engagement

## Alternatives Considered but Rejected

### JSON Patch Operations
**Rejected because**: Too complex for typical user editing scenarios, difficult to validate, and poor error messaging for business users.

### WebSocket-based Real-time Editing
**Rejected because**: Over-engineering for single-user artifact editing, adds unnecessary complexity, and most editing sessions are short-lived.

### Immutable Update Patterns
**Rejected because**: Would require significant architectural changes, and versioning requirements are not yet clear from business requirements.

## Consequences

### Positive Consequences
- **Maintainability**: Clear, predictable API patterns that follow REST conventions
- **Testability**: Individual endpoints are easy to unit test and integration test
- **Scalability**: Can optimize individual operations independently
- **User Experience**: Flexible frontend implementation enabling both simple and complex editing workflows

### Negative Consequences
- **Network Overhead**: Multiple API calls needed for complex updates
- **State Management Complexity**: Frontend needs to coordinate multiple operations
- **Potential Consistency Issues**: Brief windows where related data may be out of sync

### Risk Mitigation
- Use optimistic locking to prevent concurrent edit conflicts
- Implement comprehensive error recovery mechanisms
- Provide clear user feedback for multi-step operations
- Add monitoring to detect and alert on consistency issues

## Future Considerations

This decision establishes a foundation that can evolve:

- **Version History**: Can add audit trails without changing core API structure
- **Collaborative Editing**: Real-time features can be added as separate endpoints
- **Workflow States**: Draft/review/published states can be added to existing models
- **API Evolution**: Can migrate to GraphQL or other patterns in future versions

The chosen approach provides a solid foundation for immediate needs while maintaining flexibility for future enhancements.