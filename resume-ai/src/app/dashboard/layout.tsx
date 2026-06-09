import Sidebar from "@/components/Sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <Sidebar />
      <main className="ml-56 flex-1 bg-gradient-to-br from-slate-50 to-blue-50 min-h-screen">
        {children}
      </main>
    </div>
  );
}
