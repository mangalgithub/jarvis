"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, Input, Button } from "@heroui/react";

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
            <Input
              required
              label="Name"
              placeholder="Enter your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Input
              required
              label="Email"
              placeholder="Enter your email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Input
              required
              label="Password"
              placeholder="Create a password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <p className="text-sm text-rose-500">{error}</p>}
            <Button
              type="submit"
              color="primary"
              isLoading={loading}
              className="mt-2 w-full bg-slate-950 text-white dark:bg-white dark:text-slate-950"
            >
              Sign Up
            </Button>
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
