import type { Metadata, Viewport } from "next"
import "./globals.css"
import { siteConfig } from "@/config/site"
import { Navbar } from "@/components/layout/navbar"
import { Footer } from "@/components/layout/footer"
import { Analytics } from "@vercel/analytics/react"
import { SpeedInsights } from "@vercel/speed-insights/next"

export const viewport: Viewport = {
  themeColor: "#080a0d",
  colorScheme: "dark",
}

export const metadata: Metadata = {
  metadataBase: new URL(siteConfig.url),
  title: {
    default: "Notch — Digital Wellbeing for Windows",
    template: `%s · Notch`,
  },
  description: siteConfig.description,
  keywords: [
    "Notch",
    "Notch Windows",
    "digital wellbeing Windows",
    "Windows screen time tracker",
    "screen time control Windows",
    "Focus Mode Windows",
    "app blocker Windows",
    "app timer Windows",
    "SleepGuard",
    "app locker Windows",
    "attention control app",
    "productivity Windows",
    "student study planner Windows",
    "study session timer Windows",
    "exam and revision planning",
    "local-first wellbeing",
    "local screen time history",
  ],
  authors: [{ name: siteConfig.developer }],
  alternates: {
    canonical: "https://notch1.vercel.app/",
  },
  icons: {
    icon: "/notch-logo.png",
    apple: "/notch-logo.png",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://notch1.vercel.app/",
    title: "Notch — Digital Wellbeing for Windows",
    description:
      "Understand your computer usage, plan focused study sessions, track subjects, and protect your attention with Notch for Windows.",
    siteName: "Notch",
    images: [
      {
        url: "/notch-logo.png",
        width: 1254,
        height: 1254,
        alt: "Notch — Digital Wellbeing for Windows",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Notch — Digital Wellbeing for Windows",
    description:
      "Understand your computer usage, plan focused study sessions, track subjects, and protect your attention with Notch for Windows.",
    images: ["/notch-logo.png"],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const softwareAppJsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Notch",
    alternateName: "Notch — Digital Wellbeing for Windows",
    url: "https://notch1.vercel.app/",
    downloadUrl: "https://notch1.vercel.app/api/download",
    operatingSystem: "Windows 10, Windows 11",
    applicationCategory: "ProductivityApplication",
    description: siteConfig.description,
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      availability: "https://schema.org/InStock",
    },
  }

  const websiteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Notch",
    url: "https://notch1.vercel.app/",
    description: siteConfig.description,
    potentialAction: {
      "@type": "SearchAction",
      target: "https://notch1.vercel.app/",
    },
  }

  return (
    <html lang="en" className="dark scroll-smooth" style={{ colorScheme: "dark" }}>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("notch-website-theme")||localStorage.getItem("nyw-website-theme");if(t==="light"||(!t&&window.matchMedia&&!window.matchMedia("(prefers-color-scheme: dark)").matches)){document.documentElement.classList.remove("dark");document.documentElement.classList.add("light");document.documentElement.style.colorScheme="light";}else{document.documentElement.classList.remove("light");document.documentElement.classList.add("dark");document.documentElement.style.colorScheme="dark";}}catch(e){}})();`
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareAppJsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
        />
      </head>
      <body className="min-h-screen bg-background font-sans antialiased text-foreground selection:bg-nyw-emerald/20 selection:text-white">
        <Navbar />
        {children}
        <Footer />
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  )
}
