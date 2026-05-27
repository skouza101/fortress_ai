"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, Search, X } from "lucide-react";

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  domain: string;
  favicon?: string;
  date?: string;
}

interface SearchResultsPanelProps {
  query: string;
  onClose: () => void;
}

const RESULT_SETS: Record<string, SearchResult[]> = {
  employment: [
    {
      title: "Notice period rights: statutory minimums and contract terms",
      url: "https://www.gov.uk/redundancy-your-rights/notice-periods",
      domain: "GOV.UK",
      snippet: "Employees are usually entitled to a minimum notice period based on continuous service, but contract terms may provide a longer period.",
      date: "Mar 25, 2026",
      favicon: "https://www.google.com/s2/favicons?domain=gov.uk&sz=32",
    },
    {
      title: "Understanding notice periods at work",
      url: "https://www.acas.org.uk/notice-periods",
      domain: "Acas",
      snippet: "Guidance on statutory notice, contractual notice, payment in lieu of notice, and how employers should handle termination dates.",
      favicon: "https://www.google.com/s2/favicons?domain=acas.org.uk&sz=32",
    },
    {
      title: "Your notice period when resigning",
      url: "https://www.citizensadvice.org.uk/work/leaving-a-job/resigning/your-notice-period-when-resigning/",
      domain: "Citizens Advice",
      snippet: "Practical explanation of employee notice obligations, statutory minimums, and what to check before resigning.",
      favicon: "https://www.google.com/s2/favicons?domain=citizensadvice.org.uk&sz=32",
    },
    {
      title: "Contractual notice clauses in employment agreements",
      url: "https://www.landaulaw.co.uk/notice/",
      domain: "Landau Law",
      snippet: "Employment lawyers explain how contractual notice can exceed statutory notice and when long notice terms may be challenged.",
      favicon: "https://www.google.com/s2/favicons?domain=landaulaw.co.uk&sz=32",
    },
    {
      title: "Payment in lieu of notice: employer checklist",
      url: "https://www.xperthr.co.uk/tasks/payment-in-lieu-of-notice",
      domain: "XpertHR",
      snippet: "Checklist covering PILON clauses, tax treatment, garden leave, and documentation for termination payments.",
      favicon: "https://www.google.com/s2/favicons?domain=xperthr.co.uk&sz=32",
    },
    {
      title: "Long notice periods and enforceability",
      url: "https://www.lewissilkin.com/en/insights/notice-periods-employment-contracts",
      domain: "Lewis Silkin",
      snippet: "Discussion of when extended notice periods are commercially reasonable and how courts may evaluate proportionality.",
      favicon: "https://www.google.com/s2/favicons?domain=lewissilkin.com&sz=32",
    },
  ],
  contract: [
    {
      title: "Indemnity clauses: legal and commercial considerations",
      url: "https://www.acc.com/resource-library/indemnification-clauses-commercial-contracts",
      domain: "ACC",
      snippet: "Overview of drafting considerations for indemnity scope, defense control, third-party claims, and liability caps.",
      favicon: "https://www.google.com/s2/favicons?domain=acc.com&sz=32",
    },
    {
      title: "Limitation of liability clauses in commercial contracts",
      url: "https://www.lexisnexis.com/uk/lexispsl/commercial/document/391289/55KB-X9N1-F18B-70P2-00000-00/Limitation_of_liability_clauses",
      domain: "LexisNexis",
      snippet: "Practice note describing common liability carve-outs, aggregate caps, exclusions, and enforceability considerations.",
      favicon: "https://www.google.com/s2/favicons?domain=lexisnexis.com&sz=32",
    },
    {
      title: "Best practices for vendor agreement risk review",
      url: "https://www.contractscounsel.com/t/us/vendor-agreement",
      domain: "Contracts Counsel",
      snippet: "Common provisions to review in vendor contracts, including payment terms, data protection, termination, and warranties.",
      favicon: "https://www.google.com/s2/favicons?domain=contractscounsel.com&sz=32",
    },
    {
      title: "Contract risk management: practical controls",
      url: "https://www.worldcc.com/Resources/Blogs-and-Journals/Contracting-Excellence-Journal",
      domain: "WorldCC",
      snippet: "Guidance on operational controls that reduce downstream contract risk and improve negotiation consistency.",
      favicon: "https://www.google.com/s2/favicons?domain=worldcc.com&sz=32",
    },
    {
      title: "Termination for convenience clauses explained",
      url: "https://www.jdsupra.com/legalnews/termination-for-convenience-clauses-3089617/",
      domain: "JD Supra",
      snippet: "Legal analysis of termination rights, notice requirements, compensation, and drafting pitfalls in service contracts.",
      favicon: "https://www.google.com/s2/favicons?domain=jdsupra.com&sz=32",
    },
    {
      title: "Data processing agreements and vendor contracts",
      url: "https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/contracts-and-liabilities-between-controllers-and-processors/",
      domain: "ICO",
      snippet: "Regulatory guidance on controller-processor contract requirements, audit rights, sub-processors, and security obligations.",
      favicon: "https://www.google.com/s2/favicons?domain=ico.org.uk&sz=32",
    },
  ],
};

