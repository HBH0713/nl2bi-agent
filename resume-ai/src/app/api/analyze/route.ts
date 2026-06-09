import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import { createServerSupabase } from "@/lib/supabase/server";

const client = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY || "sk-placeholder",
  baseURL: process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com",
});

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json({ error: "请上传 PDF 文件" }, { status: 400 });
    }

    // Call Python FastAPI for PDF text extraction (pdfplumber handles Chinese well)
    let pdfText = "";
    try {
      const pythonForm = new FormData();
      pythonForm.append("file", file);
      const pyRes = await fetch("http://127.0.0.1:8000/api/extract-pdf", {
        method: "POST",
        body: pythonForm,
      });
      if (!pyRes.ok) {
        const pyErr = await pyRes.json();
        return NextResponse.json({ error: pyErr.detail || "PDF 解析失败" }, { status: 400 });
      }
      const pyData = await pyRes.json();
      pdfText = pyData.text.slice(0, 5000);
    } catch (e: any) {
      return NextResponse.json({ error: `Python 服务连接失败，请确认 API 已启动` }, { status: 500 });
    }

    if (!pdfText.trim()) {
      return NextResponse.json({ error: "PDF 内容为空" }, { status: 400 });
    }

    // AI Analysis
    const prompt = `你是资深 HR 和简历优化专家。仔细阅读以下简历，必须输出完整 JSON，每个字段都不能是空数组：

{
  "score": 0-100,
  "strengths": ["亮点1", "亮点2", "亮点3"],
  "weaknesses": ["问题1", "问题2", "问题3"],
  "suggestions": [
    {"section": "个人信息/工作经历/项目经验/技能", "original": "原文摘要(20字内)", "improved": "优化后版本", "reason": "为什么改"}
  ],
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "interviewQuestions": [
    {"question": "面试题", "referenceAnswer": "参考回答要点"}
  ]
}

请确保 strengths 至少 3 个、weaknesses 至少 3 个、suggestions 至少 2 个、keywords 至少 3 个、interviewQuestions 至少 2 个。

简历内容：
${pdfText}`;

    const completion = await client.chat.completions.create({
      model: process.env.DEEPSEEK_MODEL || "deepseek-chat",
      messages: [{ role: "user", content: prompt }],
      response_format: { type: "json_object" },
      temperature: 0.3,
      max_tokens: 3000,
    });

    const raw = completion.choices[0]?.message?.content || "{}";
    const analysis = JSON.parse(raw);

    const result = { text: pdfText.slice(0, 500), ...analysis };

    // Save to DB if user is logged in
    try {
      const supabase = await createServerSupabase();
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        await supabase.from("analyses").insert({
          user_id: user.id,
          file_name: file.name,
          score: analysis.score || 0,
          strengths: analysis.strengths || [],
          weaknesses: analysis.weaknesses || [],
          keywords: analysis.keywords || [],
          suggestions: analysis.suggestions || [],
          interview_questions: analysis.interviewQuestions || [],
        });
      }
    } catch (e) { console.error("Save failed:", e); }

    return NextResponse.json(result);
  } catch (error: any) {
    console.error("Analysis error:", error);
    return NextResponse.json(
      { error: error.message || "分析失败，请重试" },
      { status: 500 }
    );
  }
}
