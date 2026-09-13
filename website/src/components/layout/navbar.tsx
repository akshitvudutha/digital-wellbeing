"use client"
import { useState, useEffect } from "react"
import Link from "next/link"
import Image from "next/image"
import { siteConfig } from "@/config/site"
import { ArrowRight, Sun, Moon } from "lucide-react"

export function Navbar() {
  const [theme, setTheme] = useState<"dark" | "light">("dark")

  useEffect(() => {
    const saved = (localStorage.getItem("notch-website-theme") || localStorage.getItem("nyw-website-theme")) as "dark" | "light" | null
    if (saved) {
      setTheme(saved)
      if (saved === "light") {
        document.documentElement.classList.add("light")
      } else {
        document.documentElement.classList.remove("light")
      }
    } else {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
      const initial = prefersDark ? "dark" : "light"
      setTheme(initial)
      if (initial === "light") {
        document.documentElement.classList.add("light")
      }
    }
  }, [])

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark"
    setTheme(next)
    localStorage.setItem("notch-website-theme", next)
    if (next === "light") {
      document.documentElement.classList.add("light")
    } else {
      document.documentElement.classList.remove("light")
    }
  }

  const scrollToBeta = (e: React.MouseEvent) => {
    e.preventDefault()
    const elem = document.getElementById("beta")
    if (elem) {
      elem.scrollIntoView({ behavior: "smooth" })
    }
  }

  return (
    <header className="fixed top-6 left-0 right-0 z-50 flex justify-center px-4 pointer-events-none">
      <nav className="glass-island rounded-full p-2 pl-4 pr-2 flex items-center justify-between gap-6 md:gap-10 pointer-events-auto max-w-3xl w-full shadow-2xl transition-all duration-300">
        {/* Left: Canonical Logo + Name */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative w-7 h-7 flex-shrink-0 transition-transform duration-300 group-hover:scale-110">
            <Image
              src="/notch-logo.png"
              alt="Notch"
              width={28}
              height={28}
              className="object-contain"
              priority
            />
          </div>
          <span className="font-bold text-sm tracking-wider text-foreground group-hover:text-foreground/90">
            NOTCH
          </span>
          <span className="hidden sm:inline-block text-[10px] uppercase font-mono tracking-widest px-2 py-0.5 rounded-full bg-white/[0.06] text-foreground/50 border border-white/[0.08]">
            Beta
          </span>
        </Link>

        {/* Center: Navigation Links */}
        <div className="hidden md:flex items-center gap-6 text-xs font-medium text-foreground/60">
          <Link
            href="#product"
            className="hover:text-foreground transition-colors duration-200"
          >
            Product
          </Link>
          <Link
            href="#capabilities"
            className="hover:text-foreground transition-colors duration-200"
          >
            Capabilities
          </Link>
          <Link
            href="#themes"
            className="hover:text-foreground transition-colors duration-200"
          >
            Themes
          </Link>
          <Link
            href="#privacy"
            className="hover:text-foreground transition-colors duration-200"
          >
            Privacy
          </Link>
        </div>

        {/* Right: Theme Toggle & CTA Pill */}
        <div className="flex items-center gap-2">
          {/* Subtle minimal Dark/Light theme toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="p-2 rounded-full text-foreground/60 hover:text-foreground hover:bg-white/[0.06] transition-colors cursor-pointer"
            title={theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme"}
          >
            {theme === "dark" ? (
              <Sun className="w-4 h-4 text-nyw-amber" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-500" />
            )}
          </button>

          <Link
            href={siteConfig.links.github}
            target="_blank"
            rel="noreferrer"
            className="hidden sm:inline-flex text-xs font-medium text-foreground/60 hover:text-foreground transition-colors px-2.5 py-1.5"
          >
            GitHub
          </Link>
          <button
            onClick={scrollToBeta}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold transition-all duration-200 cursor-pointer bg-foreground text-background hover:opacity-90 shadow-md glow-emerald"
          >
            <span>Request Beta</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </nav>
    </header>
  )
}
