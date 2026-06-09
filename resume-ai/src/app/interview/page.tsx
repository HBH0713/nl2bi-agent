import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { MessageSquare } from "lucide-react";

export default function InterviewPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-2">面试题库</h1>
      <p className="text-muted-foreground mb-8">根据你的简历自动生成的针对性面试题</p>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><MessageSquare className="w-5 h-5 text-purple-500" />等待分析</CardTitle>
          <CardDescription>上传简历并完成分析后，面试题会自动出现在这里</CardDescription></CardHeader>
        <CardContent className="text-sm text-muted-foreground">暂无面试题。请先到「分析简历」页面提交 PDF。</CardContent>
      </Card>
    </div>
  );
}
