import { Suspense } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { ReportsView } from "@/components/reports/reports-view";

export default function ReportsPage() {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 p-6">
          <Suspense
            fallback={
              <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
                Loading Reports & Business Analytics...
              </div>
            }
          >
            <ReportsView />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
