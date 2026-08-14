"use client"
import { siteConfig } from "@/config/site"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Download, Shield, Clock, Bell, Settings, Activity, Lock, RefreshCw, Zap, Server, Code } from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { motion } from "framer-motion"

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      <main className="flex-1">
        {/* HERO SECTION */}
        <section className="relative pt-24 pb-32 md:pt-36 md:pb-40 overflow-hidden">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-accent/20 via-background to-background" />
          <div className="container mx-auto px-4 md:px-8 text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="max-w-3xl mx-auto"
            >
              <div className="inline-flex items-center rounded-full border border-border/50 bg-background/50 px-3 py-1 text-sm font-medium backdrop-blur-md mb-8">
                <span className="flex h-2 w-2 rounded-full bg-accent mr-2 animate-pulse"></span>
                Latest Version: {siteConfig.version} (Windows)
              </div>
              <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-6">
                Take control of your <br className="hidden md:block" />
                <span className="text-gradient">time on Windows.</span>
              </h1>
              <p className="text-lg md:text-xl text-foreground/70 mb-10 max-w-2xl mx-auto leading-relaxed">
                A powerful, privacy-focused screen-time tracker for Windows that helps you understand where your time goes and build healthier digital habits.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link href={siteConfig.links.download}>
                  <Button size="lg" className="rounded-full w-full sm:w-auto font-semibold gap-2">
                    <Download className="h-5 w-5" />
                    Download for Windows
                  </Button>
                </Link>
                <Link href="#features">
                  <Button variant="glass" size="lg" className="rounded-full w-full sm:w-auto font-semibold">
                    Explore Features
                  </Button>
                </Link>
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.2 }}
              className="mt-20 relative max-w-5xl mx-auto"
            >
              <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-accent/30 to-purple-500/30 blur-2xl opacity-50" />
              <div className="relative rounded-2xl border border-glass-border bg-glass p-2 shadow-2xl backdrop-blur-xl">
                {/* ACTUAL APPLICATION SCREENSHOT */}
                <div className="aspect-[16/9] w-full rounded-xl bg-card border border-border/50 flex flex-col items-center justify-center overflow-hidden relative">
                  <Image 
                    src="/dashboard.png" 
                    alt="Digital Wellbeing Dashboard" 
                    fill 
                    className="object-cover object-top opacity-90"
                    priority
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent" />
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* SCREEN TIME SECTION */}
        <section id="features" className="py-24 bg-background">
          <div className="container mx-auto px-4 md:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">Know where your time goes.</h2>
              <p className="text-lg text-foreground/70">
                Digital Wellbeing tracks application and website usage intelligently in the background, giving you a crystal clear picture of your daily habits.
              </p>
            </div>
            
            <div className="grid md:grid-cols-3 gap-8">
              <Card>
                <CardHeader>
                  <Activity className="h-10 w-10 text-accent mb-2" />
                  <CardTitle>Application Tracking</CardTitle>
                  <CardDescription>Precise foreground monitoring.</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-foreground/80">
                    Tracks exactly which apps are active. It handles focus loss and idle time perfectly, so your statistics are always accurate.
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <Code className="h-10 w-10 text-accent mb-2" />
                  <CardTitle>Website Tracking</CardTitle>
                  <CardDescription>Browser integration.</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-foreground/80">
                    Automatically extracts active URLs from your browsers, letting you distinguish productive research from doom-scrolling.
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <Zap className="h-10 w-10 text-accent mb-2" />
                  <CardTitle>Usage Dashboard</CardTitle>
                  <CardDescription>Daily & weekly insights.</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-foreground/80">
                    Visualize your data with a beautiful, built-in dashboard featuring full light and dark mode support natively integrated with Windows.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* LIMITS SECTION */}
        <section className="py-24 bg-card/30 border-y border-border/40">
          <div className="container mx-auto px-4 md:px-8">
            <div className="flex flex-col md:flex-row items-center gap-12">
              <div className="flex-1 space-y-6">
                <h2 className="text-3xl md:text-5xl font-bold tracking-tight">Set your limits.</h2>
                <p className="text-lg text-foreground/70 leading-relaxed">
                  Easily set strict usage limits for specific, distracting applications and websites. Once you hit your limit, Digital Wellbeing intervenes to protect your productivity.
                </p>
                <ul className="space-y-4">
                  <li className="flex items-center gap-3">
                    <div className="bg-accent/20 p-2 rounded-full"><Settings className="h-5 w-5 text-accent" /></div>
                    <span className="font-medium text-foreground/90">Application Timers</span>
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="bg-accent/20 p-2 rounded-full"><Settings className="h-5 w-5 text-accent" /></div>
                    <span className="font-medium text-foreground/90">Website Timers</span>
                  </li>
                </ul>
              </div>
              <div className="flex-1 w-full">
                <div className="rounded-2xl border border-glass-border bg-glass p-2 shadow-xl backdrop-blur-md">
                  <div className="aspect-video w-full rounded-xl bg-card border border-border/50 flex flex-col items-center justify-center relative overflow-hidden">
                    <Image 
                      src="/limits.png" 
                      alt="Digital Wellbeing Focus Session and Limits" 
                      fill 
                      className="object-cover object-left opacity-90"
                    />
                    <div className="absolute inset-0 bg-gradient-to-r from-background/20 to-transparent" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SLEEPGUARD SECTION */}
        <section className="py-24 bg-background">
          <div className="container mx-auto px-4 md:px-8">
            <div className="flex flex-col md:flex-row-reverse items-center gap-12">
              <div className="flex-1 space-y-6">
                <h2 className="text-3xl md:text-5xl font-bold tracking-tight">Meet SleepGuard.</h2>
                <p className="text-lg text-foreground/70 leading-relaxed">
                  A multi-action protection system that acts when you step away. Protect your computer and save energy when you are inactive.
                </p>
                <p className="text-foreground/80 bg-card p-4 rounded-lg border border-border/50">
                  SleepGuard issues a countdown warning before taking action, allowing you to easily cancel if you're still working.
                </p>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="flex items-center gap-2"><Lock className="h-4 w-4 text-accent" /> Lock PC</div>
                  <div className="flex items-center gap-2"><Lock className="h-4 w-4 text-accent" /> Sleep</div>
                  <div className="flex items-center gap-2"><Lock className="h-4 w-4 text-accent" /> Hibernate</div>
                  <div className="flex items-center gap-2"><Lock className="h-4 w-4 text-accent" /> Shut down</div>
                </div>
              </div>
              <div className="flex-1 w-full">
                <div className="rounded-2xl border border-glass-border bg-glass p-2 shadow-xl backdrop-blur-md">
                  <div className="aspect-video w-full rounded-xl bg-card border border-border/50 flex flex-col items-center justify-center relative overflow-hidden">
                    <Image 
                      src="/sleepguard.png" 
                      alt="Digital Wellbeing SleepGuard Settings" 
                      fill 
                      className="object-cover object-bottom opacity-80"
                    />
                    <div className="absolute inset-0 bg-black/20" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* PRIVACY & AUTO-UPDATES */}
        <section id="privacy" className="py-24 bg-card/30 border-y border-border/40">
          <div className="container mx-auto px-4 md:px-8 grid md:grid-cols-2 gap-12">
            <div className="space-y-6">
              <Server className="h-10 w-10 text-accent mb-2" />
              <h2 className="text-3xl font-bold tracking-tight">Your data belongs to you.</h2>
              <p className="text-foreground/80 leading-relaxed text-lg">
                We believe in 100% local privacy. Digital Wellbeing stores all your usage data locally on your machine using an encrypted SQLite database. 
              </p>
              <ul className="space-y-3 mt-4 text-foreground/70">
                <li className="flex items-center gap-2">✓ No cloud synchronization</li>
                <li className="flex items-center gap-2">✓ No telemetry collection</li>
                <li className="flex items-center gap-2">✓ No hidden analytics</li>
              </ul>
            </div>
            
            <div className="space-y-6">
              <RefreshCw className="h-10 w-10 text-accent mb-2" />
              <h2 className="text-3xl font-bold tracking-tight">Stay up to date.</h2>
              <p className="text-foreground/80 leading-relaxed text-lg">
                Digital Wellbeing features a completely custom, non-blocking automatic update engine. 
                It seamlessly checks for the latest stable releases from GitHub.
              </p>
              <div className="bg-background border border-border/50 p-6 rounded-xl mt-4">
                <p className="text-sm font-mono text-foreground/60 mb-1">Current Version</p>
                <p className="text-2xl font-bold text-accent">v{siteConfig.version}</p>
              </div>
            </div>
          </div>
        </section>

        {/* CHANGELOG & FAQ */}
        <section id="changelog" className="py-24 bg-background">
          <div className="container mx-auto px-4 md:px-8 max-w-4xl">
            <div className="mb-16">
              <h2 className="text-3xl font-bold tracking-tight mb-6">Latest Updates</h2>
              <div className="glass-panel rounded-xl p-6 md:p-8">
                <div className="flex items-center justify-between mb-4 border-b border-border/50 pb-4">
                  <h3 className="text-xl font-bold">Version {siteConfig.version}</h3>
                  <span className="text-xs font-medium bg-accent/20 text-accent px-2 py-1 rounded">Latest Release</span>
                </div>
                <ul className="space-y-3">
                  <li className="flex gap-3"><span className="text-accent">•</span> <span className="text-foreground/80">Introduced a production-ready automatic updater.</span></li>
                  <li className="flex gap-3"><span className="text-accent">•</span> <span className="text-foreground/80">Users can now update securely without manually downloading the installer.</span></li>
                  <li className="flex gap-3"><span className="text-accent">•</span> <span className="text-foreground/80">Bug fixes for background tracking and limits logic.</span></li>
                </ul>
              </div>
            </div>

            <div id="faq" className="mt-24">
              <h2 className="text-3xl font-bold tracking-tight mb-8">Frequently Asked Questions</h2>
              <div className="space-y-6">
                <div>
                  <h4 className="font-semibold text-lg mb-2">What operating systems are supported?</h4>
                  <p className="text-foreground/70">Digital Wellbeing is built exclusively for Windows desktop environments.</p>
                </div>
                <div>
                  <h4 className="font-semibold text-lg mb-2">Where is my data stored?</h4>
                  <p className="text-foreground/70">All data is kept strictly on your local machine. We do not use cloud storage, nor do we collect any analytical data on your usage.</p>
                </div>
                <div>
                  <h4 className="font-semibold text-lg mb-2">Does it run in the background?</h4>
                  <p className="text-foreground/70">Yes, the application minimizes to the system tray and tracks your screen time intelligently without draining resources.</p>
                </div>
                <div>
                  <h4 className="font-semibold text-lg mb-2">How do I report a bug or request a feature?</h4>
                  <p className="text-foreground/70">You can use our official <a href={siteConfig.links.github} className="text-accent hover:underline">GitHub repository</a> to file issues and suggest new features directly to the developer.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section id="download" className="py-32 relative overflow-hidden">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_bottom,_var(--tw-gradient-stops))] from-accent/20 via-background to-background" />
          <div className="container mx-auto px-4 md:px-8 text-center max-w-2xl">
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">Ready to regain your focus?</h2>
            <p className="text-xl text-foreground/70 mb-10">
              Download Digital Wellbeing today and start building healthier digital habits on Windows.
            </p>
            <Link href={siteConfig.links.download}>
              <Button size="lg" className="rounded-full font-bold h-14 px-8 text-lg gap-2 shadow-xl shadow-accent/20">
                <Download className="h-6 w-6" />
                Download v{siteConfig.version} for Windows
              </Button>
            </Link>
            <p className="mt-6 text-sm text-foreground/50">Free, private, and open-source.</p>
          </div>
        </section>
      </main>
    </div>
  )
}
