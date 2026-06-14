"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Upload, FileText, Sparkles, ArrowLeft, FileSearch } from "lucide-react";

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const router = useRouter();

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData(); formData.append("file", file);
    try {
      const res = await fetch("/api/analyze", { method: "POST", body: formData });
      const data = await res.json();
      sessionStorage.setItem("analysisResult", JSON.stringify(data));
      router.push("/results");
    } catch { alert("分析失败"); }
    finally { setLoading(false); }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <Link href="/dashboard" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600 mb-6"><ArrowLeft className="w-3 h-3" />返回</Link>
      
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
          <FileSearch className="w-5 h-5 text-white" />
        </div>
        <div><h1 className="text-2xl font-bold">分析简历</h1><p className="text-sm text-muted-foreground">上传 PDF 简历，AI 自动提取文字并分析</p></div>
      </div>

      <Card className={`mb-6 border-2 border-dashed transition-all duration-200 ${dragOver ? "border-indigo-400 bg-indigo-50/50 scale-[1.01]" : "border-slate-200 hover:border-indigo-300"} shadow-sm`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f?.type === "application/pdf") setFile(f); }}>
        <CardContent className="p-12">
          <div className="flex flex-col items-center gap-4">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors ${dragOver ? "bg-indigo-100" : "bg-indigo-50"}`}>
              <Upload className={`w-8 h-8 transition-colors ${dragOver ? "text-indigo-500" : "text-indigo-400"}`} />
            </div>
            <div className="text-center">
              <p className="text-lg font-medium text-slate-700">拖拽 PDF 简历到此处</p>
              <p className="text-sm text-muted-foreground mt-1">或点击下方按钮选择文件</p>
            </div>
            <input type="file" accept=".pdf" className="hidden" id="file-input"
              onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <Button variant="outline" size="lg" className="rounded-xl" onClick={() => document.getElementById("file-input")?.click()}>
              📄 选择 PDF 文件
            </Button>
            {file && (
              <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-xl text-sm font-medium">
                <FileText className="w-4 h-4" />{file.name} ({(file.size / 1024).toFixed(0)} KB)
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-center">
        <Button size="lg" disabled={!file || loading} onClick={handleAnalyze}
          className="px-8 py-6 text-lg rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 transition-all shadow-lg hover:shadow-xl disabled:opacity-50">
          <Sparkles className="w-5 h-5 mr-2" />
          {loading ? "AI 分析中..." : "开始 AI 分析"}
        </Button>
      </div>
    </div>
  );
}
