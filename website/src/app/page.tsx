"use client"
import { useState } from "react"
import { siteConfig } from "@/config/site"
import { Button } from "@/components/ui/button"
import { Download, Shield, Clock, Moon, Monitor, ChartPie, Activity, Lock, Settings, ChevronRight, CheckCircle2 } from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { motion, AnimatePresence } from "framer-motion"
import { ImageLightbox } from "@/components/ui/lightbox"

const DEMO_TABS = [
  { id: "overview", label: "Overview", icon: Monitor, fallback: "/images/app/home-dark.png", desc: "Your daily dashboard summarizing active time and focus sessions." },
  { id: "usage", label: "Usage", icon: Activity, fallback: "/images/app/usage-dark.png", desc: "Detailed breakdown of application usage and categorized screen time." },
  { id: "focus", label: "Focus", icon: Clock, fallback: "/images/app/focus-dark.png", desc: "Define an application blocklist and stay in the zone without distractions." },
  { id: "applocker", label: "App Locker", icon: Lock, fallback: "/images/app/app-locker-dark.png", desc: "Protect sensitive applications with Windows Hello biometrics or PIN." },
  { id: "insights", label: "Insights", icon: ChartPie, fallback: "/images/app/insights-dark.png", desc: "Analyze historical trends to build better digital habits." },
  { id: "sleepguard", label: "SleepGuard", icon: Moon, fallback: "/images/app/sleepguard-dark.png", desc: "Automatically lock or sleep your PC when inactivity is detected late at night." },
  { id: "settings", label: "Settings", icon: Settings, fallback: "/images/app/settings-dark.png", desc: "Customize NYW to perfectly fit your workflow and aesthetic." },
]

