"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { FileText } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const router = useRouter();
  const supabase = createClient();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    const { error: err } = await supabase.auth.signInWithPassword({ email, password });
    if (err) setError(err.message);
    else router.push("/dashboard");
    setLoading(false);
  };

  const handleSignup = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    const { error: err } = await supabase.auth.signUp({ email, password });
    if (err) setError(err.message);
    else setMessage("注册成功！请检查邮箱确认链接。");
    setLoading(false);
  };

  const handleGoogleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-2"><FileText className="w-10 h-10 text-blue-600" /></div>
          <CardTitle className="text-2xl">登录 ResumeAI</CardTitle>
          <CardDescription>AI 驱动的简历分析与面试准备</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <input type="email" placeholder="邮箱" value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" required />
            <input type="password" placeholder="密码" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" required />
            {error && <p className="text-red-500 text-sm">{error}</p>}
            {message && <p className="text-green-600 text-sm">{message}</p>}
            <Button type="submit" className="w-full" disabled={loading}>{loading ? "登录中..." : "登录"}</Button>
          </form>
          <div className="flex gap-2 mt-3">
            <Button variant="outline" className="flex-1" onClick={handleSignup} disabled={loading}>注册</Button>
            <Button variant="outline" className="flex-1" onClick={handleGoogleLogin}>Google 登录</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
