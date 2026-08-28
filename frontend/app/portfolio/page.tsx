"use client";

import { useEffect, useMemo, useState } from "react";
import { BookOpen, CircleAlert, Medal, Sparkles, Target } from "lucide-react";
import { AppShell } from "../components/app-shell";

type Profile = {
	target_role?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string; confidence?: string; evidence?: Array<{ label?: string; value?: string } | string>; last_test_score?: number }>;
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
	projects: string[];
	assessments: Array<{ skillId: string; answer: string; correct: boolean }>;
	milestones: { completed: number; available: number; locked: number };
	readinessGate?: { ready: boolean; missingCriticalSkills: string[]; criticalSkills: string[] };
};

const BACKEND_URL = "";

function titleize(value?: string | null) {
	return value ? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) : "Unavailable";
}

function evidenceToText(item: { label?: string; value?: string } | string) {
	if (typeof item === "string") return item;
	return item.label ? `${item.label}: ${item.value || ""}`.trim() : item.value || "Evidence";
}

export default function PortfolioPage() {
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
				if (!response.ok) throw new Error("Could not load portfolio.");
				const data = (await response.json()) as SummaryResponse;
				setSummary(data);
			} catch (cause) {
				setError(cause instanceof Error ? cause.message : "Could not load portfolio.");
			} finally {
				setLoading(false);
			}
		};
		void load();
	}, []);

	const verifiedSkills = useMemo(() => {
		return Object.entries(profile?.user_skills || {})
			.filter(([, skill]) => skill.status === "Completed" || skill.status === "Verified")
			.map(([skillId, skill]) => ({
				skillId,
				proficiency: skill.proficiency || 0,
				evidence: skill.evidence || [],
				score: skill.last_test_score,
			}));
	}, [profile]);

	if (loading) {
		return <AppShell title="Portfolio"><div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8">Loading...</div></AppShell>;
	}

	if (error) {
		return (
			<AppShell title="Portfolio">
				<div className="mx-auto max-w-xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<CircleAlert className="mx-auto h-10 w-10 text-rose-400" />
					<h2 className="mt-4 text-2xl font-black text-white">Portfolio unavailable</h2>
					<p className="mt-2 text-sm text-slate-400">{error}</p>
				</div>
			</AppShell>
		);
	}

	return (
		<AppShell title="Portfolio">
			<div className="space-y-5">
				<section className="rounded-2xl border border-slate-800 bg-[linear-gradient(135deg,rgba(15,23,42,0.98),rgba(8,15,28,0.94))] p-6">
					<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> Career portfolio</div>
					<h1 className="mt-3 break-words text-4xl font-black leading-tight text-white">{titleize(summary?.career || profile?.target_role)}</h1>
					<div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Career target</p><p className="mt-1 break-words text-lg font-black leading-tight text-white">{titleize(profile?.target_role)}</p></div>
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Career readiness</p><p className="mt-1 text-lg font-black text-emerald-400">{summary?.readiness.score ?? 0}%</p></div>
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Verified skills</p><p className="mt-1 text-lg font-black text-white">{verifiedSkills.length}</p></div>
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Major achievements</p><p className="mt-1 text-lg font-black text-white">{summary?.readinessGate?.ready ? "Career Ready" : "In progress"}</p></div>
					</div>
				</section>

				<section className="grid gap-5 lg:grid-cols-2">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Target className="h-3.5 w-3.5" /> Verified skills</div>
						<div className="mt-4 flex flex-wrap gap-2">
							{verifiedSkills.length ? verifiedSkills.map((skill) => (
								<span key={skill.skillId} className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-300">
									{titleize(skill.skillId)}
								</span>
							)) : <p className="text-sm text-slate-500">No verified skills yet.</p>}
						</div>
					</div>

					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><Medal className="h-3.5 w-3.5" /> Projects</div>
						<div className="mt-4 space-y-2">
							{summary?.projects.length ? summary.projects.map((project) => (
								<div key={project} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-sm text-slate-300">{titleize(project)}</div>
							)) : <p className="text-sm text-slate-500">No projects recorded yet.</p>}
						</div>
					</div>
				</section>

				<section className="grid gap-5 lg:grid-cols-2">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><BookOpen className="h-3.5 w-3.5" /> Assessment results</div>
						<div className="mt-4 space-y-2">
							{summary?.assessments.length ? summary.assessments.map((result, index) => (
								<div key={`${result.skillId}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-sm text-slate-300">
									{titleize(result.skillId)} {result.correct ? "✓" : "•"} {result.answer}
								</div>
							)) : <p className="text-sm text-slate-500">No assessment results yet.</p>}
						</div>
					</div>

					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><Sparkles className="h-3.5 w-3.5" /> Skill evidence</div>
						<div className="mt-4 space-y-3">
							{verifiedSkills.map((skill) => (
								<div key={skill.skillId} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-sm font-bold text-white">{titleize(skill.skillId)}</p>
									<div className="mt-2 space-y-1 text-xs text-slate-500">
										{skill.evidence.length ? skill.evidence.map((item, index) => <div key={index}>{evidenceToText(item)}</div>) : <div>No evidence recorded.</div>}
									</div>
								</div>
							))}
							{!verifiedSkills.length ? <p className="text-sm text-slate-500">No evidence to display yet.</p> : null}
						</div>
					</div>
				</section>

				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
					<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> Major achievements</div>
					<div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
						{[
							`Readiness: ${summary?.readiness.score ?? 0}%`,
							`Skills verified: ${verifiedSkills.length}`,
							`Projects: ${summary?.projects.length || 0}`,
							`Assessments: ${summary?.assessments.length || 0}`,
						].map((item) => (
							<div key={item} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-300">{item}</div>
						))}
					</div>
				</section>
			</div>
		</AppShell>
	);
}
