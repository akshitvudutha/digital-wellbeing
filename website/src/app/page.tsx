"use client"
import { useState } from "react"
import { siteConfig } from "@/config/site"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Download, Shield, Clock, Bell, Settings, Activity, Lock, RefreshCw, Zap, Server, Code, PlayCircle, Eye, Moon, Monitor, ChartPie } from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { motion, AnimatePresence } from "framer-motion"

const DEMO_TABS = [
  { id: "focus", label: "Focus Mode", icon: Zap, video: "/videos/focus-demo.mp4", fallback: "/images/focus.png" },
  { id: "applocker", label: "App Locker", icon: Lock, video: "/videos/applocker-demo.mp4", fallback: "/images/applocker.png" },
  { id: "sleepguard", label: "SleepGuard", icon: Moon, video: "/videos/sleepguard-demo.mp4", fallback: "/images/sleepguard.png" },
  { id: "insights", label: "Insights", icon: ChartPie, video: "/videos/insights-demo.mp4", fallback: "/images/insights.png" },
  { id: "usage", label: "Usage Analytics", icon: Activity, video: "/videos/usage-demo.mp4", fallback: "/images/usage.png" },
]

export default function Home() {
  const [activeTab, setActiveTab] = useState(DEMO_TABS[0].id)

  return (
    <div className="flex flex-col min-h-screen selection:bg-accent/30 selection:text-foreground">
      <main className="flex-1">
        
        {/* HERO SECTION */}
        <section className="relative pt-28 pb-32 md:pt-40 md:pb-48 overflow-hidden">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-accent/10 via-background to-background" />
          <div className="container mx-auto px-4 md:px-8 text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="max-w-4xl mx-auto"
            >
              <div className="inline-flex items-center rounded-full border border-border/50 bg-surface/50 px-3 py-1 text-xs font-semibold backdrop-blur-md mb-8 tracking-wide uppercase text-foreground/80">
                <span className="flex h-2 w-2 rounded-full bg-accent mr-2 animate-pulse"></span>
                v{siteConfig.version} for Windows is now available
              </div>
              <h1 className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tight mb-8 leading-[1.1]">
                Your time deserves <br className="hidden md:block" />
                <span className="text-gradient">your attention.</span>
              </h1>
              <p className="text-lg md:text-2xl text-foreground/70 mb-12 max-w-2xl mx-auto leading-relaxed font-medium">
                A premium Windows productivity utility for deep focus, screen-time awareness, app protection, and bedtime management.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link href={siteConfig.links.download}>
                  <Button size="lg" className="rounded-xl w-full sm:w-auto font-bold gap-2 text-base h-14 px-8 shadow-2xl shadow-accent/20 transition-all hover:scale-105">
                    <Download className="h-5 w-5" />
                    Download for Windows
                  </Button>
                </Link>
                <Link href="#how-it-works">
                  <Button variant="outline" size="lg" className="rounded-xl w-full sm:w-auto font-semibold h-14 px-8 border-border/60 bg-surface/30 backdrop-blur hover:bg-surface-hover">
                    See how it works
                  </Button>
                </Link>
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
              className="mt-24 relative max-w-5xl mx-auto"
            >
              <div className="absolute -inset-2 rounded-[2rem] bg-gradient-to-r from-accent/20 to-purple-500/20 blur-3xl opacity-50" />
              <div className="relative rounded-2xl border border-border/60 bg-surface/80 p-2 shadow-2xl backdrop-blur-xl">
                <div className="aspect-[16/10] w-full rounded-xl bg-card border border-border/40 overflow-hidden relative">
                  <Image 
                    src="/images/dashboard.png" 
                    alt="NYW Dashboard displaying total screen time and categories" 
                    fill 
                    className="object-cover object-top"
                    priority
                  />
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* FEATURE HIGHLIGHTS */}
        <section className="py-24 bg-surface/20 border-y border-border/30">
          <div className="container mx-auto px-4 md:px-8">
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
              {[
                { title: "Focus", icon: Zap, desc: "Block distractions and stay in the session with website and app restrictions." },
                { title: "App Locker", icon: Lock, desc: "Protect selected applications with Windows Hello biometrics or a secure PIN." },
                { title: "Usage Analytics", icon: Activity, desc: "Understand exactly where your time goes without data leaving your device." },
                { title: "SleepGuard", icon: Moon, desc: "Protect your evenings and automatically lock your PC during inactivity." }
              ].map((f, i) => (
                <div key={i} className="flex flex-col gap-4 p-6 rounded-2xl bg-surface border border-border/50 hover:border-accent/50 transition-colors">
                  <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center">
                    <f.icon className="h-6 w-6 text-accent" />
                  </div>
                  <h3 className="text-xl font-bold">{f.title}</h3>
                  <p className="text-foreground/70 leading-relaxed font-medium">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* INTERACTIVE DEMO GALLERY */}
        <section id="how-it-works" className="py-32 bg-background relative overflow-hidden">
          <div className="container mx-auto px-4 md:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-4xl md:text-5xl font-black tracking-tight mb-6">See it in action.</h2>
              <p className="text-xl text-foreground/70 font-medium">
                Premium functionality that respects your system. Here's how NYW actively manages your digital wellbeing.
              </p>
            </div>

            <div className="flex flex-col lg:flex-row gap-12 items-center">
              {/* Tab Navigation */}
              <div className="flex flex-col gap-2 w-full lg:w-1/3">
                {DEMO_TABS.map((tab) => {
                  const isActive = activeTab === tab.id
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center gap-4 p-5 rounded-2xl text-left transition-all duration-200 border ${
                        isActive 
                          ? "bg-surface border-border shadow-lg shadow-black/5" 
                          : "bg-transparent border-transparent hover:bg-surface/50 hover:border-border/50"
                      }`}
                    >
                      <div className={`p-3 rounded-xl ${isActive ? "bg-accent/10 text-accent" : "bg-surface text-foreground/60"}`}>
                        <tab.icon className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className={`text-lg font-bold ${isActive ? "text-foreground" : "text-foreground/70"}`}>{tab.label}</h4>
                      </div>
                    </button>
                  )
                })}
              </div>

              {/* Video Display */}
              <div className="w-full lg:w-2/3">
                <div className="relative rounded-2xl border border-border/60 bg-surface p-2 shadow-2xl overflow-hidden aspect-[16/10]">
                  <AnimatePresence mode="wait">
                    {DEMO_TABS.map((tab) => (
                      activeTab === tab.id && (
                        <motion.div
                          key={tab.id}
                          initial={{ opacity: 0, scale: 0.98 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.98 }}
                          transition={{ duration: 0.3 }}
                          className="absolute inset-2 rounded-xl overflow-hidden bg-card border border-border/50"
                        >
                          <video 
                            src={tab.video} 
                            poster={tab.fallback}
                            className="w-full h-full object-cover"
                            autoPlay 
                            muted 
                            loop 
                            playsInline
                          />
                        </motion.div>
                      )
                    ))}
                  </AnimatePresence>
                </div>
                <p className="text-center mt-6 text-sm text-foreground/50 font-medium flex items-center justify-center gap-2">
                  <Monitor className="w-4 h-4" /> Captured directly from the latest Windows application.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* DEEP DIVES */}
        
        {/* Focus Deep Dive */}
        <section className="py-24 bg-surface/20 border-y border-border/30">
          <div className="container mx-auto px-4 md:px-8">
            <div className="flex flex-col md:flex-row items-center gap-16">
              <div className="flex-1 space-y-8">
                <div className="inline-flex items-center rounded-lg bg-accent/10 px-3 py-1 text-sm font-bold text-accent uppercase tracking-wider">
                  <Zap className="w-4 h-4 mr-2" /> Focus Engine
                </div>
                <h2 className="text-4xl md:text-5xl font-black tracking-tight leading-tight">Block distractions. <br/> Stay in the session.</h2>
                <p className="text-xl text-foreground/70 leading-relaxed font-medium">
                  NYW's Focus Mode allows you to define specific websites and desktop applications to block during a session.
                </p>
                <ul className="space-y-5 text-lg font-medium text-foreground/80">
                  <li className="flex items-start gap-4">
                    <div className="bg-surface border border-border/50 p-2 rounded-lg mt-1"><Code className="h-5 w-5 text-accent" /></div>
                    <span><strong>Browser Title & Hosts Blocking.</strong> Ensures distractions are cut off natively.</span>
                  </li>
                  <li className="flex items-start gap-4">
                    <div className="bg-surface border border-border/50 p-2 rounded-lg mt-1"><Shield className="h-5 w-5 text-accent" /></div>
                    <span><strong>Strict Mode.</strong> Prevents ending a session early without inputting a secure PIN.</span>
                  </li>
                </ul>
              </div>
              <div className="flex-1 w-full relative">
                <div className="rounded-2xl border border-border bg-glass p-2 shadow-2xl backdrop-blur-md rotate-1 hover:rotate-0 transition-transform duration-500">
                  <Image src="/images/focus.png" alt="Focus Mode configuration" width={800} height={500} className="rounded-xl border border-border/40 w-full" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Insights & Usage Deep Dive */}
        <section className="py-24 bg-background">
          <div className="container mx-auto px-4 md:px-8">
            <div className="flex flex-col md:flex-row-reverse items-center gap-16">
              <div className="flex-1 space-y-8">
                <div className="inline-flex items-center rounded-lg bg-accent/10 px-3 py-1 text-sm font-bold text-accent uppercase tracking-wider">
                  <ChartPie className="w-4 h-4 mr-2" /> Smart Insights
                </div>
                <h2 className="text-4xl md:text-5xl font-black tracking-tight leading-tight">Turn data into <br/>useful patterns.</h2>
                <p className="text-xl text-foreground/70 leading-relaxed font-medium">
                  Stop guessing where your time goes. The Insights dashboard analyzes your raw screen time and provides factual observations about your habits.
                </p>
                <p className="text-lg text-foreground/80 font-medium">
                  View daily category breakdowns, identify your most productive days, and track your goal streaks without any confusing AI jargon.
                </p>
              </div>
              <div className="flex-1 w-full relative">
                <div className="rounded-2xl border border-border bg-surface p-2 shadow-2xl -rotate-1 hover:rotate-0 transition-transform duration-500">
                  <Image src="/images/insights.png" alt="Smart Insights Dashboard" width={800} height={500} className="rounded-xl border border-border/40 w-full" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* App Locker Deep Dive */}
        <section className="py-24 bg-surface/20 border-y border-border/30">
          <div className="container mx-auto px-4 md:px-8">
            <div className="flex flex-col md:flex-row items-center gap-16">
              <div className="flex-1 space-y-8">
                <div className="inline-flex items-center rounded-lg bg-accent/10 px-3 py-1 text-sm font-bold text-accent uppercase tracking-wider">
                  <Lock className="w-4 h-4 mr-2" /> App Locker
                </div>
                <h2 className="text-4xl md:text-5xl font-black tracking-tight leading-tight">Zero-trust for <br/>specific apps.</h2>
                <p className="text-xl text-foreground/70 leading-relaxed font-medium">
                  Require authentication before protected applications can be used. Protect sensitive apps from prying eyes when your PC is unlocked.
                </p>
                <ul className="space-y-5 text-lg font-medium text-foreground/80">
                  <li className="flex items-start gap-4">
                    <div className="bg-surface border border-border/50 p-2 rounded-lg mt-1"><Shield className="h-5 w-5 text-accent" /></div>
                    <span><strong>Windows Hello Integration.</strong> Seamlessly authenticate via Face ID, Fingerprint, or OS PIN.</span>
                  </li>
                  <li className="flex items-start gap-4">
                    <div className="bg-surface border border-border/50 p-2 rounded-lg mt-1"><Lock className="h-5 w-5 text-accent" /></div>
                    <span><strong>Fallback PIN.</strong> Set a custom NYW PIN if you don't use Windows Hello.</span>
                  </li>
                </ul>
              </div>
              <div className="flex-1 w-full relative">
                <div className="rounded-2xl border border-border bg-glass p-2 shadow-2xl backdrop-blur-md rotate-1 hover:rotate-0 transition-transform duration-500">
                  <Image src="/images/applocker.png" alt="App Locker configuration" width={800} height={500} className="rounded-xl border border-border/40 w-full" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SleepGuard Deep Dive */}
        <section className="py-24 bg-background">
          <div className="container mx-auto px-4 md:px-8">
            <div className="flex flex-col md:flex-row-reverse items-center gap-16">
              <div className="flex-1 space-y-8">
                <div className="inline-flex items-center rounded-lg bg-accent/10 px-3 py-1 text-sm font-bold text-accent uppercase tracking-wider">
                  <Moon className="w-4 h-4 mr-2" /> SleepGuard
                </div>
                <h2 className="text-4xl md:text-5xl font-black tracking-tight leading-tight">Protect your evenings.</h2>
                <p className="text-xl text-foreground/70 leading-relaxed font-medium">
                  Automatically respond to inactivity. SleepGuard monitors your activity (while respecting media playback) and triggers a configurable power action.
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-surface border border-border/50 p-4 rounded-xl flex items-center gap-3">
                    <Lock className="w-5 h-5 text-accent"/> <span className="font-bold">Lock PC</span>
                  </div>
                  <div className="bg-surface border border-border/50 p-4 rounded-xl flex items-center gap-3">
                    <Moon className="w-5 h-5 text-accent"/> <span className="font-bold">Sleep</span>
                  </div>
                  <div className="bg-surface border border-border/50 p-4 rounded-xl flex items-center gap-3">
                    <Activity className="w-5 h-5 text-accent"/> <span className="font-bold">Hibernate</span>
                  </div>
                  <div className="bg-surface border border-border/50 p-4 rounded-xl flex items-center gap-3">
                    <Zap className="w-5 h-5 text-accent"/> <span className="font-bold">Shut Down</span>
                  </div>
                </div>
              </div>
              <div className="flex-1 w-full relative">
                <div className="rounded-2xl border border-border bg-glass p-2 shadow-2xl backdrop-blur-md -rotate-1 hover:rotate-0 transition-transform duration-500">
                  <Image src="/images/sleepguard.png" alt="SleepGuard configuration" width={800} height={500} className="rounded-xl border border-border/40 w-full" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* PRIVACY & TRUST */}
        <section id="privacy" className="py-24 bg-surface/30 border-y border-border/30">
          <div className="container mx-auto px-4 md:px-8 max-w-4xl text-center">
            <Server className="h-16 w-16 text-accent mx-auto mb-6" />
            <h2 className="text-4xl md:text-5xl font-black tracking-tight mb-6">100% Local Privacy.</h2>
            <p className="text-xl text-foreground/70 leading-relaxed font-medium mb-12">
              We believe your digital habits are intensely private. NYW stores all usage data locally on your machine using an encrypted SQLite database. 
            </p>
            <div className="grid md:grid-cols-3 gap-6 text-left">
              <div className="p-6 rounded-2xl bg-surface border border-border/50">
                <h4 className="font-bold text-lg mb-2">No Cloud Sync</h4>
                <p className="text-foreground/70 text-sm">Your data never leaves your device. We do not operate storage servers.</p>
              </div>
              <div className="p-6 rounded-2xl bg-surface border border-border/50">
                <h4 className="font-bold text-lg mb-2">No Telemetry</h4>
                <p className="text-foreground/70 text-sm">We do not track how you use the app, nor do we collect analytical data.</p>
              </div>
              <div className="p-6 rounded-2xl bg-surface border border-border/50">
                <h4 className="font-bold text-lg mb-2">Open Source</h4>
                <p className="text-foreground/70 text-sm">Our codebase is publicly verifiable on GitHub to ensure complete transparency.</p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section id="download" className="py-32 relative overflow-hidden bg-background">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_bottom,_var(--tw-gradient-stops))] from-accent/10 via-background to-background" />
          <div className="container mx-auto px-4 md:px-8 text-center max-w-2xl">
            <h2 className="text-4xl md:text-5xl font-black tracking-tight mb-6">Ready to regain your focus?</h2>
            <p className="text-xl text-foreground/70 mb-10 font-medium">
              Download the latest stable release of NYW and start building healthier digital habits on Windows today.
            </p>
            <div className="flex flex-col items-center justify-center gap-4">
              <Link href={siteConfig.links.download}>
                <Button size="lg" className="rounded-xl font-bold h-16 px-10 text-xl gap-3 shadow-2xl shadow-accent/20 transition-all hover:scale-105">
                  <Download className="h-6 w-6" />
                  Download v{siteConfig.version} for Windows
                </Button>
              </Link>
              
              <div className="flex gap-4 mt-8">
                <Link href={siteConfig.links.reportBug} target="_blank" rel="noopener noreferrer">
                  <Button variant="outline" size="sm" className="rounded-xl gap-2 border-border/60 font-semibold bg-surface/50 hover:bg-surface-hover">
                    <Shield className="h-4 w-4" /> Report a Bug
                  </Button>
                </Link>
                <Link href={siteConfig.links.requestFeature} target="_blank" rel="noopener noreferrer">
                  <Button variant="outline" size="sm" className="rounded-xl gap-2 border-border/60 font-semibold bg-surface/50 hover:bg-surface-hover">
                    <Bell className="h-4 w-4" /> Request Feature
                  </Button>
                </Link>
              </div>
            </div>
            <p className="mt-10 text-sm text-foreground/50 font-medium">Compatible with Windows 10 & 11.</p>
          </div>
        </section>
      </main>
    </div>
  )
}
