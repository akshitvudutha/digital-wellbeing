"use client"
import { useState } from "react"
import { siteConfig } from "@/config/site"
import { Button } from "@/components/ui/button"
import { Download, Shield, Clock, Moon, Monitor, ChartPie, Activity, Lock, CheckCircle2, ChevronDown, Code2 } from "lucide-react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { ImageLightbox } from "@/components/ui/lightbox"

const DEMO_TABS = [
  { id: "overview", label: "Overview", icon: Monitor, fallback: "/images/app/home-dark.png", desc: "Your daily dashboard summarizing active time and focus sessions." },
  { id: "usage", label: "Usage", icon: Activity, fallback: "/images/app/usage-dark.png", desc: "Detailed breakdown of application usage and categorized screen time." },
  { id: "focus", label: "Focus", icon: Clock, fallback: "/images/app/focus-dark.png", desc: "Define an application blocklist and stay in the zone without distractions." },
  { id: "applocker", label: "App Locker", icon: Lock, fallback: "/images/app/app-locker-dark.png", desc: "Protect sensitive applications with Windows Hello biometrics or PIN." },
  { id: "insights", label: "Insights", icon: ChartPie, fallback: "/images/app/insights-dark.png", desc: "Analyze historical trends to build better digital habits." },
  { id: "sleepguard", label: "SleepGuard", icon: Moon, fallback: "/images/app/sleepguard-dark.png", desc: "Automatically lock or sleep your PC when inactivity is detected late at night." },
]

