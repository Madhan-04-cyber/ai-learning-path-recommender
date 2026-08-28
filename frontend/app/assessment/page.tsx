"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Check, ChevronLeft, Compass, RotateCcw, Sparkles, Target } from "lucide-react";

type GoalContext = { goal: string; careerTitle: string; matched_career_id?: string | null; is_ambiguous?: boolean };
type DiagnosticQuestion = { questionId: string; skillId: string; question: string; options: string[]; difficulty: string };
type AssessmentResult = { questionId: string; skillId: string; answer: string; correct: boolean; difficulty: string };
type Profile = { experienceLevel: string; knownSkills: string[]; dailyLearningMinutes: number; learningPreferences: string[]; assessmentResults: AssessmentResult[] };

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
	const [questionIndex, setQuestionIndex] = useState(0);
	const [result, setResult] = useState<{ assessmentResults: AssessmentResult[]; skillProficiency: Record<string, number>; overallScore: number } | null>(null);
	const [loading, setLoading] = useState(true);
	const [submitting, setSubmitting] = useState(false);
	const [error, setError] = useState("");

	useEffect(() => {
		const loadGoal = async () => {
			try {
				const savedGoal = JSON.parse(window.localStorage.getItem("pathmind_onboarding") || "null") as { goal?: string } | null;
				if (!savedGoal?.goal) { setError("Start with a career goal before taking the diagnostic."); setLoading(false); return; }
				const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as (Profile & { user_skills?: Record<string, { proficiency?: number }> }) | null;
				if (savedProfile && Array.isArray(savedProfile.assessmentResults)) {
					setProfile((current) => ({ ...current, ...savedProfile }));
					const skillProficiency = Object.fromEntries(Object.entries(savedProfile.user_skills || {}).map(([skillId, skill]) => [skillId, Math.max(0, Math.min(100, skill.proficiency || 0))]));
					const scores = Object.values(skillProficiency);
					setResult({ assessmentResults: savedProfile.assessmentResults, skillProficiency, overallScore: scores.length ? Math.round(scores.reduce((total, score) => total + score, 0) / scores.length) : 0 });
				}
				const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as GoalContext | null;
				if (savedAnalysis?.careerTitle && savedAnalysis.matched_career_id) { setContext(savedAnalysis); setLoading(false); return; }
				const response = await fetch(`/api/analyze-goal`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: savedGoal.goal }) });
				if (!response.ok) throw new Error("Goal analysis failed");
				const data = (await response.json()) as GoalContext;
				if (!data.careerTitle || !data.matched_career_id || data.is_ambiguous) throw new Error("That goal needs more detail before assessment.");
				window.localStorage.setItem("pathmind_analysis", JSON.stringify(data));
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
			const response = await fetch(`/api/diagnostic/submit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_role: context.matched_career_id, known_skills: profile.knownSkills, answers: questions.map((question) => ({ questionId: question.questionId, skillId: question.skillId, answer: answers[question.questionId] })) }) });
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

	return <main className="min-h-screen bg-slate-950 px-5 py-6 text-slate-100 sm:px-8"><div className="mx-auto max-w-3xl"><header className="flex items-center justify-between border-b border-slate-800 pb-5"><Link href="/" className="flex items-center gap-2 text-sm font-black text-white"><Sparkles className="h-4 w-4 text-emerald-400" /> PATHMIND AI</Link><Link href="/analysis" className="flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-white"><ArrowLeft className="h-3.5 w-3.5" /> Goal analysis</Link></header>
		{!questions.length && !result ? <section className="py-12 sm:py-20"><div className="mb-8"><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Quick profile</p><h1 className="mt-3 text-3xl font-black text-white">Help us understand where you are.</h1><p className="mt-3 text-sm text-slate-400">Your answers shape the diagnostic. There is no perfect starting point.</p><p className="mt-3 text-xs font-bold text-indigo-400">Goal: {context?.careerTitle}</p></div><div className="mb-6 h-1.5 rounded-full bg-slate-800"><div className="h-full rounded-full bg-emerald-400 transition-all" style={{ width: `${((profileStep + 1) / 4) * 100}%` }} /></div>{profileStep === 0 && <div><h2 className="text-lg font-bold text-white">How would you describe your experience?</h2><div className="mt-5 grid gap-3 sm:grid-cols-2">{experienceOptions.map((option) => <button key={option} onClick={() => setProfile((current) => ({ ...current, experienceLevel: option }))} className={`rounded-xl border p-4 text-left text-sm font-bold ${profile.experienceLevel === option ? "border-emerald-400 bg-emerald-400/10 text-emerald-300" : "border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-600"}`}>{option}</button>)}</div></div>}{profileStep === 1 && <div><h2 className="text-lg font-bold text-white">Which skills have you used?</h2><p className="mt-2 text-xs text-slate-500">Self-report helps us ask relevant questions; the diagnostic remains the stronger evidence.</p><div className="mt-5 grid gap-2 sm:grid-cols-2">{skillOptions.map(([id, label]) => <button key={id} onClick={() => toggleSkill(id)} className={`rounded-xl border p-3 text-left text-sm font-bold ${profile.knownSkills.includes(id) ? "border-emerald-400 bg-emerald-400/10 text-emerald-300" : "border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-600"}`}>{profile.knownSkills.includes(id) && <Check className="mr-2 inline h-4 w-4" />}{label}</button>)}</div></div>}{profileStep === 2 && <div><h2 className="text-lg font-bold text-white">How much time can you learn each day?</h2><div className="mt-5 grid gap-3 sm:grid-cols-2">{availabilityOptions.map((minutes) => <button key={minutes} onClick={() => setProfile((current) => ({ ...current, dailyLearningMinutes: minutes }))} className={`rounded-xl border p-4 text-left text-sm font-bold ${profile.dailyLearningMinutes === minutes ? "border-emerald-400 bg-emerald-400/10 text-emerald-300" : "border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-600"}`}>{minutes >= 120 ? `${minutes / 60}+ hours` : `${minutes} minutes`} per day</button>)}</div></div>}{profileStep === 3 && <div><h2 className="text-lg font-bold text-white">How do you prefer to learn?</h2><div className="mt-5 grid gap-3 sm:grid-cols-2">{preferenceOptions.map((option) => <button key={option} onClick={() => setProfile((current) => ({ ...current, learningPreferences: current.learningPreferences.includes(option) ? current.learningPreferences.filter((item) => item !== option) : [...current.learningPreferences, option] }))} className={`rounded-xl border p-4 text-left text-sm font-bold ${profile.learningPreferences.includes(option) ? "border-emerald-400 bg-emerald-400/10 text-emerald-300" : "border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-600"}`}>{profile.learningPreferences.includes(option) && <Check className="mr-2 inline h-4 w-4" />}{option}</button>)}</div></div>}{error && <p className="mt-5 text-xs font-bold text-rose-400" role="alert">{error}</p>}<div className="mt-8 flex justify-between gap-3">{profileStep > 0 ? <button onClick={() => setProfileStep((step) => step - 1)} className="flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-3 text-xs font-bold text-slate-300"><ChevronLeft className="h-4 w-4" /> Back</button> : <span />}{profileStep < 3 ? <button disabled={profileStep === 0 && !profile.experienceLevel} onClick={() => setProfileStep((step) => step + 1)} className="flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950 disabled:opacity-40">Next <ArrowRight className="h-4 w-4" /></button> : <button onClick={() => void startDiagnostic()} className="flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950">Begin diagnostic <ArrowRight className="h-4 w-4" /></button>}</div></section> : result ? <section className="py-12 sm:py-20"><p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Check className="h-3.5 w-3.5" /> Diagnostic complete</p><h1 className="mt-4 text-4xl font-black text-white">Now we know where to start.</h1><p className="mt-3 text-sm text-slate-400">Evidence from your {context?.careerTitle} diagnostic has been saved to your learner profile.</p><div className="mt-8 rounded-2xl border border-emerald-500/30 bg-slate-900/80 p-6"><div className="flex items-end justify-between border-b border-slate-800 pb-5"><div><p className="text-[10px] uppercase text-slate-500">Overall diagnostic score</p><p className="mt-2 text-4xl font-black text-emerald-400">{result.overallScore}%</p></div><p className="text-xs text-slate-500">{result.assessmentResults.filter((item) => item.correct).length}/{result.assessmentResults.length} correct</p></div><div className="mt-5 space-y-3">{Object.entries(result.skillProficiency).map(([skillId, score]) => <div key={skillId}><div className="mb-1 flex justify-between text-xs"><span className="font-bold text-slate-300">{labelForSkill(skillId)}</span><span className="font-bold text-slate-500">{score}% assessed</span></div><div className="h-2 rounded-full bg-slate-800"><div className={`h-full rounded-full ${score >= 75 ? "bg-emerald-400" : score < 50 ? "bg-amber-400" : "bg-indigo-400"}`} style={{ width: `${score}%` }} /></div></div>)}</div></div><p className="mt-6 text-xs text-slate-500">Your diagnostic evidence is ready for the next phase. The final learning path has not been generated yet.</p><Link href="/path-preview" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-xs font-black uppercase text-white">Continue to path preview <ArrowRight className="h-4 w-4" /></Link></section> : <section className="py-12 sm:py-20"><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Career diagnostic</p><h1 className="mt-3 text-3xl font-black text-white">Show us what you know.</h1></div><span className="text-xs font-bold text-slate-500">{questionIndex + 1} / {questions.length}</span></div><div className="mt-5 h-2 rounded-full bg-slate-800"><div className="h-full rounded-full bg-emerald-400 transition-all" style={{ width: `${((questionIndex + 1) / questions.length) * 100}%` }} /></div><article className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/80 p-5 sm:p-7"><div className="flex items-center justify-between gap-3"><span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">{labelForSkill(questions[questionIndex].skillId)}</span><span className="text-[10px] text-slate-500">{questions[questionIndex].difficulty}</span></div><h2 className="mt-5 text-xl font-bold leading-relaxed text-white">{questions[questionIndex].question}</h2><div className="mt-7 space-y-3">{questions[questionIndex].options.map((option) => <button key={option} onClick={() => setAnswers((current) => ({ ...current, [questions[questionIndex].questionId]: option }))} className={`w-full rounded-xl border p-4 text-left text-sm font-bold transition-colors ${answers[questions[questionIndex].questionId] === option ? "border-emerald-400 bg-emerald-400/10 text-emerald-300" : "border-slate-800 bg-slate-950/70 text-slate-300 hover:border-slate-600"}`}>{option}</button>)}</div></article>{error && <p className="mt-5 text-xs font-bold text-rose-400" role="alert">{error}</p>}<div className="mt-6 flex justify-between gap-3">{questionIndex > 0 ? <button onClick={() => setQuestionIndex((index) => index - 1)} className="flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-3 text-xs font-bold text-slate-300"><ChevronLeft className="h-4 w-4" /> Previous</button> : <span />}{questionIndex < questions.length - 1 ? <button disabled={!answers[questions[questionIndex].questionId]} onClick={() => setQuestionIndex((index) => index + 1)} className="flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950 disabled:opacity-40">Next <ArrowRight className="h-4 w-4" /></button> : <button disabled={submitting} onClick={() => void submitDiagnostic()} className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-xs font-black uppercase text-white disabled:opacity-40">{submitting ? "Calculating..." : "Submit assessment"} <Check className="h-4 w-4" /></button>}</div></section>}
	</div></main>;
}
