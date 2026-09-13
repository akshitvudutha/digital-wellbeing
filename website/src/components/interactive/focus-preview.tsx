"use client"
import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Image from "next/image"
import { Play, Square, ShieldCheck, Lock, Sparkles, Check } from "lucide-react"

export function FocusPreview() {
  const [isFocusing, setIsFocusing] = useState(true)
  const [seconds, setSeconds] = useState(1485) // 24m 45s
  const [mode, setMode] = useState<"deep" | "pomodoro">("deep")

  useEffect(() => {
    if (!isFocusing) return
    const interval = setInterval(() => {
      setSeconds((prev) => (prev > 0 ? prev - 1 : 1500))
    }, 1000)
    return () => clearInterval(interval)
  }, [isFocusing])

  const formatTime = (totalSec: number) => {
    const m = Math.floor(totalSec / 60)
    const s = totalSec % 60
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Dynamic Island / Floating Focus Pill */}
      <motion.div
        layout
        className="glass-island rounded-full p-2.5 px-4 md:px-6 flex items-center justify-between shadow-2xl relative overflow-hidden"
      >
        {/* Ambient Subtle Accent Glow */}
        <div
          className={`absolute inset-0 opacity-15 pointer-events-none transition-all duration-700 ${
            isFocusing
              ? "bg-[radial-gradient(ellipse_at_center,_var(--color-nyw-emerald),_transparent_70%)]"
              : "bg-[radial-gradient(ellipse_at_center,_var(--color-nyw-amber),_transparent_70%)]"
          }`}
        />

        {/* Left: Notch Symbol + State */}
        <div className="flex items-center gap-3 relative z-10">
          <div className="relative w-8 h-8 flex-shrink-0">
            <Image
              src="/notch-logo.png"
              alt="Notch"
              width={32}
              height={32}
              className="object-contain"
              priority
            />
          </div>
          <div className="flex flex-col text-left">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs text-foreground/90 tracking-wide uppercase">
                {isFocusing ? (mode === "deep" ? "Deep Focus Active" : "Pomodoro Sprint") : "Session Paused"}
              </span>
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isFocusing ? "bg-nyw-emerald animate-pulse" : "bg-nyw-amber"
                }`}
              />
            </div>
            <span className="text-[11px] text-foreground/50 font-mono">
              {isFocusing ? "Allowlist Enforced · Windows Safe" : "Ready for next block"}
            </span>
          </div>
        </div>

        {/* Center: Monospaced Timer */}
        <div className="relative z-10 px-3 py-1 rounded-lg bg-black/40 border border-white/5 font-mono text-base md:text-lg font-medium tracking-wider text-foreground">
          {formatTime(seconds)}
        </div>

        {/* Right: Interactive Toggle Control */}
        <div className="flex items-center gap-2 relative z-10">
          <button
            onClick={() => {
              setIsFocusing(!isFocusing)
              if (!isFocusing && seconds === 0) setSeconds(1500)
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 cursor-pointer ${
              isFocusing
                ? "bg-white/10 hover:bg-white/15 text-foreground border border-white/10"
                : "bg-nyw-emerald text-black hover:bg-nyw-emerald/90 shadow-lg glow-emerald"
            }`}
          >
            {isFocusing ? (
              <>
                <Square className="w-3 h-3 fill-current" />
                <span className="hidden sm:inline">Pause</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-current" />
                <span>Resume</span>
              </>
            )}
          </button>
        </div>
      </motion.div>

      {/* Supporting Interactive Sub-pill: Allowlist processes */}
      <AnimatePresence>
        {isFocusing && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25 }}
            className="mt-3 flex flex-wrap items-center justify-center gap-2 text-xs text-foreground/60"
          >
            <span className="text-[11px] uppercase tracking-wider text-foreground/40 font-mono">
              Active Allowlist:
            </span>
            {["Code.exe", "WindowsTerminal.exe", "Figma.exe"].map((app) => (
              <span
                key={app}
                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-white/[0.03] border border-white/[0.06] text-foreground/75 font-mono text-[11px]"
              >
                <Check className="w-2.5 h-2.5 text-nyw-emerald" />
                {app}
              </span>
            ))}
            <span className="text-[11px] text-foreground/40 font-mono">
              (All others restricted)
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
