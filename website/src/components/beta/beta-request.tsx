"use client"
import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ArrowRight, CheckCircle2, Loader2, ShieldCheck, Sparkles } from "lucide-react"

interface BetaRequestProps {
  variant?: "hero" | "card"
  id?: string
}

export function BetaRequest({ variant = "hero", id = "beta-input" }: BetaRequestProps) {
  const [email, setEmail] = useState("")
  const [osVersion, setOsVersion] = useState<"Windows 11" | "Windows 10">("Windows 11")
  const [honeypot, setHoneypot] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !email.includes("@")) {
      setResult({ success: false, message: "Please enter a valid email address." })
      return
    }

    setLoading(true)
    setResult(null)

    try {
      const res = await fetch("/api/beta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, osVersion, honeypot }),
      })

      const data = await res.json()
      setResult({
        success: data.success,
        message: data.message || "Beta request recorded.",
      })
      if (data.success) {
        setEmail("")
      }
    } catch (err) {
      setResult({
        success: false,
        message: "Unable to submit request at this moment. Please try again.",
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full max-w-xl mx-auto text-center" id={id}>
      <AnimatePresence mode="wait">
        {result?.success ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="p-6 rounded-2xl bg-nyw-emerald/[0.08] border border-nyw-emerald/20 text-center space-y-2"
          >
            <div className="w-10 h-10 rounded-full bg-nyw-emerald/15 text-nyw-emerald flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <h4 className="font-semibold text-white text-base">Request Received</h4>
            <p className="text-sm text-foreground/70 leading-relaxed max-w-md mx-auto">
              {result.message}
            </p>
            <button
              onClick={() => setResult(null)}
              className="text-xs text-nyw-emerald hover:underline mt-2 inline-block cursor-pointer font-medium"
            >
              Submit another request
            </button>
          </motion.div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Honeypot field (hidden from real users, catches automated bots) */}
            <input
              type="text"
              name="honeypot"
              value={honeypot}
              onChange={(e) => setHoneypot(e.target.value)}
              className="hidden"
              tabIndex={-1}
              autoComplete="off"
            />

            {/* Streamlined Pill Container */}
            <div className="glass-island rounded-full p-1.5 pl-5 flex items-center justify-between gap-2 shadow-2xl relative">
              <input
                type="email"
                required
                suppressHydrationWarning
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  if (result) setResult(null)
                }}
                placeholder="Enter your email for beta access..."
                className="w-full bg-transparent text-sm md:text-base text-foreground placeholder:text-foreground/35 focus:outline-none font-normal"
              />

              <button
                type="submit"
                disabled={loading}
                suppressHydrationWarning
                className="flex-shrink-0 flex items-center gap-2 px-5 py-3 rounded-full text-xs md:text-sm font-semibold transition-all duration-200 cursor-pointer bg-white text-black hover:bg-white/90 shadow-lg glow-emerald disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Sending...</span>
                  </>
                ) : (
                  <>
                    <span>Request Beta Access</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>

            {/* Error Display */}
            {result && !result.success && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-xs text-red-400 font-medium"
              >
                {result.message}
              </motion.p>
            )}

            {/* Sub-bar options: OS version selector & privacy notice */}
            <div className="flex items-center justify-center gap-4 text-xs text-foreground/45 pt-1">
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-[11px]">Platform:</span>
                <select
                  value={osVersion}
                  onChange={(e) => setOsVersion(e.target.value as any)}
                  className="bg-transparent border-none text-foreground/75 font-mono text-[11px] focus:outline-none cursor-pointer"
                >
                  <option value="Windows 11" className="bg-[#0e1116] text-white">
                    Windows 11
                  </option>
                  <option value="Windows 10" className="bg-[#0e1116] text-white">
                    Windows 10
                  </option>
                </select>
              </div>
              <span>•</span>
              <div className="flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-nyw-emerald" />
                <span>Zero spam · Controlled test batches</span>
              </div>
            </div>
          </form>
        )}
      </AnimatePresence>
    </div>
  )
}
