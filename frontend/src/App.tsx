import { Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { apiClient } from '@/services/apiClient'
import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import DashboardPage from '@/pages/DashboardPage'
import ArtifactsPage from '@/pages/ArtifactsPage'
import ArtifactDetailPage from '@/pages/ArtifactDetailPage'
import ArtifactUpload from '@/components/ArtifactUpload'
import GenerationsPage from '@/pages/GenerationsPage'
import GenerationCreatePage from '@/pages/GenerationCreatePage'
import GenerationDetailPage from '@/pages/GenerationDetailPage'
import ProfilePage from '@/pages/ProfilePage'

function App() {
  const { isAuthenticated, setUser, setLoading, clearAuth } = useAuthStore()

  useEffect(() => {
    // Check if user is authenticated on app load
    const initializeAuth = async () => {
      if (isAuthenticated) {
        setLoading(true)
        try {
          const user = await apiClient.getCurrentUser()
          setUser(user)
        } catch (error) {
          console.error('Failed to get current user:', error)
          clearAuth()
        } finally {
          setLoading(false)
        }
      }
    }

    initializeAuth()
  }, [isAuthenticated, setUser, setLoading, clearAuth])

  return (
    <Routes>
      {/* Default route - Dashboard first approach */}
      <Route path="/" element={<DashboardPage />} />

      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected routes */}
      <Route
        path="/dashboard"
        element={<DashboardPage />}
      />
      <Route
        path="/artifacts"
        element={
          <ProtectedRoute>
            <Layout>
              <ArtifactsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/artifacts/upload"
        element={
          <ProtectedRoute>
            <Layout>
              <ArtifactUpload />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/artifacts/upload/:artifactId"
        element={
          <ProtectedRoute>
            <Layout>
              <ArtifactUpload />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/artifacts/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <ArtifactDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/generations"
        element={
          <ProtectedRoute>
            <Layout>
              <GenerationsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/generations/create"
        element={
          <ProtectedRoute>
            <Layout>
              <GenerationCreatePage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/generations/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <GenerationDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Layout>
              <ProfilePage />
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App