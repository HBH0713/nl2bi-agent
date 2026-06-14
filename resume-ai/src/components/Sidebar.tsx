"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "../lib/utils";
import { createClient } from "../lib/supabase/client";
import { FileText, Sparkles, MessageSquare, LayoutDashboard, History, LogOut, PenLine } from "lucide-react";

const links = [
  { href: "/dashboard", label: "概览", icon: LayoutDashboard },
  { href: "/analyze", label: "分析简历", icon: Sparkles },
  { href: "/builder", label: "编辑简历", icon: PenLine },
  { href: "/interview", label: "面试题库", icon: MessageSquare },
  { href: "/history", label: "历史记录", icon: History },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setEmail(data.user?.email || ""));
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  return (
    <aside className="w-56 h-screen bg-white border-r border-slate-100 flex flex-col py-5 px-3 fixed left-0 top-0 shadow-sm">
      {/* Logo */}
      <Link href="/dashboard" className="flex items-center gap-2.5 px-3 mb-8">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
          <FileText className="w-4 h-4 text-white" />
        </div>
        <span className="font-bold text-lg text-slate-800">ResumeAI</span>
      </Link>

      {/* Nav */}
      <nav className="flex flex-col gap-0.5 flex-1">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link key={href} href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                active
                  ? "bg-indigo-50 text-indigo-700 shadow-sm"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"
              )}>
              <Icon className={cn("w-4 h-4", active ? "text-indigo-500" : "text-slate-400")} />
              {label}
              {active && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-500" />}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="border-t border-slate-100 pt-4 px-3">
        <p className="text-xs text-slate-400 truncate mb-2">{email}</p>
        <button onClick={handleLogout}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-red-500 transition-colors w-full">
          <LogOut className="w-3.5 h-3.5" />退出登录
        </button>
      </div>
    </aside>
  );
}
