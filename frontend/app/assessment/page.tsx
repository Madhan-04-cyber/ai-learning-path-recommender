"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Check, ChevronLeft, Compass, RotateCcw, Sparkles, Target } from "lucide-react";

type GoalContext = { goal: string; careerTitle: string; matched_career_id?: string | null; is_ambiguous?: boolean };
type DiagnosticQuestion = { questionId: string; skillId: string; question: string; options: string[]; difficulty: string; questionType?: "mcq" | "short_answer" | "coding"; explanation?: string };
type AssessmentResult = { questionId: string; skillId: string; answer: string; correct: boolean; difficulty: string };
type Profile = { experienceLevel: string; knownSkills: string[]; dailyLearningMinutes: number; learningPreferences: string[]; assessmentResults: AssessmentResult[]; user_skills?: Record<string, { proficiency?: number; status?: string; confidence?: string; evidence?: unknown[] }> };

const experienceOptions = ["Complete beginner", "Some experience", "Intermediate", "Advanced"];
const availabilityOptions = [30, 60, 120, 180];
const preferenceOptions = ["Hands-on", "Video", "Reading", "Projects"];
const skillOptions = [
	["python", "Python"], ["oop", "Object-oriented programming"], ["git", "Git"],
	["http_fundamentals", "HTTP"], ["rest_apis", "REST APIs"], ["sql_basics", "SQL"],
	["postgresql", "Databases"], ["fastapi", "FastAPI"], ["machine_learning_basics", "Machine learning"],
];

