# CV Tailor Frontend

A modern React application for generating targeted CVs with evidence from professional artifacts.

## Features

- **Artifact Management**: Upload and organize professional projects, documents, and work samples
- **Intelligent CV Generation**: AI-powered CV creation based on job descriptions and artifact matching
- **Document Export**: Export CVs in PDF and Word formats with customizable templates
- **User Authentication**: Secure login and registration system
- **Responsive Design**: Optimized for desktop and mobile devices

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Routing**: React Router v6
- **Form Handling**: React Hook Form with Zod validation
- **File Upload**: React Dropzone
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Notifications**: React Hot Toast

## Project Structure

```
src/
├── components/        # Reusable UI components
│   ├── Layout.tsx    # Main application layout
│   ├── ProtectedRoute.tsx
│   └── ArtifactUpload.tsx
├── pages/            # Page components
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── DashboardPage.tsx
│   ├── ArtifactsPage.tsx
│   ├── GeneratePage.tsx
│   └── ProfilePage.tsx
├── stores/           # Zustand state stores
│   ├── authStore.ts
│   ├── artifactStore.ts
│   └── generationStore.ts
├── services/         # API client and external services
│   └── apiClient.ts
├── types/            # TypeScript type definitions
│   └── index.ts
├── utils/            # Utility functions
│   ├── cn.ts
│   └── formatters.ts
├── App.tsx           # Main application component
├── main.tsx          # Application entry point
└── index.css         # Global styles
```

## Getting Started

### Prerequisites

- Node.js 18 or higher
- npm or yarn package manager

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and visit [http://localhost:3000](http://localhost:3000)

### Development Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run typecheck` - Run TypeScript type checking
- `npm test` - Run tests with Vitest

## API Integration

The frontend communicates with the Django backend API at `/api/`. The API client is configured to:

- Automatically attach JWT tokens to requests
- Handle token refresh on expiration
- Show user-friendly error messages
- Retry failed requests with exponential backoff

### Environment Variables

Create a `.env.local` file for local development:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SENTRY_DSN=your_sentry_dsn
VITE_GA_ID=your_google_analytics_id
```

## Component Guidelines

### Naming Conventions

- Use PascalCase for component names
- Use camelCase for props and functions
- Use kebab-case for CSS classes

### File Organization

- Each component should have its own file
- Related components can be grouped in subdirectories
- Export components as default exports

### State Management

- Use Zustand stores for global state
- Keep local state in components when possible
- Use React Query for server state management

### Styling

- Use Tailwind CSS utility classes
- Create reusable component variants with `cn()` utility
- Follow the design system color palette

## Features Implementation Status

### ✅ Completed
- [x] Project setup and configuration
- [x] Authentication (login/register)
- [x] Basic layout and navigation
- [x] Dashboard with overview
- [x] User profile management

### 🚧 In Progress
- [ ] Artifact upload system (ft-001)
  - [x] File upload with drag & drop
  - [x] Metadata form with validation
  - [x] Technology and collaborator management
  - [x] Evidence links support
  - [ ] Backend integration
  - [ ] Progress tracking

### 📋 Planned
- [ ] CV generation workflow (ft-002)
  - [ ] Job description analysis
  - [ ] Artifact selection and matching
  - [ ] Generation preferences
  - [ ] Real-time progress tracking

- [ ] Document export (ft-003)
  - [ ] Template selection
  - [ ] Export configuration
  - [ ] PDF/Word generation
  - [ ] Download management

## Performance Optimizations

- **Code Splitting**: Components are lazy-loaded by route
- **Bundle Analysis**: Use `npm run build` to analyze bundle size
- **Image Optimization**: All images are optimized and properly sized
- **Caching**: API responses are cached where appropriate

## Testing Strategy

- **Unit Tests**: Component logic and utility functions
- **Integration Tests**: Component interactions and API calls
- **E2E Tests**: Complete user journeys with Playwright

## Accessibility

- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader compatibility
- High contrast mode support

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Follow the existing code style and conventions
2. Write tests for new features
3. Update documentation as needed
4. Ensure all linting and type checking passes

## Deployment

The application is built for static hosting and can be deployed to:

- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages

Build the application with:
```bash
npm run build
```

The built files will be in the `dist/` directory.