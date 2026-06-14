import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { createServerSupabase } from "../../../lib/supabase/server";
import { Target, AlertCircle, Lightbulb, MessageSquare, ArrowLeft, Calendar } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

export default async function HistoryDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return notFound();

  const { data: analyses } = await supabase.from("analyses").select("*").eq("id", id).eq("user_id", user.id).single();
  if (!analyses) return notFound();

  const a: any = analyses;
  const iqs = Array.isArray(a.interview_questions) ? a.interview_questions : [];
  const suggestions = Array.isArray(a.suggestions) ? a.suggestions : [];

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <Link href="/history" className="flex items-center gap-2 text-sm text-blue-600 hover:underline mb-4">
        <ArrowLeft className="w-4 h-4" />返回历史记录
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{a.file_name || "简历分析"}</h1>
          <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
            <Calendar className="w-3 h-3" />{new Date(a.created_at).toLocaleDateString("zh-CN")}
          </p>
        </div>
        {a.score != null && (
          <div className="w-20 h-20 rounded-full bg-blue-50 flex items-center justify-center">
            <span className="text-2xl font-bold text-blue-600">{a.score}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card><CardHeader><CardTitle className="flex items-center gap-2"><Target className="w-4 h-4 text-green-500" />亮点</CardTitle></CardHeader>
          <CardContent><ul className="space-y-2">{a.strengths?.map((s: string, i: number) => <li key={i} className="text-sm flex gap-2"><span className="text-green-500">✓</span> {s}</li>)}</ul></CardContent></Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2"><AlertCircle className="w-4 h-4 text-orange-500" />待改进</CardTitle></CardHeader>
          <CardContent><ul className="space-y-2">{a.weaknesses?.map((w: string, i: number) => <li key={i} className="text-sm flex gap-2"><span className="text-orange-500">!</span> {w}</li>)}</ul></CardContent></Card>
      </div>

      {suggestions.length > 0 && (
        <Card><CardHeader><CardTitle className="flex items-center gap-2"><Lightbulb className="w-4 h-4 text-yellow-500" />优化建议</CardTitle></CardHeader>
          <CardContent className="space-y-3">{suggestions.map((s: any, i: number) => (
            <div key={i} className="border rounded-lg p-3">
              <div className="text-sm font-medium text-blue-600 mb-1">{s.section}</div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="bg-red-50 rounded p-2 text-red-400 line-through">{s.original}</div>
                <div className="bg-green-50 rounded p-2 text-green-700">{s.improved}</div>
              </div>
              <div className="text-xs text-muted-foreground mt-1">💡 {s.reason}</div>
            </div>
          ))}</CardContent></Card>
      )}

      {a.keywords?.length > 0 && (
        <Card><CardHeader><CardTitle>🏷 关键词</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-2">{a.keywords.map((k: string, i: number) => (
            <span key={i} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm">{k}</span>
          ))}</CardContent></Card>
      )}

      {iqs.length > 0 && (
        <Card><CardHeader><CardTitle className="flex items-center gap-2"><MessageSquare className="w-4 h-4 text-purple-500" />面试题</CardTitle></CardHeader>
          <CardContent className="space-y-3">{iqs.map((iq: any, i: number) => (
            <details key={i} className="border rounded-lg p-4" open>
              <summary className="font-medium">{i + 1}. {iq.question}</summary>
              <p className="text-sm text-muted-foreground mt-2 pl-3 border-l-2 border-purple-200">{iq.referenceAnswer}</p>
            </details>
          ))}</CardContent></Card>
      )}
    </div>
  );
}
