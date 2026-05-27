// ─── User & Role ───────────────────────────────────────────

export type UserType = 'attorney' | 'individual';

// ─── Contract Types ────────────────────────────────────────

export type ContractType =
  // Tier 1 — Individual
  | 'residential_lease'
  | 'employment_agreement'
  | 'freelance_agreement'
  | 'nda_personal'
  // Tier 2 — Business
  | 'partnership_agreement'
  | 'vendor_agreement'
  | 'nda_business'
  | 'consulting_agreement'
  // Catch-all
  | 'other';

export const CONTRACT_TYPE_LABELS: Record<ContractType, string> = {
  residential_lease: 'Residential Lease',
  employment_agreement: 'Employment Agreement',
  freelance_agreement: 'Freelance / Contractor',
  nda_personal: 'NDA (Personal)',
  partnership_agreement: 'Partnership Agreement',
  vendor_agreement: 'Vendor / Service Agreement',
  nda_business: 'NDA (Business)',
  consulting_agreement: 'Consulting Agreement',
  other: 'Other Contract',
};

// ─── Risk Assessment ───────────────────────────────────────

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low';

export interface RiskItem {
  id: string;
  clause: string;
  section: string;
  level: RiskLevel;
  description: string;
  suggestion?: string;
  industryStandard?: string;
  originalText?: string;

  // Phase 2 fields
  page?: number;                    // Page number where section appears
  justification?: string;           // Detailed risk reasoning
  contract_text?: string;           // Specific contract language (replaces originalText)
  priority?: number;                // Priority ranking 1-5 (1 = most urgent)
  related_sections?: string[];      // Related section numbers
  clause_type?: string;             // Clause classification (payment, liability, etc.)
}

export interface RiskMatrix {
  critical: RiskItem[];
  high: RiskItem[];
  medium: RiskItem[];
  low: RiskItem[];
}

// ─── Report ────────────────────────────────────────────────

export type ReportVerdict = 'SIGN' | 'NEGOTIATE' | 'REJECT' | 'SEEK_COUNSEL';

export interface RedFlag {
  id: string;
  title: string;
  description: string;
  section: string;
  severity: RiskLevel;
}

export interface Recommendation {
  id: string;
  forAttorneys: string;
  forIndividuals: string;
}

export interface Appendix {
  glossary: { term: string; definition: string }[];
  legalReferences: { title: string; citation: string }[];
  benchmarks: { metric: string; value: string; comparison: string }[];
  evidence?: { section: string; page?: number; quote: string; title?: string }[];
  sources?: { title: string; url: string; type?: string }[];
}

export interface ContractReport {
  verdict: ReportVerdict;
  contractType: ContractType;
  executiveSummary: string;
  riskMatrix: RiskMatrix;
  redFlags: RedFlag[];
  recommendations: Recommendation[];
  appendix: Appendix;

  // Phase 2 fields
  validation?: {
    errors?: string[];
    coverage?: {
      total_sections: number;
      analyzed_sections: number;
      section_coverage_pct: number;
      key_clause_sections: number;
      covered_key_sections: number;
      key_clause_coverage_pct: number;
      missing_key_clauses?: Array<{
        section: string;
        title: string;
        type: string;
        page: number;
      }>;
    };
  };
}

// ─── Analysis Pipeline ─────────────────────────────────────

export type StepStatus = 'idle' | 'processing' | 'completed' | 'error';

export interface AnalysisStep {
  id: string;
  label: string;
  description: string;
  status: StepStatus;
}

// ─── Chat ──────────────────────────────────────────────────

export type MessageRole = 'user' | 'assistant' | 'system';

export interface Attachment {
  id: string;
  name: string;
  size: number;
  type: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  attachment?: Attachment;
  isStreaming?: boolean;
  /** Inline report rendered by the assistant */
  report?: ContractReport;
  /** Pipeline progress indicator */
  analysisSteps?: AnalysisStep[];
  /** Sources referenced by the message */
  sources?: { title: string; url: string }[];
}

export interface Conversation {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  messages: Message[];
  contractType?: ContractType;
  userType?: UserType;
  verdict?: ReportVerdict;
  isPinned?: boolean;
}

// ─── Attached Files Panel ──────────────────────────────────

export type AttachedFileSource = 'upload' | 'shared' | 'generated';

export interface AttachedFile {
  id: string;
  name: string;
  /** Human-readable size string, e.g. "16.46 KB" */
  size: string;
  /** MIME type, e.g. "image/png" */
  type: string;
  /** Data URL or remote URL for image previews */
  thumbnailUrl?: string;
  uploadedAt: Date;
  messageId?: string;
  source: AttachedFileSource;
}
