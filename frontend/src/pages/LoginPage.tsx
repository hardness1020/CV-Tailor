import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { Eye, EyeOff, ArrowRight, Lock } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { apiClient } from '@/services/apiClient'
import { GoogleSignInButton } from '@/components/GoogleSignInButton'
import { GoogleAuthError } from '@/services/googleAuth'
import { cn } from '@/utils/cn'
import type { User } from '@/types'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [failedAttempts, setFailedAttempts] = useState(0)
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(null)
  const [remainingCooldown, setRemainingCooldown] = useState(0)
  const navigate = useNavigate()
  const location = useLocation()
  const { setUser, setTokens } = useAuthStore()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldownUntil) {
      const interval = setInterval(() => {
        const remaining = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000))
        setRemainingCooldown(remaining)

        if (remaining === 0) {
          setCooldownUntil(null)
          setFailedAttempts(0)
        }
      }, 1000)

      return () => clearInterval(interval)
    }
  }, [cooldownUntil])

  const onSubmit = async (data: LoginForm) => {
    // Check if in cooldown period
    if (cooldownUntil && Date.now() < cooldownUntil) {
      toast.error(`Too many failed attempts. Please wait ${remainingCooldown} seconds.`)
      return
    }

    setIsLoading(true)
    try {
      const response = await apiClient.login(data.email, data.password)
      setUser(response.user)
      setTokens(response.access, response.refresh)

      // Reset rate limiting on successful login
      setFailedAttempts(0)
      setCooldownUntil(null)

      toast.success('Welcome back!')

      // Redirect to the page they were trying to access or dashboard
      const from = location.state?.from?.pathname || '/dashboard'
      navigate(from, { replace: true })
    } catch (error) {
      console.error('Login error:', error)

      // Implement exponential backoff: 5s, 10s, 30s after 3rd, 4th, 5th+ attempts
      const newAttempts = failedAttempts + 1
      setFailedAttempts(newAttempts)

      let cooldownSeconds = 0
      if (newAttempts >= 3 && newAttempts < 5) {
        cooldownSeconds = 5 * Math.pow(2, newAttempts - 3) // 5s, 10s
      } else if (newAttempts >= 5) {
        cooldownSeconds = 30 // 30s for 5+ attempts
      }

      if (cooldownSeconds > 0) {
        const cooldownEnd = Date.now() + (cooldownSeconds * 1000)
        setCooldownUntil(cooldownEnd)
        setRemainingCooldown(cooldownSeconds)
        toast.error(`Too many failed attempts. Please wait ${cooldownSeconds} seconds.`)
      } else {
        toast.error('Invalid email or password')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleSuccess = (_user: User, created: boolean) => {
    toast.success(created ? 'Welcome to CV Tailor!' : 'Welcome back!')

    // Redirect to the page they were trying to access or dashboard
    const from = location.state?.from?.pathname || '/dashboard'
    navigate(from, { replace: true })
  }

  const handleGoogleError = (error: GoogleAuthError) => {
    if (error.type === 'USER_CANCELLED') {
      // Don't show error for user cancellation
      return
    }

    toast.error(error.message)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center py-8 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-blue-400/10 to-indigo-400/10 rounded-full -translate-y-48 translate-x-48" />
      <div className="absolute bottom-0 left-0 w-80 h-80 bg-gradient-to-tr from-purple-400/10 to-pink-400/10 rounded-full translate-y-40 -translate-x-40" />
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-gradient-to-r from-indigo-400/5 to-purple-400/5 rounded-full" />

      <div className="max-w-md w-full relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-100 to-indigo-100 border border-blue-200 rounded-full mb-2">
              <Lock className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-semibold text-blue-700">Secure Login</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 tracking-tight">
              Welcome to
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent"> CV Tailor</span>
            </h1>
            <p className="text-gray-600 leading-relaxed">
              Generate tailored CVs with AI-powered insights from your professional artifacts
            </p>
          </div>
        </div>

        {/* Login Card */}
        <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/50 p-8 space-y-6">
          {/* Google Sign-In Button */}
          <GoogleSignInButton
            mode="signin"
            onSuccess={handleGoogleSuccess}
            onError={handleGoogleError}
            disabled={isLoading}
            className="w-full"
          />

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t-2 border-gradient-to-r from-gray-200 via-gray-300 to-gray-200" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-4 py-2 bg-white text-sm font-semibold text-gray-600 rounded-full border border-gray-200">
                Or continue with email
              </span>
            </div>
          </div>

          {/* Email/Password Form */}
          <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
            <div className="space-y-5">
              <div>
                <label htmlFor="email" className="block text-sm font-bold text-gray-800 mb-3">
                  Email address
                </label>
                <input
                  {...register('email')}
                  type="email"
                  autoComplete="email"
                  className={cn(
                    'w-full px-4 py-4 border-2 border-gray-200 rounded-xl text-sm font-medium placeholder-gray-400 bg-white/50 backdrop-blur-sm focus:outline-none focus:ring-4 focus:ring-blue-100 focus:border-blue-500 transition-all duration-200',
                    errors.email && 'border-red-300 focus:border-red-500 focus:ring-red-100'
                  )}
                  placeholder="Enter your email address"
                />
                {errors.email && (
                  <p className="mt-2 text-sm text-red-600 font-medium">{errors.email.message}</p>
                )}
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-bold text-gray-800 mb-3">
                  Password
                </label>
                <div className="relative">
                  <input
                    {...register('password')}
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    className={cn(
                      'w-full px-4 py-4 pr-12 border-2 border-gray-200 rounded-xl text-sm font-medium placeholder-gray-400 bg-white/50 backdrop-blur-sm focus:outline-none focus:ring-4 focus:ring-blue-100 focus:border-blue-500 transition-all duration-200',
                      errors.password && 'border-red-300 focus:border-red-500 focus:ring-red-100'
                    )}
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600 transition-colors duration-200"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
                {errors.password && (
                  <p className="mt-2 text-sm text-red-600 font-medium">{errors.password.message}</p>
                )}
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="group relative overflow-hidden w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 disabled:transform-none disabled:opacity-60 disabled:cursor-not-allowed disabled:shadow-md"
              >
                <div className="flex items-center justify-center gap-3">
                  {isLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      <span>Signing you in...</span>
                    </>
                  ) : (
                    <>
                      <span>Sign In</span>
                      <ArrowRight className="h-5 w-5 transform group-hover:translate-x-1 transition-transform duration-200" />
                    </>
                  )}
                </div>
                {!isLoading && (
                  <div className="absolute inset-0 bg-white/10 transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                )}
              </button>
            </div>

            <div className="text-center">
              <span className="text-sm text-gray-600">
                Don't have an account?{' '}
                <Link
                  to="/register"
                  className="font-bold text-blue-600 hover:text-blue-500 transition-colors duration-200"
                >
                  Sign up
                </Link>
              </span>
            </div>
          </form>
        </div>

        {/* Trust indicators */}
        <div className="mt-8 text-center">
          <div className="flex items-center justify-center gap-6 text-xs text-gray-500">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="font-medium">Secure & Private</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="font-medium">AI-Powered</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              <span className="font-medium">Professional</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}