"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle, Loader2, AlertCircle, ArrowLeft } from "lucide-react";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [countdown, setCountdown] = useState(5);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setErrorMessage("No verification token found in the link. Please check your email and try again.");
      return;
    }

    // Call the backend to verify the email token
    const verifyToken = async () => {
      try {
        const res = await fetch("/api/users/verify-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "Verification failed. The link may have expired.");
        }

        setStatus("success");
      } catch (err: unknown) {
        console.error(err);
        setStatus("error");
        setErrorMessage(
          err instanceof Error ? err.message : "An unexpected error occurred."
        );
      }
    };

    verifyToken();
  }, [token]);

  // Start countdown only after successful verification
  useEffect(() => {
    if (status !== "success") return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          router.push("/auth/login");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [status, router]);

  if (status === "verifying") {
    return (
      <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30 text-center">
        <div className="w-16 h-16 rounded-2xl bg-[#1B3A5C]/20 border border-[#1B3A5C]/30 flex items-center justify-center mx-auto mb-6">
          <Loader2 className="w-8 h-8 text-blue-300 animate-spin" />
        </div>
        <h1 className="text-2xl font-extrabold text-secondary mb-2">Verifying your email...</h1>
        <p className="text-sm text-muted-foreground">Please wait while we confirm your account.</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30 text-center">
        <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
          <AlertCircle className="w-8 h-8 text-red-400" />
        </div>
        <h1 className="text-2xl font-extrabold text-secondary mb-2">Verification Failed</h1>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed max-w-xs mx-auto">
          {errorMessage}
        </p>
        <div className="space-y-3">
          <Link
            href="/auth/forgot-password"
            className="w-full inline-flex items-center justify-center gap-2 bg-[#1B3A5C] hover:bg-[#234a72] text-white font-bold text-sm py-3 rounded-xl border border-[#1B3A5C]/60 shadow-lg transition-all"
          >
            Request a New Link
          </Link>
          <Link
            href="/auth/login"
            className="w-full inline-flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-secondary transition-colors py-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Sign In
          </Link>
        </div>
      </div>
    );
  }

  // Success state
  return (
    <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30 text-center">
      <div className="w-16 h-16 rounded-2xl bg-success/10 border border-success/20 flex items-center justify-center mx-auto mb-6 shadow-[0_0_20px_rgba(7,202,107,0.2)]">
        <CheckCircle className="w-8 h-8 text-success" />
      </div>
      <h1 className="text-2xl font-extrabold text-secondary mb-2">Email verified!</h1>
      <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
        Your account has been verified successfully. You can now sign in and start analyzing contracts.
      </p>
      <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin text-blue-300" />
        <span>Redirecting to sign in in {countdown}s...</span>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="glass-panel rounded-2xl p-8 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
