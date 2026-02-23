import React from 'react'
import { Card } from './ui/Card'
import { cn } from '@/utils/cn'

interface SkeletonProps {
  className?: string
}

const Skeleton: React.FC<SkeletonProps> = ({ className }) => (
  <div
    className={cn(
      'animate-pulse bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 bg-[length:200%_100%] rounded',
      className
    )}
    style={{
      animation: 'shimmer 2s infinite linear',
    }}
  />
)

export const ArtifactDetailSkeleton: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      {/* Header Skeleton */}
      <div className="flex items-center justify-between min-w-0 gap-4">
        <div className="flex items-center space-x-4 flex-1 min-w-0">
          {/* Back Button */}
          <Skeleton className="h-10 w-24" />

          <div className="flex-1 min-w-0">
            {/* Title */}
            <Skeleton className="h-8 w-64 mb-2" />
            {/* Metadata line */}
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-1" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-1" />
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-4 w-1" />
              <Skeleton className="h-4 w-28" />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-3 flex-shrink-0">
          <Skeleton className="h-10 w-20" />
          <Skeleton className="h-10 w-24" />
        </div>
      </div>

      {/* Tabs Skeleton */}
      <div className="border-b border-gray-200 bg-gray-50">
        <div className="flex space-x-2 px-2">
          <Skeleton className="h-12 w-24" />
          <Skeleton className="h-12 w-36" />
        </div>
      </div>

      {/* Content Area Skeleton */}
      <div className="mt-6 space-y-6">
        {/* Your Context - Prominent */}
        <Card className="relative overflow-hidden border-2 border-purple-200 bg-gradient-to-br from-purple-50 via-white to-purple-50">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-purple-600 to-pink-600"></div>
          <div className="p-6 pl-8">
            <div className="flex items-center gap-3 mb-4">
              <Skeleton className="h-10 w-10 rounded-xl" />
              <div className="flex-1">
                <Skeleton className="h-6 w-40 mb-2" />
                <Skeleton className="h-4 w-56" />
              </div>
            </div>
            <div className="p-5 bg-white rounded-lg border border-gray-200 shadow-sm">
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          </div>
        </Card>

        {/* Main Content - Full Width */}
        <div className="space-y-6">
          {/* Description Card */}
          <Card className="p-6">
            <Skeleton className="h-5 w-32 mb-4" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </Card>

          {/* Technologies Card */}
          <Card className="p-6">
            <Skeleton className="h-5 w-28 mb-4" />
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-8 w-20 rounded-lg" />
              <Skeleton className="h-8 w-24 rounded-lg" />
              <Skeleton className="h-8 w-16 rounded-lg" />
              <Skeleton className="h-8 w-28 rounded-lg" />
            </div>
          </Card>

          {/* Evidence Card */}
          <Card className="p-6">
            <Skeleton className="h-5 w-36 mb-4" />
            <div className="space-y-3">
              <Skeleton className="h-16 w-full rounded-lg" />
              <Skeleton className="h-16 w-full rounded-lg" />
            </div>
          </Card>
        </div>
      </div>

      {/* Add shimmer animation styles */}
      <style>{`
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
      `}</style>
    </div>
  )
}
