"use client";

import Link from "next/link";
import { motion, type Variants } from "framer-motion";
import Header from "@/components/shared/Header";
import Footer from "@/components/shared/Footer";
import {
  ShieldCheck,
  Upload,
  Brain,
  FileCheck,
  BarChart3,
  Scale,
  FileText,
  Lock,
  Sparkles,
  ArrowRight,
  CheckCircle,
  Briefcase,
  User,
  Zap,
} from "lucide-react";

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.1, ease: "easeOut" as const },
  }),
};

const FEATURES = [
  { icon: ShieldCheck, title: "Verdict Engine", desc: "SIGN, NEGOTIATE, REJECT, or SEEK COUNSEL — an instant, clear recommendation." },
  { icon: BarChart3, title: "Risk Matrix", desc: "Visual risk distribution across Critical, High, Medium, and Low categories." },
  { icon: FileText, title: "Clause Analysis", desc: "Every clause examined against industry standards with suggested modifications." },
  { icon: Scale, title: "Dual Persona", desc: "Attorney mode with legal citations, or Individual mode with plain language." },
  { icon: Sparkles, title: "8 Contract Types", desc: "NDA, Lease, Employment, Freelance, Partnership, Vendor, Consulting, and more." },
  { icon: Lock, title: "Private & Secure", desc: "Documents are never stored. Analysis runs on isolated infrastructure." },
];

const STEPS = [
  { icon: Upload, title: "Upload", desc: "Drop your contract — PDF, DOCX, TXT, or photo." },
  { icon: Brain, title: "AI Analysis", desc: "4-stage pipeline: Parse → Extract → Assess → Report." },
  { icon: FileCheck, title: "Risk Report", desc: "Structured report with verdict, red flags, and actionable advice." },
];


