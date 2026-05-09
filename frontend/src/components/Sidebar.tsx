"use client";

import { useState } from "react";
import {
  ShieldCheck,
  MessageSquarePlus,
  Clock,
  Settings,
  FileText,
  PanelRightOpen,
  Zap,
  Info,
  Languages,
  Mail,
  Upload,
} from "lucide-react";
import { Conversation, CONTRACT_TYPE_LABELS } from "@/types";
import ChatActionsMenu from "./ChatActionsMenu";
import { useSession } from "next-auth/react";
import { motion } from "framer-motion";
import Image from "next/image";

// ... (SidebarProps and VERDICT_DOT unchanged)

export default function Sidebar({
  conversations,
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  onPinConversation,
  onToggleSidebar,
  isDragging = false,
}: SidebarProps) {
  const [showFooterMenu, setShowFooterMenu] = useState(false);
  const [imageError, setImageError] = useState(false);
  const { data: session } = useSession();

  type AuthUser = {
    name?: string | null;
    email?: string | null;
    image?: string | null;
    userType?: string | null;
  };

  const user = session?.user as AuthUser | undefined;
  const userType = user?.userType;
  const initials = user?.name 
    ? user.name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() || "??";

  return (
    <motion.aside 
      initial={{ x: -300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -300, opacity: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className={`w-72 border-r border-white/10 bg-surface/80 backdrop-blur-2xl flex flex-col hidden md:flex z-20 shadow-[4px_0_24px_rgba(0,0,0,0.2)] transition-colors duration-300 ${
        isDragging ? "ring-2 ring-primary ring-inset bg-primary/5" : ""
      }`}
    >
      {/* Brand */}
      <div className="h-16 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center mr-3 border border-primary/20 shadow-[0_0_10px_rgba(24,86,255,0.15)]">
            <ShieldCheck className="w-5 h-5 text-primary" />
          </div>
          <span className="font-bold text-lg tracking-wide text-secondary">
            FORTRESS AI
          </span>
        </div>
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="p-1.5 rounded-md hover:bg-white/5 text-muted-foreground transition-colors"
            title="Hide Sidebar (⌘B)"
          >
            <PanelRightOpen className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* New Analysis Button */}
      <div className="px-4 pt-4 pb-2 shrink-0">
        <button
          onClick={onNewChat}
          className="w-full glass-panel glass-panel-hover rounded-lg px-4 py-3 flex items-center justify-between text-sm font-semibold text-muted-foreground hover:text-secondary transition-all group"
        >
          <div className="flex items-center gap-2.5">
            <MessageSquarePlus className="w-4 h-4 text-primary" />
            New Analysis
          </div>
          <span className="flex items-center gap-1">
            <kbd className="hidden md:inline-flex items-center justify-center h-5 min-w-[22px] px-1 text-[11px] leading-none font-inter font-black rounded-[4px] bg-white/[0.08] text-muted-foreground border border-white/10 shadow-[0_1px_2px_rgba(0,0,0,0.3)] group-hover:border-white/20 group-hover:text-secondary transition-colors">
              ⌘
            </kbd>
            <kbd className="hidden md:inline-flex items-center justify-center h-5 min-w-[20px] px-1 text-[13px] leading-none font-inter font-black rounded-[4px] bg-white/[0.08] text-muted-foreground border border-white/10 shadow-[0_1px_2px_rgba(0,0,0,0.3)] group-hover:border-white/20 group-hover:text-secondary transition-colors">
              K
            </kbd>
          </span>
        </button>
      </div>

      {/* Conversation History */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1 scrollbar-hide relative">
        {isDragging && (
          <div className="absolute inset-0 z-10 bg-surface/60 backdrop-blur-sm flex flex-col items-center justify-center p-4 text-center animate-in fade-in duration-300">
            <div className="w-12 h-12 rounded-2xl bg-primary/20 border border-primary/30 flex items-center justify-center mb-3 animate-bounce">
              <Upload className="w-6 h-6 text-primary" />
            </div>
            <p className="text-xs font-bold text-secondary uppercase tracking-wider">Drop to start</p>
            <p className="text-[10px] text-muted-foreground mt-1">New analysis will begin</p>
          </div>
        )}
        
        {conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
            <Clock className="w-5 h-5 mb-2 opacity-50" />
            <p className="text-xs font-medium">No analyses yet</p>
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            const verdictDot = conv.verdict ? VERDICT_DOT[conv.verdict] : null;
            return (
              <div
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                className={`w-full cursor-pointer text-left flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-200 group relative ${
                  isActive
                    ? "bg-white/10 border border-white/20 shadow-sm"
                    : "border border-transparent hover:bg-white/5"
                }`}
              >
                <FileText
                  className={`w-4 h-4 mt-0.5 shrink-0 ${
                    isActive ? "text-primary" : "text-muted-foreground"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    {verdictDot && (
                      <span className={`w-2 h-2 rounded-full shrink-0 ${verdictDot}`} />
                    )}
                    <p
                      className={`text-sm font-medium truncate ${
                        isActive ? "text-secondary" : "text-muted-foreground"
                      }`}
                    >
                      {conv.title}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    {conv.contractType && (
                      <span className="text-[9px] font-mono text-primary/70 bg-primary/10 px-1.5 py-0.5 rounded border border-primary/15">
                        {CONTRACT_TYPE_LABELS[conv.contractType]}
                      </span>
                    )}
                  </div>
                </div>
                <ChatActionsMenu
                  chatId={conv.id}
                  chatName={conv.title}
                  isPinned={conv.isPinned}
                  onDelete={onDeleteConversation}
                  onRename={onRenameConversation}
                  onPin={onPinConversation}
                />
              </div>
            );
          })
        )}
      </div>

      {/* Footer Menu */}
      {showFooterMenu && (
        <div className="px-3 py-2 border-t border-white/5 space-y-0.5 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-secondary hover:bg-white/5 transition-all group">
            <Zap className="w-4 h-4 text-primary group-hover:scale-110 transition-transform" />
            <span>Upgrade Plan</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-secondary hover:bg-white/5 transition-all">
            <Info className="w-4 h-4" />
            <span>About Us</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-secondary hover:bg-white/5 transition-all relative">
            <Languages className="w-4 h-4" />
            <span>Language</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-secondary hover:bg-white/5 transition-all">
            <Mail className="w-4 h-4" />
            <span>User Feedback</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-secondary hover:bg-white/5 transition-all">
            <Settings className="w-4 h-4" />
            <span>Settings</span>
          </button>
        </div>
      )}

      {/* Footer */}
      <div className="px-4 py-4 border-t border-white/10 shrink-0">
        <div className="flex items-center gap-3 px-2">
          {user?.image && !imageError ? (
            <Image
              src={user.image}
              alt={user.name || "User"}
              width={32}
              height={32}
              className="rounded-full border border-primary/20 shadow-sm"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-[10px] font-bold text-primary">
              {initials}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-secondary truncate">
              {user?.name || "Fortress User"}
            </p>
            <p className="text-[10px] text-muted-foreground capitalize">
              {userType || "Member"}
            </p>
          </div>
          <button
            onClick={() => setShowFooterMenu(!showFooterMenu)}
            className={`p-1.5 rounded-lg transition-all duration-200 ${
              showFooterMenu
                ? "bg-primary/10 text-primary shadow-[0_0_10px_rgba(24,86,255,0.1)]"
                : "hover:bg-white/5 text-muted-foreground hover:text-secondary"
            }`}
          >
            <Settings className={`w-4 h-4 transition-transform duration-300 ${showFooterMenu ? 'rotate-90' : ''}`} />
          </button>
        </div>
      </div>
    </motion.aside>
  );
}