export default function AssessmentPage() {
	const [context, setContext] = useState<GoalContext | null>(null);
	const [profile, setProfile] = useState<Profile>({ experienceLevel: "", knownSkills: [], dailyLearningMinutes: 60, learningPreferences: [], assessmentResults: [] });
	const [profileStep, setProfileStep] = useState(0);
	const [questions, setQuestions] = useState<DiagnosticQuestion[]>([]);
	const [answers, setAnswers] = useState<Record<string, string>>({});
	const [textAnswers, setTextAnswers] = useState<Record<string, string>>({});
	const [questionIndex, setQuestionIndex] = useState(0);
	const [result, setResult] = useState<{ assessmentResults: AssessmentResult[]; skillProficiency: Record<string, number>; overallScore: number } | null>(null);
	const [loading, setLoading] = useState(true);
	const [submitting, setSubmitting] = useState(false);
	const [error, setError] = useState("");

	useEffect(() => {
		const loadGoal = async () => {
			try {
				const savedGoal = JSON.parse(window.localStorage.getItem("pathmind_onboarding") || "null") as { goal?: string } | null;
				const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as GoalContext | null;
				const goal = savedGoal?.goal || savedAnalysis?.goal;
				if (!goal) { setError("Start with a career goal before taking the diagnostic."); setLoading(false); return; }
				const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as (Profile & { user_skills?: Record<string, { proficiency?: number }> }) | null;
				if (savedProfile) {
					setProfile((current) => ({ ...current, ...savedProfile }));
				}
				if (savedProfile && Array.isArray(savedProfile.assessmentResults)) {
					const skillProficiency = Object.fromEntries(Object.entries(savedProfile.user_skills || {}).map(([skillId, skill]) => [skillId, Math.max(0, Math.min(100, skill.proficiency || 0))]));
					const scores = Object.values(skillProficiency);
					setResult({ assessmentResults: savedProfile.assessmentResults, skillProficiency, overallScore: scores.length ? Math.round(scores.reduce((total, score) => total + score, 0) / scores.length) : 0 });
				}
				if (savedAnalysis?.careerTitle && savedAnalysis.matched_career_id) { setContext(savedAnalysis); setLoading(false); return; }
				const response = await fetch(`/api/analyze-goal`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: goal }) });
				if (!response.ok) throw new Error("Goal analysis failed");
				const data = (await response.json()) as GoalContext;
				if (!data.careerTitle || !data.matched_career_id || data.is_ambiguous) throw new Error("That goal needs more detail before assessment.");
				window.localStorage.setItem("pathmind_analysis", JSON.stringify(data));
				window.localStorage.setItem("pathmind_onboarding", JSON.stringify({ goal, createdAt: new Date().toISOString() }));
				setContext(data);
			} catch (cause) {
				setError(cause instanceof Error ? cause.message : "We could not prepare your assessment.");
			} finally { setLoading(false); }
		};
		void loadGoal();
	}, []);

	const toggleSkill = (skillId: string) => setProfile((current) => ({ ...current, knownSkills: current.knownSkills.includes(skillId) ? current.knownSkills.filter((id) => id !== skillId) : [...current.knownSkills, skillId] }));
	const startDiagnostic = async () => {
		if (!context?.matched_career_id) return;
		setLoading(true); setError("");
		try {
			const response = await fetch(`/api/diagnostic/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_role: context.matched_career_id }) });
			if (!response.ok) throw new Error("We could not load the career-specific questions.");
			const data = (await response.json()) as { questions?: DiagnosticQuestion[] };
			if (!Array.isArray(data.questions) || data.questions.length === 0 || data.questions.some((question) => !question.questionId || !question.skillId || !question.question || !Array.isArray(question.options))) throw new Error("The diagnostic response was invalid.");
			setQuestions(data.questions); setQuestionIndex(0); setAnswers({}); setLoading(false);
		} catch (cause) { setError(cause instanceof Error ? cause.message : "We could not load the diagnostic."); setLoading(false); }
	};
	const submitDiagnostic = async () => {
		if (!context?.matched_career_id || questions.some((question) => !answers[question.questionId])) { setError("Answer every question before submitting."); return; }
		setSubmitting(true); setError("");
		try {
			const response = await fetch(`/api/diagnostic/submit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_role: context.matched_career_id, known_skills: profile.knownSkills, current_skills: profile.user_skills || {}, answers: questions.map((question) => ({ questionId: question.questionId, skillId: question.skillId, answer: (question.questionType === "mcq" ? answers[question.questionId] : textAnswers[question.questionId]) || "" })) }) });
			if (!response.ok) throw new Error("We could not calculate your result. Please try again.");
			const data = (await response.json()) as { assessmentResults?: AssessmentResult[]; skillProficiency?: Record<string, number>; overallScore?: number };
			if (!Array.isArray(data.assessmentResults) || !data.skillProficiency || typeof data.overallScore !== "number") throw new Error("The assessment result was invalid.");
			const assessmentResult = { assessmentResults: data.assessmentResults, skillProficiency: data.skillProficiency, overallScore: data.overallScore };
			setResult(assessmentResult);
			const userSkills = Object.fromEntries(Object.entries(data.skillProficiency).map(([skillId, proficiency]) => [skillId, { proficiency, status: proficiency >= 75 ? "Completed" : proficiency < 50 ? "Needs Improvement" : "In Progress", confidence: "Assessed" }]));
			window.localStorage.setItem("pathmind_profile", JSON.stringify({ ...profile, target_role: context.matched_career_id, user_skills: userSkills, assessmentResults: data.assessmentResults }));
		} catch (cause) { setError(cause instanceof Error ? cause.message : "We could not calculate your result."); }
		finally { setSubmitting(false); }
	};
	const labelForSkill = (skillId: string) => skillOptions.find(([id]) => id === skillId)?.[1] || skillId.replaceAll("_", " ");

	if (loading) return <main className="min-h-screen bg-slate-950 px-5 py-6 text-slate-100"><div className="mx-auto max-w-3xl"><header className="border-b border-slate-800 pb-5"><Link href="/" className="flex items-center gap-2 text-sm font-black text-white"><Sparkles className="h-4 w-4 text-emerald-400" /> PATHMIND AI</Link></header><section className="py-24 text-center"><Compass className="mx-auto h-10 w-10 animate-pulse text-emerald-400" /><h1 className="mt-6 text-2xl font-black text-white">Preparing your assessment...</h1><p className="mt-2 text-sm text-slate-500">Loading questions for your selected career.</p></section></div></main>;
	if (error && !context) return <main className="min-h-screen bg-slate-950 px-5 py-6 text-slate-100"><div className="mx-auto max-w-2xl"><Link href="/" className="flex items-center gap-2 text-sm font-black text-white"><Sparkles className="h-4 w-4 text-emerald-400" /> PATHMIND AI</Link><section className="py-24 text-center"><Target className="mx-auto h-10 w-10 text-rose-400" /><h1 className="mt-5 text-3xl font-black text-white">Assessment unavailable</h1><p className="mt-3 text-sm text-slate-400">{error}</p><Link href="/" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950">Choose a goal <ArrowRight className="h-4 w-4" /></Link></section></div></main>;

	return (
		<main className="min-h-screen bg-slate-950 px-5 py-6 text-slate-100 sm:px-8">
			<div className="mx-auto max-w-3xl">
				<header className="flex items-center justify-between border-b border-slate-800 pb-5">
					<Link href="/" className="flex items-center gap-2 text-sm font-black text-white">
						<Sparkles className="h-4 w-4 text-emerald-400" /> PATHMIND AI
					</Link>
					<Link href="/analysis" className="flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-white">
						<ArrowLeft className="h-3.5 w-3.5" /> Goal analysis
					</Link>
				</header>

				<section className="py-10">
					<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Assessment</p>
					<h1 className="mt-3 text-3xl font-black text-white">Show us what you know</h1>
					<p className="mt-3 text-sm text-slate-400">
						We use your current goal and the selected career to prepare a short diagnostic before the roadmap continues.
					</p>

					{!result && !questions.length ? (
						<div className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
							<p className="text-sm text-slate-300">
								Ready to assess <span className="font-bold text-white">{context?.careerTitle || "your selected career"}</span>?
							</p>
							<p className="mt-2 text-sm text-slate-500">This keeps the route aligned with the career you chose in Analysis.</p>
							<button
								type="button"
								onClick={() => void startDiagnostic()}
								className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950"
							>
								Begin diagnostic
								<ArrowRight className="h-4 w-4" />
							</button>
						</div>
					) : null}

					{questions.length > 0 && !result ? (
						<div className="mt-8 space-y-4">
							<div className="flex items-center justify-between">
								<p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Career diagnostic</p>
								<p className="text-xs text-slate-500">{questions.length} questions</p>
							</div>
							{questions.map((question, index) => (
								<article key={question.questionId} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
									<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">Question {index + 1}</p>
									<h2 className="mt-3 text-lg font-black text-white">{question.question}</h2>
									<div className="mt-4 grid gap-2">
										{question.options.map((option) => (
											<button
												key={option}
												type="button"
												onClick={() => setAnswers((current) => ({ ...current, [question.questionId]: option }))}
												className={`rounded-xl border px-4 py-3 text-left text-sm transition ${
													answers[question.questionId] === option ? "border-emerald-400 bg-emerald-400/10 text-emerald-300" : "border-slate-800 bg-slate-950/70 text-slate-300 hover:border-slate-700"
												}`}
											>
												{option}
											</button>
										))}
									</div>
								</article>
							))}
							<div className="flex justify-end">
								<button
									type="button"
									disabled={submitting}
									onClick={() => void submitDiagnostic()}
									className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950 disabled:opacity-50"
								>
									Submit assessment
									<ArrowRight className="h-4 w-4" />
								</button>
							</div>
						</div>
					) : null}

					{result ? (
						<div className="mt-8 rounded-2xl border border-emerald-500/20 bg-slate-900/70 p-6">
							<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Diagnostic complete</p>
							<h2 className="mt-3 text-2xl font-black text-white">Your diagnostic results</h2>
							<p className="mt-2 text-sm text-slate-400">Your score is {result.overallScore}%.</p>
							<Link href="/path-preview" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950">
								Continue to path preview
								<ArrowRight className="h-4 w-4" />
							</Link>
						</div>
					) : null}

					{error ? <p className="mt-6 text-sm text-rose-400">{error}</p> : null}
				</section>
			</div>
		</main>
	);
}
