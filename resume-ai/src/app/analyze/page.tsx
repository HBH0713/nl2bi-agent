"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Upload, FileText, Sparkles } from "lucide-react";

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("/api/analyze", { method: "POST", body: formData });
      const data = await res.json();
      // Store result in sessionStorage for the results page
      sessionStorage.setItem("analysisResult", JSON.stringify(data));
      router.push("/results");
    } catch {
      alert("分析失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">分析简历</h1>
      <p className="text-muted-foreground mb-8">上传 PDF 简历，AI 自动提取文字并分析</p>

      <Card className="mb-6 border-2 border-dashed border-slate-200 hover:border-blue-400 transition-colors">
        <CardContent className="p-12">
          <div className="flex flex-col items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center">
              <Upload className="w-7 h-7 text-blue-500" />
            </div>
            <p className="text-lg font-medium">拖拽或选择 PDF 简历文件</p>
            <input type="file" accept=".pdf" className="hidden" id="file-input"
              onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <Button variant="outline" size="lg" onClick={() => document.getElementById("file-input")?.click()}>
              📄 选择文件
            </Button>
            {file && <div className="flex items-center gap-2 text-sm text-green-600 font-medium"><FileText className="w-4 h-4" />{file.name}</div>}
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-center">
        <Button size="lg" disabled={!file || loading} onClick={handleAnalyze} className="px-8 py-6 text-lg">
          <Sparkles className="w-5 h-5 mr-2" />
          {loading ? "分析中..." : "开始 AI 分析"}
        </Button>
      </div>
    </div>
  );
}
