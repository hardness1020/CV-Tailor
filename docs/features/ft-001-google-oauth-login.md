# Feature Specification: Google OAuth Login Integration

**Document ID:** FT-001-GOOGLE-OAUTH-LOGIN
**Date:** 2024-09-24
**Last Updated:** 2025-10-26
**Status:** Implemented ✅
**Author:** Claude Code
**Related Documents:** PRD-20250924, SPEC-20250924-SYSTEM, ADR-012-google-auth-strategy, OP-001-google-oauth-credential-update

## Implementation Status

**Deployed**: October 26, 2025

| Component | Status | Notes |
|-----------|--------|-------|
| **Backend (Django + django-allauth)** | ✅ Implemented | OAuth endpoints configured |
| **Frontend (Google Identity Services)** | ✅ Implemented | Sign-in button integrated |
| **Development Environment** | ✅ Working | Tested successfully |
| **Production Frontend** | ✅ Deployed | CloudFront + S3 |
| **Production Backend** | ⚠️ Infrastructure Issue | Pre-existing ALB problem (not OAuth related) |
| **OAuth Consent Screen** | ✅ Production Mode | All users allowed (not restricted) |

**Current Credentials**:
- **Email**: admin@<YOUR_DOMAIN>
- **Client ID**: `<YOUR_GOOGLE_CLIENT_ID>.apps.googleusercontent.com`
- **Consent Screen**: Production (all Google users can authenticate)

See [OP-001](../op-notes/op-001-google-oauth-credential-update.md) for credential rotation details.

## Feature Overview

Integrate Google OAuth 2.0 authentication to enable users to sign in using their existing Google accounts, reducing friction in the registration and login process while maintaining our existing user management system.

## User Stories

### Primary User Stories

**US-001: New User Google Sign-Up**
```
As a new user visiting CV Tailor
I want to sign up using my Google account
So that I can quickly start creating CVs without creating another password
```

**Acceptance Criteria:**
- [ ] Google Sign-In button is prominently displayed on registration page
- [ ] Clicking Google Sign-In opens Google OAuth consent dialog
- [ ] After consent, user is automatically registered and logged in
- [ ] User profile is pre-populated with Google account information (name, email, profile picture)
- [ ] User is redirected to dashboard after successful registration
- [ ] Registration process completes in under 30 seconds

**US-002: Existing User Google Login**
```
As an existing user who has linked their Google account
I want to log in using Google
So that I can access my account without remembering my password
```

**Acceptance Criteria:**
- [ ] Google Sign-In button is available on login page
- [ ] Clicking Google Sign-In authenticates existing linked user
- [ ] User is redirected to their previous page or dashboard
- [ ] Login process completes in under 10 seconds
- [ ] User session is properly established with JWT tokens

**US-003: Account Linking for Existing Users**
```
As an existing user with email/password authentication
I want to link my Google account to my existing profile
So that I can use Google login in the future
```

**Acceptance Criteria:**
- [ ] "Link Google Account" option available in user profile/settings
- [ ] Clicking link initiates OAuth flow
- [ ] After consent, Google account is linked to existing user profile
- [ ] User receives confirmation of successful linking
- [ ] Linked account shows in user settings with option to unlink
- [ ] User can subsequently use Google login

**US-004: Profile Synchronization**
```
As a user with a linked Google account
I want my profile information to stay updated with my Google account
So that my information is always current
```

**Acceptance Criteria:**
- [ ] Profile picture is synchronized from Google account
- [ ] Name is synchronized from Google account (with option to override)
- [ ] Email updates are handled appropriately
- [ ] User can control which fields sync from Google
- [ ] Sync status is visible in profile settings

## Technical Requirements

### Backend Requirements

#### Django Settings Configuration
```python
INSTALLED_APPS = [
    # ... existing apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
        'FETCH_USERINFO': True,
    }
}
```

#### API Endpoints

