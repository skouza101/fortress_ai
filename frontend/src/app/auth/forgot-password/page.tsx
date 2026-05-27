"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mail, Loader2, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/users/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      // Always show success regardless of whether email exists (security best practice)
      if (res.ok || res.status === 404) {
        setSubmitted(true);
      } else {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to send reset email");
      }
    } catch (err: unknown) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30 text-center">
        <div className="w-16 h-16 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center mx-auto mb-6 shadow-[0_0_20px_rgba(34,197,94,0.15)]">
          <CheckCircle className="w-8 h-8 text-green-400" />
        </div>
        <h1 className="text-2xl font-extrabold text-secondary mb-2">Check your email</h1>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed max-w-xs mx-auto">
          If an account exists for <span className="text-blue-300 font-medium">{email}</span>,
          you will receive a password reset link shortly.
        </p>
        <p className="text-xs text-muted-foreground mb-6">
          Didn&apos;t receive it?{" "}
          <button
            onClick={() => setSubmitted(false)}
            className="text-blue-300 hover:text-blue-200 font-medium transition-colors"
          >
            Try again
          </button>
        </p>
        <Link
          href="/auth/login"
          className="w-full inline-flex items-center justify-center gap-2 bg-[#1B3A5C] hover:bg-[#234a72] text-white font-bold text-sm py-3 rounded-xl border border-[#1B3A5C]/60 shadow-lg shadow-[#1B3A5C]/20 transition-all"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Sign In
        </Link>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30">
      <div className="text-center mb-8">
        <div className="w-14 h-14 rounded-2xl bg-[#1B3A5C]/20 border border-[#1B3A5C]/30 flex items-center justify-center mx-auto mb-5">
          <Mail className="w-7 h-7 text-blue-300" />
        </div>
        <h1 className="text-2xl font-extrabold text-secondary mb-2">Forgot Password?</h1>
        <p className="text-sm text-muted-foreground leading-relaxed max-w-xs mx-auto">
          Enter your email address and we&apos;ll send you a link to reset your password.
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="bg-red-500/10 border border-red-500/50 text-red-400 text-sm p-3 rounded-xl mb-4 text-center"
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="forgot-email"
            className="text-[10px] font-mono font-bold uppercase text-muted-foreground tracking-wider block mb-1.5"
          >
            Email Address
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              id="forgot-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
              autoFocus
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-secondary placeholder:text-muted-foreground focus:outline-none focus:border-[#1B3A5C]/60 focus:shadow-[0_0_10px_rgba(27,58,92,0.2)] transition-all"
            />
          </div>
        </div>

        <Button
          type="submit"
          disabled={loading || !email}
          variant="glass"
          size="lg"
          className="w-full"
        >
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {loading ? "Sending..." : "Send Reset Link"}
        </Button>
      </form>

      <div className="mt-6 text-center">
        <Link
          href="/auth/login"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-secondary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Sign In
        </Link>
      </div>
    </div>
  );
}
