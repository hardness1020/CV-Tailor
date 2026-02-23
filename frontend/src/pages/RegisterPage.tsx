import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { Eye, EyeOff, ArrowRight, UserPlus } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { apiClient } from '@/services/apiClient'
import { GoogleSignInButton } from '@/components/GoogleSignInButton'
import { GoogleAuthError } from '@/services/googleAuth'
import { cn } from '@/utils/cn'
import type { User } from '@/types'

const registerSchema = z.object({
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
})

type RegisterForm = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()
  const { setUser, setTokens } = useAuthStore()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true)
    try {
      const { confirmPassword, firstName, lastName, ...formData } = data
      const registerData = {
        ...formData,
        firstName: firstName,
        lastName: lastName,
        passwordConfirm: confirmPassword,
      }
      const response = await apiClient.register(registerData)
      setUser(response.user)
      setTokens(response.access, response.refresh)

      toast.success('Welcome to CV Tailor!')
      navigate('/dashboard', { replace: true })
    } catch (error: any) {
      console.error('Registration error:', error)

      // Show specific error messages from the API
      if (error.response?.data) {
        const errorData = error.response.data
        if (typeof errorData === 'string') {
          toast.error(errorData)
        } else if (errorData.error) {
          toast.error(errorData.error)
        } else if (errorData.email) {
          toast.error(`Email: ${errorData.email[0]}`)
        } else if (errorData.password) {
          toast.error(`Password: ${errorData.password[0]}`)
        } else {
          toast.error('Failed to create account. Please check your information.')
        }
      } else {
        toast.error('Failed to create account. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleSuccess = (_user: User, created: boolean) => {
    toast.success(created ? 'Welcome to CV Tailor!' : 'Welcome back!')
    navigate('/dashboard', { replace: true })
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
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-100 to-pink-100 border border-purple-200 rounded-full mb-2">
              <UserPlus className="h-4 w-4 text-purple-600" />
              <span className="text-sm font-semibold text-purple-700">Join CV Tailor</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 tracking-tight">
              Create Your
              <span className="bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent"> Account</span>
            </h1>
            <p className="text-gray-600 leading-relaxed">
              Start generating tailored CVs with AI-powered insights from your professional artifacts
            </p>
          </div>
        </div>

        {/* Register Card */}
        <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/50 p-8 space-y-6">
          {/* Google Sign-In Button */}
          <GoogleSignInButton
            mode="signup"
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
                Or create with email
              </span>
            </div>
          </div>

          {/* Email/Password Form */}
          <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="firstName" className="block text-sm font-bold text-gray-800 mb-3">
                    First name
                  </label>
                  <input
                    {...register('firstName')}
                    type="text"
                    autoComplete="given-name"
                    className={cn(
                      'w-full px-4 py-4 border-2 border-gray-200 rounded-xl text-sm font-medium placeholder-gray-400 bg-white/50 backdrop-blur-sm focus:outline-none focus:ring-4 focus:ring-purple-100 focus:border-purple-500 transition-all duration-200',
                      errors.firstName && 'border-red-300 focus:border-red-500 focus:ring-red-100'
                    )}
                    placeholder="Enter first name"
                  />
                  {errors.firstName && (
                    <p className="mt-2 text-sm text-red-600 font-medium">{errors.firstName.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="lastName" className="block text-sm font-bold text-gray-800 mb-3">
                    Last name
                  </label>
                  <input
                    {...register('lastName')}
                    type="text"
                    autoComplete="family-name"
                    className={cn(
                      'w-full px-4 py-4 border-2 border-gray-200 rounded-xl text-sm font-medium placeholder-gray-400 bg-white/50 backdrop-blur-sm focus:outline-none focus:ring-4 focus:ring-purple-100 focus:border-purple-500 transition-all duration-200',
                      errors.lastName && 'border-red-300 focus:border-red-500 focus:ring-red-100'
                    )}
                    placeholder="Enter last name"
                  />
                  {errors.lastName && (
                    <p className="mt-2 text-sm text-red-600 font-medium">{errors.lastName.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-bold text-gray-800 mb-3">
                  Email address
                </label>
                <input
                  {...register('email')}
                  type="email"
                  autoComplete="email"
                  className={cn(
                    'w-full px-4 py-4 border-2 border-gray-200 rounded-xl text-sm font-medium placeholder-gray-400 bg-white/50 backdrop-blur-sm focus:outline-none focus:ring-4 focus:ring-purple-100 focus:border-purple-500 transition-all duration-200',
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
                    autoComplete="new-password"
                    className={cn(
                      'w-full px-4 py-4 pr-12 border-2 border-gray-200 rounded-xl text-sm font-medium placeholder-gray-400 bg-white/50 backdrop-blur-sm focus:outline-none focus:ring-4 focus:ring-purple-100 focus:border-purple-500 transition-all duration-200',
                      errors.password && 'border-red-300 focus:border-red-500 focus:ring-red-100'
                    )}
                    placeholder="Create a strong password"
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

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-bold text-gray-800 mb-3">
                  Confirm password
                </label>
                <div className="relative">
                  <input
                    {...register('confirmPassword')}
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    className={cn(
                      'w-full px-4 py-4 pr-12 border-2 border-gray-200 rounded-xl text-sm font-medium placeholder-gray-400 bg-white/50 backdrop-blur-sm focus:outline-none focus:ring-4 focus:ring-purple-100 focus:border-purple-500 transition-all duration-200',
                      errors.confirmPassword && 'border-red-300 focus:border-red-500 focus:ring-red-100'
                    )}
                    placeholder="Confirm your password"
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600 transition-colors duration-200"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="mt-2 text-sm text-red-600 font-medium">{errors.confirmPassword.message}</p>
                )}
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="group relative overflow-hidden w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold px-8 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 disabled:transform-none disabled:opacity-60 disabled:cursor-not-allowed disabled:shadow-md"
              >
                <div className="flex items-center justify-center gap-3">
                  {isLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      <span>Creating account...</span>
                    </>
                  ) : (
                    <>
                      <span>Create Account</span>
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
                Already have an account?{' '}
                <Link
                  to="/login"
                  className="font-bold text-purple-600 hover:text-purple-500 transition-colors duration-200"
                >
                  Sign in
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
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              <span className="font-medium">AI-Powered</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-pink-500 rounded-full"></div>
              <span className="font-medium">Professional</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}