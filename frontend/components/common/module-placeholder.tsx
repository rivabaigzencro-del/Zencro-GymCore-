import Link from "next/link";
import { ArrowLeft, Clock, Dumbbell, Sparkles } from "lucide-react";

type Props = {
  title: string;
  description: string;
  phase: string;
};

export function ModulePlaceholder({ title, description, phase }: Props) {
  return (
    <div className="flex min-h-[65vh] items-center justify-center p-4">
      <div className="w-full max-w-xl rounded-2xl border border-border bg-card p-8 sm:p-12 text-center shadow-lg relative overflow-hidden">
        {/* Subtle decorative gold glow background */}
        <div className="absolute -top-24 -right-24 h-48 w-48 rounded-full bg-[#C9A04F]/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 h-48 w-48 rounded-full bg-[#C9A04F]/10 blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#C9A04F]/15 text-[#C9A04F] shadow-sm border border-[#C9A04F]/20">
            <Dumbbell size={30} className="stroke-[2.2]" />
          </div>

          <div className="mt-5 inline-flex items-center gap-1.5 rounded-full border border-[#C9A04F]/30 bg-[#C9A04F]/10 px-3 py-1 text-xs font-semibold text-[#C9A04F]">
            <Clock size={13} />
            <span>{phase}</span>
          </div>

          <h1 className="mt-4 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            {title}
          </h1>

          <p className="mt-2 text-sm text-muted-foreground leading-relaxed max-w-md">
            {description}
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-xl bg-[#C9A04F] px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-[#b68d3e] shadow-sm"
            >
              <ArrowLeft size={16} />
              <span>Back to Dashboard</span>
            </Link>
            <Link
              href="/members"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground transition hover:bg-muted"
            >
              <Sparkles size={16} className="text-[#C9A04F]" />
              <span>Go to Members</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

