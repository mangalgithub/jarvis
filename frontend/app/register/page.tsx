"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@heroui/react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:3000";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Registration failed");
      }

      localStorage.setItem("jarvis_token", data.access_token);
      localStorage.setItem("jarvis_user_id", data.user_id);
      localStorage.setItem("jarvis_name", data.name);
      
      router.push("/");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-900 p-4">
      <Card className="w-full max-w-md p-6">
        <div className="flex flex-col items-center gap-2 mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-950 dark:bg-white">
            <span className="text-xl font-bold text-white dark:text-slate-950">J</span>
          </div>
          <h1 className="text-2xl font-bold">Create Account</h1>
          <p className="text-sm text-slate-500">Join your personal Jarvis OS</p>
        </div>
        <div>
          <form onSubmit={handleRegister} className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-semibold mb-1.5 text-slate-700 dark:text-slate-300">Name</label>
              <input
                required
                type="text"
                placeholder="Enter your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-white/10 dark:bg-white/10 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold mb-1.5 text-slate-700 dark:text-slate-300">Email</label>
              <input
                required
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-white/10 dark:bg-white/10 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold mb-1.5 text-slate-700 dark:text-slate-300">Password</label>
              <input
                required
                type="password"
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-white/10 dark:bg-white/10 dark:text-white"
              />
            </div>

            {error && <p className="text-sm text-rose-500">{error}</p>}
            
            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full rounded-xl bg-slate-950 py-3 text-sm font-bold text-white transition-all hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-950"
            >
              {loading ? "Signing Up..." : "Sign Up"}
            </button>
            
            <p className="text-center text-sm text-slate-500 mt-4">
              Already have an account?{" "}
              <button 
                type="button" 
                onClick={() => router.push("/login")}
                className="font-semibold text-blue-600 hover:underline"
              >
                Log in
              </button>
            </p>
          </form>
        </div>
      </Card>
    </div>
  );
}
