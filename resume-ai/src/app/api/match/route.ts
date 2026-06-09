import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY || "sk-placeholder",
  baseURL: process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com",
});

export async function POST(req: NextRequest) {
  try {
    const { resumeText, jdText } = await req.json();
    if (!resumeText || !jdText) {
      return NextResponse.json({ error: "请提供简历文本和 JD 文本" }, { status: 400 });
    }

    const prompt = `你是资深招聘专家。对比以下简历和职位描述(JD)，输出 JSON：

{
  "matchScore": 0-100 的整体匹配度,
  "matchedKeywords": ["JD中提到的且简历有的关键词"],
  "missingKeywords": ["JD要求但简历缺少的关键词"],
  "strengthAreas": [{ "requirement": "JD要求", "evidence": "简历中的证据", "score": 8 }],
  "gapAreas": [{ "requirement": "JD要求", "gap": "具体差距", "suggestion": "如何弥补" }],
  "tailoredBullets": ["针对此JD优化的简历要点1", "要点2"],
  "interviewTips": ["面试准备建议1", "准备建议2"]
}

简历：
${resumeText.slice(0, 3000)}

职位描述(JD)：
${jdText.slice(0, 2000)}`;

    const completion = await client.chat.completions.create({
      model: process.env.DEEPSEEK_MODEL || "deepseek-chat",
      messages: [{ role: "user", content: prompt }],
      response_format: { type: "json_object" },
      temperature: 0.3,
      max_tokens: 2500,
    });

    const raw = completion.choices[0]?.message?.content || "{}";
    return NextResponse.json(JSON.parse(raw));
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
