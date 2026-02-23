import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  FolderOpen,
  Zap,
  Download,
  TrendingUp,
  FileText,
  Award
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useArtifactStore } from '@/stores/artifactStore'
import { useGenerationStore } from '@/stores/generationStore'
import { apiClient } from '@/services/apiClient'
import Layout from '@/components/Layout'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuthStore()
  const { artifacts, setArtifacts, setLoading } = useArtifactStore()
  const { completedDocuments } = useGenerationStore()
  const [stats, setStats] = useState({
    totalArtifacts: 0,
    totalGenerations: 0,
    recentActivity: 0
  })

  const handleProtectedAction = (path: string) => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: { pathname: path } } })
    } else {
      navigate(path)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      const loadDashboardData = async () => {
        setLoading(true)
        try {
          const artifactsResponse = await apiClient.getArtifacts()
          setArtifacts(artifactsResponse.results)

          setStats({
            totalArtifacts: artifactsResponse.count,
            totalGenerations: completedDocuments.length,
            recentActivity: artifactsResponse.results.filter(
              a => new Date(a.createdAt) > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
            ).length
          })
        } catch (error) {
          console.error('Failed to load dashboard data:', error)
        } finally {
          setLoading(false)
        }
      }

      loadDashboardData()
    }
  }, [isAuthenticated, setArtifacts, setLoading, completedDocuments.length])

  const recentArtifacts = isAuthenticated ? artifacts.slice(0, 3) : []
  const recentGenerations = isAuthenticated ? completedDocuments.slice(0, 3) : []

  // Dashboard content component for authenticated users
  const DashboardContent = () => (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-200 rounded-full mb-3">
              <TrendingUp className="h-4 w-4 text-emerald-600" />
              <span className="text-sm font-medium text-emerald-700">Dashboard Overview</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 tracking-tight mb-2">
              Welcome back,
              <span className="bg-gradient-to-r from-emerald-600 to-green-600 bg-clip-text text-transparent"> {user?.firstName}</span>
            </h1>
            <p className="text-gray-600 max-w-2xl">
              Track your artifacts and document generation progress across your professional portfolio.
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">Total Artifacts</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.totalArtifacts}</p>
            </div>
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <FolderOpen className="h-5 w-5 text-purple-600" />
            </div>
          </div>
          <div className="mt-4">
            <Link
              to="/artifacts"
              className="text-sm text-purple-600 hover:text-purple-700 font-medium"
            >
              Manage artifacts →
            </Link>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">Documents Generated</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.totalGenerations}</p>
            </div>
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Zap className="h-5 w-5 text-blue-600" />
            </div>
          </div>
          <div className="mt-4">
            <Link
              to="/generations/create"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Generate new CV →
            </Link>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">Recent Activity</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.recentActivity}</p>
            </div>
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-orange-600" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm text-gray-600">New artifacts this week</p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Link
            to="/artifacts?action=upload"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-colors"
          >
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <FolderOpen className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">Upload Artifact</p>
              <p className="text-sm text-gray-600">Add a new project or document</p>
            </div>
          </Link>

          <Link
            to="/generations/create"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
          >
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Zap className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">Generate CV</p>
              <p className="text-sm text-gray-600">Create a targeted resume</p>
            </div>
          </Link>

          <div className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg opacity-50">
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <Download className="h-5 w-5 text-gray-400" />
            </div>
            <div>
              <p className="font-medium text-gray-900">Export Documents</p>
              <p className="text-sm text-gray-600">Coming soon</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Artifacts */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Artifacts</h2>
            <Link to="/artifacts" className="text-sm text-purple-600 hover:text-purple-700 font-medium">
              View all →
            </Link>
          </div>

          {recentArtifacts.length > 0 ? (
            <div className="space-y-3">
              {recentArtifacts.map((artifact) => (
                <div key={artifact.id} className="flex items-start gap-3 p-3 border border-gray-100 rounded-lg hover:border-gray-200 hover:bg-gray-50 transition-colors">
                  <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FileText className="h-4 w-4 text-purple-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 truncate">{artifact.title}</h3>
                    <p className="text-sm text-gray-600 truncate">{artifact.description}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(artifact.createdAt).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="w-12 h-12 mx-auto bg-gray-100 rounded-lg flex items-center justify-center mb-3">
                <FolderOpen className="h-6 w-6 text-gray-400" />
              </div>
              <h3 className="font-medium text-gray-900 mb-1">No artifacts yet</h3>
              <p className="text-sm text-gray-600 mb-4">Start building your professional portfolio</p>
              <Link
                to="/artifacts"
                className="inline-flex items-center px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors"
              >
                Upload your first artifact
              </Link>
            </div>
          )}
        </div>

        {/* Recent Generations */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent CV Generations</h2>
            <Link to="/generations/create" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
              Generate new →
            </Link>
          </div>

          {recentGenerations.length > 0 ? (
            <div className="space-y-3">
              {recentGenerations.map((generation) => (
                <div key={generation.id} className="flex items-start gap-3 p-3 border border-gray-100 rounded-lg hover:border-gray-200 hover:bg-gray-50 transition-colors">
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Award className="h-4 w-4 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900">CV Generation</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        generation.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {generation.status === 'completed' ? 'Completed' : 'Processing'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(generation.createdAt).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="w-12 h-12 mx-auto bg-gray-100 rounded-lg flex items-center justify-center mb-3">
                <Zap className="h-6 w-6 text-gray-400" />
              </div>
              <h3 className="font-medium text-gray-900 mb-1">No CV generations yet</h3>
              <p className="text-sm text-gray-600 mb-4">Create your first AI-powered CV</p>
              <Link
                to="/generations/create"
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                Generate your first CV
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )

  // Return conditional layout based on authentication
  if (isAuthenticated) {
    return (
      <Layout>
        <DashboardContent />
      </Layout>
    )
  }

  // Public dashboard for unauthenticated users
  return (
    <div className="min-h-screen bg-emerald-50/30">
      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-16 px-4 sm:px-6 lg:px-8">
        <div className="space-y-8">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {isAuthenticated ? 'Dashboard' : (
                <span className="inline-block bg-gradient-to-r from-blue-600 via-purple-600 to-emerald-600 bg-clip-text text-transparent animate-pulse hover:scale-105 transition-transform duration-300 ease-in-out drop-shadow-lg">
                  Welcome to CV Tailor
                </span>
              )}
            </h1>
            <p className="mb-10 mt-2 text-gray-600">
              {isAuthenticated
                ? "Welcome back! Here's an overview of your CV generation journey."
                : 'Generate targeted documents with evidence from your professional artifacts. Sign in to get started.'
              }
            </p>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Artifacts</p>
                  <p className="text-3xl font-bold text-gray-900">—</p>
                </div>
                <div className="p-3 bg-blue-100 rounded-full">
                  <FolderOpen className="h-6 w-6 text-blue-600" />
                </div>
              </div>
              <div className="mt-4">
                <button
                  onClick={() => handleProtectedAction('/artifacts')}
                  className="text-sm text-blue-600 hover:text-blue-500 font-medium"
                >
                  Sign in to view →
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Documents Generated</p>
                  <p className="text-3xl font-bold text-gray-900">—</p>
                </div>
                <div className="p-3 bg-green-100 rounded-full">
                  <Zap className="h-6 w-6 text-green-600" />
                </div>
              </div>
              <div className="mt-4">
                <button
                  onClick={() => handleProtectedAction('/generations/create')}
                  className="text-sm text-green-600 hover:text-green-500 font-medium"
                >
                  Sign in to generate →
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Recent Activity</p>
                  <p className="text-3xl font-bold text-gray-900">—</p>
                </div>
                <div className="p-3 bg-purple-100 rounded-full">
                  <TrendingUp className="h-6 w-6 text-purple-600" />
                </div>
              </div>
              <p className="mt-4 text-sm text-gray-500">Sign in to track activity</p>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-lg shadow p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
              <button
                onClick={() => handleProtectedAction('/artifacts?action=upload')}
                className="flex items-center space-x-3 p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors"
              >
                <div className="p-2 bg-blue-100 rounded-md">
                  <FolderOpen className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium text-gray-900">Upload Artifact</p>
                  <p className="text-sm text-gray-500">Sign in to upload artifacts</p>
                </div>
              </button>

              <button
                onClick={() => handleProtectedAction('/generations/create')}
                className="flex items-center space-x-3 p-4 border border-gray-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition-colors"
              >
                <div className="p-2 bg-green-100 rounded-md">
                  <Zap className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium text-gray-900">Generate CV</p>
                  <p className="text-sm text-gray-500">Sign in to generate documents</p>
                </div>
              </button>

              <button
                disabled
                className="flex items-center space-x-3 p-4 border border-gray-200 rounded-lg opacity-50 cursor-not-allowed"
              >
                <div className="p-2 bg-gray-100 rounded-md">
                  <Download className="h-5 w-5 text-gray-400" />
                </div>
                <div>
                  <p className="font-medium text-gray-900">Export Documents</p>
                  <p className="text-sm text-gray-500">Coming soon</p>
                </div>
              </button>
            </div>
          </div>

          {/* Call to Action for Unauthenticated Users */}
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="max-w-2xl mx-auto">
              <FileText className="h-16 w-16 text-blue-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Ready to Build Your Perfect CV?
              </h2>
              <p className="text-gray-600 mb-6">
                Upload your professional artifacts, add evidence links, and generate targeted documents
                that highlight your relevant experience for each job application.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/register"
                  className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                >
                  Get Started Free
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                >
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}