"use client";

import { useState } from "react";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import Link from "next/link";
import { Plus, Trash2, Download, ChevronUp, ChevronDown, ArrowLeft } from "lucide-react";

type Template = "blue" | "dark" | "green";
type FontChoice = "sans" | "serif" | "mono";

const THEMES: Record<Template, { primary: string; light: string; accent: string }> = {
  blue:   { primary: "#2563eb", light: "#eef2ff", accent: "#1e40af" },
  dark:   { primary: "#1f2937", light: "#f3f4f6", accent: "#111827" },
  green:  { primary: "#059669", light: "#ecfdf5", accent: "#065f46" },
};

const FONTS: Record<FontChoice, string> = {
  sans: "'Segoe UI', system-ui, sans-serif",
  serif: "Georgia, 'Times New Roman', serif",
  mono: "'JetBrains Mono', 'Courier New', monospace",
};

const TIPS: Record<string, string> = {
  summary: "💡 用 2–3 句话总结你的核心优势，突出年限、关键技能、代表作",
  experience: "💡 每段经历用 STAR 法则：情境 → 任务 → 行动 → 结果",
  bullets: "💡 每行一个量化成果，例如：\"将 API 响应时间从 200ms 降到 30ms\"",
  skills: "💡 按熟练度排序，最擅长的放前面。逗号或顿号分隔",
  education: "💡 列出最高学历即可，应届生可加上 GPA 和相关课程",
  projects: "💡 选 2–3 个最有代表性的项目，突出技术栈和个人贡献",
};

interface ResumeSection { id: string; label: string; visible: boolean; order: number }

interface ResumeData {
  name: string; title: string; email: string; phone: string; location: string; website: string;
  summary: string;
  experience: { company: string; role: string; dates: string; bullets: string }[];
  education: { school: string; degree: string; year: string }[];
  skills: string;
  projects: { name: string; desc: string; tech: string }[];
}

const emptyData: ResumeData = {
  name: "", title: "", email: "", phone: "", location: "", website: "",
  summary: "",
  experience: [{ company: "", role: "", dates: "", bullets: "" }],
  education: [{ school: "", degree: "", year: "" }],
  skills: "",
  projects: [{ name: "", desc: "", tech: "" }],
};

