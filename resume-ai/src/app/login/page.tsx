"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "../../lib/supabase/client";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
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
    setLoading(true); setError("");
    const { error: err } = await supabase.auth.signInWithPassword({ email, password });
    if (err) setError(err.message); else router.push("/dashboard");
    setLoading(false);
  };

  const handleSignup = async () => {
    setLoading(true); setError(""); setMessage("");
    const { error: err } = await supabase.auth.signUp({ email, password });
    if (err) setError(err.message); else setMessage("注册成功！请检查邮箱确认链接。");
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex">
      {/* Left: Brand */}
      <div className="hidden lg:flex w-1/2 bg-gradient-to-br from-indigo-600 via-purple-600 to-violet-700 items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iMyIvPjwvZz48L2c+PC9zdmc+')] opacity-30" />
        <div className="relative text-white text-center p-12">
          <div className="w-20 h-20 rounded-2xl bg-white/20 backdrop-blur flex items-center justify-center mx-auto mb-6">
            <FileText className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold mb-4 tracking-tight">ResumeAI</h1>
          <p className="text-lg text-indigo-200 max-w-sm mx-auto leading-relaxed">
            AI 驱动的简历优化平台<br />分析 · 评分 · 匹配 · 面试题
          </p>
        </div>
      </div>

      {/* Right: Login */}
      <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-slate-50 to-indigo-50 p-8">
        <Card className="w-full max-w-md border-0 shadow-xl">
          <CardHeader className="text-center pb-2">
            <div className="lg:hidden flex justify-center mb-4">
              <div className="w-12 h-12 rounded-xl bg-indigo-100 flex items-center justify-center">
                <FileText className="w-6 h-6 text-indigo-600" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold">欢迎回来</CardTitle>
            <CardDescription>登录 ResumeAI，继续优化你的简历</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">邮箱</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow" required />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block">密码</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2.5 border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow" required />
              </div>
              {error && <p className="text-red-500 text-sm bg-red-50 rounded-lg p-2.5">{error}</p>}
              {message && <p className="text-green-600 text-sm bg-green-50 rounded-lg p-2.5">{message}</p>}
              <Button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl py-2.5" disabled={loading}>
                {loading ? "登录中..." : "登录"}
              </Button>
            </form>
            <div className="flex gap-2 pt-2">
              <Button variant="outline" className="flex-1 rounded-xl" onClick={handleSignup} disabled={loading}>注册账号</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