export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 pt-16">
        {/* ─── HERO ──────────────────────────────────── */}
        <section className="relative min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center overflow-hidden">
          <div className="max-w-7xl mx-auto px-6 text-center relative z-10">
            <motion.div initial="hidden" animate="visible" variants={fadeUp} custom={0}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold mb-8">
              <Zap className="w-3.5 h-3.5" /> AI-Powered Legal Intelligence
            </motion.div>

            <motion.h1 initial="hidden" animate="visible" variants={fadeUp} custom={1}
              className="text-4xl sm:text-5xl md:text-7xl font-extrabold text-secondary tracking-tight leading-[1.1] mb-6">
              Contract Risk<br />
              <span className="bg-gradient-to-r from-primary via-blue-400 to-primary bg-clip-text text-transparent">Assessment</span>
            </motion.h1>

            <motion.p initial="hidden" animate="visible" variants={fadeUp} custom={2}
              className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
              Upload any contract. Get a professional risk report with verdict, clause analysis, and actionable recommendations — in seconds.
            </motion.p>

            <motion.div initial="hidden" animate="visible" variants={fadeUp} custom={3}
              className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/auth/signup" className="glass-button text-sm font-bold px-8 py-3.5 rounded-xl flex items-center gap-2 shadow-[0_0_30px_rgba(24,86,255,0.3)]">
                Start Free <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="/auth/login" className="glass-button-secondary text-sm font-semibold px-8 py-3.5 rounded-xl">
                Sign In
              </Link>
            </motion.div>
          </div>
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/20 rounded-full blur-[180px] -z-10" />
          <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-success/10 rounded-full blur-[150px] -z-10" />
        </section>

        {/* ─── HOW IT WORKS ──────────────────────────── */}
        <section className="py-24 relative">
          <div className="max-w-5xl mx-auto px-6">
            <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={fadeUp} custom={0} className="text-center mb-16">
              <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-primary mb-3">How It Works</p>
              <h2 className="text-3xl md:text-4xl font-extrabold text-secondary">Three steps to clarity</h2>
            </motion.div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {STEPS.map((step, i) => {
                const Icon = step.icon;
                return (
                  <motion.div key={step.title} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={fadeUp} custom={i + 1}
                    className="glass-panel rounded-2xl p-8 text-center relative group">
                    <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-5 group-hover:bg-primary/20 transition-colors">
                      <Icon className="w-6 h-6 text-primary" />
                    </div>
                    <span className="absolute top-4 right-4 text-xs font-mono font-bold text-muted-foreground">0{i + 1}</span>
                    <h3 className="text-lg font-bold text-secondary mb-2">{step.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{step.desc}</p>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ─── FEATURES ──────────────────────────────── */}
        <section id="features" className="py-24 relative">
          <div className="max-w-6xl mx-auto px-6">
            <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={fadeUp} custom={0} className="text-center mb-16">
              <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-primary mb-3">Features</p>
              <h2 className="text-3xl md:text-4xl font-extrabold text-secondary">Everything you need for contract clarity</h2>
            </motion.div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {FEATURES.map((f, i) => {
                const Icon = f.icon;
                return (
                  <motion.div key={f.title} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={fadeUp} custom={i * 0.5}
                    className="glass-panel glass-panel-hover rounded-xl p-6">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
                      <Icon className="w-5 h-5 text-primary" />
                    </div>
                    <h3 className="text-sm font-bold text-secondary mb-1.5">{f.title}</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ─── ATTORNEY vs INDIVIDUAL ──────────────── */}
        <section id="for-attorneys" className="py-24 relative">
          <div className="max-w-5xl mx-auto px-6">
            <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} variants={fadeUp} custom={0} className="text-center mb-16">
              <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-primary mb-3">Built for Everyone</p>
              <h2 className="text-3xl md:text-4xl font-extrabold text-secondary">Two modes. One powerful tool.</h2>
            </motion.div>
            <div className="grid md:grid-cols-2 gap-6">
              <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} custom={1} className="glass-panel rounded-2xl p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center"><Briefcase className="w-5 h-5 text-primary" /></div>
                  <div><h3 className="text-lg font-bold text-secondary">For Attorneys</h3><p className="text-xs text-muted-foreground">Professional-grade analysis</p></div>
                </div>
                <ul className="space-y-3">
                  {["Legal citations and statutory references", "Negotiation leverage points", "Redline-ready suggested language", "Client-sharable reports", "Industry benchmark comparisons"].map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-muted-foreground"><CheckCircle className="w-4 h-4 text-success mt-0.5 shrink-0" />{item}</li>
                  ))}
                </ul>
              </motion.div>
              <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} custom={2} className="glass-panel rounded-2xl p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 rounded-xl bg-success/10 border border-success/20 flex items-center justify-center"><User className="w-5 h-5 text-success" /></div>
                  <div><h3 className="text-lg font-bold text-secondary">For Individuals</h3><p className="text-xs text-muted-foreground">Clear, actionable guidance</p></div>
                </div>
                <ul className="space-y-3">
                  {["Plain English explanations", "\"What this means for you\" summaries", "\"When to hire a lawyer\" guidance", "Risk severity in simple terms", "Step-by-step action items"].map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-muted-foreground"><CheckCircle className="w-4 h-4 text-success mt-0.5 shrink-0" />{item}</li>
                  ))}
                </ul>
              </motion.div>
            </div>
          </div>
        </section>

        {/* ─── PRICING MENTION ─────────────────────── */}
        <section id="pricing" className="py-24 relative">
          <div className="max-w-4xl mx-auto px-6 text-center">
            <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} custom={0}>
              <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-primary mb-3">Pricing</p>
              <h2 className="text-3xl md:text-4xl font-extrabold text-secondary mb-4">Start free. Upgrade when ready.</h2>
              <p className="text-muted-foreground text-base max-w-lg mx-auto mb-8 leading-relaxed">
                Get 3 free contract analyses per month. Upgrade to Professional for unlimited reports, priority processing, and premium features.
              </p>
              <Link href="/auth/signup" className="glass-button inline-flex items-center gap-2 text-sm font-bold px-8 py-3.5 rounded-xl">
                Start Free <ArrowRight className="w-4 h-4" />
              </Link>
            </motion.div>
          </div>
        </section>


        {/* ─── FINAL CTA ───────────────────────────── */}
        <section className="py-28 relative overflow-hidden">
          <div className="max-w-3xl mx-auto px-6 text-center relative z-10">
            <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} custom={0}>
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 mb-8 shadow-[0_0_40px_rgba(24,86,255,0.2)]">
                <ShieldCheck className="w-8 h-8 text-primary" />
              </div>
              <h2 className="text-3xl md:text-4xl font-extrabold text-secondary mb-4">Ready to protect yourself?</h2>
              <p className="text-muted-foreground text-base max-w-md mx-auto mb-10 leading-relaxed">
                Don&apos;t sign another contract without understanding the risks. Start your free analysis today.
              </p>
              <Link href="/auth/signup" className="glass-button text-sm font-bold px-8 py-3.5 rounded-xl inline-flex items-center gap-2 shadow-[0_0_30px_rgba(24,86,255,0.3)]">
                Start Free <ArrowRight className="w-4 h-4" />
              </Link>
            </motion.div>
          </div>
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/5 to-transparent -z-10" />
        </section>
      </main>
      <Footer />
    </div>
  );
}
