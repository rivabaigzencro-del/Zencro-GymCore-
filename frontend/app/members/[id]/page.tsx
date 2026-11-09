import { Suspense } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { MemberProfileView } from "@/components/members/member-profile-view";

type MemberProfilePageProps = {
  params: Promise<{ id: string }>;
};

async function MemberProfileContent({ params }: MemberProfilePageProps) {
  const { id } = await params;
  return <MemberProfileView memberId={id} />;
}

export default function MemberProfilePage({
  params,
}: MemberProfilePageProps) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />

        <main className="flex-1 space-y-6 p-4 sm:p-6 lg:p-8">
          <Suspense
            fallback={
              <div className="flex h-64 items-center justify-center">
                <p className="text-sm text-muted-foreground animate-pulse">
                  Loading member profile...
                </p>
              </div>
            }
          >
            <MemberProfileContent params={params} />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
