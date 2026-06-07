"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { PanelLeft, Upload, FileCheck } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import EmptyState from "@/components/EmptyState";
import AttachedFilesPanel from "@/components/AttachedFilesPanel";
import { motion, AnimatePresence } from "framer-motion";
import {
  Message,
  Conversation,
  ContractType,
  UserType,
  AnalysisStep,
  CONTRACT_TYPE_LABELS,
  AttachedFile,
  ContractReport,
  RiskItem,
  RedFlag,
  RiskLevel
} from "@/types";
import { conversationsApi, chatApi } from "@/lib/api";

function genId() {
  return Math.random().toString(36).substring(2, 11);
}

// ── Convert API conversation → frontend Conversation ─────────
function apiConvToLocal(api: import("@/lib/api").ApiConversation): Conversation {
  return {
    id: api.id,
    title: api.title,
    lastMessage: api.lastMessage,
    timestamp: new Date(api.timestamp),
    messages: (api.messages ?? []).map(apiMsgToLocal),
    contractType: api.contractType as ContractType | undefined,
    userType: api.userType as UserType | undefined,
    verdict: api.verdict as Conversation["verdict"],
    isPinned: api.isPinned,
  };
}

function apiMsgToLocal(m: import("@/lib/api").ApiMessage): Message {
  return {
    id: m.id,
    role: m.role as Message["role"],
    content: m.content,
    timestamp: new Date(m.timestamp),
    attachment: m.attachment
      ? { id: m.attachment.id, name: m.attachment.name, size: m.attachment.size, type: m.attachment.type }
      : undefined,
  };
}

