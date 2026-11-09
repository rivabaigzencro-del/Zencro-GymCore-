import { Suspense } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { MemberTable } from "@/components/members/member-table";

export default function MembersPage() {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />

        <main className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8">
          <div>
            <h1 className="text-2xl font-bold">
              Members
            </h1>
            <p className="mt-1 text-sm text-muted-foreground mb-6">
              Manage your gym members, statuses, and contact information.
            </p>
            <Suspense
              fallback={
                <div className="flex h-64 items-center justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#C9A04F] border-t-transparent" />
                </div>
              }
            >
              <MemberTable />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}
