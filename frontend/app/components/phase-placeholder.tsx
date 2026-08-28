import { ArrowRight, Construction } from "lucide-react";
import Link from "next/link";
import { AppShell } from "./app-shell";

const descriptions: Record<string, string> = {
  Home: "Your next best action and a clear view of how close you are to your career goal.",
  "My Path": "A dependency-aware route from your current skills to your target career.",
  Skills: "Your skill passport, evidence, gaps, and prerequisite relationships.",
  "AI Coach": "Contextual guidance grounded in your goal, route, and current progress.",
  Progress: "See readiness, skill growth, completed milestones, and adaptive insights.",
  Resources: "Learning resources selected for the skills your route needs next.",
  Profile: "Your goal, experience, schedule, preferences, and verified skills.",
  Settings: "Learning and product preferences for your PathMind workspace.",
  "Choose your goal": "Tell PathMind where you want to go and we will prepare the right starting point.",
  "Goal analysis": "Review the career destination and the competencies that shape your route.",
  "Quick assessment": "Answer a few focused questions so your route starts from what you already know.",
  "Your path preview": "See the first version of your dependency-aware route before you begin learning.",
};

export function PhasePlaceholder({ title }: { title: string }) {
  return (
    <AppShell title={title}>
      <section className="mx-auto max-w-3xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl md:p-10">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-400/10 text-emerald-400"><Construction className="h-6 w-6" /></div>
        <p className="mt-6 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Phase 1 foundation</p>
        <h2 className="mt-2 text-3xl font-black text-white">{title}</h2>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-400">{descriptions[title]}</p>
        <p className="mt-6 border-t border-slate-800 pt-4 text-xs text-slate-500">The shared shell and route are ready. This destination will receive its product workflow in a later implementation phase.</p>
        <Link href="/home" className="mt-6 inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-emerald-300">Back to Home <ArrowRight className="h-3.5 w-3.5" /></Link>
      </section>
    </AppShell>
  );
}
