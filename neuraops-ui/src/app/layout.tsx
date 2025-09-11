import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { cn } from '@/lib/utils'
import AuthInitializer from '@/components/auth-initializer'

// Font optimization
const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  metadataBase: new URL('http://localhost:3000'),
  title: {
    default: 'NeuraOps - AI-Powered DevOps Operations',
    template: '%s | NeuraOps',
  },
  description: 'Modern DevOps automation platform powered by AI. Manage agents, workflows, monitoring, and more with intelligent automation.',
  keywords: [
    'DevOps',
    'AI',
    'Automation',
    'Monitoring',
    'Workflows',
    'Infrastructure',
    'Next.js',
    'TypeScript',
  ],
  authors: [{ name: 'NeuraOps Team' }],
  creator: 'NeuraOps',
  publisher: 'NeuraOps',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/site.webmanifest',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://neuraops.com',
    siteName: 'NeuraOps',
    title: 'NeuraOps - AI-Powered DevOps Operations',
    description: 'Modern DevOps automation platform powered by AI',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'NeuraOps - AI-Powered DevOps Operations',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NeuraOps - AI-Powered DevOps Operations',
    description: 'Modern DevOps automation platform powered by AI',
    images: ['/og-image.png'],
    creator: '@neuraops',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
}

// Interface with readonly for root layout props
interface RootLayoutProps {
  readonly children: React.ReactNode
}

export default function RootLayout({
  children,
}: RootLayoutProps) {
  return (
    <html 
      lang="en" 
      className={cn(
        'dark', // Default to dark theme
        inter.variable,
        jetbrainsMono.variable
      )}
      suppressHydrationWarning
    >
      <head />
      <body 
        className={cn(
          'min-h-screen bg-dark-900 font-sans antialiased',
          'selection:bg-primary-500/20'
        )}
        suppressHydrationWarning
      >
        {/* Initialize authentication on app load */}
        <AuthInitializer />
        
        {/* Remove the redundant flex container - let DashboardLayout handle it */}
        {children}
        
        {/* Development indicators */}
        {process.env.NODE_ENV === 'development' && (
          <div className="fixed bottom-4 left-4 z-50">
            <div className="flex items-center space-x-2 rounded-full bg-dark-800 px-3 py-1 text-xs text-gray-400 border border-gray-700">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span>Dev Mode</span>
            </div>
          </div>
        )}
      </body>
    </html>
  )
}