**POST /api/auth/google/**
```json
Request:
{
  "credential": "eyJhbGciOiJSUzI1NiIs..." // Google ID token
}

Response (Success):
{
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "profile_image": "https://...",
    // ... other user fields
  },
  "created": false // true if new user was created
}

Response (Error):
{
  "error": "google_auth_failed",
  "message": "Invalid Google token",
  "recoverable": true
}
```

**POST /api/auth/google/link/**
```json
Request:
{
  "credential": "eyJhbGciOiJSUzI1NiIs..." // Google ID token
}

Response (Success):
{
  "message": "Google account linked successfully",
  "linked_email": "user@gmail.com"
}

Response (Error):
{
  "error": "account_already_linked",
  "message": "This Google account is already linked to another user"
}
```

#### Custom Social Account Adapter
```python
# accounts/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Handle account linking and duplicate prevention."""
        # Implementation details in technical spec
        pass

    def save_user(self, request, sociallogin, form=None):
        """Create user with Google profile data."""
        # Implementation details in technical spec
        pass
```

### Frontend Requirements

#### Google Identity Services Integration
```typescript
// services/googleAuth.ts
interface GoogleAuthConfig {
  clientId: string;
  redirectUri?: string;
}

interface GoogleCredentialResponse {
  credential: string;
  select_by: string;
}

export class GoogleAuthService {
  private config: GoogleAuthConfig;

  constructor(config: GoogleAuthConfig) {
    this.config = config;
  }

  async initialize(): Promise<void> {
    // Load Google Identity Services
  }

  async signIn(): Promise<GoogleCredentialResponse> {
    // Initiate Google Sign-In flow
  }

  async exchangeCredentialForTokens(credential: string): Promise<AuthTokens> {
    // Exchange Google credential for JWT tokens
  }
}
```

#### React Components

**GoogleSignInButton Component**
```tsx
interface GoogleSignInButtonProps {
  mode: 'login' | 'signup' | 'link';
  onSuccess?: (user: User) => void;
  onError?: (error: GoogleAuthError) => void;
  disabled?: boolean;
}

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  mode,
  onSuccess,
  onError,
  disabled = false
}) => {
  // Implementation with proper error handling and loading states
};
```

#### Auth Store Updates
```typescript
// stores/authStore.ts extensions
interface AuthState {
  // ... existing fields
  googleLinked: boolean;
  linkGoogleAccount: (credential: string) => Promise<void>;
  unlinkGoogleAccount: () => Promise<void>;
}
```

## User Experience Design

### UI/UX Requirements

#### Login/Registration Pages
- Google Sign-In button positioned prominently below title
- Visual hierarchy: Google button → divider → email form
- Consistent styling with existing button components
- Loading states during OAuth flow
- Clear error messaging for failed attempts

#### Button Design Specifications
```css
.google-signin-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #dadce0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #3c4043;
  cursor: pointer;
  transition: all 0.2s ease;
}

.google-signin-button:hover {
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.google-signin-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
```

#### Profile Settings Integration
- "Connected Accounts" section in user profile
- Visual indicator for linked Google account
- "Link Google Account" button for unlinked users
- "Unlink Account" option with confirmation dialog
- Sync preferences toggle switches

### User Flow Diagrams

#### New User Google Sign-Up Flow
```
[Landing Page] → [Click "Sign up with Google"] → [Google Consent] → [Profile Creation] → [Dashboard]
                                                       ↓
                                              [Error Handling] → [Retry/Fallback]
```

#### Existing User Account Linking Flow
```
[Profile Settings] → [Click "Link Google"] → [Google Consent] → [Confirmation] → [Settings Updated]
                                                    ↓
                                           [Account Already Linked] → [Error Message]
```

## Error Handling and Edge Cases

### Error Scenarios

#### Google Service Unavailable
- **Detection**: Google Identity Services fails to load
- **User Experience**: Show fallback email/password form
- **Technical**: Graceful degradation with retry mechanism
- **Recovery**: Automatic retry after 30 seconds, manual retry button

#### Invalid/Expired Google Token
- **Detection**: Backend token validation fails
- **User Experience**: "Authentication failed" message with retry option
- **Technical**: Clear any stored invalid tokens
- **Recovery**: Restart OAuth flow

#### Account Email Mismatch
- **Detection**: Google account email differs from existing account email
- **User Experience**: Clear explanation and options to link or create new account
- **Technical**: Prevent automatic account creation, require user decision
- **Recovery**: Manual account linking process

#### Network Connectivity Issues
- **Detection**: API calls fail with network errors
- **User Experience**: "Connection problem" message with retry
- **Technical**: Exponential backoff retry logic
- **Recovery**: Offline queue for retry when connection restored

### Edge Case Handling

#### Multiple Google Accounts
- User has multiple Google accounts in browser
- Google account chooser dialog appears
- Selected account is used for authentication
- Clear indication of which account was selected

#### Previously Deleted User Account
- Google account was linked to deleted user account
- Allow creation of new account with same Google account
- Clear any orphaned social account records

#### Profile Data Conflicts
- Google profile data conflicts with existing user data
- Provide user choice to keep existing or update from Google
- Maintain audit log of profile changes

## Security Requirements

### OAuth 2.0 Security

#### PKCE Implementation
- Code challenge and verifier generated for each OAuth flow
- Protection against authorization code interception attacks
- Server-side validation of code challenge

#### Token Security
```python
# Security settings
SOCIALACCOUNT_STORE_TOKENS = False  # Don't store OAuth access tokens
SOCIALACCOUNT_AUTO_SIGNUP = True    # Allow automatic user creation
SOCIALACCOUNT_EMAIL_VERIFICATION = 'optional'  # Trust Google email verification
```

#### Input Validation
- Validate Google ID tokens server-side
- Verify token audience and issuer
- Check token expiration and signature
- Rate limiting on authentication endpoints

### Data Privacy

#### User Data Handling
- Request minimal scopes (profile, email only)
- No storage of Google access tokens long-term
- Clear privacy policy updates explaining Google integration
- User consent for profile data synchronization

#### GDPR Compliance
- User control over data synchronization
- Right to unlink Google account
- Data export includes linked account information
- Account deletion removes social account links

## Testing Strategy

### Unit Tests

#### Backend Testing
```python
# tests/test_google_auth.py
class GoogleAuthTestCase(TestCase):
    def test_valid_google_token_creates_user(self):
        """Test user creation from valid Google ID token."""

    def test_existing_user_google_login(self):
        """Test login for user with linked Google account."""

    def test_account_linking(self):
        """Test linking Google account to existing user."""

    def test_invalid_token_rejection(self):
        """Test rejection of invalid Google tokens."""

    def test_duplicate_account_prevention(self):
        """Test prevention of duplicate Google account links."""
```

#### Frontend Testing
```typescript
// __tests__/googleAuth.test.tsx
describe('Google Authentication', () => {
  it('should render Google sign-in button', () => {
    // Test component rendering
  });

  it('should handle successful Google authentication', async () => {
    // Mock successful OAuth flow
  });

  it('should handle authentication errors', async () => {
    // Test error scenarios
  });

  it('should update auth store on successful login', async () => {
    // Test state management
  });
});
```

### Integration Tests

#### End-to-End Authentication Flow
```typescript
// e2e/googleAuth.e2e.test.ts
describe('Google Authentication E2E', () => {
  it('should complete full new user signup flow', async () => {
    // Test complete OAuth flow from UI to backend
  });

  it('should handle account linking for existing users', async () => {
    // Test account linking flow
  });
});
```

### Performance Tests

#### Load Testing Scenarios
- 100 concurrent Google OAuth flows
- Token refresh rate testing (1000/minute)
- Database query performance with social accounts
- Frontend bundle size impact measurement

## Deployment Requirements

### Environment Configuration

#### Development Environment
```bash
# .env.development
GOOGLE_CLIENT_ID=your-dev-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-dev-client-secret
```

#### Production Environment
```bash
# .env.production
GOOGLE_CLIENT_ID=your-prod-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-prod-client-secret
```

#### Google Cloud Console Setup
1. Create OAuth 2.0 Client ID
2. Configure authorized redirect URIs
3. Set up consent screen
4. Enable Google+ API (for profile information)

### Database Migrations

#### Required Migrations
```python
# Migration plan
# 1. django-allauth initial migration (automatic)
# 2. No custom User model changes required
# 3. Update fixtures for testing with social accounts
```

### Monitoring and Analytics

#### Key Metrics to Track
- Google authentication success rate
- Google authentication error rate by type
- New user conversion rate (Google vs email)
- Account linking adoption rate
- OAuth flow completion time

#### Logging Requirements
```python
# Structured logging for Google auth events
import logging

google_auth_logger = logging.getLogger('google_auth')

# Log authentication attempts, successes, failures
# Log account linking events
# Log token refresh activities
```

## Rollout Strategy

### Phase 1: Internal Testing (Week 1)
- Deploy to staging environment
- Internal team testing
- Security review
- Performance baseline establishment

### Phase 2: Beta Release (Week 2)
- Limited beta with 10% of new users
- Monitor key metrics and error rates
- Gather user feedback
- Address any critical issues

### Phase 3: Full Rollout (Week 3)
- Enable Google authentication for all users
- Monitor adoption rates
- Customer support training
- Documentation updates

### Phase 4: Optimization (Week 4+)
- Performance optimizations based on usage data
- User experience improvements
- Additional features (profile sync preferences)
- Consider additional OAuth providers

## Success Metrics

### Quantitative Metrics
- **Adoption Rate**: 70% of new users choose Google authentication within 30 days
- **Conversion Rate**: 25% improvement in visitor-to-registered-user conversion
- **Authentication Speed**: < 3 seconds for complete OAuth flow
- **Error Rate**: < 1% authentication failure rate
- **Support Tickets**: 60% reduction in authentication-related tickets

### Qualitative Metrics
- User satisfaction surveys showing improved onboarding experience
- Reduced user complaints about password management
- Positive feedback on authentication flow simplicity
- Customer support team reports fewer authentication issues

## Maintenance and Support

### Ongoing Maintenance Tasks
- Monitor Google API status and deprecations
- Update Google client libraries regularly
- Review and rotate OAuth client secrets quarterly
- Monitor authentication metrics weekly
- Review error logs and user feedback monthly

### Support Documentation
- User guide for Google authentication
- Troubleshooting guide for common issues
- Admin documentation for account management
- Developer documentation for API usage

### Escalation Procedures
- Authentication system outage response plan
- Google API outage mitigation procedures
- Security incident response for OAuth-related issues
- User account recovery procedures for linked accounts