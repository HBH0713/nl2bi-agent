"use client";

import { useEffect, useState } from "react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Target, AlertCircle, Lightbulb, MessageSquare, Briefcase, TrendingUp } from "lucide-react";

/* eslint-disable @typescript-eslint/no-explicit-any */
interface AnalysisResult {
  text?: string; score?: number; strengths?: string[]; weaknesses?: string[];
  suggestions?: { section: string; original: string; improved: string; reason: string }[];
  keywords?: string[]; interviewQuestions?: { question: string; referenceAnswer: string }[];
  error?: string;
}

/* eslint-disable @typescript-eslint/no-explicit-any */
interface MatchResult {
  matchScore?: number; matchedKeywords?: string[]; missingKeywords?: string[];
  strengthAreas?: { requirement: string; evidence: string; score: number }[];
  gapAreas?: { requirement: string; gap: string; suggestion: string }[];
  tailoredBullets?: string[]; interviewTips?: string[]; error?: string;
}

export default function ResultsPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [jdText, setJdText] = useState("");
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [matching, setMatching] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("analysisResult");
    if (raw) {
      const parsed = JSON.parse(raw);
      setTimeout(() => setResult(parsed), 0);
    }
  }, []);

  const handleMatch = async () => {
    if (!jdText.trim()) return;
    setMatching(true);
    try {
      const res = await fetch("/api/match", {
        method: "POST",
        body: JSON.stringify({ resumeText: result?.text || "", jdText }),
        headers: { "Content-Type": "application/json" },
      });
      setMatchResult(await res.json());
    } catch { setMatchResult({ error: "匹配失败" }); }
    finally { setMatching(false); }
  };

  if (!result) return <div className="p-8 text-muted-foreground">暂无分析结果，请先上传简历</div>;
  if (result.error) return <Card className="m-8"><CardContent className="p-6 text-red-500">❌ {result.error}</CardContent></Card>;

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">分析结果</h1>

      {result.score != null && (
        <Card><CardContent className="p-6 flex items-center gap-6">
          <div className="w-24 h-24 rounded-full bg-blue-50 flex items-center justify-center"><span className="text-3xl font-bold text-blue-600">{result.score}</span></div>
          <div><h2 className="text-xl font-bold">ATS 综合评分</h2><p className="text-sm text-muted-foreground">{result.score >= 80 ? "简历质量较高" : result.score >= 60 ? "有提升空间" : "建议重点优化"}</p></div>
        </CardContent></Card>
      )}

      <div className="grid grid-cols-2 gap-6">
        <Card><CardHeader><CardTitle className="flex items-center gap-2"><Target className="w-5 h-5 text-green-500" />亮点</CardTitle></CardHeader>
          <CardContent><ul className="space-y-2">{result.strengths?.map((s, i) => <li key={i} className="text-sm flex gap-2"><span className="text-green-500">✓</span> {s}</li>)}</ul></CardContent></Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2"><AlertCircle className="w-5 h-5 text-orange-500" />待改进</CardTitle></CardHeader>
          <CardContent><ul className="space-y-2">{result.weaknesses?.map((w, i) => <li key={i} className="text-sm flex gap-2"><span className="text-orange-500">!</span> {w}</li>)}</ul></CardContent></Card>
      </div>

      {/* JD Matching */}
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Briefcase className="w-5 h-5 text-indigo-500" />职位匹配分析</CardTitle></CardHeader>
        <CardContent>
          <textarea value={jdText} onChange={(e) => setJdText(e.target.value)}
            className="w-full p-3 border rounded-lg text-sm min-h-[120px] focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="粘贴目标职位的 JD（职位描述），AI 会对比你的简历给出匹配度分析..." />
          <Button onClick={handleMatch} disabled={!jdText.trim() || matching} className="mt-3">
            <Briefcase className="w-4 h-4 mr-2" />{matching ? "匹配中..." : "开始匹配分析"}
          </Button>
        </CardContent>
      </Card>

      {matchResult && !matchResult.error && (
        <div className="space-y-4">
          {matchResult.matchScore != null && (
            <Card><CardContent className="p-6 flex items-center gap-6">
              <div className="w-24 h-24 rounded-full bg-indigo-50 flex items-center justify-center"><span className="text-3xl font-bold text-indigo-600">{matchResult.matchScore}%</span></div>
              <div><h2 className="text-xl font-bold">岗位匹配度</h2><p className="text-sm text-muted-foreground">{matchResult.matchScore >= 70 ? "匹配度较高" : matchResult.matchScore >= 50 ? "有一定差距" : "需要重点提升"}</p></div>
            </CardContent></Card>
          )}
          <div className="grid grid-cols-2 gap-4">
            {matchResult.matchedKeywords && (
              <Card><CardHeader><CardTitle>✅ 匹配关键词</CardTitle></CardHeader>
                <CardContent className="flex flex-wrap gap-2">{matchResult.matchedKeywords.map((k, i) => <span key={i} className="px-2 py-1 bg-green-50 text-green-700 rounded text-sm">{k}</span>)}</CardContent></Card>)}
            {matchResult.missingKeywords && (
              <Card><CardHeader><CardTitle>❌ 缺失关键词</CardTitle></CardHeader>
                <CardContent className="flex flex-wrap gap-2">{matchResult.missingKeywords.map((k, i) => <span key={i} className="px-2 py-1 bg-red-50 text-red-600 rounded text-sm">{k}</span>)}</CardContent></Card>)}
          </div>
          {matchResult.tailoredBullets && (
            <Card><CardHeader><CardTitle>📝 针对此 JD 的优化要点</CardTitle></CardHeader>
              <CardContent><ul className="space-y-1">{matchResult.tailoredBullets.map((b, i) => <li key={i} className="text-sm">• {b}</li>)}</ul></CardContent></Card>)}
          {matchResult.interviewTips && (
            <Card><CardHeader><CardTitle>🎯 面试准备建议</CardTitle></CardHeader>
              <CardContent><ul className="space-y-1">{matchResult.interviewTips.map((t, i) => <li key={i} className="text-sm">• {t}</li>)}</ul></CardContent></Card>)}
        </div>
      )}

      {/* Original suggestions, keywords, interview */}
      {/* ...rest of original analysis sections... */}
    </div>
  );
}
