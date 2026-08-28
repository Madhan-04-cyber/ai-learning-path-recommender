"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, BrainCircuit, Check, Compass, GitBranch, Sparkles, Target, Zap } from "lucide-react";
import { useRouter } from "next/navigation";

const careerExamples = [
  { name: "Backend AI Developer", detail: "Build intelligent APIs and services" },
  { name: "AI Engineer", detail: "Ship useful machine learning products" },
  { name: "Data Scientist", detail: "Turn data into better decisions" },
  { name: "Full Stack Developer", detail: "Create products from idea to launch" },
];

const steps = [
  ["01", "Tell us your destination", "Start with the career you want to grow into."],
  ["02", "See what the journey needs", "We map the skills and prerequisites behind it."],
  ["03", "Build your route", "Get a focused path from your current level."],
  ["04", "Keep adapting", "Assess, practice, and let your route respond."],
];

export default function LandingPage() {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const saved = window.localStorage.getItem("pathmind_onboarding");
    if (saved) {
      try {
        const data = JSON.parse(saved) as { goal?: string };
        if (typeof data.goal === "string") setGoal(data.goal);
      } catch {
        window.localStorage.removeItem("pathmind_onboarding");
      }
    }
  }, []);

  const submitGoal = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanGoal = goal.trim();
    if (!cleanGoal) {
      setError("Tell us what you want to become first.");
      return;
    }
    setError("");
    window.localStorage.setItem("pathmind_onboarding", JSON.stringify({ goal: cleanGoal, createdAt: new Date().toISOString() }));
    router.push("/analysis");
  };

  return (
    <main className="min-h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-5 pb-20 pt-6 sm:px-8 lg:px-10">
        <header className="flex items-center justify-between border-b border-slate-800 pb-5">
          <button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} className="flex items-center gap-2 text-left" aria-label="PathMind AI home">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-400 text-slate-950"><Sparkles className="h-4 w-4" /></span>
            <span><span className="block text-sm font-black tracking-wide text-white">PATHMIND AI</span><span className="block text-[10px] text-slate-500">Your career learning GPS</span></span>
          </button>
          <a href="#how-it-works" className="hidden text-xs font-bold text-slate-400 transition-colors hover:text-emerald-400 sm:block">How it works</a>
        </header>

        <section className="grid items-center gap-12 py-20 lg:grid-cols-[1.08fr_0.92fr] lg:py-28">
          <div>
            <p className="mb-5 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-400"><Compass className="h-3.5 w-3.5" /> A clearer route forward</p>
            <h1 className="max-w-2xl text-5xl font-black leading-[0.98] tracking-tight text-white sm:text-6xl">Your career has a destination. <span className="text-emerald-400">Start with the route.</span></h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-slate-400 sm:text-lg">Tell PathMind where you want to go. We turn your goal into the skills, milestones, and next steps that get you there.</p>
          </div>

          <form onSubmit={submitGoal} className="rounded-2xl border border-emerald-500/30 bg-slate-900/80 p-5 shadow-2xl shadow-emerald-950/20 sm:p-6">
            <div className="mb-5 flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-400/10 text-emerald-400"><Target className="h-5 w-5" /></span><div><p className="text-sm font-bold text-white">Where do you want to go?</p><p className="text-xs text-slate-500">No account needed to begin.</p></div></div>
            <label htmlFor="career-goal" className="mb-2 block text-xs font-bold text-slate-300">Your career goal</label>
            <textarea id="career-goal" value={goal} maxLength={500} onChange={(event) => { setGoal(event.target.value); if (error) setError(""); }} placeholder="I want to become a Backend AI Developer" className="min-h-32 w-full resize-y rounded-xl border border-slate-700 bg-slate-950 p-4 text-sm leading-relaxed text-white placeholder:text-slate-600 focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-400/20" aria-describedby={error ? "goal-error" : "goal-count"} />
            <div className="mt-2 flex justify-between text-[10px] text-slate-600"><span id="goal-count">{goal.length}/500</span>{error && <span id="goal-error" className="font-bold text-rose-400" role="alert">{error}</span>}</div>
            <button type="submit" className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-950 transition-colors hover:bg-emerald-300">Build my path <ArrowRight className="h-4 w-4" /></button>
            <button type="button" onClick={() => document.getElementById("career-examples")?.scrollIntoView({ behavior: "smooth" })} className="mt-4 flex w-full items-center justify-center gap-2 text-xs font-bold text-slate-400 hover:text-white">Explore career paths <ArrowRight className="h-3.5 w-3.5" /></button>
          </form>
        </section>

        <section id="how-it-works" className="border-t border-slate-800 py-16"><div className="mb-8 max-w-xl"><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">How it works</p><h2 className="mt-3 text-3xl font-black text-white">From uncertainty to your next best step.</h2></div><div className="grid gap-4 md:grid-cols-4">{steps.map(([number, title, detail]) => <div key={number} className="border-l border-slate-700 pl-4"><span className="text-xs font-black text-emerald-400">{number}</span><h3 className="mt-4 text-sm font-bold text-white">{title}</h3><p className="mt-2 text-xs leading-relaxed text-slate-500">{detail}</p></div>)}</div></section>

        <section className="grid gap-8 border-t border-slate-800 py-16 lg:grid-cols-[0.8fr_1.2fr]"><div><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Why PathMind</p><h2 className="mt-3 text-3xl font-black text-white">More than a list of courses.</h2><p className="mt-4 text-sm leading-relaxed text-slate-400">Your route is grounded in what a career actually requires and adapts as your evidence grows.</p></div><div className="grid gap-3 sm:grid-cols-2">{[[BrainCircuit, "Skill-gap based", "Know what you are missing."], [GitBranch, "Prerequisite-aware", "Learn in an order that makes sense."], [Zap, "Adaptive", "Your route changes with your results."], [Check, "Career-focused", "Every step points to an outcome."]].map(([Icon, title, detail]) => { const FeatureIcon = Icon as typeof BrainCircuit; return <div key={title as string} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4"><FeatureIcon className="h-4 w-4 text-emerald-400" /><h3 className="mt-4 text-sm font-bold text-white">{title as string}</h3><p className="mt-1 text-xs text-slate-500">{detail as string}</p></div>; })}</div></section>

        <section id="career-examples" className="border-t border-slate-800 py-16"><div className="mb-7 flex items-end justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">Explore careers</p><h2 className="mt-3 text-3xl font-black text-white">Find a direction worth exploring.</h2></div><button onClick={() => document.getElementById("career-goal")?.focus()} className="hidden text-xs font-bold text-emerald-400 hover:text-emerald-300 sm:block">Start with your own goal <ArrowRight className="ml-1 inline h-3.5 w-3.5" /></button></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{careerExamples.map((career) => <button key={career.name} onClick={() => { setGoal(`I want to become a ${career.name}`); document.getElementById("career-goal")?.focus(); window.scrollTo({ top: 0, behavior: "smooth" }); }} className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-left transition-colors hover:border-emerald-500/50 hover:bg-slate-900"><span className="text-sm font-bold text-white">{career.name}</span><span className="mt-2 block text-xs text-slate-500">{career.detail}</span></button>)}</div></section>

        <footer className="flex flex-col gap-3 border-t border-slate-800 pt-6 text-[10px] text-slate-600 sm:flex-row sm:items-center sm:justify-between"><span>PATHMIND AI · Your career learning GPS</span><span>Goal → Gap → Route → Career ready</span></footer>
      </div>
    </main>
  );
}