export default function Home() {
  const [activeTab, setActiveTab] = useState(DEMO_TABS[0].id)
  const activeTabData = DEMO_TABS.find(t => t.id === activeTab) || DEMO_TABS[0]

  return (
    <div className="flex flex-col min-h-screen selection:bg-accent/30 selection:text-foreground">
      <main className="flex-1">
        
        {/* HERO SECTION */}
        <section className="relative pt-28 pb-20 md:pt-40 md:pb-32 overflow-hidden">
          {/* Deep elegant background */}
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-background via-background to-background" />
          
          <div className="container mx-auto px-4 md:px-8 text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="max-w-4xl mx-auto"
            >
              <div className="inline-flex items-center rounded-full border border-border/50 bg-surface px-4 py-1.5 text-xs font-semibold backdrop-blur-md mb-8 tracking-wide text-foreground/80 shadow-sm">
                <span className="flex h-2 w-2 rounded-full bg-accent mr-2"></span>
                Latest stable {siteConfig.version}
              </div>
              
              <h1 className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tight mb-8 leading-[1.1]">
                Your time. <br className="hidden md:block" />
                <span className="text-foreground/90">Your rules.</span>
              </h1>
              
              <p className="text-lg md:text-2xl text-foreground/60 mb-12 max-w-2xl mx-auto leading-relaxed font-medium">
                A focused Windows utility for understanding where your time goes, staying focused, protecting applications, and keeping your digital routine under control.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link href={siteConfig.links.download}>
                  <Button size="lg" className="rounded-xl w-full sm:w-auto font-bold gap-2 text-base h-14 px-8 shadow-xl shadow-accent/10 transition-all hover:scale-105 bg-foreground text-background hover:bg-foreground/90">
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

            {/* HERO PRODUCT IMAGE */}
            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
              className="mt-20 relative max-w-5xl mx-auto"
            >
              <div className="relative rounded-2xl border border-glass-border bg-glass p-2 shadow-2xl backdrop-blur-xl">
                <div className="aspect-[16/9] w-full rounded-xl bg-card border border-border/40 overflow-hidden relative">
                  <ImageLightbox 
                    src="/images/app/home-dark.png" 
                    alt="NYW v3.1.5 Dashboard in Dark Mode" 
                    className="w-full h-full"
                    priority
                  />
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* HOW IT WORKS (PRODUCT STORY) */}
        <section id="how-it-works" className="py-24 bg-surface/10 border-y border-border/20">
          <div className="container mx-auto px-4 md:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">How it works</h2>
              <p className="text-foreground/60 text-lg">A simple, effective flow to reclaim your productivity.</p>
            </div>
            
            <div className="grid md:grid-cols-4 gap-8 max-w-5xl mx-auto relative">
              <div className="hidden md:block absolute top-6 left-1/8 right-1/8 h-px bg-border/50 -z-10" />
              
              {[
                { step: "01", title: "Install NYW", desc: "Download and run the lightweight Windows utility." },
                { step: "02", title: "See where your time goes", desc: "Let the background tracker analyze your application usage." },
                { step: "03", title: "Set your Focus rules", desc: "Define blocks of time and applications to restrict." },
                { step: "04", title: "Protect what matters", desc: "Lock sensitive apps behind Windows Hello biometrics." }
              ].map((item, idx) => (
                <div key={idx} className="flex flex-col items-center text-center">
                  <div className="w-12 h-12 rounded-full bg-surface border border-border/60 flex items-center justify-center font-bold text-lg mb-6 shadow-sm">
                    {item.step}
                  </div>
                  <h3 className="text-xl font-bold mb-2">{item.title}</h3>
                  <p className="text-foreground/60 text-sm font-medium leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* INTERACTIVE DEMO GALLERY */}
        <section className="py-32 bg-background relative overflow-hidden">
          <div className="container mx-auto px-4 md:px-8">
            <div className="flex flex-col lg:flex-row gap-12 lg:items-start">
              
              {/* Tab Navigation */}
              <div className="flex flex-col gap-2 w-full lg:w-1/3 pt-4">
                <h2 className="text-3xl font-bold mb-8 px-2">Explore Features</h2>
                {DEMO_TABS.map((tab) => {
                  const isActive = activeTab === tab.id
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex flex-col gap-2 p-5 rounded-2xl text-left transition-all duration-200 border ${
                        isActive 
                          ? "bg-surface border-border shadow-md" 
                          : "bg-transparent border-transparent hover:bg-surface/40"
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${isActive ? "bg-foreground/10 text-foreground" : "bg-transparent text-foreground/50"}`}>
                          <tab.icon className="w-5 h-5" />
                        </div>
                        <h4 className={`text-lg font-bold ${isActive ? "text-foreground" : "text-foreground/70"}`}>{tab.label}</h4>
                      </div>
                      {isActive && (
                        <motion.p 
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          className="text-foreground/60 text-sm pl-13 pt-1"
                        >
                          {tab.desc}
                        </motion.p>
                      )}
                    </button>
                  )
                })}
              </div>

              {/* Dynamic Image Display */}
              <div className="w-full lg:w-2/3">
                <div className="relative rounded-2xl border border-glass-border bg-glass p-2 shadow-xl overflow-hidden aspect-[16/9]">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={activeTab}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.25 }}
                      className="absolute inset-2 rounded-xl overflow-hidden bg-card border border-border/30"
                    >
                      <ImageLightbox 
                        src={activeTabData.fallback}
                        alt={`NYW ${activeTabData.label} UI`}
                        className="w-full h-full"
                      />
                    </motion.div>
                  </AnimatePresence>
                </div>
                <div className="flex items-center justify-center gap-2 mt-6 text-sm text-foreground/40 font-medium">
                  <Monitor className="w-4 h-4" /> <span>Actual v3.1.5 application screenshots.</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FEATURE SHOWCASE: FOCUS */}
        <section className="py-24 bg-surface/10 border-y border-border/20">
          <div className="container mx-auto px-4 md:px-8">
            <div className="flex flex-col md:flex-row items-center gap-16">
              <div className="flex-1 space-y-6">
                <h2 className="text-3xl md:text-5xl font-bold tracking-tight">Stay in the zone.</h2>
                <p className="text-xl text-foreground/60 leading-relaxed">
                  Focus Mode is designed to eliminate desktop distractions by restricting access to specific applications while you work.
                </p>
                <ul className="space-y-4 pt-4">
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-foreground/40 shrink-0" />
                    <span><strong>Application Blocklist:</strong> Define exact applications (e.g., discord.exe, games) to block during your session.</span>
                  </li>
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-foreground/40 shrink-0" />
                    <span><strong>Strict Mode:</strong> Prevents cancelling the timer early without entering your secure PIN.</span>
                  </li>
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-foreground/40 shrink-0" />
                    <span><strong>No browser extensions:</strong> Works purely at the OS level by managing application processes.</span>
                  </li>
                </ul>
              </div>
              <div className="flex-1 w-full">
                <div className="relative rounded-2xl border border-border/40 p-1 shadow-2xl bg-surface">
                  <div className="relative rounded-xl border border-border/20 w-full aspect-[16/9] overflow-hidden bg-card">
                    <ImageLightbox src="/images/app/focus-dark.png" alt="Focus Mode" className="w-full h-full" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FEATURE SHOWCASE: APP LOCKER */}
        <section className="py-24 bg-background">
          <div className="container mx-auto px-4 md:px-8">
            <div className="flex flex-col md:flex-row-reverse items-center gap-16">
              <div className="flex-1 space-y-6">
                <h2 className="text-3xl md:text-5xl font-bold tracking-tight">Protect sensitive apps.</h2>
                <p className="text-xl text-foreground/60 leading-relaxed">
                  App Locker guards your selected applications from unauthorized access. Native Windows Security integration ensures a seamless experience.
                </p>
                <ul className="space-y-4 pt-4">
                  <li className="flex items-start gap-3 text-foreground/80">
                    <Shield className="w-6 h-6 text-foreground/40 shrink-0" />
                    <span><strong>Windows Hello Support:</strong> Unlock protected apps using your face, fingerprint, or Windows PIN.</span>
                  </li>
                  <li className="flex items-start gap-3 text-foreground/80">
                    <Clock className="w-6 h-6 text-foreground/40 shrink-0" />
                    <span><strong>Temporary Grants:</strong> Grant access for 5 minutes, 15 minutes, or until the application is closed.</span>
                  </li>
                </ul>
              </div>
              <div className="flex-1 w-full">
                <div className="relative rounded-2xl border border-border/40 p-1 shadow-2xl bg-surface">
                  <div className="relative rounded-xl border border-border/20 w-full aspect-[16/9] overflow-hidden bg-card">
                    <ImageLightbox src="/images/app/app-locker-dark.png" alt="App Locker" className="w-full h-full" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
        
        {/* FEATURE SHOWCASE: INSIGHTS & SLEEPGUARD */}
        <section className="py-24 bg-surface/10 border-t border-border/20">
          <div className="container mx-auto px-4 md:px-8">
            <div className="grid md:grid-cols-2 gap-12">
              <div className="space-y-6 p-8 rounded-2xl border border-border/30 bg-surface hover:border-border/60 transition-colors flex flex-col h-full">
                <ChartPie className="w-8 h-8 text-foreground/70" />
                <h3 className="text-2xl font-bold">Data-driven Insights</h3>
                <p className="text-foreground/60 leading-relaxed">
                  Understand your habits with historical trends. See your highest-usage categories, daily averages, and identify areas where your productivity thrives or falls. All data remains locally on your device.
                </p>
                <div className="pt-4 mt-auto">
                   <div className="relative rounded-xl border border-border/20 w-full aspect-[16/9] overflow-hidden bg-card">
                     <ImageLightbox src="/images/app/insights-dark.png" alt="Insights" className="w-full h-full" />
                   </div>
                </div>
              </div>
              
              <div className="space-y-6 p-8 rounded-2xl border border-border/30 bg-surface hover:border-border/60 transition-colors flex flex-col h-full">
                <Moon className="w-8 h-8 text-foreground/70" />
                <h3 className="text-2xl font-bold">SleepGuard</h3>
                <p className="text-foreground/60 leading-relaxed">
                  Protect your evenings. SleepGuard detects inactivity late at night and provides a countdown before automatically sleeping or locking your PC, ensuring you disconnect when intended.
                </p>
                <div className="pt-4 mt-auto">
                   <div className="relative rounded-xl border border-border/20 w-full aspect-[16/9] overflow-hidden bg-card">
                     <ImageLightbox src="/images/app/sleepguard-dark.png" alt="SleepGuard" className="w-full h-full" />
                   </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* USE CASES */}
        <section className="py-24 bg-background">
           <div className="container mx-auto px-4 md:px-8 text-center max-w-4xl">
              <h2 className="text-3xl font-bold mb-12">Practical Use Cases</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                 {[
                   "Deep Work Sessions",
                   "Study & Preparation",
                   "Reducing Distractions",
                   "Screen Time Awareness",
                   "Protecting Privacy",
                   "Idle PC Protection"
                 ].map((usecase, i) => (
                    <div key={i} className="p-4 rounded-xl border border-border/40 bg-surface/50 text-foreground/80 font-medium">
                       {usecase}
                    </div>
                 ))}
              </div>
           </div>
        </section>

      </main>
    </div>
  )
}
