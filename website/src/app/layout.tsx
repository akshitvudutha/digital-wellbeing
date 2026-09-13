import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { siteConfig } from "@/config/site"
import { Navbar } from "@/components/layout/navbar"
import { Footer } from "@/components/layout/footer"

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })

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
    "Digital Wellbeing for Windows",
    "Windows digital wellbeing",
    "intentional computing",
    "deep focus",
    "app timer",
    "app locker",
    "SleepGuard",
    "local-first",
    "privacy-first screen time",
  ],
  authors: [{ name: siteConfig.developer }],
  icons: {
    icon: "/notch-logo.png",
    apple: "/notch-logo.png",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: siteConfig.url,
    title: "Notch — Digital Wellbeing for Windows",
    description: siteConfig.description,
    siteName: siteConfig.fullName,
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
    description: siteConfig.description,
    images: ["/notch-logo.png"],
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
    name: "Notch",
    alternateName: "Notch — Digital Wellbeing for Windows",
    operatingSystem: "Windows 10, Windows 11",
    applicationCategory: "ProductivityApplication",
    offers: {
      "@type": "Offer",
      price: "0",
      availability: "https://schema.org/PreOrder",
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
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className={`${inter.variable} min-h-screen bg-background font-sans antialiased text-foreground selection:bg-nyw-emerald/20 selection:text-white`}>
        <Navbar />
        {children}
        <Footer />
      </body>
    </html>
  )
}
