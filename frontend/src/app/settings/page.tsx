"use client";

import { useState, useEffect } from "react";
import { 
  User, 
  ArrowLeft, 
  Brain, 
  Sliders, 
  Save, 
  CheckCircle2
} from "lucide-react";
import Header from "@/components/shared/Header";
import Footer from "@/components/shared/Footer";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";

export default function SettingsPage() {
  const router = useRouter();
  const { data: session } = useSession();

  // User states
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [userRole, setUserRole] = useState("individual");

  // Analysis states
  const [defaultModel, setDefaultModel] = useState("fast");
  const [deepAnalysis, setDeepAnalysis] = useState(true);
  const [autoFlag, setAutoFlag] = useState(true);

  // Interface states
  const [compactMode, setCompactMode] = useState(false);
  const [soundNotify, setSoundNotify] = useState(true);


  // UI state
  const [isSaving, setIsSaving] = useState(false);
  const [showSuccessToast, setShowSuccessToast] = useState(false);
  const [activeTab, setActiveTab] = useState("general");

  // Load settings on mount
  useEffect(() => {
    if (session?.user) {
      setFullName(session.user.name || "Fortress User");
      setEmail(session.user.email || "");
      if ((session.user as any).userType) {
        setUserRole((session.user as any).userType);
      }
    }

    const saved = localStorage.getItem("fortress_app_settings");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.defaultModel) setDefaultModel(parsed.defaultModel);
        if (parsed.deepAnalysis !== undefined) setDeepAnalysis(parsed.deepAnalysis);
        if (parsed.autoFlag !== undefined) setAutoFlag(parsed.autoFlag);
        if (parsed.compactMode !== undefined) setCompactMode(parsed.compactMode);
        if (parsed.soundNotify !== undefined) setSoundNotify(parsed.soundNotify);
        if (parsed.userRole) setUserRole(parsed.userRole);
      } catch (e) {
        console.warn("Failed to load saved settings:", e);
      }
    }
  }, [session]);

  const handleSave = () => {
    setIsSaving(true);
    
    // Save locally
    const settings = {
      defaultModel,
      deepAnalysis,
      autoFlag,
      compactMode,
      soundNotify,
      userRole
    };
    
    localStorage.setItem("fortress_app_settings", JSON.stringify(settings));

    setTimeout(() => {
      setIsSaving(false);
      setShowSuccessToast(true);
      setTimeout(() => setShowSuccessToast(false), 3000);
    }, 800);
  };


  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden bg-[#0A0D14] text-[#E8EAED]">
      {/* Background Ambient Glows */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-[#E89558]/5 rounded-full blur-[100px] pointer-events-none" />

      <Header />

      <main className="flex-1 pt-24 pb-20 relative z-10">
        <div className="max-w-5xl mx-auto px-6">
          
          {/* Header Action Row */}
          <div className="flex items-center gap-3 mb-8">
            <button 
              onClick={() => router.back()} 
              className="p-2 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 text-muted-foreground hover:text-secondary transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <span className="text-[10px] font-bold text-primary uppercase tracking-[0.2em] bg-primary/10 px-2.5 py-1 rounded-full border border-primary/20 shadow-sm">
                System Customization
              </span>
              <h1 className="text-3xl font-extrabold tracking-tight mt-1 text-secondary">
                Fortress Settings
              </h1>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            
            {/* Tabs List */}
            <div className="md:col-span-1 space-y-1">
              {[
                { id: "general", label: "General", icon: User },
                { id: "analysis", label: "Analysis Engine", icon: Brain },
                { id: "interface", label: "Preferences", icon: Sliders },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                      isActive 
                        ? "bg-primary text-white shadow-[0_0_20px_rgba(24,86,255,0.25)] border border-primary/40" 
                        : "text-muted-foreground hover:text-secondary hover:bg-white/5 border border-transparent"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Tab Contents */}
            <div className="md:col-span-3">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
                className="glass-panel border-white/10 bg-surface/30 p-8 rounded-3xl backdrop-blur-xl relative"
              >
                {/* Visual accent glow inside card */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-2xl pointer-events-none" />

                {activeTab === "general" && (
                  <div className="space-y-6 animate-in fade-in duration-200">
                    <h2 className="text-xl font-bold text-secondary flex items-center gap-2 border-b border-white/5 pb-4">
                      <User className="w-5 h-5 text-primary" /> General Profile
                    </h2>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Full Name</label>
                        <input
                          type="text"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          className="w-full h-11 bg-white/[0.03] border border-white/10 rounded-xl px-4 text-sm focus:border-primary/50 focus:ring-1 focus:ring-primary/20 outline-none text-secondary transition-all"
                          placeholder="Your full name"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Email Address</label>
                        <input
                          type="email"
                          value={email}
                          disabled
                          className="w-full h-11 bg-white/[0.01] border border-white/5 rounded-xl px-4 text-sm outline-none text-muted-foreground cursor-not-allowed"
                          placeholder="your.email@example.com"
                        />
                      </div>
                    </div>

                    <div className="space-y-3 pt-2">
                      <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider block">Assessed User Role</label>
                      <p className="text-xs text-muted-foreground -mt-1 mb-4 leading-normal">
                        This adjusts recommendations tailored for individuals signing contracts versus lawyers auditing contracts.
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {[
                          { id: "individual", title: "Individual Signer", desc: "For freelancers, employees, or customers signing consumer/business terms." },
                          { id: "attorney", title: "Legal Professional", desc: "For attorneys, legal counsel, or risk auditors analyzing corporate contracts." },
                        ].map((role) => {
                          const isSelected = userRole === role.id;
                          return (
                            <button
                              key={role.id}
                              onClick={() => setUserRole(role.id)}
                              className={`text-left p-4 rounded-2xl border transition-all ${
                                isSelected 
                                  ? "border-primary bg-primary/5 text-secondary shadow-[inset_0_0_12px_rgba(24,86,255,0.08)]" 
                                  : "border-white/10 hover:border-white/20 hover:bg-white/[0.01] text-muted-foreground"
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1.5">
                                <span className={`text-sm font-bold ${isSelected ? "text-primary" : "text-secondary"}`}>{role.title}</span>
                                {isSelected && <div className="w-2 h-2 rounded-full bg-primary" />}
                              </div>
                              <span className="text-xs text-muted-foreground block leading-normal">{role.desc}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "analysis" && (
                  <div className="space-y-6">
                    <h2 className="text-xl font-bold text-secondary flex items-center gap-2 border-b border-white/5 pb-4">
                      <Brain className="w-5 h-5 text-primary" /> Analysis Engine Settings
                    </h2>

                    <div className="space-y-3">
                      <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider block">Default LLM Model</label>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {[
                          { id: "fast", title: "Fast Mode", model: "Gemini 3.5 Flash", speed: "Instant", accuracy: "Standard", desc: "High-speed parsing ideal for basic lookups and routine reviews." },
                          { id: "thinking", title: "Thinking Mode", model: "Gemini 3.1 Pro", speed: "5-10s", accuracy: "Superior", desc: "High-fidelity reasoning suitable for finding intricate liabilities and red flags." },
                        ].map((model) => {
                          const isSelected = defaultModel === model.id;
                          return (
                            <button
                              key={model.id}
                              onClick={() => setDefaultModel(model.id)}
                              className={`text-left p-4 rounded-2xl border transition-all relative overflow-hidden ${
                                isSelected 
                                  ? "border-primary bg-primary/5 text-secondary shadow-[inset_0_0_12px_rgba(24,86,255,0.08)]" 
                                  : "border-white/10 hover:border-white/20 hover:bg-white/[0.01] text-muted-foreground"
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className={`text-sm font-bold ${isSelected ? "text-primary" : "text-secondary"}`}>{model.title}</span>
                                {isSelected && <div className="w-2 h-2 rounded-full bg-primary" />}
                              </div>
                              <span className="text-[10px] font-mono text-muted-foreground font-bold tracking-wider uppercase block">{model.model}</span>
                              <p className="text-xs text-muted-foreground leading-normal mt-2 mb-4">{model.desc}</p>
                              
                              <div className="flex items-center gap-4 text-[10px] font-mono text-muted-foreground mt-auto pt-2 border-t border-white/5">
                                <div>Speed: <span className="text-secondary font-bold">{model.speed}</span></div>
                                <div>Accuracy: <span className="text-secondary font-bold">{model.accuracy}</span></div>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="space-y-4 pt-4 border-t border-white/5">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-sm font-bold text-secondary">High-Fidelity Multi-Step Auditing</h3>
                          <p className="text-xs text-muted-foreground mt-0.5 max-w-[450px]">
                            Enable multi-agent operational protocols (parsing, extraction, risk grading, and reporting) for heavy document analysis.
                          </p>
                        </div>
                        <button
                          onClick={() => setDeepAnalysis(!deepAnalysis)}
                          className={`w-11 h-6 rounded-full transition-all relative ${
                            deepAnalysis ? "bg-primary" : "bg-white/10"
                          }`}
                        >
                          <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-all ${
                            deepAnalysis ? "left-6" : "left-1"
                          }`} />
                        </button>
                      </div>

                      <div className="flex items-center justify-between pt-4 border-t border-white/5">
                        <div>
                          <h3 className="text-sm font-bold text-secondary">Automated Red Flag Check</h3>
                          <p className="text-xs text-muted-foreground mt-0.5 max-w-[450px]">
                            Instantly check critical liability lines (indemnification, warranty, notice periods) and prompt alerts.
                          </p>
                        </div>
                        <button
                          onClick={() => setAutoFlag(!autoFlag)}
                          className={`w-11 h-6 rounded-full transition-all relative ${
                            autoFlag ? "bg-primary" : "bg-white/10"
                          }`}
                        >
                          <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-all ${
                            autoFlag ? "left-6" : "left-1"
                          }`} />
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "interface" && (
                  <div className="space-y-6">
                    <h2 className="text-xl font-bold text-secondary flex items-center gap-2 border-b border-white/5 pb-4">
                      <Sliders className="w-5 h-5 text-primary" /> UI & Preferences
                    </h2>

                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-sm font-bold text-secondary">Compact Sidebar History</h3>
                        <p className="text-xs text-muted-foreground mt-0.5 max-w-[450px]">
                          Minimize vertical spacings in chat conversation list elements for higher density.
                        </p>
                      </div>
                      <button
                        onClick={() => setCompactMode(!compactMode)}
                        className={`w-11 h-6 rounded-full transition-all relative ${
                          compactMode ? "bg-primary" : "bg-white/10"
                        }`}
                      >
                        <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-all ${
                          compactMode ? "left-6" : "left-1"
                        }`} />
                      </button>
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t border-white/5">
                      <div>
                        <h3 className="text-sm font-bold text-secondary">Audio Sound Notifications</h3>
                        <p className="text-xs text-muted-foreground mt-0.5 max-w-[450px]">
                          Play a subtle tone when the deep risk audit finishes running in the background.
                        </p>
                      </div>
                      <button
                        onClick={() => setSoundNotify(!soundNotify)}
                        className={`w-11 h-6 rounded-full transition-all relative ${
                          soundNotify ? "bg-primary" : "bg-white/10"
                        }`}
                      >
                        <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-all ${
                          soundNotify ? "left-6" : "left-1"
                        }`} />
                      </button>
                    </div>

                    <div className="space-y-2 pt-4 border-t border-white/5">
                      <h3 className="text-sm font-bold text-secondary">Dark Mode & Appearance</h3>
                      <p className="text-xs text-muted-foreground max-w-[500px]">
                        Fortress AI runs on high-fidelity, high-contrast dark space glass modes. Light mode is currently disabled in developer beta.
                      </p>
                    </div>
                  </div>
                )}



                {/* Footer Save Row */}
                <div className="mt-8 pt-6 border-t border-white/5 flex justify-end">
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:brightness-110 disabled:opacity-50 text-white text-xs font-bold shadow-[0_0_20px_rgba(24,86,255,0.3)] transition-all cursor-pointer"
                  >
                    {isSaving ? (
                      <>
                        <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Saving...</span>
                      </>
                    ) : (
                      <>
                        <Save className="w-3.5 h-3.5" />
                        <span>Save Changes</span>
                      </>
                    )}
                  </button>
                </div>

              </motion.div>
            </div>

          </div>

        </div>
      </main>

      <Footer />

      {/* Success Toast */}
      <AnimatePresence>
        {showSuccessToast && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.95 }}
            className="fixed bottom-6 right-6 z-[100] flex items-center gap-2.5 px-4 py-3 rounded-xl bg-success/15 border border-success/30 backdrop-blur-xl text-success text-xs font-bold shadow-[0_10px_30px_rgba(7,202,107,0.15)] animate-in fade-in duration-300"
          >
            <CheckCircle2 className="w-4 h-4 text-success" />
            <span>Settings Saved Successfully!</span>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
