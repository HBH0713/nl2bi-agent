import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { FileText, Target, MessageSquare, TrendingUp } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-8">概览</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[
          { icon: FileText, label: "已分析简历", value: "1", color: "text-blue-500" },
          { icon: Target, label: "平均评分", value: "78", color: "text-green-500" },
          { icon: MessageSquare, label: "面试题库", value: "8", color: "text-purple-500" },
          { icon: TrendingUp, label: "改进幅度", value: "+12%", color: "text-orange-500" },
        ].map((m, i) => (
          <Card key={i}><CardContent className="p-6 flex items-center gap-4">
            <m.icon className={`w-10 h-10 ${m.color}`} />
            <div><p className="text-2xl font-bold">{m.value}</p><p className="text-sm text-muted-foreground">{m.label}</p></div>
          </CardContent></Card>
        ))}
      </div>
      <Card>
        <CardHeader><CardTitle>最近分析</CardTitle><CardDescription>上传简历后在此查看分析历史</CardDescription></CardHeader>
        <CardContent className="text-muted-foreground text-sm">暂无分析记录。点击左侧「分析简历」开始。</CardContent>
      </Card>
    </div>
  );
}
