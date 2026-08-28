"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Award, CircleAlert, Download, Medal, Sparkles, Target } from "lucide-react";
import { AppShell } from "../components/app-shell";

type Profile = {
	target_role?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string; confidence?: string; evidence?: unknown[] }>;
	assessmentResults?: Array<{ skillId: string; answer: string; correct: boolean }>;
	practiceHistory?: Array<{ skillId: string; question: string; answer: string; correct: boolean; difficulty: string; timestamp: string }>;
};

type SummaryResponse = {
	career: string;
	readiness: {
		score: number;
		completedSkills: number;
		totalSkills: number;
		biggestGap: string | null;
		biggestBlocker: string | null;
		nextAction: string | null;
	};
	readinessGate?: { ready: boolean; missingCriticalSkills: string[]; criticalSkills: string[]; readiness: { score: number; completedSkills: number; totalSkills: number; biggestGap: string | null; biggestBlocker: string | null; nextAction: string | null } };
	milestones: { completed: number; available: number; locked: number };
	projects: string[];
	assessments: Array<{ skillId: string; answer: string; correct: boolean }>;
};

const BACKEND_URL = "";

function titleize(value?: string | null) {
	return value ? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) : "Unavailable";
}

export default function CareerReadyPage() {
	const [profile, setProfile] = useState<Profile | null>(null);
	const [summary, setSummary] = useState<SummaryResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");

	useEffect(() => {
		const load = async () => {
			try {
				const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as Profile | null;
				const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as { matched_career_id?: string } | null;
				const targetRole = savedProfile?.target_role || savedAnalysis?.matched_career_id || "backend_ai_developer";
				const currentSkills = savedProfile?.user_skills || {};
				setProfile(savedProfile || { target_role: targetRole, user_skills: currentSkills });

				const response = await fetch(`${BACKEND_URL}/api/progress/summary`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						target_role: targetRole,
						current_skills: currentSkills,
						daily_learning_minutes: savedProfile?.practiceHistory?.length ? 60 : 0,
						assessment_results: savedProfile?.assessmentResults || [],
						practice_history: savedProfile?.practiceHistory || [],
					}),
				});
				if (!response.ok) throw new Error("Could not load career readiness.");
				const data = (await response.json()) as SummaryResponse;
				setSummary(data);
			} catch (cause) {
				setError(cause instanceof Error ? cause.message : "Could not load career readiness.");
			} finally {
				setLoading(false);
			}
		};
		void load();
	}, []);

	if (loading) {
		return <AppShell title="Career Ready"><div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8">Loading...</div></AppShell>;
	}

	if (error) {
		return (
			<AppShell title="Career Ready">
				<div className="mx-auto max-w-2xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<CircleAlert className="mx-auto h-10 w-10 text-rose-400" />
					<h2 className="mt-4 text-2xl font-black text-white">Career Ready unavailable</h2>
					<p className="mt-2 text-sm text-slate-400">{error}</p>
				</div>
			</AppShell>
		);
	}

	const gate = summary?.readinessGate;
	const ready = gate?.ready && (summary?.readiness?.score || 0) >= 90;

	return (
		<AppShell title="Career Ready">
			<div className="space-y-5">
				<section className="rounded-2xl border border-slate-800 bg-[radial-gradient(circle_at_top,_rgba(82,224,179,0.18),_transparent_35%),linear-gradient(135deg,rgba(13,20,33,0.98),rgba(8,15,28,0.94))] p-6">
					<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Award className="h-3.5 w-3.5" /> Career gate</div>
					<h1 className="mt-3 text-4xl font-black text-white">{ready ? "🏆 CAREER READY" : "Keep going"}</h1>
					<p className="mt-2 text-sm text-slate-400">{titleize(summary?.career || profile?.target_role)}</p>
					<div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Career Readiness</p><p className="mt-1 text-2xl font-black text-emerald-400">{summary?.readiness.score ?? 0}%</p></div>
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Skills verified</p><p className="mt-1 text-2xl font-black text-white">{summary?.readiness.completedSkills ?? 0} / {summary?.readiness.totalSkills ?? 0}</p></div>
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Projects</p><p className="mt-1 text-2xl font-black text-white">{summary?.projects?.length || 0}</p></div>
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Assessments</p><p className="mt-1 text-2xl font-black text-white">{summary?.assessments?.length || 0}</p></div>
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Capstone</p><p className="mt-1 text-2xl font-black text-white">{ready ? "Completed" : "In progress"}</p></div>
					</div>
					{ready ? <p className="mt-4 text-sm font-bold text-emerald-400">Critical skills are complete and the readiness gate passed.</p> : <p className="mt-4 text-sm text-amber-300">Career Ready is withheld until critical skills are complete.</p>}
					<div className="mt-5 flex flex-wrap gap-3">
						<Link href="/portfolio" className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950"><Target className="h-4 w-4" /> View Portfolio</Link>
					</div>
				</section>

				<section className="grid gap-5 lg:grid-cols-2">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> Major achievements</div>
						<div className="mt-4 space-y-3 text-sm text-slate-300">
							{[
								`Biggest gap: ${titleize(summary?.readiness.biggestGap)}`,
								`Biggest blocker: ${titleize(summary?.readiness.biggestBlocker)}`,
								`Next action: ${summary?.readiness.nextAction || "Unavailable"}`,
								`Critical skills: ${(gate?.criticalSkills || []).map(titleize).join(", ") || "Unavailable"}`,
							].map((item) => <div key={item} className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2">{item}</div>)}
						</div>
					</div>

					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><Medal className="h-3.5 w-3.5" /> Portfolio access</div>
						<p className="mt-3 text-sm leading-relaxed text-slate-300">Your portfolio collects verified skills, projects, assessment results, evidence, and major achievements for review.</p>
						<div className="mt-5 flex flex-wrap gap-3">
							<Link href="/portfolio" className="inline-flex items-center gap-2 rounded-xl border border-slate-800 px-4 py-3 text-xs font-black uppercase text-white">Open Portfolio <ArrowRight className="h-4 w-4" /></Link>
							<span className="inline-flex items-center gap-2 rounded-xl border border-slate-800 px-4 py-3 text-xs font-black uppercase text-slate-500">Download / Share unavailable</span>
						</div>
					</div>
				</section>
			</div>
		</AppShell>
	);
}
