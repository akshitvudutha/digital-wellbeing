import Link from "next/link"
import { siteConfig } from "@/config/site"
import { Activity } from "lucide-react"

export function Footer() {
  return (
    <footer className="border-t border-border/40 py-10 md:py-14 bg-background/50">
      <div className="container mx-auto px-4 md:px-8 flex flex-col md:flex-row items-start justify-between gap-8">
        <div className="flex flex-col gap-2 max-w-sm">
          <Link href="/" className="flex items-center space-x-2">
            <Activity className="h-5 w-5 text-accent" />
            <span className="font-bold tracking-tight text-lg">{siteConfig.name}</span>
          </Link>
          <p className="text-sm text-foreground/60 mt-2">
            Your time. Your rules. Build healthier digital habits with powerful, privacy-first tracking.
          </p>
          <p className="text-sm text-foreground/40 mt-4">
            Built by {siteConfig.developer}.
          </p>
        </div>

        <div className="flex flex-col md:flex-row gap-12 md:gap-24">
          <div className="flex flex-col gap-3">
            <h4 className="font-semibold text-sm">Product</h4>
            <Link href="#how-it-works" className="text-sm text-foreground/60 hover:text-foreground">How it works</Link>
            <Link href={siteConfig.links.download} className="text-sm text-foreground/60 hover:text-foreground">Download v{siteConfig.version}</Link>
            <Link href={siteConfig.links.releases} className="text-sm text-foreground/60 hover:text-foreground">Changelog</Link>
          </div>

          <div className="flex flex-col gap-3">
            <h4 className="font-semibold text-sm">Community & Support</h4>
            <Link href={siteConfig.links.github} target="_blank" rel="noreferrer" className="text-sm text-foreground/60 hover:text-foreground">
              GitHub Repository
            </Link>
            <Link href={siteConfig.links.reportBug} target="_blank" rel="noreferrer" className="text-sm text-foreground/60 hover:text-foreground">
              Report a Bug
            </Link>
            <Link href={siteConfig.links.requestFeature} target="_blank" rel="noreferrer" className="text-sm text-foreground/60 hover:text-foreground">
              Request a Feature
            </Link>
          </div>
          
          <div className="flex flex-col gap-3">
            <h4 className="font-semibold text-sm">Legal</h4>
            <Link href="#privacy" className="text-sm text-foreground/60 hover:text-foreground">
              Privacy Policy
            </Link>
            <span className="text-sm text-foreground/40 mt-4">
              © {new Date().getFullYear()} {siteConfig.developer}
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}
