"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

/**
 * SSO Callback page.
 * After a successful Google OAuth login, NextAuth redirects here briefly.
 * We simply redirect to /chat (or wherever the callbackUrl was set).
 * NextAuth handles the session establishment automatically via the /api/auth/* routes.
 */
export default function SSOCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    // NextAuth processes the OAuth callback automatically.
    // If the user lands here, just send them to chat.
    router.replace("/chat");
  }, [router]);

  return (
    <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30 text-center">
      <div className="w-16 h-16 rounded-2xl bg-[#1B3A5C]/20 border border-[#1B3A5C]/30 flex items-center justify-center mx-auto mb-6">
        <Loader2 className="w-8 h-8 text-blue-300 animate-spin" />
      </div>
      <h1 className="text-2xl font-extrabold text-secondary mb-2">Signing you in...</h1>
      <p className="text-sm text-muted-foreground">
        Completing authentication, please wait.
      </p>
    </div>
  );
}
