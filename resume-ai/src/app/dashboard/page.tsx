import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { FileText, Target, MessageSquare, TrendingUp, Sparkles, ArrowRight } from "lucide-react";
import { createServerSupabase } from "../../lib/supabase/server";
import Link from "next/link";

async function getStats(userId: string) {
  const supabase = await createServerSupabase();
  const { data, error } = await supabase
    .from("analyses")
    .select("score, interview_questions")
    .eq("user_id", userId);
  if (error || !data) return { count: 0, avgScore: null, totalQuestions: 0 };
  const count = data.length;
  const scores = data.map((r: any) => r.score).filter((s: any) => typeof s === "number");
  const avgScore = scores.length > 0 ? Math.round(scores.reduce((a: number, b: number) => a + b, 0) / scores.length) : null;
  const totalQuestions = data.reduce((sum: number, r: any) => {
    const qs = Array.isArray(r.interview_questions) ? r.interview_questions.length : 0;
    return sum + qs;
  }, 0);
  return { count, avgScore, totalQuestions };
}

export default async function DashboardPage() {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  const stats = user ? await getStats(user.id) : { count: 0, avgScore: null, totalQuestions: 0 };

  const cards = [
    { icon: FileText, label: "已分析简历", value: `${stats.count}`, color: "from-violet-500 to-purple-600", bg: "bg-violet-50", text: "text-violet-600" },
    { icon: Target, label: "平均评分", value: stats.avgScore !== null ? `${stats.avgScore}` : "—", color: "from-amber-500 to-orange-600", bg: "bg-amber-50", text: "text-amber-600" },
    { icon: MessageSquare, label: "面试题库", value: `${stats.totalQuestions} 题`, color: "from-emerald-500 to-teal-600", bg: "bg-emerald-50", text: "text-emerald-600" },
    { icon: TrendingUp, label: "改进建议", value: `${stats.count * 2}+`, color: "from-rose-500 to-pink-600", bg: "bg-rose-50", text: "text-rose-600" },
  ];

  const actions = [
    { icon: Sparkles, title: "分析简历", desc: "上传 PDF，AI 评分 + 优化建议", href: "/analyze", color: "bg-indigo-50 text-indigo-600 hover:bg-indigo-100" },
    { icon: FileText, title: "编辑简历", desc: "在线编辑器，多模板 + 导出 PDF", href: "/builder", color: "bg-emerald-50 text-emerald-600 hover:bg-emerald-100" },
    { icon: MessageSquare, title: "面试题库", desc: "根据简历生成针对性面试题", href: "/interview", color: "bg-amber-50 text-amber-600 hover:bg-amber-100" },
  ];

  return (
    <div>
      {/* Hero */}
      <div className="relative overflow-hidden bg-gradient-to-br from-indigo-600 via-purple-600 to-violet-700 text-white">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-30" />
        <div className="relative px-8 py-12 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-2">ResumeAI 控制台</h1>
            <p className="text-indigo-200 text-sm max-w-lg">AI 驱动的简历优化平台 — 上传简历、智能评分、JD 匹配、面试题生成，助你拿到心仪 offer</p>
          </div>
          {user && (
            <span className="text-xs text-indigo-200 bg-white/10 rounded-full px-3 py-1 backdrop-blur">
              {user.email}
            </span>
          )}
        </div>
      </div>

      <div className="p-8 space-y-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {cards.map((s, i) => {
            const Icon = s.icon;
            return (
              <Card key={i} className="group hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 border-0 shadow-sm">
                <CardContent className="p-5 flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl ${s.bg} flex items-center justify-center group-hover:scale-110 transition-transform`}>
                    <Icon className={`w-6 h-6 ${s.text}`} />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{s.value}</p>
                    <p className="text-xs text-muted-foreground">{s.label}</p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="text-lg font-bold text-slate-800 mb-4">快速操作</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {actions.map((a, i) => {
              const Icon = a.icon;
              return (
                <Link key={i} href={a.href}>
                  <Card className="group hover:shadow-lg transition-all duration-200 hover:-translate-y-1 border-0 shadow-sm cursor-pointer h-full">
                    <CardContent className="p-6">
                      <div className={`w-10 h-10 rounded-lg ${a.color} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <CardTitle className="text-base mb-1">{a.title}</CardTitle>
                      <CardDescription className="text-xs">{a.desc}</CardDescription>
                      <div className="flex items-center gap-1 text-xs text-indigo-500 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                        开始使用 <ArrowRight className="w-3 h-3" />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Recent */}
        <Card className="border-0 shadow-sm">
          <CardHeader><CardTitle>最近分析</CardTitle><CardDescription>上传简历后，分析记录和面试题会在这里展示</CardDescription></CardHeader>
          <CardContent>
            <Link href="/history" className="text-sm text-indigo-500 hover:underline inline-flex items-center gap-1">
              查看历史记录 ({stats.count}) <ArrowRight className="w-3 h-3" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
