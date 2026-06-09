import { createServerSupabase } from "@/lib/supabase/server";

export async function saveAnalysis(userId: string, data: {
  fileName: string; score: number; strengths: string[];
  weaknesses: string[]; keywords: string[];
  suggestions: any[]; interviewQuestions: any[];
}) {
  const supabase = await createServerSupabase();
  const { error } = await supabase.from("analyses").insert({
    user_id: userId,
    file_name: data.fileName,
    score: data.score,
    strengths: data.strengths,
    weaknesses: data.weaknesses,
    keywords: data.keywords,
    suggestions: data.suggestions,
    interview_questions: data.interviewQuestions,
  });
  if (error) console.error("Save analysis error:", error);
}

export async function getAnalyses(userId: string) {
  const supabase = await createServerSupabase();
  const { data, error } = await supabase
    .from("analyses")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(20);
  if (error) return [];
  return data;
}
