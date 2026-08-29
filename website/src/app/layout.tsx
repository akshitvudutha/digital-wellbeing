import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { siteConfig } from "@/config/site"
import { Navbar } from "@/components/layout/navbar"
import { Footer } from "@/components/layout/footer"

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "white" },
    { media: "(prefers-color-scheme: dark)", color: "black" },
  ],
}

export const metadata: Metadata = {
  title: {
    default: "NYW - Windows Screen Time Tracker & Focus App",
    template: `%s - NYW`,
  },
  description: siteConfig.description,
  keywords: ["Windows productivity app", "screen time tracker for Windows", "focus app for Windows", "app blocker for Windows", "digital wellbeing Windows", "Windows app locker", "focus mode Windows"],
  authors: [
    {
      name: siteConfig.developer,
    },
  ],
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://not-your-wellbeing.vercel.app",
    title: "NYW - Premium Digital Wellbeing for Windows",
    description: siteConfig.description,
    siteName: siteConfig.name,
    images: [
      {
        url: "/images/dashboard.png",
        width: 1200,
        height: 630,
        alt: "NYW Windows Application Dashboard",
      }
    ]
  },
  twitter: {
    card: "summary_large_image",
    title: "NYW - Windows Screen Time Tracker",
    description: siteConfig.description,
    images: ["/images/dashboard.png"],
  },
  icons: {
    icon: "/favicon.ico",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark scroll-smooth" style={{ colorScheme: "dark" }}>
      <body className={`${inter.variable} min-h-screen bg-background font-sans antialiased`}>
        <Navbar />
        {children}
        <Footer />
      </body>
    </html>
  )
}
