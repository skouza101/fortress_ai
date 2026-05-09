import Link from "next/link";
import { ArrowLeft, AlertCircle } from "lucide-react";

export default function ResetPasswordPage() {
  return (
    <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30 text-center">
      <div className="w-14 h-14 rounded-2xl bg-warning/10 border border-warning/20 flex items-center justify-center mx-auto mb-5">
        <AlertCircle className="w-7 h-7 text-warning" />
      </div>
      <h1 className="text-2xl font-extrabold text-secondary mb-2">Feature Unavailable</h1>
      <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
        Password reset is currently disabled. Please use Google Sign In or contact{" "}
        <a href="mailto:support@fortress-ai.com" className="text-blue-300 hover:text-blue-200 underline">
          Fortress AI support
        </a>
        {" "}if you have lost access to your account.
      </p>
      <Link
        href="/auth/login"
        className="w-full inline-flex items-center justify-center gap-2 bg-[#1B3A5C] hover:bg-[#234a72] text-white font-bold text-sm py-3 rounded-xl border border-[#1B3A5C]/60 shadow-lg shadow-[#1B3A5C]/20 transition-all text-center"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Sign In
      </Link>
    </div>
  );
}
