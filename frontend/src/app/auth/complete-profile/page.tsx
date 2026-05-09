"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { User, Scale, Loader2, CheckCircle, ArrowRight, UserCircle, Shield, Briefcase, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSession } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";

type AccountTypeId = "individual" | "attorney";
const MAX_NAME_LENGTH = 100;
const ACCOUNT_TYPES: Array<{ id: AccountTypeId; icon: typeof User | typeof Briefcase; title: string; desc: string }> = [
  { id: "individual", icon: User, title: "Individual", desc: "Personal legal assistance and review." },
  { id: "attorney", icon: Briefcase, title: "Legal Professional", desc: "Audit client contracts and firm workflows." },
];

export default function CompleteProfilePage() {
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [accountType, setAccountType] = useState<AccountTypeId | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const { data: session, update } = useSession();

  const handleNextStep = () => {
    if (step === 1 && name.trim()) {
      setStep(2);
    }
  };

  const handleSubmit = async () => {
    if (!accountType || !name) return;
    setLoading(true);
    setError("");

    try {
      // Call backend API to update profile - moved to /api/users to avoid NextAuth conflict
      const res = await fetch("/api/users/complete-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, userType: accountType }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to update profile");
      }

      // Update the NextAuth session
      await update({ name, userType: accountType });
      
      router.push("/chat");
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020817] relative overflow-hidden p-6">
      {/* Background Decorative Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/5 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/5 blur-[120px] rounded-full pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel max-w-lg w-full rounded-3xl p-8 md:p-12 border-white/5 relative z-10"
      >
        {/* Header Section */}
        <div className="mb-10 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-[10px] font-bold uppercase tracking-wider mb-4">
            <Shield className="w-3 h-3" /> Secure Onboarding
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Configure your <span className="text-primary font-black">Workspace</span>
          </h1>
          <p className="text-muted-foreground text-sm mt-2 max-w-[280px] mx-auto leading-relaxed">
            Tailor Fortress AI to your specific legal analysis needs.
          </p>
        </div>

        {/* Progress Tracker */}
        <div className="flex items-center justify-between mb-12 relative px-4">
          <div className="absolute left-4 right-4 top-1/2 -translate-y-1/2 h-0.5 bg-white/5 z-0" />
          <div 
            className="absolute left-4 top-1/2 -translate-y-1/2 h-0.5 bg-primary transition-all duration-500 ease-in-out z-0" 
            style={{ width: step === 1 ? '0%' : 'calc(100% - 32px)' }}
          />
          {[1, 2].map((i) => (
            <div 
              key={i}
              className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-500 ${
                step >= i 
                  ? "bg-primary border-primary text-white shadow-[0_0_15px_rgba(24,86,255,0.4)]" 
                  : "bg-[#0A101F] border-white/10 text-muted-foreground"
              }`}
            >
              {step > i ? <CheckCircle className="w-5 h-5" /> : <span className="text-xs font-bold">{i}</span>}
            </div>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {step === 1 ? (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="space-y-6"
            >
              <div className="space-y-4">
                <div className="group">
                  <label className="text-[11px] font-mono font-bold uppercase text-muted-foreground tracking-widest block mb-2 px-1">
                    What should we call you?
                  </label>
                  <div className="relative">
                    <UserCircle className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground group-focus-within:text-primary transition-colors" />
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value.slice(0, MAX_NAME_LENGTH))}
                      maxLength={MAX_NAME_LENGTH}
                      placeholder="Your full name"
                      autoFocus
                      className="w-full bg-white/[0.03] border border-white/10 rounded-2xl pl-12 pr-4 py-4 text-secondary placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 focus:bg-white/[0.05] focus:shadow-[0_0_20px_rgba(24,86,255,0.05)] transition-all text-lg"
                      onKeyDown={(e) => e.key === "Enter" && name.trim() && handleNextStep()}
                    />
                  </div>
                </div>
              </div>

              <Button
                onClick={handleNextStep}
                disabled={!name.trim()}
                variant="glass"
                size="lg"
                className="w-full py-7 rounded-2xl text-lg font-bold shadow-xl shadow-primary/10 group"
              >
                Next Step <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Button>
            </motion.div>
          ) : (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="space-y-6"
            >
              <div className="space-y-3">
                <label className="text-[11px] font-mono font-bold uppercase text-muted-foreground tracking-widest block mb-2 px-1">
                  Choose your account type
                </label>
                
                <div className="grid grid-cols-1 gap-4" role="radiogroup" aria-label="Account type">
                  {ACCOUNT_TYPES.map((type) => (
                    <button
                      key={type.id}
                      type="button"
                      role="radio"
                      aria-checked={accountType === type.id}
                      onClick={() => setAccountType(type.id)}
                      onKeyDown={(e) => {
                        if (e.key === " " || e.key === "Enter") {
                          e.preventDefault();
                          setAccountType(type.id);
                        }
                      }}
                      className={`flex items-center gap-5 p-5 rounded-2xl text-left border transition-all relative group ${
                        accountType === type.id
                          ? "bg-primary/10 border-primary text-white shadow-[0_0_25px_rgba(24,86,255,0.1)]"
                          : "bg-white/[0.03] border-white/10 text-muted-foreground hover:bg-white/[0.06] hover:border-white/20"
                      }`}
                    >
                      <div className={`w-14 h-14 rounded-xl flex items-center justify-center transition-all ${
                        accountType === type.id ? "bg-primary text-white scale-110 shadow-lg" : "bg-white/5 text-muted-foreground group-hover:text-secondary"
                      }`}>
                        <type.icon className="w-7 h-7" />
                      </div>
                      <div className="flex-1">
                        <p className={`font-bold text-base ${accountType === type.id ? "text-white" : "text-secondary"}`}>
                          {type.title}
                        </p>
                        <p className="text-xs opacity-60 leading-relaxed mt-0.5">{type.desc}</p>
                      </div>
                      {accountType === type.id && (
                        <motion.div 
                          layoutId="active-check"
                          className="absolute right-5"
                        >
                          <div className="bg-primary rounded-full p-1 shadow-lg">
                            <CheckCircle className="w-4 h-4 text-white" />
                          </div>
                        </motion.div>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <motion.p 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="text-red-400 text-xs font-medium bg-red-500/10 p-3 rounded-xl border border-red-500/20"
                >
                  {error}
                </motion.p>
              )}

              <div className="flex flex-col gap-4 pt-2">
                <Button
                  onClick={handleSubmit}
                  disabled={!accountType || loading}
                  variant="glass"
                  size="lg"
                  className="w-full py-7 rounded-2xl text-lg font-bold shadow-xl shadow-primary/10"
                >
                  {loading ? (
                    <div className="flex items-center gap-3">
                      <Loader2 className="w-5 h-5 animate-spin" /> Finalizing...
                    </div>
                  ) : (
                    "Complete Setup"
                  )}
                </Button>
                
                <button 
                  onClick={() => setStep(1)}
                  className="flex items-center justify-center gap-2 text-xs font-bold text-muted-foreground hover:text-white transition-colors py-2 uppercase tracking-tighter"
                  disabled={loading}
                >
                  <ChevronLeft className="w-4 h-4" /> Change Name
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Brand Footer */}
        <div className="mt-12 pt-8 border-t border-white/5 text-center">
          <p className="text-[10px] text-muted-foreground uppercase tracking-[0.2em] font-medium opacity-40">
            Powered by Fortress AI Intelligence
          </p>
        </div>
      </motion.div>
    </div>
  );
}
