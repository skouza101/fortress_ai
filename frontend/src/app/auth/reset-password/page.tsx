"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Lock, Eye, EyeOff, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

const MIN_PASSWORD_LENGTH = 8;

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [showConfirmPass, setShowConfirmPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const passwordsMatch = password === confirmPassword;
  const isPasswordValid = password.length >= MIN_PASSWORD_LENGTH;
  const canSubmit = isPasswordValid && passwordsMatch && !!token && !loading;

  // If no token in URL, show an error immediately
  if (!token) {
    return (
      <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30 text-center">
        <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5">
          <AlertCircle className="w-7 h-7 text-red-400" />
        </div>
        <h1 className="text-2xl font-extrabold text-secondary mb-2">Invalid Reset Link</h1>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
          This password reset link is invalid or has expired. Please request a new one.
        </p>
        <Link
          href="/auth/forgot-password"
          className="w-full inline-flex items-center justify-center gap-2 bg-[#1B3A5C] hover:bg-[#234a72] text-white font-bold text-sm py-3 rounded-xl border border-[#1B3A5C]/60 shadow-lg transition-all"
        >
          Request New Link
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30 text-center">
        <div className="w-16 h-16 rounded-2xl bg-green-500/10 border border-green-500/20 flex items-center justify-center mx-auto mb-6 shadow-[0_0_20px_rgba(34,197,94,0.15)]">
          <CheckCircle className="w-8 h-8 text-green-400" />
        </div>
        <h1 className="text-2xl font-extrabold text-secondary mb-2">Password Reset!</h1>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
          Your password has been updated successfully. You can now sign in with your new password.
        </p>
        <Link
          href="/auth/login"
          className="w-full inline-flex items-center justify-center gap-2 bg-[#1B3A5C] hover:bg-[#234a72] text-white font-bold text-sm py-3 rounded-xl border border-[#1B3A5C]/60 shadow-lg transition-all"
        >
          <ArrowLeft className="w-4 h-4" /> Go to Sign In
        </Link>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/users/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to reset password. The link may have expired.");
      }

      setSuccess(true);
    } catch (err: unknown) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30">
      <div className="text-center mb-8">
        <div className="w-14 h-14 rounded-2xl bg-[#1B3A5C]/20 border border-[#1B3A5C]/30 flex items-center justify-center mx-auto mb-5">
          <Lock className="w-7 h-7 text-blue-300" />
        </div>
        <h1 className="text-2xl font-extrabold text-secondary mb-2">Set New Password</h1>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Choose a strong password for your account.
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
        {/* New Password */}
        <div>
          <label
            htmlFor="reset-password"
            className="text-[10px] font-mono font-bold uppercase text-muted-foreground tracking-wider block mb-1.5"
          >
            New Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              id="reset-password"
              type={showPass ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min. 8 characters"
              required
              minLength={MIN_PASSWORD_LENGTH}
              autoComplete="new-password"
              autoFocus
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-12 py-3 text-sm text-secondary placeholder:text-muted-foreground focus:outline-none focus:border-[#1B3A5C]/60 transition-all"
            />
            <button
              type="button"
              onClick={() => setShowPass(!showPass)}
              aria-label={showPass ? "Hide password" : "Show password"}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-secondary transition-colors"
            >
              {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Confirm Password */}
        <div>
          <label
            htmlFor="reset-confirm-password"
            className="text-[10px] font-mono font-bold uppercase text-muted-foreground tracking-wider block mb-1.5"
          >
            Confirm New Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              id="reset-confirm-password"
              type={showConfirmPass ? "text" : "password"}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat new password"
              required
              autoComplete="new-password"
              className={`w-full bg-white/5 border rounded-xl pl-10 pr-12 py-3 text-sm text-secondary placeholder:text-muted-foreground focus:outline-none transition-all ${
                confirmPassword && !passwordsMatch
                  ? "border-red-500/50 focus:border-red-500/60"
                  : "border-white/10 focus:border-[#1B3A5C]/60"
              }`}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPass(!showConfirmPass)}
              aria-label={showConfirmPass ? "Hide password" : "Show password"}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-secondary transition-colors"
            >
              {showConfirmPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {confirmPassword && !passwordsMatch && (
            <p className="text-[10px] text-red-400 mt-1 font-medium">Passwords do not match</p>
          )}
        </div>

        <Button
          type="submit"
          disabled={!canSubmit}
          variant="glass"
          size="lg"
          className="w-full"
        >
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {loading ? "Updating..." : "Reset Password"}
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

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="glass-panel rounded-2xl p-8 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