export default function BuilderPage() {
  const [data, setData] = useState<ResumeData>(emptyData);
  const [tab, setTab] = useState("info");
  const [template, setTemplate] = useState<Template>("blue");
  const [font, setFont] = useState<FontChoice>("sans");
  const [showTips, setShowTips] = useState(true);

  const update = (key: keyof ResumeData, val: any) => setData({ ...data, [key]: val });
  const t = THEMES[template];
  const f = FONTS[font];

  const addExp = () => update("experience", [...data.experience, { company: "", role: "", dates: "", bullets: "" }]);
  const addEdu = () => update("education", [...data.education, { school: "", degree: "", year: "" }]);
  const addProj = () => update("projects", [...data.projects, { name: "", desc: "", tech: "" }]);

  const moveExp = (i: number, dir: number) => {
    if (i + dir < 0 || i + dir >= data.experience.length) return;
    const n = [...data.experience]; [n[i], n[i + dir]] = [n[i + dir], n[i]]; update("experience", n);
  };

  const handlePrint = () => {
    const w = window.open("", "_blank"); if (!w) return;
    const hasExp = data.experience.some(e => e.company);
    const hasEdu = data.education.some(e => e.school);
    const hasProj = data.projects.some(p => p.name);
    const contactLine = [data.email, data.phone, data.location, data.website].filter(Boolean).join(" · ");
    const skillList = data.skills.split(/[,，]/).filter(Boolean).map(s => s.trim());

    w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${data.name || "简历"}</title><style>
      @page{size:A4;margin:18mm 16mm}
      body{font-family:${f};max-width:700px;margin:0 auto;color:#1a1a1a;line-height:1.55}
      h1{margin:0;font-size:26px;font-weight:700;color:${t.accent}}
      h2{font-size:13px;color:#555;margin:3px 0 14px;font-weight:400}
      h3{border-bottom:2px solid ${t.primary};padding-bottom:3px;font-size:14px;margin:18px 0 8px;font-weight:700;color:${t.accent};text-transform:uppercase;letter-spacing:1px}
      .exp{margin-bottom:10px}.exp-title{font-weight:600;font-size:14px}.exp-meta{color:#666;font-size:12px;margin-bottom:3px}
      ul{margin:3px 0;padding-left:18px}li{font-size:13px;margin:1px 0}
      .skills{display:flex;flex-wrap:wrap;gap:5px;margin-top:4px}.skill{background:${t.light};color:${t.accent};padding:2px 10px;border-radius:10px;font-size:12px;font-weight:500}
      @media print{body{margin:0;padding:0}}
    </style></head><body>
      <h1>${data.name || ""}</h1><h2>${[data.title, contactLine].filter(Boolean).join(" · ")}</h2>
      ${data.summary ? `<p style="font-size:13px;margin-bottom:14px">${data.summary}</p>` : ""}
      ${hasExp ? `<h3>工作经历</h3>${data.experience.filter(e => e.company).map(e => `<div class="exp"><div class="exp-title">${e.role} — ${e.company}</div><div class="exp-meta">${e.dates}</div><ul>${e.bullets.split("\n").filter(Boolean).map(b => `<li>${b}</li>`).join("")}</ul></div>`).join("")}` : ""}
      ${hasEdu ? `<h3>教育背景</h3>${data.education.filter(e => e.school).map(e => `<div class="exp"><div class="exp-title">${e.school}</div><div class="exp-meta">${e.degree}${e.degree&&e.year?" · ":""}${e.year}</div></div>`).join("")}` : ""}
      ${skillList.length>0 ? `<h3>技能</h3><div class="skills">${skillList.map(s => `<span class="skill">${s}</span>`).join("")}</div>` : ""}
      ${hasProj ? `<h3>项目经验</h3>${data.projects.filter(p => p.name).map(p => `<div class="exp"><div class="exp-title">${p.name}</div><div class="exp-meta">${p.tech}</div><p style="font-size:13px;margin:3px 0">${p.desc}</p></div>`).join("")}` : ""}
      <script>window.print();setTimeout(()=>window.close(),800)</script>
    </body></html>`);
    w.document.close();
  };

  const input = "w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors";
  const label = "text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5 block";

  return (
    <div className="flex h-[calc(100vh-0px)]">
      {/* Left: Form */}
      <div className="w-[500px] overflow-y-auto p-6 border-r bg-white">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-5 flex-wrap gap-2">
          <Link href="/dashboard" className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600"><ArrowLeft className="w-3 h-3" />返回</Link><h1 className="text-lg font-bold">编辑简历</h1>
          <div className="flex gap-2">
            <Button onClick={handlePrint} size="sm" style={{background:t.primary}}><Download className="w-3.5 h-3.5 mr-1" />导出 PDF</Button>
            <button onClick={() => setShowTips(!showTips)} className="text-xs text-slate-400 hover:text-slate-600">{showTips ? "隐藏提示" : "显示提示"}</button>
          </div>
        </div>

        {/* Template & Font */}
        <div className="flex gap-3 mb-5">
          <div>
            <span className="text-xs text-slate-400 mr-2">模板</span>
            {(["blue","dark","green"] as Template[]).map(c => (
              <button key={c} onClick={() => setTemplate(c)}
                className={`w-5 h-5 rounded-full mr-1 border-2 ${template===c?"border-slate-600":"border-transparent"}`}
                style={{background:THEMES[c].primary}} title={c} />
            ))}
          </div>
          <select value={font} onChange={e => setFont(e.target.value as FontChoice)}
            className="text-xs border rounded px-2 py-1">
            <option value="sans">无衬线</option><option value="serif">衬线</option><option value="mono">等宽</option>
          </select>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b pb-3">
          {[
            {key:"info",label:"基本信息",icon:"👤"},
            {key:"exp",label:"经历",icon:"💼"},
            {key:"edu",label:"教育",icon:"🎓"},
            {key:"skills",label:"技能",icon:"⚡"},
            {key:"proj",label:"项目",icon:"🚀"},
          ].map(({key,label,icon}) => (
            <button key={key} onClick={() => setTab(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${tab===key?"text-white":"text-slate-500 hover:bg-slate-100"}`}
              style={tab===key?{background:t.primary}:{}}>{icon} {label}</button>
          ))}
        </div>

        {/* Tips */}
        {showTips && TIPS[tab] && <div className="text-xs text-slate-500 bg-slate-50 rounded-lg p-2.5 mb-4 leading-relaxed">{TIPS[tab]}</div>}

        {/* info */}
        {tab==="info" && <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><label className={label}>姓名 *</label><input className={input} value={data.name} onChange={e=>update("name",e.target.value)} placeholder="张三" style={{borderColor: !data.name ? "#fca5a5" : ""}} /></div>
            <div><label className={label}>职位</label><input className={input} value={data.title} onChange={e=>update("title",e.target.value)} placeholder="全栈开发工程师" /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={label}>邮箱</label><input className={input} value={data.email} onChange={e=>update("email",e.target.value)} placeholder="zhang@example.com" /></div>
            <div><label className={label}>电话</label><input className={input} value={data.phone} onChange={e=>update("phone",e.target.value)} placeholder="138xxxx" /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={label}>城市</label><input className={input} value={data.location} onChange={e=>update("location",e.target.value)} placeholder="北京" /></div>
            <div><label className={label}>个人网站/GitHub</label><input className={input} value={data.website} onChange={e=>update("website",e.target.value)} placeholder="github.com/xxx" /></div>
          </div>
          <div>
            <label className={label}>个人总结</label>
            <textarea className={input} rows={3} value={data.summary} onChange={e=>update("summary",e.target.value)}
              placeholder="3年全栈开发经验，主导过从0到1的SaaS产品..." />
            <div className="text-right text-xs text-slate-400 mt-1">{data.summary.length}/600</div>
          </div>
        </div>}

        {/* experience */}
        {tab==="exp" && <div className="space-y-3">
          {data.experience.map((exp,i) => (
            <Card key={i}><CardContent className="p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase">经历 #{i+1}</span>
                <div className="flex gap-1">
                  <button onClick={()=>moveExp(i,-1)} disabled={i===0} className="disabled:opacity-30"><ChevronUp className="w-3 h-3" /></button>
                  <button onClick={()=>moveExp(i,1)} disabled={i===data.experience.length-1} className="disabled:opacity-30"><ChevronDown className="w-3 h-3" /></button>
                  {data.experience.length>1 && <button onClick={()=>update("experience",data.experience.filter((_,j)=>j!==i))}><Trash2 className="w-3 h-3 text-red-400" /></button>}
                </div>
              </div>
              <input className={input} value={exp.company} onChange={e=>{const n=[...data.experience];n[i]={...n[i],company:e.target.value};update("experience",n)}} placeholder="公司名称" />
              <div className="grid grid-cols-2 gap-2">
                <input className={input} value={exp.role} onChange={e=>{const n=[...data.experience];n[i]={...n[i],role:e.target.value};update("experience",n)}} placeholder="职位" />
                <input className={input} value={exp.dates} onChange={e=>{const n=[...data.experience];n[i]={...n[i],dates:e.target.value};update("experience",n)}} placeholder="2021.06 - 2024.01" />
              </div>
              <textarea className={input} rows={3} value={exp.bullets} onChange={e=>{const n=[...data.experience];n[i]={...n[i],bullets:e.target.value};update("experience",n)}} placeholder="每行一个量化成果&#10;将 API 延迟降低 40%&#10;主导 3 人团队完成..." />
            </CardContent></Card>
          ))}
          <Button variant="outline" size="sm" onClick={addExp} className="w-full text-xs"><Plus className="w-3 h-3 mr-1" />添加经历</Button>
        </div>}

        {/* education */}
        {tab==="edu" && <div className="space-y-3">
          {data.education.map((edu,i) => (
            <Card key={i}><CardContent className="p-3 space-y-2">
              <input className={input} value={edu.school} onChange={e=>{const n=[...data.education];n[i]={...n[i],school:e.target.value};update("education",n)}} placeholder="学校名称" />
              <div className="grid grid-cols-2 gap-2">
                <input className={input} value={edu.degree} onChange={e=>{const n=[...data.education];n[i]={...n[i],degree:e.target.value};update("education",n)}} placeholder="计算机科学 本科" />
                <input className={input} value={edu.year} onChange={e=>{const n=[...data.education];n[i]={...n[i],year:e.target.value};update("education",n)}} placeholder="2024" />
              </div>
            </CardContent></Card>
          ))}
          <Button variant="outline" size="sm" onClick={addEdu} className="w-full text-xs"><Plus className="w-3 h-3 mr-1" />添加教育</Button>
        </div>}

        {/* skills */}
        {tab==="skills" && <div>
          <label className={label}>技术技能（逗号分隔，按熟练度排序）</label>
          <textarea className={input} rows={3} value={data.skills} onChange={e=>update("skills",e.target.value)}
            placeholder="Python, React, TypeScript, PostgreSQL, Docker, AWS, Git" />
          {data.skills && <div className="flex flex-wrap gap-1.5 mt-3">
            {data.skills.split(/[,，]/).filter(Boolean).map((s,i) => (
              <span key={i} className="px-2 py-0.5 text-xs rounded-full font-medium" style={{background:t.light,color:t.accent}}>{s.trim()}</span>
            ))}
          </div>}
        </div>}

        {/* projects */}
        {tab==="proj" && <div className="space-y-3">
          {data.projects.map((p,i) => (
            <Card key={i}><CardContent className="p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase">项目 #{i+1}</span>
                {data.projects.length>1 && <button onClick={()=>update("projects",data.projects.filter((_,j)=>j!==i))}><Trash2 className="w-3 h-3 text-red-400" /></button>}
              </div>
              <input className={input} value={p.name} onChange={e=>{const n=[...data.projects];n[i]={...n[i],name:e.target.value};update("projects",n)}} placeholder="NL2BI Agent — 自然语言数据分析平台" />
              <input className={input} value={p.tech} onChange={e=>{const n=[...data.projects];n[i]={...n[i],tech:e.target.value};update("projects",n)}} placeholder="Python, LangGraph, FastAPI, PostgreSQL" />
              <textarea className={input} rows={2} value={p.desc} onChange={e=>{const n=[...data.projects];n[i]={...n[i],desc:e.target.value};update("projects",n)}} placeholder="一句话描述项目成果和你的贡献" />
            </CardContent></Card>
          ))}
          <Button variant="outline" size="sm" onClick={addProj} className="w-full text-xs"><Plus className="w-3 h-3 mr-1" />添加项目</Button>
        </div>}
      </div>

      {/* Right: Preview */}
      <div className="flex-1 bg-slate-200 overflow-y-auto p-8 flex items-start justify-center">
        <div className="w-full max-w-[210mm] bg-white shadow-xl min-h-[297mm] p-10" style={{fontFamily:f,color:"#1a1a1a",lineHeight:1.55}}>
          {/* Header */}
          <h1 style={{margin:0,fontSize:26,fontWeight:700,color:t.accent}}>{data.name||"你的姓名"}</h1>
          <p style={{fontSize:13,color:"#555",margin:"3px 0 14px"}}>
            {[data.title,[data.email,data.phone,data.location,data.website].filter(Boolean).join(" · ")].filter(Boolean).join(" · ")}
          </p>
          {data.summary&&<p style={{fontSize:13,marginBottom:14}}>{data.summary}</p>}

          {/* Experience */}
          {data.experience.some(e=>e.company) && <>
            <h3 style={{borderBottom:`2px solid ${t.primary}`,paddingBottom:3,fontSize:13,fontWeight:700,margin:"18px 0 8px",color:t.accent,textTransform:"uppercase",letterSpacing:1}}>工作经历</h3>
            {data.experience.filter(e=>e.company).map((e,i) => (
              <div key={i} style={{marginBottom:10}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline"}}>
                  <span style={{fontWeight:600,fontSize:14}}>{e.role||"职位"} — {e.company}</span>
                  <span style={{color:"#888",fontSize:12}}>{e.dates}</span>
                </div>
                {e.bullets&&<ul style={{margin:"4px 0",paddingLeft:18}}>{e.bullets.split("\n").filter(Boolean).map((b,j)=><li key={j} style={{fontSize:13,margin:"1px 0"}}>{b}</li>)}</ul>}
              </div>
            ))}
          </>}

          {/* Education */}
          {data.education.some(e=>e.school) && <>
            <h3 style={{borderBottom:`2px solid ${t.primary}`,paddingBottom:3,fontSize:13,fontWeight:700,margin:"18px 0 8px",color:t.accent,textTransform:"uppercase",letterSpacing:1}}>教育背景</h3>
            {data.education.filter(e=>e.school).map((e,i) => (
              <div key={i} style={{marginBottom:8,display:"flex",justifyContent:"space-between"}}>
                <span style={{fontWeight:600,fontSize:14}}>{e.school}</span>
                <span style={{color:"#888",fontSize:12}}>{e.degree}{e.degree&&e.year?" · ":""}{e.year}</span>
              </div>
            ))}
          </>}

          {/* Skills */}
          {data.skills && <>
            <h3 style={{borderBottom:`2px solid ${t.primary}`,paddingBottom:3,fontSize:13,fontWeight:700,margin:"18px 0 8px",color:t.accent,textTransform:"uppercase",letterSpacing:1}}>技能</h3>
            <div style={{display:"flex",flexWrap:"wrap",gap:5}}>
              {data.skills.split(/[,，]/).filter(Boolean).map((s,i) => (
                <span key={i} style={{background:t.light,color:t.accent,padding:"2px 10px",borderRadius:10,fontSize:12,fontWeight:500}}>{s.trim()}</span>
              ))}
            </div>
          </>}

          {/* Projects */}
          {data.projects.some(p=>p.name) && <>
            <h3 style={{borderBottom:`2px solid ${t.primary}`,paddingBottom:3,fontSize:13,fontWeight:700,margin:"18px 0 8px",color:t.accent,textTransform:"uppercase",letterSpacing:1}}>项目经验</h3>
            {data.projects.filter(p=>p.name).map((p,i) => (
              <div key={i} style={{marginBottom:10}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline"}}>
                  <span style={{fontWeight:600,fontSize:14}}>{p.name}</span>
                  <span style={{color:"#888",fontSize:11}}>{p.tech}</span>
                </div>
                {p.desc&&<p style={{fontSize:13,margin:"2px 0"}}>{p.desc}</p>}
              </div>
            ))}
          </>}

          {/* Empty state */}
          {!data.name&&<div style={{textAlign:"center",color:"#ccc",marginTop:80,fontSize:14}}>👈 左边填表，这里实时预览</div>}
        </div>
      </div>
    </div>
  );
}
