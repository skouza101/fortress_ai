"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { 
  Database, 
  FileText, 
  Search, 
  Play, 
  Info,
  ShieldCheck,
  Zap,
  LayoutDashboard,
  ExternalLink
} from "lucide-react";
import Header from "@/components/shared/Header";
import Footer from "@/components/shared/Footer";
import { useRouter } from "next/navigation";

interface CUADSample {
  id: string;
  title: string;
  content: string;
  full_content: string;
  source: string;
}

function isCUADSample(value: unknown): value is CUADSample {
  if (!value || typeof value !== "object") return false;

  const sample = value as Record<string, unknown>;
  return (
    typeof sample.id === "string" &&
    typeof sample.title === "string" &&
    typeof sample.content === "string" &&
    typeof sample.full_content === "string" &&
    typeof sample.source === "string"
  );
}

export default function BenchmarkPage() {
  const [samples, setSamples] = useState<CUADSample[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const router = useRouter();

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/datasets/cuad/samples?limit=10`)
      .then(async (res) => {
        const data: unknown = await res.json();
        if (!res.ok) {
          const detail = data && typeof data === "object" && "detail" in data
            ? String((data as { detail: unknown }).detail)
            : `Request failed with status ${res.status}`;
          throw new Error(detail);
        }
        return data;
      })
      .then(data => {
        setSamples(Array.isArray(data) ? data.filter(isCUADSample) : []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch samples:", err);
        setLoading(false);
      });
  }, []);

  const filteredSamples = samples.filter(s => 
    s.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    s.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const startAnalysis = (sample: CUADSample) => {
    // In a real app, we'd pass this content to the chat page via state or localStorage
    localStorage.setItem("fortress_pending_analysis", JSON.stringify({
      title: sample.title,
      content: sample.full_content,
      type: "cuad_sample"
    }));
    router.push("/chat");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 pt-24 pb-16">
        <div className="max-w-6xl mx-auto px-6">
          {/* ─── HEADER ───────────────────────────────── */}
          <div className="mb-12">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-[10px] font-bold uppercase tracking-widest mb-4"
            >
              <Database className="w-3 h-3" /> Benchmark Suite
            </motion.div>
            <motion.h1 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-4xl md:text-5xl font-extrabold text-secondary mb-4"
            >
              The Atticus Project: <span className="text-primary">CUAD</span>
            </motion.h1>
            <motion.p 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-muted-foreground text-lg max-w-2xl leading-relaxed"
            >
              Evaluate Fortress AI against the industry-standard Contract Understanding Atticus Dataset (CUAD). 
              Test our multi-agent pipeline on real-world expert-annotated legal contracts.
            </motion.p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* ─── INFO PANEL ─────────────────────────── */}
            <div className="lg:col-span-1 space-y-6">
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 }}
                className="glass-panel rounded-2xl p-6 border-primary/20 bg-primary/5"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                    <Info className="w-5 h-5 text-primary" />
                  </div>
                  <h3 className="font-bold text-secondary text-lg">About CUAD</h3>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                  CUAD is a curated dataset of 510 commercial contracts, annotated by legal experts with 13,000+ annotations across 41 label categories.
                </p>
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs text-secondary font-medium">
                    <ShieldCheck className="w-4 h-4 text-success" /> 510 Commercial Contracts
                  </div>
                  <div className="flex items-center gap-2 text-xs text-secondary font-medium">
                    <Zap className="w-4 h-4 text-warning" /> 41 Analysis Categories
                  </div>
                  <div className="flex items-center gap-2 text-xs text-secondary font-medium">
                    <FileText className="w-4 h-4 text-primary" /> Expert Annotated
                  </div>
                </div>
                <hr className="my-5 border-white/10" />
                <a 
                  href="https://www.atticusprojectai.org/cuad" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-center justify-between text-xs font-bold text-primary hover:underline"
                >
                  Official Dataset Page <ExternalLink className="w-3 h-3" />
                </a>
              </motion.div>

              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.4 }}
                className="glass-panel rounded-2xl p-6"
              >
                <h3 className="font-bold text-secondary mb-4 flex items-center gap-2">
                  <LayoutDashboard className="w-4 h-4 text-primary" /> How to use
                </h3>
                <ol className="space-y-4">
                  <li className="flex gap-3">
                    <span className="w-5 h-5 rounded-full bg-surface-lighter flex items-center justify-center text-[10px] font-bold shrink-0">1</span>
                    <p className="text-xs text-muted-foreground leading-normal">Browse the samples below and select a contract to analyze.</p>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-5 h-5 rounded-full bg-surface-lighter flex items-center justify-center text-[10px] font-bold shrink-0">2</span>
                    <p className="text-xs text-muted-foreground leading-normal">Fortress AI will run its 4-stage pipeline on the full text.</p>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-5 h-5 rounded-full bg-surface-lighter flex items-center justify-center text-[10px] font-bold shrink-0">3</span>
                    <p className="text-xs text-muted-foreground leading-normal">Compare results with expert benchmarks provided by Atticus.</p>
                  </li>
                </ol>
              </motion.div>
            </div>

            {/* ─── SAMPLE LIST ────────────────────────── */}
            <div className="lg:col-span-2 space-y-6">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input 
                  type="text" 
                  placeholder="Search samples by name or content..."
                  className="w-full h-12 bg-surface/40 border border-white/10 rounded-xl pl-11 pr-4 text-sm focus:border-primary/50 focus:ring-1 focus:ring-primary/20 outline-none transition-all backdrop-blur-sm"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-1 gap-4">
                {loading ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="h-48 glass-panel rounded-2xl animate-pulse" />
                  ))
                ) : filteredSamples.length > 0 ? (
                  filteredSamples.map((sample, i) => (
                    <motion.div 
                      key={sample.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.1 * i }}
                      className="glass-panel glass-panel-hover rounded-2xl p-6 group"
                    >
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="font-bold text-secondary text-lg group-hover:text-primary transition-colors">{sample.title}</h3>
                          <p className="text-[10px] font-mono text-muted-foreground mt-1 uppercase tracking-widest">{sample.source}</p>
                        </div>
                        <button 
                          onClick={() => startAnalysis(sample)}
                          className="flex items-center gap-2 px-4 py-2 bg-primary/10 hover:bg-primary text-primary hover:text-white rounded-xl text-xs font-bold transition-all border border-primary/20"
                        >
                          Run Audit <Play className="w-3 h-3 fill-current" />
                        </button>
                      </div>
                      <div className="bg-surface/50 rounded-xl p-4 border border-white/5 relative overflow-hidden">
                        <p className="text-xs text-muted-foreground leading-relaxed font-mono">
                          {sample.content}
                        </p>
                        <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-surface to-transparent" />
                      </div>
                    </motion.div>
                  ))
                ) : (
                  <div className="text-center py-20 glass-panel rounded-3xl">
                    <Database className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-20" />
                    <p className="text-muted-foreground">No samples found matching your search.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
