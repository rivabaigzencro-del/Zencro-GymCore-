import { Suspense } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { DashboardOverview } from "@/components/dashboard/dashboard-overview";

export default function Home() {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />

        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <Suspense
            fallback={
              <div className="flex h-64 items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#C9A04F] border-t-transparent" />
              </div>
            }
          >
            <DashboardOverview />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