function pickResultSet(query: string): SearchResult[] {
  const lowerQuery = query.toLowerCase();

  if (/(employment|employee|notice|termination|dismissal|redundancy|pilon)/.test(lowerQuery)) {
    return RESULT_SETS.employment;
  }

  return RESULT_SETS.contract;
}

function fetchMockResults(query: string): Promise<SearchResult[]> {
  const baseResults = pickResultSet(query);
  const normalizedQuery = query.trim() || "contract risk";

  return new Promise((resolve) => {
    window.setTimeout(() => {
      resolve(
        baseResults.map((result, index) => ({
          ...result,
          title: index === 0 ? `${result.title} - ${normalizedQuery}` : result.title,
        }))
      );
    }, 450);
  });
}

export default function SearchResultsPanel({ query, onClose }: SearchResultsPanelProps) {
  const [searchState, setSearchState] = useState<{
    query: string;
    results: SearchResult[];
    loading: boolean;
  }>({
    query,
    results: [],
    loading: true,
  });

  useEffect(() => {
    let isMounted = true;

    fetchMockResults(query).then((nextResults) => {
      if (!isMounted) return;
      setSearchState({ query, results: nextResults, loading: false });
    });

    return () => {
      isMounted = false;
    };
  }, [query]);

  const loading = searchState.loading || searchState.query !== query;
  const results = searchState.query === query ? searchState.results : [];

  return (
    <motion.aside
      initial={{ x: 40, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 40, opacity: 0 }}
      transition={{ duration: 0.24, ease: "easeOut" }}
      className="h-full w-[min(400px,100vw)] shrink-0 overflow-hidden border-l border-white/10 bg-[#101114]/95 shadow-[-24px_0_60px_rgba(0,0,0,0.32)] backdrop-blur-xl"
      aria-label="Search results"
    >
      <div className="flex h-full flex-col">
        <header className="shrink-0 border-b border-white/10 px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-sm font-semibold text-secondary">
                <Search className="h-4 w-4 text-primary" />
                <span>{loading ? "Search results" : `Search ${results.length} results`}</span>
              </div>
              <p className="mt-1 truncate text-xs text-muted-foreground" title={query}>
                {query}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-white/10 hover:text-secondary"
              aria-label="Close search results"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-3 py-3">
          {loading ? (
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="animate-pulse rounded-lg px-2 py-2">
                  <div className="mb-3 flex items-center gap-2">
                    <div className="h-4 w-4 rounded bg-white/10" />
                    <div className="h-3 w-24 rounded bg-white/10" />
                  </div>
                  <div className="mb-2 h-4 w-11/12 rounded bg-white/10" />
                  <div className="mb-2 h-4 w-7/12 rounded bg-white/10" />
                  <div className="h-10 w-full rounded bg-white/[0.06]" />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-1">
              {results.map((result) => (
                <a
                  key={result.url}
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group block rounded-lg px-3 py-3 transition-colors hover:bg-white/[0.06]"
                >
                  <div className="mb-1.5 flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
                    {result.favicon ? (
                      <span
                        className="h-4 w-4 shrink-0 rounded-sm bg-white/10 bg-cover bg-center"
                        style={{ backgroundImage: `url(${result.favicon})` }}
                        aria-hidden="true"
                      />
                    ) : (
                      <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    )}
                    <span className="truncate font-medium text-white/70 group-hover:text-primary/90">
                      {result.domain}
                    </span>
                    {result.date && <span className="shrink-0 text-white/35">{result.date}</span>}
                  </div>
                  <h4 className="line-clamp-2 text-sm font-semibold leading-snug text-secondary transition-colors group-hover:text-primary">
                    {result.title}
                  </h4>
                  <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                    {result.snippet}
                  </p>
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.aside>
  );
}
