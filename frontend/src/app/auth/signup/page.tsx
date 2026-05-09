"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, Eye, EyeOff, Loader2, Scale, User } from "lucide-react";
import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [accountType, setAccountType] = useState<"attorney" | "individual">("individual");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const passwordsMatch = password === confirmPassword;
  const canSubmit = !!(email && password && confirmPassword && passwordsMatch && acceptTerms && !loading);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError("");

    try {
      // In a real app, you'd call an API to create the user
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, accountType }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.message || "Failed to create account");
      }

      // Automatically sign in after signup
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        router.push("/auth/login?registered=true");
      } else {
        router.push("/chat");
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to create account");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignUp = async (e: React.MouseEvent) => {
    e.preventDefault();
    await signIn("google", { callbackUrl: "/chat" });
  };

  return (
    <div className="glass-panel rounded-2xl p-8 border-[#1B3A5C]/30">
      <div className="text-center mb-8">
        <h1 className="text-2xl font-extrabold text-secondary mb-1">Create your account</h1>
        <p className="text-sm text-muted-foreground">Start analyzing contracts in minutes</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-500 text-sm p-3 rounded-xl mb-4 text-center">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Account Type Toggle */}
        <div>
          <label className="text-[10px] font-mono font-bold uppercase text-muted-foreground tracking-wider block mb-2">
            I am
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setAccountType("individual")}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold border transition-all ${
                accountType === "individual"
                  ? "bg-[#1B3A5C]/20 border-[#1B3A5C]/40 text-blue-300"
                  : "bg-white/5 border-white/10 text-muted-foreground hover:bg-white/10"
              }`}
            >
              <User className="w-4 h-4" /> Individual
            </button>
            <button
              type="button"
              onClick={() => setAccountType("attorney")}
              className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold border transition-all ${
                accountType === "attorney"
                  ? "bg-[#1B3A5C]/20 border-[#1B3A5C]/40 text-blue-300"
                  : "bg-white/5 border-white/10 text-muted-foreground hover:bg-white/10"
              }`}
            >
              <Scale className="w-4 h-4" /> Attorney
            </button>
          </div>
        </div>

        {/* Email */}
        <div>
          <label className="text-[10px] font-mono font-bold uppercase text-muted-foreground tracking-wider block mb-1.5">Email</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-secondary placeholder:text-muted-foreground focus:outline-none focus:border-[#1B3A5C]/60 focus:shadow-[0_0_10px_rgba(27,58,92,0.2)] transition-all"
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <label className="text-[10px] font-mono font-bold uppercase text-muted-foreground tracking-wider block mb-1.5">Password</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type={showPass ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min. 8 characters"
              required
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-12 py-3 text-sm text-secondary placeholder:text-muted-foreground focus:outline-none focus:border-[#1B3A5C]/60 focus:shadow-[0_0_10px_rgba(27,58,92,0.2)] transition-all"
            />
            <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-secondary transition-colors">
              {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Confirm Password */}
        <div>
          <label className="text-[10px] font-mono font-bold uppercase text-muted-foreground tracking-wider block mb-1.5">Confirm Password</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type={showPass ? "text" : "password"}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat password"
              required
              className={`w-full bg-white/5 border rounded-xl pl-10 pr-4 py-3 text-sm text-secondary placeholder:text-muted-foreground focus:outline-none transition-all ${
                confirmPassword && !passwordsMatch ? "border-red-500/50 focus:border-red-500/60" : "border-white/10 focus:border-[#1B3A5C]/60"
              }`}
            />
          </div>
          {confirmPassword && !passwordsMatch && (
            <p className="text-[10px] text-red-400 mt-1 font-medium">Passwords do not match</p>
          )}
        </div>

        {/* Terms */}
        <label className="flex items-start gap-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={acceptTerms}
            onChange={(e) => setAcceptTerms(e.target.checked)}
            className="w-3.5 h-3.5 rounded border-white/20 bg-white/5 text-[#1B3A5C] focus:ring-[#1B3A5C]/40 mt-0.5"
          />
          <span className="text-xs text-muted-foreground leading-relaxed">
            I agree to the{" "}
            <Link href="#" className="text-blue-300 hover:text-blue-200">Terms of Service</Link>
            {" "}and{" "}
            <Link href="#" className="text-blue-300 hover:text-blue-200">Privacy Policy</Link>
          </span>
        </label>

        {/* Submit */}
        <Button
          type="submit"
          disabled={!canSubmit}
          variant="glass"
          size="lg"
          className="w-full"
        >
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {loading ? "Creating account..." : "Create Account"}
        </Button>
      </form>

      {/* Divider */}
      <div className="flex items-center gap-3 my-6">
        <div className="flex-1 border-t border-white/5" />
        <span className="text-[10px] font-mono text-muted-foreground uppercase">Or continue with</span>
        <div className="flex-1 border-t border-white/5" />
      </div>

      {/* Social */}
      <div className="grid grid-cols-1 gap-3">
        <Button
          type="button"
          onClick={handleGoogleSignUp}
          variant="glass-secondary"
          size="lg"
          className="w-full"
        >
          <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.47 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Google
        </Button>
      </div>

      <p className="text-center text-xs text-muted-foreground mt-8">
        Already have an account?{" "}
        <Link href="/auth/login" className="text-blue-300 hover:text-blue-200 font-semibold transition-colors">
          Sign in
        </Link>
      </p>
    </div>
  );
}
