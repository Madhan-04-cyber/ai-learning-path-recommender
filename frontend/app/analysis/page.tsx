"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Check, Compass, Sparkles, Target } from "lucide-react";

type GoalAnalysis = {
	goal: string;
	careerTitle: string;
	description: string;
	requiredSkills: string[];
	estimatedDuration: string;
	readiness: number;
	matched_career_id?: string | null;
	is_ambiguous?: boolean;
	clarification_question?: string;
};

const analysisSteps = [
	"Understanding your career goal",
	"Identifying the skills it requires",
	"Mapping the prerequisite route",
	"Checking your current experience",
	"Preparing your assessment",
	"Building your route",
];

const backendUrl = "";

export default function AnalysisPage() {
	const [analysis, setAnalysis] = useState<GoalAnalysis | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState("");

	const analyzeGoal = useCallback(async (query: string) => {
		setLoading(true);
		setError("");

		try {
			const response = await fetch(`${backendUrl}/api/analyze-goal`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ query }),
			});

			if (!response.ok) throw new Error("Goal analysis request failed");

			const data: unknown = await response.json();
			if (!data || typeof data !== "object") throw new Error("Invalid analysis response");

			const result = data as Partial<GoalAnalysis>;
			if (
				typeof result.careerTitle !== "string" ||
				!Array.isArray(result.requiredSkills) ||
				typeof result.estimatedDuration !== "string" ||
				typeof result.readiness !== "number"
			) {
				throw new Error("Invalid analysis response");
			}

			const normalized = { ...result, goal: query } as GoalAnalysis;
			window.localStorage.setItem("pathmind_analysis", JSON.stringify(normalized));
			setAnalysis(normalized);
		} catch {
			setError("Goal analysis is temporarily unavailable. Please try again.");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		const saved = window.localStorage.getItem("pathmind_onboarding");
		if (!saved) {
			return;
		}

		try {
			const data = JSON.parse(saved) as { goal?: string };
			const savedGoal = typeof data.goal === "string" ? data.goal.trim() : "";
			if (!savedGoal || savedGoal.length > 500) {
				window.setTimeout(() => {
					setError("Your saved goal is invalid. Please enter it again.");
				}, 0);
				return;
			}
			window.setTimeout(() => {
				void analyzeGoal(savedGoal);
			}, 0);
		} catch {
			window.localStorage.removeItem("pathmind_onboarding");
			window.setTimeout(() => {
				setError("We could not read your saved goal. Please enter it again.");
			}, 0);
		}
	}, [analyzeGoal]);

	return (
		<main className="min-h-screen bg-slate-950 px-5 py-8 text-slate-100 sm:px-8 sm:py-10">
			<div className="mx-auto max-w-4xl">
				<header className="flex items-center justify-between border-b border-slate-800 pb-5">
					<Link href="/" className="flex items-center gap-2 text-sm font-black text-white">
						<span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-400 text-slate-950">
							<Sparkles className="h-4 w-4" />
						</span>
						PATHMIND AI
					</Link>
					<Link href="/" className="flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-white">
						<ArrowLeft className="h-3.5 w-3.5" />
						Edit goal
					</Link>
				</header>

				{!loading && !analysis && !error ? (
					<section className="py-24 text-center">
						<Target className="mx-auto h-10 w-10 text-amber-400" />
						<h1 className="mt-5 text-3xl font-black text-white sm:text-4xl">Start with a destination.</h1>
						<p className="mt-3 text-sm text-slate-400">We need a career goal before we can prepare your route.</p>
						<Link href="/" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950">
							Choose a goal
							<ArrowRight className="h-4 w-4" />
						</Link>
					</section>
				) : loading ? (
					<section className="py-16 sm:py-24">
						<div className="mx-auto max-w-lg text-center">
							<div className="mx-auto flex h-16 w-16 animate-pulse items-center justify-center rounded-full border border-emerald-400/40 bg-emerald-400/10 text-emerald-400">
								<Compass className="h-7 w-7" />
							</div>
							<h1 className="mt-8 text-3xl font-black text-white sm:text-4xl">Understanding your goal...</h1>
							<div className="mt-8 space-y-3 text-left">
								{analysisSteps.map((step) => (
									<div key={step} className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-400">
										<span className="h-5 w-5 animate-pulse rounded-full bg-emerald-400/20" />
										{step}
									</div>
								))}
							</div>
						</div>
					</section>
				) : error ? (
					<section className="py-24 text-center">
						<Target className="mx-auto h-10 w-10 text-rose-400" />
						<h1 className="mt-5 text-3xl font-black text-white sm:text-4xl">We could not analyze that goal.</h1>
						<p className="mt-3 text-sm text-slate-400">{error}</p>
						<Link href="/" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950">
							Try again
							<ArrowRight className="h-4 w-4" />
						</Link>
					</section>
				) : analysis?.is_ambiguous ? (
					<section className="mx-auto max-w-2xl py-14 sm:py-20">
						<div className="rounded-3xl border border-amber-500/25 bg-[radial-gradient(circle_at_top_left,_rgba(245,184,75,0.08),_transparent_32%),linear-gradient(180deg,rgba(15,23,42,0.95),rgba(9,17,31,0.98))] p-6 shadow-2xl shadow-amber-950/10 sm:p-8">
							<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400">More detail needed</p>
							<h1 className="mt-4 max-w-xl text-3xl font-black leading-tight text-white sm:text-5xl">Let us find the right destination.</h1>
							<p className="mt-4 max-w-xl text-sm leading-relaxed text-slate-400">
								We matched part of your goal, but not enough to build a reliable route yet.
							</p>
							<div className="mt-8 rounded-2xl border border-amber-500/30 bg-slate-900/80 p-5 sm:p-6">
								<p className="text-sm leading-relaxed text-slate-300">
									{analysis.clarification_question || "Please describe the career you want to pursue."}
								</p>
								<Link href="/" className="mt-7 inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950 hover:bg-emerald-300">
									Edit goal
									<ArrowRight className="h-4 w-4" />
								</Link>
							</div>
						</div>
					</section>
				) : (
					<section className="py-16 sm:py-24">
						<div className="mx-auto max-w-xl">
							<p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
								<Check className="h-3.5 w-3.5" />
								Destination found
							</p>
							<h1 className="mt-5 text-4xl font-black leading-tight text-white">We found your destination.</h1>
							<div className="mt-8 rounded-2xl border border-emerald-500/30 bg-slate-900/80 p-6 shadow-2xl">
								<div className="flex items-start gap-4">
									<span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-400/10 text-emerald-400">
										<Target className="h-5 w-5" />
									</span>
									<div>
										<p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Career target</p>
										<p className="mt-2 text-2xl font-black text-white">{analysis?.careerTitle || "Career target"}</p>
										<p className="mt-2 text-sm leading-relaxed text-slate-400">
											{analysis?.description || "A structured career route based on your goal."}
										</p>
									</div>
								</div>

								<div className="mt-7 grid gap-3 border-t border-slate-800 pt-5 sm:grid-cols-3">
									<div>
										<p className="text-[10px] uppercase text-slate-500">Competencies</p>
										<p className="mt-1 text-lg font-black text-white">{analysis?.requiredSkills.length || 0}</p>
									</div>
									<div>
										<p className="text-[10px] uppercase text-slate-500">Estimated journey</p>
										<p className="mt-1 text-sm font-bold text-slate-200">{analysis?.estimatedDuration || "To be estimated"}</p>
									</div>
									<div>
										<p className="text-[10px] uppercase text-slate-500">Current readiness</p>
										<p className="mt-1 text-lg font-black text-indigo-400">{analysis?.readiness ?? 0}%</p>
									</div>
								</div>

								<details className="mt-6 border-t border-slate-800 pt-4">
									<summary className="cursor-pointer text-xs font-bold text-slate-300">View required competencies</summary>
									<div className="mt-3 flex flex-wrap gap-2">
										{analysis?.requiredSkills.map((skill) => (
											<span key={skill} className="rounded-full border border-slate-700 px-2.5 py-1 text-[10px] text-slate-400">
												{skill.replaceAll("_", " ")}
											</span>
										))}
									</div>
								</details>

								<Link href="/assessment" className="mt-7 flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-950 hover:bg-emerald-300">
									Continue to diagnostic
									<ArrowRight className="h-4 w-4" />
								</Link>
							</div>
						</div>
					</section>
				)}
			</div>
		</main>
	);
}