// ── Parser to build ContractReport from backend output ───────
function parseBackendReport(riskAnalysis: any, contractType?: ContractType): ContractReport {
  const safeData = riskAnalysis || {};
  
  const mapSeverityToRiskLevel = (sev: string): RiskLevel => {
    const s = (sev || "").toLowerCase();
    if (s.includes("crit") || s.includes("high")) return "high"; // backend only has High/Med/Low typically
    if (s.includes("med")) return "medium";
    return "low";
  };

  const rawFindings = Array.isArray(safeData.findings) ? safeData.findings : [];
  const rawRedFlags = Array.isArray(safeData.red_flags) ? safeData.red_flags : [];
  const rawPenalties = Array.isArray(safeData.penalties) ? safeData.penalties : [];
  const rawObligations = Array.isArray(safeData.obligations) ? safeData.obligations : [];

  const normalizeSection = (value: unknown): string => {
    const text = String(value || "").trim();
    if (!text || /^general$/i.test(text)) return "Unknown";
    return text;
  };

  const isPlaceholderFinding = (f: any): boolean => {
    const title = String(f?.title || "").trim().toLowerCase();
    const justification = String(f?.justification || "").trim().toLowerCase();
    const section = normalizeSection(f?.section).toLowerCase();
    if (section !== "unknown") return false;

    if (title === "obligation" || title === "risk issue" || title === "identified risk") {
      return true;
    }

    if (justification === "potential liability or violation found." || justification === "") {
      return true;
    }

    return false;
  };

  const usableFindings = rawFindings.filter((f: any) => !isPlaceholderFinding(f));

  const parsedRedFlags: RedFlag[] = usableFindings
    .filter((f: any) => {
      const level = mapSeverityToRiskLevel(f.risk || f.severity || "");
      return level === "high" || level === "critical";
    })
    .map((f: any, i: number) => ({
      id: `rf-${i}`,
      title: f.title || "Identified Risk",
      description: f.justification || f.description || "Potential liability or violation found.",
      section: normalizeSection(f.section),
      severity: mapSeverityToRiskLevel(f.risk || f.severity),
    }));

  // Backward compatibility: if no findings are available, use legacy red_flags array.
  if (parsedRedFlags.length === 0 && usableFindings.length === 0) {
    parsedRedFlags.push(
      ...rawRedFlags.map((rf: any, i: number) => ({
        id: `rf-${i}`,
        title: rf.issue || "Identified Risk",
        description: rf.description || "Potential liability or violation found.",
        section: normalizeSection(rf.section),
        severity: mapSeverityToRiskLevel(rf.severity),
      }))
    );
  }

  const parsedRiskMatrix = {
    critical: [] as RiskItem[],
    high: [] as RiskItem[],
    medium: [] as RiskItem[],
    low: [] as RiskItem[],
  };

  // Prefer structured findings from backend.
  let itemCounter = 0;
  usableFindings.forEach((item: any) => {
    const level = mapSeverityToRiskLevel(item.risk || item.severity || "medium");
    const riskItem: RiskItem = {
      id: `ri-${itemCounter++}`,
      clause: item.title || item.issue || item.task || "Risk Issue",
      section: normalizeSection(item.section),
      level,
      description: item.justification || item.description || item.impact || "Potential liability or violation found.",
      page: item.page,
      contract_text: item.contract_text,
      recommendation: item.recommendation,
      priority: item.priority,
      related_sections: Array.isArray(item.related_sections) ? item.related_sections : undefined,
      clause_type: item.clause_type,
    };

    if (level === "critical") parsedRiskMatrix.critical.push(riskItem);
    else if (level === "high") parsedRiskMatrix.high.push(riskItem);
    else if (level === "medium") parsedRiskMatrix.medium.push(riskItem);
    else parsedRiskMatrix.low.push(riskItem);
  });

  // Backward compatibility when findings are absent.
  if (usableFindings.length === 0) {
    [...rawPenalties, ...rawObligations, ...rawRedFlags].forEach((item: any) => {
      const level = mapSeverityToRiskLevel(item.severity || "medium");
      const riskItem: RiskItem = {
        id: `ri-${itemCounter++}`,
        clause: item.title || item.issue || item.type || item.task || "Risk Issue",
        section: normalizeSection(item.section || (item.deadline ? `Deadline: ${item.deadline}` : "Unknown")),
        level,
        description: item.justification || item.description || item.impact || "Potential liability or violation found.",
      };

      if (level === "critical") parsedRiskMatrix.critical.push(riskItem);
      else if (level === "high") parsedRiskMatrix.high.push(riskItem);
      else if (level === "medium") parsedRiskMatrix.medium.push(riskItem);
      else parsedRiskMatrix.low.push(riskItem);
    });
  }

  // Calculate verdict based on red flags
  const verdict = parsedRedFlags.length > 2 || parsedRiskMatrix.high.length > 2 
    ? "SEEK_COUNSEL" 
    : parsedRedFlags.length > 0 ? "NEGOTIATE" : "SIGN";

  const topFinding = usableFindings[0];
  const recForAttorneys = topFinding?.recommendation
    ? `Prioritize revisions for ${normalizeSection(topFinding.section)} and validate enforceability of the proposed changes.`
    : "Review the identified high-severity clauses and ensure indemnification caps are appropriate.";

  const recForIndividuals = topFinding?.recommendation
    ? topFinding.recommendation
    : "Consider asking for clarification on the highlighted red flags before signing.";

  return {
    verdict,
    contractType: contractType || "other",
    executiveSummary: safeData.summary || "The contract has been analyzed. See the risk matrix and red flags below.",
    riskMatrix: parsedRiskMatrix,
    redFlags: parsedRedFlags,
    recommendations: [
      {
        id: "rec-1",
        forAttorneys: recForAttorneys,
        forIndividuals: recForIndividuals,
      }
    ],
    appendix: {
      glossary: [],
      legalReferences: [],
      benchmarks: [],
    },
  };
}

