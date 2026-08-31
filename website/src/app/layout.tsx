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
  metadataBase: new URL(siteConfig.url),
  title: {
    default: "NYW — Digital Wellbeing for Windows | Not Your Wellbeing",
    template: `%s - NYW`,
  },
  description: siteConfig.description,
  keywords: ["Windows productivity", "screen time", "Focus", "application blocking", "App Locker", "SleepGuard", "digital wellbeing"],
  authors: [
    {
      name: siteConfig.developer,
    },
  ],
  openGraph: {
    type: "website",
    locale: "en_US",
    url: siteConfig.url,
    title: "NYW — Digital Wellbeing for Windows",
    description: siteConfig.description,
    siteName: siteConfig.fullName,
    images: [
      {
        url: "/images/app/home-dark.png",
        width: 1280,
        height: 720,
        alt: "NYW - Your time. Your rules.",
      }
    ]
  },
  twitter: {
    card: "summary_large_image",
    title: "NYW — Digital Wellbeing for Windows",
    description: siteConfig.description,
    images: ["/images/app/home-dark.png"],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "NYW",
    "alternateName": "Not Your Wellbeing",
    "operatingSystem": "Windows 10, Windows 11",
    "applicationCategory": "Productivity",
    "offers": {
      "@type": "Offer",
      "price": "0"
    }
  };

  return (
    <html lang="en" className="dark scroll-smooth" style={{ colorScheme: "dark" }}>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className={`${inter.variable} min-h-screen bg-background font-sans antialiased`}>
        <Navbar />
        {children}
        <Footer />
      </body>
    </html>
  )
}
