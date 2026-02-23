/**
 * Page Theme Configuration System
 *
 * Provides consistent color theming across CVs and Artifacts pages
 * while allowing each to maintain its brand identity.
 */

export interface PageTheme {
  name: string
  colors: {
    // Primary gradient colors
    primary: string
    primaryDark: string
    secondary: string
    secondaryDark: string

    // Badge colors
    badgeBg: string
    badgeBorder: string
    badgeText: string

    // Focus and interaction states
    focusRing: string
    focusBorder: string

    // Icon colors
    iconBg: string
    iconText: string
    iconHoverBg: string
    iconHoverText: string

    // Selection colors
    selectionBg: string
    selectionRing: string
    selectionBorder: string

    // Button colors
    buttonBg: string
    buttonHoverBg: string

    // Metadata box colors
    metadataBg: string
    metadataBorder: string
  }
}

export const cvsTheme: PageTheme = {
  name: 'CVs',
  colors: {
    // Primary: Blue/Indigo gradient
    primary: 'blue-600',
    primaryDark: 'blue-700',
    secondary: 'indigo-600',
    secondaryDark: 'indigo-700',

    // Badge
    badgeBg: 'from-blue-50 to-indigo-50',
    badgeBorder: 'blue-200',
    badgeText: 'blue-700',

    // Focus states
    focusRing: 'blue-100',
    focusBorder: 'blue-500',

    // Icons
    iconBg: 'blue-100',
    iconText: 'blue-600',
    iconHoverBg: 'blue-600',
    iconHoverText: 'white',

    // Selection
    selectionBg: 'blue-50',
    selectionRing: 'blue-500/10',
    selectionBorder: 'blue-500',

    // Buttons
    buttonBg: 'from-blue-600 to-indigo-600',
    buttonHoverBg: 'from-blue-700 to-indigo-700',

    // Metadata
    metadataBg: 'from-gray-50 to-blue-50/30',
    metadataBorder: 'blue-100',
  }
}

export const artifactsTheme: PageTheme = {
  name: 'Artifacts',
  colors: {
    // Primary: Purple/Pink gradient
    primary: 'purple-600',
    primaryDark: 'purple-700',
    secondary: 'pink-600',
    secondaryDark: 'pink-700',

    // Badge
    badgeBg: 'from-purple-50 to-pink-50',
    badgeBorder: 'purple-200',
    badgeText: 'purple-700',

    // Focus states
    focusRing: 'purple-100',
    focusBorder: 'purple-500',

    // Icons
    iconBg: 'purple-100',
    iconText: 'purple-600',
    iconHoverBg: 'purple-600',
    iconHoverText: 'white',

    // Selection
    selectionBg: 'purple-50',
    selectionRing: 'purple-500/10',
    selectionBorder: 'purple-500',

    // Buttons
    buttonBg: 'from-purple-600 to-pink-600',
    buttonHoverBg: 'from-purple-700 to-pink-700',

    // Metadata
    metadataBg: 'from-gray-50 to-purple-50/30',
    metadataBorder: 'purple-100',
  }
}

/**
 * Helper functions to generate theme-aware class names
 */
export const getThemeClasses = (theme: PageTheme) => ({
  // Gradient text for titles
  titleGradient: `bg-gradient-to-r from-${theme.colors.primary} to-${theme.colors.secondary} bg-clip-text text-transparent`,

  // Badge styling
  badge: `bg-gradient-to-r ${theme.colors.badgeBg} border border-${theme.colors.badgeBorder}`,
  badgeText: `text-${theme.colors.badgeText}`,
  badgeIcon: `text-${theme.colors.primary}`,

  // Button styling
  primaryButton: `bg-gradient-to-r ${theme.colors.buttonBg} hover:${theme.colors.buttonHoverBg}`,

  // Focus states
  focusRing: `focus:ring-${theme.colors.focusRing} focus:border-${theme.colors.focusBorder}`,

  // Icon styling
  icon: `bg-${theme.colors.iconBg} text-${theme.colors.iconText}`,
  iconHover: `group-hover:bg-${theme.colors.iconHoverBg} group-hover:text-${theme.colors.iconHoverText}`,

  // Selection styling
  selectionOverlay: `bg-${theme.colors.selectionBg}/50`,
  selectionRing: `ring-4 ring-${theme.colors.selectionRing}`,
  selectionBorder: `border-${theme.colors.selectionBorder}`,
  selectionCheckbox: `bg-${theme.colors.selectionBorder} border-${theme.colors.selectionBorder}`,
  selectionBar: `bg-${theme.colors.selectionBg}`,
  selectionBarText: `text-${theme.colors.primary}`,
  selectionBarBadge: `bg-${theme.colors.primary}`,

  // Metadata box
  metadataBox: `bg-gradient-to-br ${theme.colors.metadataBg} border border-${theme.colors.metadataBorder}`,

  // Hover effects
  hoverBorder: `hover:border-${theme.colors.primary}`,
  hoverText: `hover:text-${theme.colors.primary}`,
  hoverBg: `hover:bg-${theme.colors.selectionBg}`,
})

/**
 * Get raw color values for inline styles or dynamic usage
 */
export const getThemeColors = (theme: PageTheme) => ({
  primary: theme.colors.primary,
  primaryDark: theme.colors.primaryDark,
  secondary: theme.colors.secondary,
  secondaryDark: theme.colors.secondaryDark,
  iconBg: theme.colors.iconBg,
  iconText: theme.colors.iconText,
  iconHoverBg: theme.colors.iconHoverBg,
  iconHoverText: theme.colors.iconHoverText,
})