// ────────────────────────────────────────────────────────────
// Main Page
// ────────────────────────────────────────────────────────────
export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const chatId = params.id as string;

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(chatId);
  const [isStreaming, setIsStreaming] = useState(false);
  const [userType, setUserType] = useState<UserType>("individual");
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleStop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const messages = activeConversation?.messages ?? [];

  // ── Scroll to bottom on new messages ───────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Sync activeConversationId with URL ──────────────────────
  useEffect(() => {
    if (chatId && chatId !== activeConversationId) {
      setActiveConversationId(chatId);
      handleSelectConversation(chatId);
    }
  }, [chatId]);

  // ── Load conversations from backend on mount ────────────────
  useEffect(() => {
    conversationsApi.list().then((list) => {
      setConversations((prev) => {
        return list.map((apiConv) => {
          const local = apiConvToLocal(apiConv);
          const existing = prev.find((p) => p.id === local.id);
          if (existing && existing.messages.length > 0) {
            local.messages = existing.messages;
          }
          return local;
        });
      });
    }).catch(console.error);
  }, []);

  // ── Local helpers ───────────────────────────────────────────
  const updateConversation = useCallback(
    (id: string, updater: (c: Conversation) => Conversation) => {
      setConversations((prev) => prev.map((c) => (c.id === id ? updater(c) : c)));
    },
    []
  );

  const addMessage = useCallback(
    (convId: string, msg: Message) => {
      updateConversation(convId, (c) => ({
        ...c,
        messages: [...c.messages, msg],
        lastMessage: msg.content.slice(0, 60),
        timestamp: new Date(),
      }));
    },
    [updateConversation]
  );

  const updateMessage = useCallback(
    (convId: string, msgId: string, updates: Partial<Message>) => {
      updateConversation(convId, (c) => ({
        ...c,
        messages: c.messages.map((m) => (m.id === msgId ? { ...m, ...updates } : m)),
      }));
    },
    [updateConversation]
  );

  // ── Select a conversation — load messages from backend ──────
  const handleSelectConversation = useCallback(
    async (id: string) => {
      if (id !== chatId) {
        router.push(`/chat/${id}`);
        return;
      }
      
      setActiveConversationId(id);
      // If we already have messages locally, no need to refetch
      const existing = conversations.find((c) => c.id === id);
      if (existing && existing.messages.length > 0) return;

      try {
        const full = await conversationsApi.get(id);
        setConversations((prev) =>
          prev.map((c) => (c.id === id ? apiConvToLocal(full) : c))
        );
      } catch (err) {
        console.error("Failed to load conversation:", err);
      }
    },
    [conversations, chatId, router]
  );

  // ── Create new conversation ─────────────────────────────────
  const createNewChat = useCallback(async () => {
    try {
      const api = await conversationsApi.create({ title: "New Analysis" });
      const conv = apiConvToLocal(api);
      setConversations((prev) => [conv, ...prev]);
      router.push(`/chat/${conv.id}`);
    } catch {
      // Fallback: local-only conversation
      const id = genId();
      const newConv: Conversation = {
        id, title: "New Analysis", lastMessage: "", timestamp: new Date(), messages: [],
      };
      setConversations((prev) => [newConv, ...prev]);
      router.push(`/chat/${id}`);
    }
  }, [router]);

  // ── Global hotkeys ─────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); createNewChat(); }
      if ((e.metaKey || e.ctrlKey) && e.key === "b") { e.preventDefault(); setIsSidebarOpen((p) => !p); }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [createNewChat]);

  // ── Run the full audit pipeline (SSE) ───────────────────────
  const runAnalysis = useCallback(
    async (convId: string, contractType: ContractType, _fileName: string) => {
      const steps: AnalysisStep[] = [
        { id: "parsing",    label: "Document Parsing",  description: "Analyzing document structure",        status: "idle" },
        { id: "extraction", label: "Clause Extraction", description: "Identifying key clauses",             status: "idle" },
        { id: "risk",       label: "Risk Analysis",     description: "Evaluating risk levels",              status: "idle" },
        { id: "report",     label: "Report Generation", description: "Synthesizing assessment report",      status: "idle" },
      ];

      const progressMsgId = genId();
      addMessage(convId, {
        id: progressMsgId, role: "assistant", content: "", timestamp: new Date(),
        analysisSteps: [...steps],
      });

      setIsStreaming(true);
      const reportMsgId = genId();
      let reportContent = "";
      let reportMsgAdded = false;

      try {
        abortControllerRef.current = new AbortController();
        for await (const event of chatApi.audit({
          message: "Please analyze this contract.",
          conversation_id: convId,
          user_type: userType,
          contract_type: contractType,
        }, abortControllerRef.current.signal)) {
          const ev = event.event as string;
          const data = event.data as Record<string, unknown>;

          if (ev === "steps_init") {
            // Backend sent canonical step list — use it
            const backendSteps = data.steps as Array<{id: string; label: string; description: string}>;
            const fresh = backendSteps.map((s) => ({ ...s, status: "idle" as const }));
            updateMessage(convId, progressMsgId, { analysisSteps: fresh });
          } else if (ev === "step_update") {
            const stepId = data.step_id as string;
            const status = data.status as AnalysisStep["status"];
            updateMessage(convId, progressMsgId, {
              analysisSteps: steps.map((s) => s.id === stepId ? { ...s, status } : s),
            });
            // Keep local steps in sync for next iteration
            const idx = steps.findIndex((s) => s.id === stepId);
            if (idx !== -1) steps[idx].status = status;
          } else if (ev === "content_chunk") {
            const chunk = data.chunk as string;
            reportContent += chunk;
            // Add or update the report message (streamed markdown)
            if (!reportMsgAdded) {
              addMessage(convId, {
                id: reportMsgId, role: "assistant", content: reportContent,
                timestamp: new Date(), isStreaming: true,
              });
              reportMsgAdded = true;
            } else {
              updateMessage(convId, reportMsgId, { content: reportContent, isStreaming: true });
            }
          } else if (ev === "done") {
            const riskAnalysis = data.risk_analysis as any;
            const backendReport = typeof data.report === "string" ? data.report : "";
            const hasStructuredFindings = Array.isArray(riskAnalysis?.findings) && riskAnalysis.findings.length > 0;

            if (hasStructuredFindings) {
              const contractReport = parseBackendReport(riskAnalysis, contractType);
              updateMessage(convId, reportMsgId, {
                isStreaming: false,
                report: contractReport,
              });
            } else {
              updateMessage(convId, reportMsgId, {
                content: backendReport || reportContent || "Analysis completed, but no structured report was returned.",
                isStreaming: false,
              });
            }
            updateConversation(convId, (c) => ({ ...c, contractType }));
          } else if (ev === "error") {
            const errMsg = data.message as string;
            addMessage(convId, {
              id: genId(), role: "assistant",
              content: `⚠️ Analysis error: ${errMsg}`,
              timestamp: new Date(),
            });
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError' || err.message.includes('abort')) {
          addMessage(convId, {
            id: genId(), role: "assistant",
            content: `*Analysis stopped by user.*`,
            timestamp: new Date(),
          });
        } else {
          addMessage(convId, {
            id: genId(), role: "assistant",
            content: `⚠️ Failed to connect to analysis service. Please ensure the backend is running.\n\n\`\`\`\n${err}\n\`\`\``,
            timestamp: new Date(),
          });
        }
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [addMessage, updateMessage, updateConversation, userType]
  );

  // ── Handle pending analysis (from Benchmarks page) ──────────
  useEffect(() => {
    const pending = localStorage.getItem("fortress_pending_analysis");
    if (pending) {
      localStorage.removeItem("fortress_pending_analysis");
      const { title, content } = JSON.parse(pending);
      
      const startPending = async () => {
        try {
          const api = await conversationsApi.create({ title });
          const conv = apiConvToLocal(api);
          setConversations((prev) => [conv, ...prev]);
          setActiveConversationId(conv.id);
          
          // Add user message
          addMessage(conv.id, {
            id: genId(), role: "user", content: `Analyze this CUAD contract: ${title}\n\n${content.slice(0, 500)}...`,
            timestamp: new Date()
          });

          // In a real app, we'd upload this content or send it as a special message
          // For now, let's just trigger the analysis on the backend (mocked for demo)
          setTimeout(() => runAnalysis(conv.id, "vendor_agreement", title), 1000);
        } catch (err) {
          console.error("Failed to start pending analysis:", err);
        }
      };
      startPending();
    }
  }, [addMessage, runAnalysis]);

  // ── Remove attached file ────────────────────────────────────
  const handleRemoveFile = useCallback((id: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  // ── Register a file into the panel ─────────────────────────
  const registerFile = useCallback(
    (file: File, msgId: string, thumbnailUrl?: string) => {
      const kb = file.size / 1024;
      const size = kb < 1024 ? `${kb.toFixed(2)} KB` : `${(kb / 1024).toFixed(2)} MB`;
      setAttachedFiles((prev) => [
        {
          id: genId(), name: file.name, size, type: file.type,
          thumbnailUrl, uploadedAt: new Date(), messageId: msgId, source: "upload" as const,
        },
        ...prev,
      ]);
    },
    []
  );

  // ── Handle file selection (Attach only, don't send) ─────────
  const handleAttachFiles = useCallback((files: File[]) => {
    setPendingFiles((prev) => [...prev, ...files]);
  }, []);

  // ── Handle contract type chip click ────────────────────────
  const handleContractTypeHint = useCallback(
    async (type: ContractType) => {
      let convId = activeConversationId;
      const title = CONTRACT_TYPE_LABELS[type];

      if (!convId) {
        try {
          const api = await conversationsApi.create({ title, contract_type: type });
          const conv = apiConvToLocal(api);
          setConversations((prev) => [conv, ...prev]);
          setActiveConversationId(conv.id);
          convId = conv.id;
        } catch {
          const newConv: Conversation = {
            id: genId(), title, lastMessage: "", timestamp: new Date(),
            messages: [], contractType: type,
          };
          setConversations((prev) => [newConv, ...prev]);
          setActiveConversationId(newConv.id);
          convId = newConv.id;
        }
      }

      addMessage(convId, {
        id: genId(), role: "user",
        content: `I want to analyze a ${CONTRACT_TYPE_LABELS[type]}.`,
        timestamp: new Date(),
      });

      // Stream response so users see partial output immediately.
      try {
        setIsStreaming(true);
        const assistantMsgId = genId();
        let accumulated = "";
        let started = false;
        abortControllerRef.current = new AbortController();

        for await (const event of chatApi.stream({
          message: `I want to analyze a ${CONTRACT_TYPE_LABELS[type]}.`,
          conversation_id: convId,
          user_type: userType,
          contract_type: type,
        }, abortControllerRef.current.signal)) {
          const ev = event.event as string;

          if (ev === "start") {
            addMessage(convId!, {
              id: assistantMsgId,
              role: "assistant",
              content: "",
              timestamp: new Date(),
              isStreaming: true,
            });
            started = true;
          } else if (ev === "chunk") {
            if (!started) {
              addMessage(convId!, {
                id: assistantMsgId,
                role: "assistant",
                content: "",
                timestamp: new Date(),
                isStreaming: true,
              });
              started = true;
            }
            accumulated += (event.content as string) ?? "";
            updateMessage(convId!, assistantMsgId, {
              content: accumulated,
              isStreaming: true,
            });
          } else if (ev === "done") {
            updateMessage(convId!, assistantMsgId, { isStreaming: false });
          } else if (ev === "error") {
            updateMessage(convId!, assistantMsgId, {
              content: `⚠️ ${event.message as string}`,
              isStreaming: false,
            });
          }
        }
      } catch {
        // Fallback local message
        setTimeout(() => {
          addMessage(convId!, {
            id: genId(), role: "assistant",
            content: `Great! Please upload your **${CONTRACT_TYPE_LABELS[type]}** document using the 📎 button below, or drag and drop it into the chat.\n\nI'll analyze it and generate a complete **Contract Risk Assessment Report** with:\n- ✅ Verdict (Sign / Negotiate / Reject)\n- 📊 Risk matrix\n- 📄 Clause-by-clause analysis\n- 🚩 Red flags\n- 💡 Recommendations tailored to your role`,
            timestamp: new Date(),
          });
        }, 600);
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [activeConversationId, addMessage, userType, updateMessage]
  );

  // ── Handle chat message send (handles both text and files) ──
  const handleSend = useCallback(
    async (content: string, files?: File[]) => {
      let convId = activeConversationId;
      const firstFile = files?.[0];
      const title = firstFile ? firstFile.name.replace(/\.[^/.]+$/, "").slice(0, 35) : (content.slice(0, 50) || "New Analysis");

      if (!convId) {
        try {
          const api = await conversationsApi.create({ title });
          const conv = apiConvToLocal(api);
          setConversations((prev) => [conv, ...prev]);
          setActiveConversationId(conv.id);
          convId = conv.id;
        } catch {
          const newConv: Conversation = {
            id: genId(), title, lastMessage: "", timestamp: new Date(), messages: [],
          };
          setConversations((prev) => [newConv, ...prev]);
          setActiveConversationId(newConv.id);
          convId = newConv.id;
        }
      } else if (firstFile) {
        updateConversation(convId, (c) => ({ ...c, title }));
      }

      if (files && files.length > 0) {
        let effectiveConvId = convId!;
        let failedUploads = 0;

        // Register all files in panel and send messages
        for (const file of files) {
          const msgId = genId();
          if (file.type.startsWith("image/")) {
            const reader = new FileReader();
            reader.onload = (ev) => registerFile(file, msgId, ev.target?.result as string);
            reader.readAsDataURL(file);
          } else {
            registerFile(file, msgId);
          }

          addMessage(effectiveConvId, {
            id: msgId, role: "user",
            content: content || `Analyze this contract: ${file.name}`,
            timestamp: new Date(),
            attachment: { id: genId(), name: file.name, size: file.size, type: file.type },
          });

          try {
            await chatApi.upload(file, effectiveConvId);
          } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            const isMissingConversation =
              message.includes("Conversation not found") || message.includes("404");

            if (isMissingConversation) {
              try {
                const api = await conversationsApi.create({ title });
                const conv = apiConvToLocal(api);
                setConversations((prev) => [conv, ...prev]);
                setActiveConversationId(conv.id);
                effectiveConvId = conv.id;

                // Retry once with a fresh conversation id.
                await chatApi.upload(file, effectiveConvId);
              } catch (retryErr) {
                failedUploads += 1;
                console.warn(`File upload retry failed for ${file.name}:`, retryErr);
              }
            } else {
              failedUploads += 1;
              console.warn(`File upload failed for ${file.name}:`, err);
            }
          }
        }

        if (failedUploads >= files.length) {
          addMessage(effectiveConvId, {
            id: genId(),
            role: "assistant",
            content: "⚠️ Upload failed. The target conversation may have been deleted or expired. Please try again.",
            timestamp: new Date(),
          });
          return;
        }

        // Trigger analysis for the batch
        setIsStreaming(true);
        addMessage(effectiveConvId, {
          id: genId(), role: "assistant",
          content: `I've received **${files.length}** document(s). Starting multi-step legal audit...`,
          timestamp: new Date(),
        });
        runAnalysis(effectiveConvId, "vendor_agreement", firstFile!.name);
        return;
      }

      // Add user message locally
      addMessage(convId, {
        id: genId(), role: "user", content, timestamp: new Date(),
      });

      setIsStreaming(true);
      const assistantMsgId = genId();
      let accumulated = "";

      try {
        let started = false;
        abortControllerRef.current = new AbortController();

        for await (const event of chatApi.stream({
          message: content,
          conversation_id: convId,
          user_type: userType,
          contract_type: activeConversation?.contractType,
        }, abortControllerRef.current.signal)) {
          const ev = event.event as string;

          if (ev === "start") {
            addMessage(convId!, {
              id: assistantMsgId, role: "assistant",
              content: "", timestamp: new Date(), isStreaming: true,
            });
            started = true;
          } else if (ev === "chunk") {
            if (!started) {
              addMessage(convId!, {
                id: assistantMsgId, role: "assistant",
                content: "", timestamp: new Date(), isStreaming: true,
              });
              started = true;
            }
            accumulated += (event.content as string) ?? "";
            updateMessage(convId!, assistantMsgId, {
              content: accumulated,
              isStreaming: true,
            });
          } else if (ev === "done") {
            updateMessage(convId!, assistantMsgId, { isStreaming: false });
          } else if (ev === "error") {
            updateMessage(convId!, assistantMsgId, {
              content: `⚠️ ${event.message as string}`,
              isStreaming: false,
            });
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError' || err.message.includes('abort')) {
           updateMessage(convId!, assistantMsgId, {
              isStreaming: false,
           });
        } else {
          addMessage(convId!, {
            id: genId(), role: "assistant",
            content: `⚠️ Connection error. Is the backend running?\n\n\`${err}\``,
            timestamp: new Date(),
          });
        }
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [
      activeConversationId, addMessage, updateMessage, updateConversation,
      userType, activeConversation, registerFile, runAnalysis
    ]
  );

  // ── Handle export request ───────────────────────────────────
  const handleExportRequest = useCallback(
    (format: "pdf" | "docx") => {
      if (!activeConversationId) return;
      const ext = format;
      const fname = `Fortress_AI_Report.${ext}`;
      addMessage(activeConversationId, {
        id: genId(), role: "assistant",
        content: `Your report has been exported as **${format.toUpperCase()}**. Click below to download.`,
        timestamp: new Date(),
        attachment: { id: genId(), name: fname, size: 245760, type: "download" },
      });
      setAttachedFiles((prev) => [
        {
          id: genId(), name: fname, size: "240 KB",
          type: format === "pdf" ? "application/pdf" : "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          uploadedAt: new Date(), source: "generated" as const,
        },
        ...prev,
      ]);
    },
    [activeConversationId, addMessage]
  );

  // ── Delete conversation ─────────────────────────────────────
  const handleDelete = useCallback(
    async (id: string) => {
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) setActiveConversationId(null);
      try {
        await conversationsApi.delete(id);
      } catch (err) {
        console.warn("Backend delete failed:", err);
      }
    },
    [activeConversationId]
  );

  // ── Rename conversation ─────────────────────────────────────
  const handleRename = useCallback(
    async (id: string, currentName: string) => {
      const newName = prompt("Edit Chat Name", currentName);
      if (!newName?.trim()) return;
      updateConversation(id, (c) => ({ ...c, title: newName.trim() }));
      try {
        await conversationsApi.update(id, { title: newName.trim() });
      } catch (err) {
        console.warn("Backend rename failed:", err);
      }
    },
    [updateConversation]
  );

  // ── Pin/Unpin conversation ──────────────────────────────────
  const handlePin = useCallback(
    async (id: string) => {
      const conv = conversations.find((c) => c.id === id);
      const newPinned = !conv?.isPinned;
      updateConversation(id, (c) => ({ ...c, isPinned: newPinned }));
      try {
        await conversationsApi.update(id, { is_pinned: newPinned });
      } catch (err) {
        console.warn("Backend pin failed:", err);
      }
    },
    [conversations, updateConversation]
  );

  const hasMessages = messages.length > 0;
  const contractType = activeConversation?.contractType;

  const sortedConversations = [...conversations].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return b.timestamp.getTime() - a.timestamp.getTime();
  });

  return (
    <div 
      className="flex h-full min-h-screen overflow-hidden relative"
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) handleAttachFiles(files);
      }}
    >
      {/* Drag Overlay */}
      <AnimatePresence>
        {isDragging && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-[100] bg-surface/40 backdrop-blur-[20px] flex items-center justify-center transition-all"
          >
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="relative bg-surface/80 border border-white/20 rounded-[48px] p-16 flex flex-col items-center gap-8 shadow-[0_0_80px_rgba(0,0,0,0.4),0_0_40px_rgba(24,86,255,0.1)] max-w-lg w-full mx-4 overflow-hidden group"
            >
              {/* Background Glow */}
              <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
              
              <div className="relative">
                <motion.div 
                  animate={{ 
                    scale: [1, 1.2, 1],
                    opacity: [0.3, 0.1, 0.3],
                    rotate: [0, 90, 180, 270, 360]
                  }}
                  transition={{ repeat: Infinity, duration: 8, ease: "linear" }}
                  className="absolute -inset-12 bg-primary/20 rounded-full blur-[60px]"
                />
                
                <div className="relative w-24 h-24 rounded-[32px] bg-primary/10 border border-primary/30 flex items-center justify-center shadow-[inset_0_0_20px_rgba(24,86,255,0.1)] group-hover:scale-110 transition-transform duration-500">
                  <Upload className="w-12 h-12 text-primary animate-bounce" />
                </div>
              </div>
              
              <div className="text-center relative z-10">
                <h3 className="text-3xl font-extrabold text-secondary mb-3 tracking-tight">
                  Ready to Analyze
                </h3>
                <p className="text-muted-foreground text-base leading-relaxed max-w-[280px] mx-auto">
                  Drop your legal document anywhere to start the high-fidelity risk assessment.
                </p>
              </div>

              <div className="flex items-center gap-4 text-[10px] font-mono font-bold text-primary uppercase tracking-[0.2em] bg-primary/10 px-6 py-2.5 rounded-full border border-primary/20 shadow-sm">
                <FileCheck className="w-4 h-4" />
                Secure Analysis Channel
              </div>

              {/* Corner Accents */}
              <div className="absolute top-0 left-0 w-16 h-16 border-t-2 border-l-2 border-primary/30 rounded-tl-[48px]" />
              <div className="absolute top-0 right-0 w-16 h-16 border-t-2 border-r-2 border-primary/30 rounded-tr-[48px]" />
              <div className="absolute bottom-0 left-0 w-16 h-16 border-b-2 border-l-2 border-primary/30 rounded-bl-[48px]" />
              <div className="absolute bottom-0 right-0 w-16 h-16 border-b-2 border-r-2 border-primary/30 rounded-br-[48px]" />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {isSidebarOpen && (
        <Sidebar
          conversations={sortedConversations}
          activeConversationId={activeConversationId}
          onNewChat={createNewChat}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDelete}
          onRenameConversation={handleRename}
          onPinConversation={handlePin}
          onToggleSidebar={() => setIsSidebarOpen(false)}
          isDragging={isDragging}
        />
      )}

      <main className="flex-1 flex flex-col overflow-hidden relative z-10">
        {/* Floating toggle for empty state */}
        {!isSidebarOpen && !hasMessages && (
          <div className="absolute top-4 left-6 z-20">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 rounded-lg bg-surface/60 backdrop-blur-xl border border-white/10 text-muted-foreground hover:text-secondary transition-colors shadow-lg"
              title="Toggle Sidebar (⌘B)"
            >
              <PanelLeft className="w-5 h-5" />
            </button>
          </div>
        )}

        {!hasMessages ? (
          <>
            <EmptyState onUpload={(file) => handleAttachFiles([file])} onContractTypeHint={handleContractTypeHint} />
            <ChatInput
              onSend={handleSend}
              isStreaming={isStreaming}
              userType={userType}
              onUserTypeChange={setUserType}
              showRoleSelector={false}
              onStop={handleStop}
              externalFiles={pendingFiles}
              onExternalFilesUsed={() => setPendingFiles([])}
            />
          </>
        ) : (
          <>
            {/* Header */}
            <div className="h-14 border-b border-white/10 bg-surface/60 backdrop-blur-xl flex items-center px-4 shrink-0 gap-3">
              {!isSidebarOpen && (
                <button
                  onClick={() => setIsSidebarOpen(true)}
                  className="p-1.5 rounded-md hover:bg-white/5 text-muted-foreground transition-colors"
                  title="Show Sidebar (⌘B)"
                >
                  <PanelLeft className="w-5 h-5" />
                </button>
              )}
              <h2 className="text-sm font-bold text-secondary truncate">
                {activeConversation?.title}
              </h2>
              {contractType && (
                <span className="ml-3 text-[9px] font-mono text-primary/80 bg-primary/10 px-2 py-0.5 rounded-md border border-primary/15">
                  {CONTRACT_TYPE_LABELS[contractType]}
                </span>
              )}
              <div className="ml-auto flex items-center gap-3">
                {isStreaming && (
                  <span className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-primary uppercase tracking-wider">
                    <span className="w-2 h-2 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(24,86,255,0.5)]" />
                    Analyzing
                  </span>
                )}
                <AttachedFilesPanel files={attachedFiles} onRemove={handleRemoveFile} />
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl mx-auto">
                {messages.map((msg) => (
                  <ChatMessage
                    key={msg.id}
                    message={msg}
                    userType={userType}
                    onRequestExport={handleExportRequest}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input */}
            <ChatInput
              onSend={handleSend}
              isStreaming={isStreaming}
              userType={userType}
              onUserTypeChange={setUserType}
              showRoleSelector={false}
              selectedContractType={contractType}
              onStop={handleStop}
              externalFiles={pendingFiles}
              onExternalFilesUsed={() => setPendingFiles([])}
            />
          </>
        )}
      </main>
    </div>
  );
}
