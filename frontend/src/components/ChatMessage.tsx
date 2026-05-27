"use client";

import { motion } from "framer-motion";
import { Bot, User, FileText, Download, Copy, ThumbsUp, ThumbsDown, Check, ChevronDown, ChevronRight, BrainCircuit, Globe, Search } from "lucide-react";
import { useState } from "react";
import { Message } from "@/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ReportView from "@/components/report/ReportView";
import AnalysisProgress from "@/components/report/AnalysisProgress";
import { CHAT_MD_COMPONENTS } from "@/lib/mdComponents";

interface ChatMessageProps {
  message: Message;
  userType?: "attorney" | "individual";
  onRequestExport?: (format: "pdf" | "docx") => void;
  onSearchClick?: (query: string) => void;
}

export default function ChatMessage({ message, userType, onRequestExport, onSearchClick }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const isSystem = message.role === "system";
  const hasReport = !!message.report;
  const hasAnalysis = !!message.analysisSteps;
  const hasSources = !!message.sources && message.sources.length > 0;
  const [copied, setCopied] = useState(false);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);

  // System messages (confirmations, etc.)
  if (isSystem) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="flex justify-center py-3 px-4 md:px-8"
      >
        <div className="max-w-md text-center px-4 py-2 rounded-full border text-xs text-muted-foreground">
          {message.content}
        </div>
      </motion.div>
    );
  }

  // Pre-process <think> blocks for reasoning models
  let displayContent = message.content || "";
  let thinkContent = "";
  const thinkMatch = displayContent.match(/<think>([\s\S]*?)(?:<\/think>|$)/);

  if (thinkMatch) {
    thinkContent = thinkMatch[1].trim();
    // Remove the think block from the main content
    displayContent = displayContent.replace(/<think>[\s\S]*?(?:<\/think>|$)/, "").trim();
  } else {
    // Attempt to parse ReAct style OR Orchestrator style if no <think> tags are present
    const REACT_KEYWORDS = /(?:^|\n)\s*(?:#+\s*)?(?:\*\*)?(?:Thought|Action|Action Input|Observation|Final Answer)(?:\s*\(.*?\))?(?:\*\*)?:/i;
    const ORCH_KEYWORDS = /(?:^|\n)\s*(?:#+\s*)?(?:\*\*)?(?:Task Delegation|Agent Assigned|Query Executed|Operational Protocol|Search Execution|Legal Researcher|Knowledge Retriever|Risk Auditor|Ingestion Specialist)(?:\s*[&\w\s]*)?(?:\*\*)?[:\n]/i;
    const FINAL_ANSWER = /(?:^|\n|\.\s+|\s+)\s*(?:#+\s*)?(?:\*\*)?(?:Final Answer|Findings|Research Results|Final Report)(?:\*\*)?\s*(?:\n|:|$)/i;

    const hasReAct = REACT_KEYWORDS.test(displayContent) || FINAL_ANSWER.test(displayContent);
    const hasOrch = ORCH_KEYWORDS.test(displayContent);

    if (hasReAct || hasOrch) {
      const match = displayContent.match(FINAL_ANSWER);
      if (match && match.index !== undefined) {
        thinkContent = displayContent.substring(0, match.index).trim();
        displayContent = displayContent.substring(match.index + match[0].length).trim();
      } else {
        thinkContent = displayContent.trim();
        displayContent = "";
      }
    }
  }

  // Strip any disclaimer text the model might still generate
  displayContent = displayContent.replace(/\n*\s*\*?Disclaimer:?\*?\s*I\s*am\s*an\s*AI[\s\S]*$/i, '').trim();

  // Extract search queries from thinkContent (supports both ReAct and Orchestrator formats)
  const searchQueries: string[] = [];
  // ReAct format: **Action:** search("...")
  const reactSearchRegex = /(?:\*\*Action:\*\*|Action:)\s*`?search[a-z_]*\(["'](.*?)["']\)`?/gi;
  let searchMatch;
  while ((searchMatch = reactSearchRegex.exec(thinkContent)) !== null) {
    if (searchMatch[1] && !searchQueries.includes(searchMatch[1])) {
      searchQueries.push(searchMatch[1]);
    }
  }
  // Orchestrator format: **Query Executed:** "..."  or  Query Executed: "..."
  const orchSearchRegex = /(?:\*\*)?Query Executed(?:\*\*)?[:\s]+[""]([^""]+)[""]|(?:\*\*)?Query Executed(?:\*\*)?[:\s]+(.+)/gi;
  while ((searchMatch = orchSearchRegex.exec(thinkContent)) !== null) {
    let query = (searchMatch[1] || searchMatch[2] || '').trim();
    // Clean up any leading/trailing Markdown artifacts like **, ", or *
    query = query.replace(/^[*"`\s]+|[*"`\s]+$/g, '');
    if (query && !searchQueries.includes(query)) {
      searchQueries.push(query);
    }
  }
  // Action: search_internal("...") or search_web("...")
  const actionSearchRegex = /`search[a-z_]*\(["'](.*?)["']\)`/gi;
  while ((searchMatch = actionSearchRegex.exec(thinkContent)) !== null) {
    if (searchMatch[1] && !searchQueries.includes(searchMatch[1])) {
      searchQueries.push(searchMatch[1]);
    }
  }

  // Force thinking block expanded when actively streaming thought chunks
  const isStreamingThoughts = message.isStreaming && !displayContent && !!thinkContent;
  const showThinking = isThinkingExpanded || isStreamingThoughts;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`flex gap-4 py-5 px-4 md:px-8 group ${isUser ? "justify-end" : "justify-start"
        }`}
    >
      {/* Avatar — Assistant */}
      {isAssistant && (
        <div className="shrink-0 w-8 h-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shadow-[0_0_10px_rgba(24,86,255,0.15)] mt-1">
          <Bot className="w-4 h-4 text-primary" />
        </div>
      )}

      {/* Content */}
      <div className={`min-w-0 ${isUser ? "max-w-[75%]" : "max-w-[85%] flex-1"}`}>
        {/* Attachment badge */}
        {message.attachment && (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs font-medium text-muted-foreground mb-2">
            {message.attachment.type === 'download' ? (
              <Download className="w-3.5 h-3.5 text-success" />
            ) : (
              <FileText className="w-3.5 h-3.5 text-primary" />
            )}
            <span className="truncate max-w-[250px]">{message.attachment.name}</span>
            {message.attachment.size > 0 && (
              <span className="text-[10px] opacity-60">
                {(message.attachment.size / 1024 / 1024).toFixed(1)} MB
              </span>
            )}
          </div>
        )}


        {/* Sources Section */}
        {hasSources && (
          <div className="flex flex-wrap gap-2 mb-3">
            {message.sources!.map((source, i) => (
              <a
                key={i}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs transition-colors"
                title={source.url}
              >
                <Globe className="w-3.5 h-3.5 text-primary/70" />
                <span className="truncate max-w-[150px] font-medium text-muted-foreground hover:text-secondary transition-colors">
                  {source.title}
                </span>
              </a>
            ))}
          </div>
        )}

        {/* Analysis progress (Execution Plan) - Now stays visible! */}
        {hasAnalysis && (
          <div className={hasReport ? "mb-6" : ""}>
            <AnalysisProgress steps={message.analysisSteps!} />
          </div>
        )}

        {/* Report view */}
        {hasReport && (
          <ReportView
            report={message.report!}
            userType={userType}
            onRequestExport={onRequestExport}
          />
        )}

        {/* Regular text bubble */}
        {!hasReport && !hasAnalysis && (
          <div
            className={`rounded-2xl px-5 py-3 text-sm leading-relaxed ${isUser
              ? "bg-[#292929] text-white border border-white/10 shadow-sm rounded-br-md"
              : "text-secondary rounded-bl-md"
              }`}
          >
            {message.isStreaming && !displayContent && !thinkContent ? (
              <div className="flex items-center gap-3 text-muted-foreground py-1">
                <div className="flex gap-1.5">
                  <motion.div
                    className="w-2 h-2 rounded-full bg-primary/60"
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                  />
                  <motion.div
                    className="w-2 h-2 rounded-full bg-primary/80"
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0.15 }}
                  />
                  <motion.div
                    className="w-2 h-2 rounded-full bg-primary"
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: 0.3 }}
                  />
                </div>
                <span className="text-xs font-medium bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary animate-pulse">
                  Model is thinking...
                </span>
              </div>
            ) : isAssistant ? (
              <div className="flex flex-col gap-3">
                {/* Search Pills */}
                {searchQueries.length > 0 && (
                  <div className="flex flex-col gap-2">
                    {searchQueries.map((query, idx) => (
                      <button
                        type="button"
                        key={idx}
                        onClick={() => onSearchClick?.(query)}
                        className="w-full flex cursor-pointer items-center justify-between px-4 py-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 transition-colors text-xs text-muted-foreground group"
                        aria-label={`Open search results for ${query}`}
                      >
                        <div className="flex items-center gap-2.5 overflow-hidden flex-1 pr-4">
                          <Search className={`w-3.5 h-3.5 text-primary/70 shrink-0 ${isStreamingThoughts && idx === searchQueries.length - 1 ? "animate-pulse" : ""}`} />
                          <span className="font-medium shrink-0">{isStreamingThoughts && idx === searchQueries.length - 1 ? "Researching" : "Search"}</span>
                          <div className="w-[1px] h-3 bg-white/10 shrink-0"></div>
                          <span className="text-white/80 truncate">
                            {query}
                          </span>
                        </div>
                        {isStreamingThoughts && idx === searchQueries.length - 1 ? (
                          <span className="flex gap-1 shrink-0">
                            <span className="w-1 h-1 rounded-full bg-primary/60 animate-pulse" />
                            <span className="w-1 h-1 rounded-full bg-primary/80 animate-pulse" style={{ animationDelay: "0.15s" }} />
                            <span className="w-1 h-1 rounded-full bg-primary animate-pulse" style={{ animationDelay: "0.3s" }} />
                          </span>
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5 shrink-0 transition-transform group-hover:translate-x-0.5" />
                        )}
                      </button>
                    ))}
                  </div>
                )}

                {/* Thinking Block */}
                {thinkContent && (
                  <div className="rounded-lg border border-white/10 bg-white/5 overflow-hidden">
                    <button
                      onClick={() => setIsThinkingExpanded(!showThinking)}
                      className="w-full flex items-center justify-between px-4 py-2 hover:bg-white/5 transition-colors text-xs font-medium text-muted-foreground"
                    >
                      <div className="flex items-center gap-2">
                        <BrainCircuit className={`w-3.5 h-3.5 text-primary/70 ${isStreamingThoughts ? "animate-pulse" : ""}`} />
                        <span>{isStreamingThoughts ? "Thinking..." : "Thought Process"}</span>
                        {isStreamingThoughts && (
                          <span className="flex gap-1 ml-1">
                            <span className="w-1 h-1 rounded-full bg-primary/60 animate-pulse" />
                            <span className="w-1 h-1 rounded-full bg-primary/80 animate-pulse" style={{ animationDelay: "0.15s" }} />
                            <span className="w-1 h-1 rounded-full bg-primary animate-pulse" style={{ animationDelay: "0.3s" }} />
                          </span>
                        )}
                      </div>
                      {showThinking ? (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" />
                      )}
                    </button>
                    {showThinking && (
                      <div className="px-4 pb-3 pt-2 text-xs text-muted-foreground border-t border-white/5 prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-p:text-muted-foreground prose-li:text-muted-foreground prose-headings:text-muted-foreground/90 [&_strong]:text-muted-foreground/90 [&_h1]:text-xs [&_h2]:text-xs [&_h3]:text-xs [&_h3]:font-semibold [&_ul]:my-1 [&_li]:my-0.5 [&_p]:my-1 [&_p]:text-xs [&_li]:text-xs">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {thinkContent}
                        </ReactMarkdown>
                        {isStreamingThoughts && (
                          <span className="inline-block w-1.5 h-3 bg-primary/60 animate-pulse ml-0.5 align-middle rounded-sm" />
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Main Content */}
                {displayContent && (
                  <div className="prose prose-invert prose-sm max-w-none font-serif [&>p]:mb-2 [&>p:last-child]:mb-0 [&>ul]:mt-1 [&>ol]:mt-1 [&_strong]:text-secondary [&_a]:text-[#8AB4F8] [&_h1]:text-base [&_h1]:font-sans [&_h2]:text-sm [&_h2]:font-sans [&_h3]:text-sm [&_h3]:font-sans">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={CHAT_MD_COMPONENTS}>{displayContent}</ReactMarkdown>
                    {message.isStreaming && (
                      <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1 align-middle rounded-sm" />
                    )}
                  </div>
                )}
              </div>
            ) : (
              <p>{displayContent}</p>
            )}
          </div>
        )}

        {/* Actions & Timestamp Row */}
        {!hasAnalysis && (
          <div className={`flex items-center gap-3 mt-1.5 ${isUser ? "justify-end" : "justify-start ml-3"}`}>
            {/* Timestamp */}
            <p className="text-[10px] text-muted-foreground font-mono">
              {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </p>

            {/* Message Actions (Assistant only) */}
            {isAssistant && !message.isStreaming && (
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <button
                  className="p-1.5 rounded-md text-muted-foreground hover:text-secondary hover:bg-white/5 transition-all"
                  title="Helpful"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                </button>
                <button
                  className="p-1.5 rounded-md text-muted-foreground hover:text-secondary hover:bg-white/5 transition-all"
                  title="Not helpful"
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(message.content || "");
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="px-1.5 rounded-md text-muted-foreground hover:text-secondary hover:bg-white/5 transition-all"
                  title="Copy message"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Avatar — User */}
      {isUser && (
        <div className="shrink-0 w-8 h-8 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center mt-1">
          <User className="w-4 h-4 text-secondary" />
        </div>
      )}
    </motion.div>
  );
}
