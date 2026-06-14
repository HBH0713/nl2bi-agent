import { Card, CardContent } from "../../components/ui/card";
import { TrendingUp, Calendar, ArrowLeft, FileText, Target } from "lucide-react";
import { getAnalyses } from "../../lib/db";
import { createServerSupabase } from "../../lib/supabase/server";
import Link from "next/link";

const scoreColor = (s: number) => s >= 80 ? "bg-emerald-50 text-emerald-700" : s >= 60 ? "bg-amber-50 text-amber-700" : "bg-rose-50 text-rose-700";
const scoreGrad = (s: number) => s >= 80 ? "from-emerald-500 to-teal-500" : s >= 60 ? "from-amber-500 to-orange-500" : "from-rose-500 to-pink-500";

export default async function HistoryPage() {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  const analyses = user ? await getAnalyses(user.id) : [];

  return (
    <div className="p-8 max-w-4xl">
      <Link href="/dashboard" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600 mb-4"><ArrowLeft className="w-3 h-3" />返回</Link>
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
          <TrendingUp className="w-5 h-5 text-white" />
        </div>
        <div><h1 className="text-2xl font-bold">历史记录</h1><p className="text-sm text-muted-foreground">所有简历分析记录，点击查看详情</p></div>
      </div>

      {analyses.length === 0 ? (
        <Card className="border-0 shadow-sm"><CardContent className="p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 flex items-center justify-center mx-auto mb-4"><FileText className="w-8 h-8 text-indigo-400" /></div>
          <h3 className="text-lg font-semibold text-slate-700 mb-1">暂无记录</h3>
          <p className="text-sm text-muted-foreground">上传简历并完成分析后，记录会出现在这里。</p>
        </CardContent></Card>
      ) : (
        <div className="space-y-3">
          {analyses.map((a: any, i: number) => (
            <Link key={a.id} href={`/history/${a.id}`}>
              <Card className="group border-0 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer overflow-hidden">
                <div className="flex">
                  <div className={`w-1.5 bg-gradient-to-b ${scoreGrad(a.score || 0)}`} />
                  <CardContent className="p-5 flex items-center justify-between flex-1">
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-xl ${scoreColor(a.score || 0)} flex items-center justify-center font-bold text-lg`}>
                        {a.score || "-"}
                      </div>
                      <div>
                        <p className="font-medium text-slate-800">{a.file_name || "未命名"}</p>
                        <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                          <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{new Date(a.created_at).toLocaleDateString("zh-CN")}</span>
                          {a.keywords?.length > 0 && <span className="flex items-center gap-1"><Target className="w-3 h-3" />{a.keywords.slice(0, 3).join(", ")}</span>}
                        </div>
                      </div>
                    </div>
                    <span className="text-xs text-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity font-medium">
                      查看详情 →
                    </span>
                  </CardContent>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
