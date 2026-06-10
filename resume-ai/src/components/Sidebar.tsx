"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "../lib/utils";
import { createClient } from "../lib/supabase/client";
import { FileText, Sparkles, MessageSquare, LayoutDashboard, History, LogOut } from "lucide-react";

const links = [
  { href: "/dashboard", label: "概览", icon: LayoutDashboard },
  { href: "/analyze", label: "分析简历", icon: Sparkles },
  { href: "/interview", label: "面试题库", icon: MessageSquare },
  { href: "/history", label: "历史记录", icon: History },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email || "");
    });
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  return (
    <aside className="w-56 h-screen bg-white border-r border-slate-200 flex flex-col py-6 px-3 fixed left-0 top-0">
      <Link href="/dashboard" className="flex items-center gap-2 px-3 mb-8">
        <FileText className="w-6 h-6 text-blue-600" />
        <span className="font-bold text-lg">ResumeAI</span>
      </Link>
      <nav className="flex flex-col gap-1 flex-1">
        {links.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href}
            className={cn("flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              pathname.startsWith(href) ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900")}>
            <Icon className="w-4 h-4" />{label}
          </Link>
        ))}
      </nav>
      <div className="border-t pt-4 px-3">
        <p className="text-xs text-muted-foreground truncate mb-2">{email}</p>
        <button onClick={handleLogout} className="flex items-center gap-2 text-sm text-red-500 hover:text-red-700 w-full">
          <LogOut className="w-4 h-4" />退出登录
        </button>
      </div>
    </aside>
  );
}
