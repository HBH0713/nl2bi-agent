import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { History, TrendingUp, Calendar } from "lucide-react";
import { getAnalyses } from "@/lib/db";
import { createServerSupabase } from "@/lib/supabase/server";

export default async function HistoryPage() {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  const analyses = user ? await getAnalyses(user.id) : [];

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-2">历史记录</h1>
      <p className="text-muted-foreground mb-8">所有简历分析记录，追踪改进历程</p>
      {analyses.length === 0 ? (
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><History className="w-5 h-5 text-slate-500" />暂无记录</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">上传简历并完成分析后，记录会出现在这里。</CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {analyses.map((a: any) => (
            <Card key={a.id}>
              <CardContent className="p-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center">
                    <span className="text-lg font-bold text-blue-600">{a.score}</span>
                  </div>
                  <div>
                    <p className="font-medium">{a.file_name || "未命名"}</p>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1">
                      <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{new Date(a.created_at).toLocaleDateString("zh-CN")}</span>
                      <span className="flex items-center gap-1"><TrendingUp className="w-3 h-3" />{a.keywords?.slice(0, 3).join(", ") || "-"}</span>
                    </div>
                  </div>
                </div>
                <div className="text-2xl font-bold text-blue-600">{a.score}<span className="text-sm font-normal text-muted-foreground">/100</span></div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

