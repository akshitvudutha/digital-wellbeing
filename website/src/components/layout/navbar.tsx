import Link from "next/link"
import { siteConfig } from "@/config/site"
import { Logo } from "../ui/logo"
import { Button } from "../ui/button"

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/60 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center px-4 md:px-8 max-w-[1400px]">
        <Link href="/" className="flex items-center space-x-3 mr-6">
          <Logo className="h-6 w-6 text-accent" />
          <span className="font-bold inline-block tracking-tight text-lg">
            {siteConfig.name}
          </span>
        </Link>
        <nav className="flex items-center space-x-6 text-sm font-medium">
          <Link
            href="#explore"
            className="transition-colors hover:text-foreground/80 text-foreground/60 hidden sm:inline-block"
          >
            Features
          </Link>
        </nav>
        <div className="flex flex-1 items-center justify-end space-x-4">
          <nav className="flex items-center space-x-2">
            <Link
              href={siteConfig.links.github}
              target="_blank"
              rel="noreferrer"
              className="text-foreground/60 hover:text-foreground transition-colors hidden sm:inline-block text-sm mr-4 font-semibold"
            >
              GitHub
            </Link>
            <Link href={siteConfig.links.download}>
              <Button variant="default" size="sm" className="hidden sm:inline-flex rounded-lg font-bold bg-foreground text-background hover:bg-foreground/90">
                Download v{siteConfig.version}
              </Button>
            </Link>
          </nav>
        </div>
      </div>
    </header>
  )
}