export default function Home() {
  const [activeTab, setActiveTab] = useState(DEMO_TABS[0].id)
  const activeTabData = DEMO_TABS.find(t => t.id === activeTab) || DEMO_TABS[0]
  const [faqOpen, setFaqOpen] = useState<number | null>(0)

  return (
    <div className="flex flex-col min-h-screen selection:bg-accent/30 selection:text-foreground">
      <main className="flex-1">
        
        {/* HERO SECTION */}
        <section className="relative pt-32 pb-24 md:pt-48 md:pb-32 overflow-hidden">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-background via-background to-background" />
          
          <div className="container mx-auto px-4 md:px-8 text-center max-w-[1400px]">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="max-w-4xl mx-auto"
            >
              <div className="inline-flex items-center rounded-full border border-border/50 bg-surface px-4 py-1.5 text-xs font-semibold backdrop-blur-md mb-8 tracking-wide text-foreground/80 shadow-sm">
                <span className="flex h-2 w-2 rounded-full bg-accent mr-2"></span>
                NYW · Latest stable v{siteConfig.stableVersion}
              </div>
              
              <h1 className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tight mb-8 leading-[1.1]">
                Your time. <br className="hidden md:block" />
                <span className="text-foreground/90">Your rules.</span>
              </h1>
              
              <p className="text-lg md:text-2xl text-foreground/60 mb-12 max-w-2xl mx-auto leading-relaxed font-medium">
                Understand your screen time, focus on what matters, protect distracting applications, and build better digital habits on Windows.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link href={siteConfig.links.download}>
                  <Button size="lg" className="rounded-xl w-full sm:w-auto font-bold gap-2 text-base h-14 px-8 shadow-xl shadow-accent/20 transition-all hover:scale-105 bg-accent text-background hover:bg-accent/90">
                    <Download className="h-5 w-5" />
                    Download for Windows
                  </Button>
                </Link>
                <Link href="#explore">
                  <Button variant="outline" size="lg" className="rounded-xl w-full sm:w-auto font-semibold h-14 px-8 border-border/60 bg-surface/30 backdrop-blur hover:bg-surface-hover">
                    Explore NYW
                  </Button>
                </Link>
              </div>
            </motion.div>

            {/* HERO PRODUCT IMAGE - MASSIVE */}
            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
              className="mt-24 relative w-full mx-auto"
            >
              <div className="relative rounded-xl border border-glass-border bg-glass p-1 md:p-2 shadow-2xl backdrop-blur-xl">
                <div className="aspect-[16/9] w-full rounded-lg bg-black border border-border/40 overflow-hidden relative">
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

        {/* PRODUCT VALUE STRIP */}
        <section className="py-12 border-y border-border/20 bg-surface/30 backdrop-blur-sm">
          <div className="container mx-auto px-4 md:px-8 max-w-[1400px]">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {[
                { title: "Understand your time", desc: "Detailed, local-first analytics." },
                { title: "Protect what matters", desc: "Biometric app locker security." },
                { title: "Build focused sessions", desc: "Application-level blocklists." },
                { title: "Stay in control", desc: "Native Windows experience." },
              ].map((val, idx) => (
                <div key={idx} className="flex flex-col gap-1 border-l-2 border-accent/40 pl-4">
                  <h4 className="font-bold text-foreground text-lg">{val.title}</h4>
                  <p className="text-foreground/50 text-sm font-medium">{val.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* STORYTELLING: 01 UNDERSTAND */}
        <section id="explore" className="py-32 overflow-hidden">
          <div className="container mx-auto px-4 md:px-8 max-w-[1400px]">
            <div className="flex flex-col lg:flex-row items-center gap-16 lg:gap-24">
              <div className="w-full lg:w-[35%] space-y-6">
                <div className="inline-flex items-center rounded-md bg-surface px-3 py-1 text-sm font-semibold border border-border/50 text-accent">01 // Understand</div>
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight">See where your time goes.</h2>
                <p className="text-xl text-foreground/60 leading-relaxed">
                  The Usage dashboard provides a clear, categorized breakdown of your screen time. See your active time, idle time, and identify your most distracting applications natively.
                </p>
                <ul className="space-y-4 pt-4">
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-accent shrink-0" />
                    <span><strong>Categorized analytics:</strong> Automatically group related applications.</span>
                  </li>
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-accent shrink-0" />
                    <span><strong>Idle detection:</strong> Smart tracking separates real usage from away time.</span>
                  </li>
                </ul>
              </div>
              <div className="w-full lg:w-[65%]">
                <div className="aspect-[16/9] w-full rounded-xl bg-black border border-border/40 overflow-hidden shadow-2xl">
                  <ImageLightbox src="/images/app/usage-dark.png" alt="Usage screen" className="w-full h-full" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* STORYTELLING: 02 FOCUS */}
        <section className="py-32 bg-surface/10 border-y border-border/20 overflow-hidden">
          <div className="container mx-auto px-4 md:px-8 max-w-[1400px]">
            <div className="flex flex-col lg:flex-row-reverse items-center gap-16 lg:gap-24">
              <div className="w-full lg:w-[35%] space-y-6">
                <div className="inline-flex items-center rounded-md bg-surface px-3 py-1 text-sm font-semibold border border-border/50 text-accent">02 // Focus</div>
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight">Create distraction-free sessions.</h2>
                <p className="text-xl text-foreground/60 leading-relaxed">
                  Block distracting Windows applications entirely during a Focus session. NYW operates at the OS level to manage application processes—no browser extensions required.
                </p>
                <ul className="space-y-4 pt-4">
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-accent shrink-0" />
                    <span><strong>Application-level blocking:</strong> Instantly restrict any .exe from running.</span>
                  </li>
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-accent shrink-0" />
                    <span><strong>Strict Mode:</strong> Prevent yourself from stopping the timer early.</span>
                  </li>
                </ul>
              </div>
              <div className="w-full lg:w-[65%]">
                <div className="aspect-[16/9] w-full rounded-xl bg-black border border-border/40 overflow-hidden shadow-2xl">
                  <ImageLightbox src="/images/app/focus-dark.png" alt="Focus mode screen" className="w-full h-full" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* STORYTELLING: 03 PROTECT */}
        <section className="py-32 overflow-hidden">
          <div className="container mx-auto px-4 md:px-8 max-w-[1400px]">
            <div className="flex flex-col lg:flex-row items-center gap-16 lg:gap-24">
              <div className="w-full lg:w-[35%] space-y-6">
                <div className="inline-flex items-center rounded-md bg-surface px-3 py-1 text-sm font-semibold border border-border/50 text-accent">03 // Protect</div>
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight">Lock sensitive applications.</h2>
                <p className="text-xl text-foreground/60 leading-relaxed">
                  Use App Locker to restrict access to specific applications on your PC. Unlocking requires your secure Windows Hello biometric or PIN authentication.
                </p>
                <ul className="space-y-4 pt-4">
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-accent shrink-0" />
                    <span><strong>Windows Hello Integration:</strong> Native biometric security.</span>
                  </li>
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-accent shrink-0" />
                    <span><strong>Timeout controls:</strong> Automatically re-lock apps after you finish.</span>
                  </li>
                </ul>
              </div>
              <div className="w-full lg:w-[65%]">
                <div className="aspect-[16/9] w-full rounded-xl bg-black border border-border/40 overflow-hidden shadow-2xl">
                  <ImageLightbox src="/images/app/app-locker-dark.png" alt="App Locker screen" className="w-full h-full" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* STORYTELLING: 04 RECOVER */}
        <section className="py-32 bg-surface/10 border-y border-border/20 overflow-hidden">
          <div className="container mx-auto px-4 md:px-8 max-w-[1400px]">
            <div className="flex flex-col lg:flex-row-reverse items-center gap-16 lg:gap-24">
              <div className="w-full lg:w-[35%] space-y-6">
                <div className="inline-flex items-center rounded-md bg-surface px-3 py-1 text-sm font-semibold border border-border/50 text-accent">04 // Recover</div>
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight">Manage downtime gracefully.</h2>
                <p className="text-xl text-foreground/60 leading-relaxed">
                  SleepGuard monitors your inactivity. If you fall asleep watching a video, it will automatically lock or suspend your PC after a warning countdown.
                </p>
                <ul className="space-y-4 pt-4">
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-accent shrink-0" />
                    <span><strong>Smart inactivity detection:</strong> Only triggers when you are truly away.</span>
                  </li>
                  <li className="flex items-start gap-3 text-foreground/80">
                    <CheckCircle2 className="w-6 h-6 text-accent shrink-0" />
                    <span><strong>Custom actions:</strong> Choose between Lock, Sleep, or Hibernate.</span>
                  </li>
                </ul>
              </div>
              <div className="w-full lg:w-[65%]">
                <div className="aspect-[16/9] w-full rounded-xl bg-black border border-border/40 overflow-hidden shadow-2xl">
                  <ImageLightbox src="/images/app/sleepguard-dark.png" alt="SleepGuard screen" className="w-full h-full" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* INTERACTIVE DEMO GALLERY */}
        <section className="py-32 bg-background relative overflow-hidden">
          <div className="container mx-auto px-4 md:px-8 max-w-[1400px]">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">Explore the complete UI</h2>
              <p className="text-foreground/60 text-lg">Every setting and dashboard designed with precision.</p>
            </div>
            
            <div className="flex flex-col lg:flex-row gap-12 lg:gap-16">
              
              {/* Tab Navigation */}
              <div className="flex flex-col gap-2 w-full lg:w-[25%]">
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
                        <div className={`p-2 rounded-lg ${isActive ? "bg-accent/10 text-accent" : "bg-transparent text-foreground/50"}`}>
                          <tab.icon className="w-5 h-5" />
                        </div>
                        <h4 className={`text-lg font-bold ${isActive ? "text-foreground" : "text-foreground/70"}`}>{tab.label}</h4>
                      </div>
                    </button>
                  )
                })}
              </div>

              {/* Dynamic Image Display */}
              <div className="w-full lg:w-[75%]">
                <div className="relative rounded-2xl border border-glass-border bg-glass p-2 shadow-2xl overflow-hidden aspect-[16/9]">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={activeTab}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.25 }}
                      className="absolute inset-2 rounded-xl overflow-hidden bg-black border border-border/30"
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
                  <Monitor className="w-4 h-4" /> <span>Click any screenshot to expand actual size.</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* WHY NYW / TRUST */}
        <section className="py-24 bg-surface/10 border-y border-border/20">
          <div className="container mx-auto px-4 md:px-8 max-w-[1400px]">
            <div className="grid md:grid-cols-3 gap-12">
              <div className="flex flex-col gap-4">
                <Shield className="w-10 h-10 text-accent" />
                <h3 className="text-2xl font-bold">Privacy first. Local only.</h3>
                <p className="text-foreground/60 leading-relaxed">
                  Your screen time data is strictly stored locally on your device in an SQLite database. No telemetry, no accounts, no cloud sync.
                </p>
              </div>
              <div className="flex flex-col gap-4">
                <Monitor className="w-10 h-10 text-accent" />
                <h3 className="text-2xl font-bold">Windows Native</h3>
                <p className="text-foreground/60 leading-relaxed">
                  Designed specifically for Windows 10 and 11, utilizing OS-level process management and native Windows Hello biometrics.
                </p>
              </div>
              <div className="flex flex-col gap-4">
                <Code2 className="w-10 h-10 text-accent" />
                <h3 className="text-2xl font-bold">Open Source</h3>
                <p className="text-foreground/60 leading-relaxed">
                  Distributed transparently on GitHub. You can inspect the source code, compile it yourself, or download the verified public releases.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-32">
          <div className="container mx-auto px-4 md:px-8 max-w-4xl">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">Frequently Asked Questions</h2>
            </div>
            
            <div className="space-y-4">
              {[
                { q: "What does NYW stand for?", a: "NYW stands for 'Not Your Wellbeing', a premium digital wellbeing and screen time tracker for Windows." },
                { q: "Does Focus Mode block websites?", a: "No. Currently, NYW's Focus Mode is strictly application-level (e.g., blocking discord.exe). It does not interact with your browser to block specific URLs or websites." },
                { q: "How does App Locker work?", a: "App Locker uses OS process suspension combined with Windows Hello to securely lock specified applications behind your biometric or PIN prompt." },
                { q: "Does NYW collect my data?", a: "No. NYW operates entirely offline. All analytics and settings are stored locally on your machine." }
              ].map((faq, idx) => (
                <div key={idx} className="border border-border/40 rounded-xl overflow-hidden bg-surface/30">
                  <button 
                    className="w-full text-left px-6 py-5 flex items-center justify-between font-bold text-lg hover:bg-surface/50 transition-colors"
                    onClick={() => setFaqOpen(faqOpen === idx ? null : idx)}
                  >
                    {faq.q}
                    <ChevronDown className={`w-5 h-5 transition-transform ${faqOpen === idx ? "rotate-180" : ""}`} />
                  </button>
                  <AnimatePresence>
                    {faqOpen === idx && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="px-6 pb-5 text-foreground/60 leading-relaxed"
                      >
                        {faq.a}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FINAL CTA */}
        <section className="py-32 bg-[radial-gradient(ellipse_at_bottom,_var(--tw-gradient-stops))] from-accent/10 via-background to-background relative border-t border-border/20">
          <div className="container mx-auto px-4 md:px-8 text-center max-w-3xl">
            <h2 className="text-4xl md:text-6xl font-black tracking-tight mb-8">Take back your time.</h2>
            <p className="text-xl text-foreground/60 mb-12">
              Start building healthier digital habits today with NYW for Windows.
            </p>
            <div className="flex justify-center">
              <Link href={siteConfig.links.download}>
                <Button size="lg" className="rounded-xl font-bold gap-2 text-base h-16 px-10 shadow-2xl shadow-accent/20 transition-all hover:scale-105 bg-accent text-background hover:bg-accent/90">
                  <Download className="h-6 w-6" />
                  Download v{siteConfig.stableVersion}
                </Button>
              </Link>
            </div>
            <p className="mt-8 text-sm text-foreground/40 font-medium">Free and Open Source • Windows 10 & 11</p>
          </div>
        </section>

      </main>
    </div>
  )
}
