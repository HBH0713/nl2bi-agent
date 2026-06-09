# ResumeAI 学习指南

每个技术你只需要看懂项目里用到的部分，不要求精通。

---

## 1. Next.js 15（项目框架）

**它做了什么：** 把你的 TypeScript 代码变成网页和后端 API

**你需要看懂：**

| 概念 | 在项目哪里 | 一句话 |
|------|------|------|
| App Router | `src/app/` 目录结构 | 文件夹路径 = 网页 URL |
| `page.tsx` | `src/app/dashboard/page.tsx` | 每个文件夹里的 `page.tsx` 就是这个页面的内容 |
| `layout.tsx` | `src/app/dashboard/layout.tsx` | 这个目录下所有页面共享的框架（侧边栏） |
| API Route | `src/app/api/analyze/route.ts` | `route.ts` 就是后端接口 |
| `"use client"` | `src/app/results/page.tsx` 第一行 | 标记这个文件在浏览器里运行（能用 useState） |
| Server Component | `src/app/history/page.tsx` | 默认就是服务端运行，能直接调数据库 |

**快速理解：**
```
浏览器请求 /dashboard → Next.js 执行 page.tsx → 生成 HTML → 返回给浏览器
浏览器请求 /api/analyze → Next.js 执行 route.ts → 调用 DeepSeek → 返回 JSON
```

**推荐看：** Next.js 官方教程前 3 章 https://nextjs.org/learn （1 小时）

---

## 2. TypeScript（编程语言）

**它做了什么：** 给 JavaScript 加了类型标注，提前暴露 bug

**你需要看懂：**

```typescript
// 普通变量
const name: string = "张三";      // : string 表示这是字符串

// 函数参数和返回值
function add(a: number, b: number): number {
  return a + b;
}

// 接口（自定义类型）
interface AnalysisResult {
  score: number;                   // 必须有 score 字段，类型是数字
  strengths: string[];             // 字符串数组
  error?: string;                  // ? 表示可选，可以有可以没有
}

// React 组件
const [file, setFile] = useState<File | null>(null);
//                                ↑ File 类型 或 null
```

**快速理解：** 把 TypeScript 想象成给变量贴标签。`const age: number = 18` 这行——如果有人传了字符串给你，编辑器直接标红。

**推荐看：** TypeScript 官方 5 分钟入门 https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes.html

---

## 3. React（前端界面）

**它做了什么：** 把页面拆成可复用的组件

**你需要看懂：**

| 概念 | 在项目哪里 |
|------|------|
| 组件 | `src/components/Sidebar.tsx` — 一个函数返回 HTML |
| useState | `src/app/results/page.tsx` — 存储界面状态 |
| useEffect | `src/app/results/page.tsx` — 页面加载时执行 |

```tsx
// React 组件就是一个返回 HTML 的函数
function MyButton() {
  const [count, setCount] = useState(0);  // 创建状态变量
  return <button onClick={() => setCount(count + 1)}>点击 {count} 次</button>;
}
```

**快速理解：** NL2BI 你用 `st.button()` 和 `st.text_input()` 拼界面。React 把这些 `st.xxx` 换成了函数返回 `<Button>` `<input>` HTML 标签。写法变了，思路一样。

**推荐看：** React 官方快速入门 https://react.dev/learn （前 3 节，30 分钟）

---

## 4. Tailwind CSS（样式）

**它做了什么：** 不用写 CSS 文件，直接在 HTML 标签上写样式类名

**你在项目里看到的：**
```tsx
className="flex items-center gap-4 px-3 py-2 rounded-lg text-sm bg-blue-50"
// 翻译：弹性布局 垂直居中 间距4 左右内边距3 上下内边距2 圆角 小字 蓝色背景
```

**快速理解：** 每个 `className` 就是一堆缩写的 CSS 属性。`p-4` = padding 16px，`text-sm` = font-size 14px，`bg-blue-50` = 浅蓝背景。不需要死记，用的时候查。

**推荐看：** Tailwind 速查表 https://tailwindcss.com/docs （边写边查就行）

---

## 5. Supabase（后端服务）

**它做了什么：** 三个功能合一的云服务

| 功能 | 在项目哪里 | 相当于 |
|------|------|------|
| **Auth** | `src/middleware.ts` + `src/app/login/` | 用户注册/登录/鉴权 |
| **Database** | `src/lib/db.ts` 的 `saveAnalysis/getAnalyses` | PostgreSQL |
| **RLS** | SQL Editor 里创建的 POLICY | 数据权限隔离 |

**快速理解：** Auth 部分不用管原理，会用就行。DB 部分和 NL2BI 的 PostgreSQL 一样是 SQL 数据库，区别是你用 `.insert()` `.select()` 而不是写 SQL。

---

## 6. 项目数据流（串联所有技术）

```
用户打开浏览器 → 输入 http://localhost:3001
    ↓
Next.js middleware.ts 检查登录 → 没登录跳 /login
    ↓
用户注册 → Supabase Auth 创建账号 → 登录成功 → 跳 /dashboard
    ↓
用户点「分析简历」→ /analyze → 选 PDF → 点分析
    ↓
前端 fetch("/api/analyze") → API route.ts 执行：
    ① 把 PDF 发给 Python FastAPI (pdfplumber) 提取文字
    ② 拼 Prompt 发给 DeepSeek
    ③ DeepSeek 返回 JSON → 存入 Supabase PostgreSQL
    ④ 返回结果给前端
    ↓
前端收到 JSON → useState 更新 → React 重新渲染 → 看到评分/建议/面试题
    ↓
用户点「历史记录」→ /history → Server Component 直接从 DB 读取 → 显示列表
```

---

## 7. 面试会怎么问

| 问题 | 答案 |
|------|------|
| "Next.js 的 App Router 是什么？" | 文件夹路径就是 URL，`page.tsx` 是页面，`route.ts` 是 API |
| "Server Component 和 Client Component 区别？" | Server 在服务端跑，能直接查数据库；Client 在浏览器跑，能用 useState |
| "为什么用 Supabase 不用自己搭？" | 省时间——Auth + DB + RLS 三合一，免费额度够用 |
| "Prisma 装不上怎么解决的？" | Prisma 7 改 API 不兼容，直接换 Supabase JS SDK 读写数据库 |
| "这个项目和 NL2BI 有什么区别？" | NL2BI 是 Python + Agent 编排；ResumeAI 是 TypeScript + 全栈 SaaS，用来补前端技术栈 |

---

**学习顺序建议：** 先看 Next.js（30分钟）→ 再看 React（30分钟）→ Tailwind 查着用 → TypeScript 跟着项目代码学 → Supabase 只读文档里用到的部分
