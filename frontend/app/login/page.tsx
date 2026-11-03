"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.replace("/dashboard/members");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#080808] p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold tracking-tight">
            <span className="text-[#D4A84F]">GYM</span>
            <span className="text-white">CORE</span>
          </h1>
          <p className="text-[#9B968C] mt-2 text-sm">Gym Management Platform</p>
        </div>

        {/* Card */}
        <div className="bg-[#1D1D1D] border border-[#2A2A2A] rounded-2xl p-8">
          <h2 className="text-xl font-semibold mb-6">Sign in to your gym</h2>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700/50 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="owner@yourgym.com"
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-3 text-white placeholder-[#4A4A4A] focus:border-[#D4A84F] focus:outline-none transition-colors"
              />
            </div>

            <div>
              <label className="block text-sm text-[#9B968C] mb-1.5">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-[#151515] border border-[#2A2A2A] rounded-lg px-4 py-3 text-white placeholder-[#4A4A4A] focus:border-[#D4A84F] focus:outline-none transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#D4A84F] hover:bg-[#F0C96A] text-black font-semibold py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </div>

        <p className="text-center text-[#9B968C] text-xs mt-6">
          GymCore &copy; {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
}

