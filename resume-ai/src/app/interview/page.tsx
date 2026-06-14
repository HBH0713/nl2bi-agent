import Link from "next/link";
import { Card, CardContent } from "../../components/ui/card";
import { MessageSquare, Calendar, ArrowLeft, ChevronDown } from "lucide-react";
import { createServerSupabase } from "../../lib/supabase/server";

const palette = ["from-violet-500 to-purple-600","from-emerald-500 to-teal-600","from-amber-500 to-orange-600","from-rose-500 to-pink-600"];

export default async function InterviewPage() {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  let questions: any[] = [];
  if (user) {
    const { data } = await supabase.from("analyses").select("file_name, interview_questions, created_at").eq("user_id", user.id).order("created_at", { ascending: false }).limit(10);
    if (data) questions = data;
  }

  return (
    <div className="p-8 max-w-4xl">
      <Link href="/dashboard" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600 mb-4"><ArrowLeft className="w-3 h-3" />返回</Link>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
          <MessageSquare className="w-5 h-5 text-white" />
        </div>
        <div><h1 className="text-2xl font-bold">面试题库</h1><p className="text-sm text-muted-foreground">根据你的简历自动生成的针对性面试题</p></div>
      </div>

      <div className="mt-8 space-y-6">
        {questions.length === 0 ? (
          <Card className="border-0 shadow-sm">
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-violet-50 flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-8 h-8 text-violet-400" />
              </div>
              <h3 className="text-lg font-semibold text-slate-700 mb-1">等待分析</h3>
              <p className="text-sm text-muted-foreground">上传简历并完成 AI 分析后，面试题会自动出现在这里</p>
            </CardContent>
          </Card>
        ) : questions.map((q: any, qi: number) => {
          const iqs = Array.isArray(q.interview_questions) ? q.interview_questions : [];
          if (iqs.length === 0) return null;
          const grad = palette[qi % palette.length];
          return (
            <Card key={qi} className="border-0 shadow-sm overflow-hidden">
              <div className={`h-1 bg-gradient-to-r ${grad}`} />
              <div className="p-5">
                <div className="flex items-center gap-2 text-sm text-slate-400 mb-4">
                  <Calendar className="w-3.5 h-3.5" />
                  {q.file_name || "简历分析"} · {new Date(q.created_at).toLocaleDateString("zh-CN")} · {iqs.length} 道面试题
                </div>
                <div className="space-y-3">
                  {iqs.map((iq: any, i: number) => (
                    <details key={i} className="group border border-slate-100 rounded-xl p-4 hover:border-indigo-100 transition-colors" open>
                      <summary className="font-medium text-sm cursor-pointer flex items-center justify-between">
                        <span className="flex items-center gap-2">
                          <span className={`w-6 h-6 rounded-lg bg-gradient-to-br ${grad} flex items-center justify-center text-white text-xs font-bold`}>{i + 1}</span>
                          {iq.question}
                        </span>
                        <ChevronDown className="w-4 h-4 text-slate-300 group-open:rotate-180 transition-transform" />
                      </summary>
                      <p className="text-sm text-slate-600 mt-3 pl-8 border-l-2 border-indigo-200 ml-3">{iq.referenceAnswer}</p>
                    </details>
                  ))}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
