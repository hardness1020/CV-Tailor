import React from 'react'
import * as RadixTabs from '@radix-ui/react-tabs'
import { cn } from '@/utils/cn'

interface TabsRootProps extends RadixTabs.TabsProps {
  children: React.ReactNode
}

interface TabsListProps {
  children: React.ReactNode
  className?: string
}

interface TabsTriggerProps {
  value: string
  children: React.ReactNode
  count?: number
  className?: string
}

interface TabsContentProps extends RadixTabs.TabsContentProps {
  value: string
  children: React.ReactNode
  className?: string
}

const TabsRoot: React.FC<TabsRootProps> = ({ children, ...props }) => {
  return <RadixTabs.Root {...props}>{children}</RadixTabs.Root>
}

const TabsList: React.FC<TabsListProps> = ({ children, className }) => {
  return (
    <RadixTabs.List
      className={cn('border-b border-gray-200 bg-gray-50 flex', className)}
    >
      {children}
    </RadixTabs.List>
  )
}

const TabsTrigger: React.FC<TabsTriggerProps> = ({
  value,
  children,
  count,
  className,
}) => {
  return (
    <RadixTabs.Trigger
      value={value}
      className={cn(
        'px-6 py-3 text-sm font-medium transition-colors border-b-2',
        'data-[state=active]:border-purple-600 data-[state=active]:text-purple-700 data-[state=active]:bg-white',
        'data-[state=inactive]:border-transparent data-[state=inactive]:text-gray-600 hover:text-gray-900 hover:bg-gray-100',
        'focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
    >
      <span className="flex items-center gap-2">
        {children}
        {count !== undefined && (
          <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full font-semibold">
            {count}
          </span>
        )}
      </span>
    </RadixTabs.Trigger>
  )
}

const TabsContent: React.FC<TabsContentProps> = ({
  value,
  children,
  className,
  ...props
}) => {
  return (
    <RadixTabs.Content
      value={value}
      className={cn(
        'focus:outline-none focus:ring-2 focus:ring-purple-500',
        className
      )}
      {...props}
    >
      {children}
    </RadixTabs.Content>
  )
}

export const Tabs = {
  Root: TabsRoot,
  List: TabsList,
  Trigger: TabsTrigger,
  Content: TabsContent,
}
