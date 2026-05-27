import Link from "next/link";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  FileText,
  Scale,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import Header from "@/components/shared/Header";
import Footer from "@/components/shared/Footer";

const PRINCIPLES = [
  {
    title: "Legal Judgment First",
    body: "Fortress AI is built around contract review workflows that lawyers and business teams already understand: issue spotting, clause context, severity, and next actions.",
    icon: Scale,
  },
  {
    title: "Evidence Over Guesswork",
    body: "Every review surface is designed to preserve document context, section references, sources, and reasoning trails so findings can be checked quickly.",
    icon: FileText,
  },
  {
    title: "Private By Default",
    body: "Contract analysis should be handled with the same care as the underlying agreement, with clear boundaries around uploads, processing, and user access.",
    icon: ShieldCheck,
  },
];

const METRICS = [
  { value: "4", label: "Audit stages" },
  { value: "41", label: "CUAD categories" },
  { value: "510", label: "Benchmark contracts" },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Header />

      <main className="flex-1 pt-24 pb-20">
        <section className="max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-10 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-[10px] font-bold uppercase tracking-widest mb-5">
                <Building2 className="w-3.5 h-3.5" />
                About Fortress AI
              </div>
              <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-secondary max-w-3xl">
                Contract intelligence for faster, clearer risk decisions.
              </h1>
              <p className="mt-6 text-base md:text-lg text-muted-foreground leading-relaxed max-w-2xl">
                Fortress AI helps attorneys, operators, and individuals review contracts with structured analysis, risk scoring, and practical explanations that make dense legal language easier to act on.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-3">
                <Link
                  href="/chat"
                  className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-primary text-white text-sm font-bold shadow-[0_0_24px_rgba(24,86,255,0.25)] hover:brightness-110 transition-all"
                >
                  Start Analysis
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/benchmarks"
                  className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl border border-white/10 bg-white/[0.03] text-secondary text-sm font-bold hover:bg-white/[0.07] transition-all"
                >
                  View Benchmarks
                </Link>
              </div>
            </div>

            <div className="glass-panel rounded-2xl p-6 border-primary/20 bg-primary/5">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-11 h-11 rounded-xl bg-primary/15 border border-primary/25 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-secondary">What We Build</h2>
                  <p className="text-xs text-muted-foreground">Structured contract review workflows</p>
                </div>
              </div>
              <div className="space-y-3">
                {[
                  "Multi-step document parsing and risk assessment",
                  "Plain-language explanations for individual signers",
                  "Attorney-grade issue summaries and exportable reports",
                  "Benchmark workflows based on public legal datasets",
                ].map((item) => (
                  <div key={item} className="flex gap-3 text-sm text-muted-foreground">
                    <CheckCircle2 className="w-4 h-4 text-success shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mt-16 border-y border-white/10 bg-white/[0.02]">
          <div className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-1 sm:grid-cols-3 gap-6">
            {METRICS.map((metric) => (
              <div key={metric.label}>
                <p className="text-3xl font-extrabold text-secondary">{metric.value}</p>
                <p className="text-xs font-mono uppercase tracking-wider text-muted-foreground mt-1">
                  {metric.label}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="max-w-6xl mx-auto px-6 mt-16">
          <div className="flex items-end justify-between gap-6 mb-8">
            <div>
              <div className="inline-flex items-center gap-2 text-[10px] font-bold text-primary uppercase tracking-widest mb-3">
                <Users className="w-3.5 h-3.5" />
                Operating Principles
              </div>
              <h2 className="text-2xl md:text-3xl font-extrabold text-secondary">
                Built for serious contract work.
              </h2>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PRINCIPLES.map((principle) => {
              const Icon = principle.icon;
              return (
                <article key={principle.title} className="glass-panel glass-panel-hover rounded-xl p-5">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-primary" />
                  </div>
                  <h3 className="text-sm font-bold text-secondary mb-2">{principle.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{principle.body}</p>
                </article>
              );
            })}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
