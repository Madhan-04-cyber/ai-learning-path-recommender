"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowRight, Bot, CircleAlert, RefreshCw, Sparkles } from "lucide-react";
import { AppShell } from "../components/app-shell";
import Link from "next/link";
import { usePathname } from "next/navigation";

type Message = { role: "user" | "assistant"; content: string };

type Profile = {
	target_role?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string; confidence?: string }>;
	learningInsight?: string;
	roadmapChanged?: boolean;
	practiceHistory?: Array<{ skillId: string; question: string; answer: string; correct: boolean; difficulty: string; timestamp: string }>;
	assessmentResults?: Array<{ skillId: string; answer: string; correct: boolean }>;
};

type RoadmapItem = { skillId: string; title: string; reason: string; status: string };
type RoadmapData = { items: RoadmapItem[]; nextBestAction: RoadmapItem | null };

const BACKEND_URL = "";

const quickActions = [
	"Why am I learning this?",
	"Explain my next step",
	"I don't understand this",
	"Give me practice",
	"Can I skip this?",
	"Change my schedule",
];

function pageContextLabel(pathname: string) {
	if (pathname === "/home") return "Home";
	if (pathname === "/path") return "My Path";
	if (pathname === "/skills") return "Skills";
	return "Learning Workspace";
}

export default function CoachPage() {
	const pathname = usePathname();
	const [profile, setProfile] = useState<Profile | null>(null);
	const [roadmap, setRoadmap] = useState<RoadmapData | null>(null);
	const [messages, setMessages] = useState<Message[]>([]);
	const [input, setInput] = useState("");
	const [loading, setLoading] = useState(true);
	const [sending, setSending] = useState(false);
	const [error, setError] = useState("");
	const [aiStatus, setAiStatus] = useState<"ready" | "fallback" | "error">("ready");

	useEffect(() => {
		const load = async () => {
			try {
				const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as Profile | null;
				const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as { matched_career_id?: string } | null;
				const targetRole = savedProfile?.target_role || savedAnalysis?.matched_career_id || "backend_ai_developer";
				setProfile(savedProfile || { target_role: targetRole });

				const currentSkills = savedProfile?.user_skills || {};
				const response = await fetch(`${BACKEND_URL}/api/path/generate`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ target_role: targetRole, current_skills: currentSkills, daily_learning_minutes: 60, learning_preferences: [], assessment_results: savedProfile?.assessmentResults || [] }),
				});
				if (response.ok) {
					const data = (await response.json()) as RoadmapData;
					setRoadmap(data);
				}
				setMessages([{ role: "assistant", content: "I’m your context-aware coach. Ask about your next milestone, a skill you want to skip, or how to adjust your schedule." }]);
			} catch (cause) {
				setError(cause instanceof Error ? cause.message : "Coach unavailable.");
			} finally {
				setLoading(false);
			}
		};
		void load();
	}, []);

	const context = useMemo(() => {
		const currentSkillId = roadmap?.nextBestAction?.skillId || roadmap?.items.find((item) => item.status === "CURRENT")?.skillId || null;
		const currentSkill = currentSkillId ? profile?.user_skills?.[currentSkillId] : undefined;
		const weakAreas = Object.entries(profile?.user_skills || {})
			.filter(([, value]) => value.status === "Needs Improvement")
			.map(([key]) => key);
		const recentAssessment = profile?.assessmentResults?.at(-1) || null;
		const recentMistakes = (profile?.practiceHistory || []).filter((item) => !item.correct).slice(-5);
		return {
			current_page: pageContextLabel(pathname),
			current_milestone: roadmap?.nextBestAction?.title || "",
			current_skill: currentSkillId || "",
			skill_proficiency: currentSkill?.proficiency,
			weak_areas: weakAreas,
			roadmap: roadmap?.items || [],
			recent_assessment: recentAssessment || undefined,
			recent_mistakes: recentMistakes,
			learning_preference: "adaptive",
			bottleneck: roadmap?.nextBestAction?.skillId || "",
			next_action: roadmap?.nextBestAction?.title || "",
		};
	}, [pathname, profile, roadmap]);

	const sendMessage = async (message: string) => {
		if (!message.trim()) return;
		const userMessage: Message = { role: "user", content: message };
		setMessages((current) => [...current, userMessage]);
		setInput("");
		setSending(true);
		setError("");
		try {
			const response = await fetch(`${BACKEND_URL}/api/chat`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					message,
					history: messages.slice(-8).map((item) => ({ role: item.role, content: item.content })),
					target_role: profile?.target_role || "backend_ai_developer",
					user_skills: profile?.user_skills || {},
					...context,
				}),
			});
			if (!response.ok) throw new Error("AI service unavailable.");
			const data = (await response.json()) as { response?: string };
			const text = data.response?.trim();
			if (!text) throw new Error("Empty AI response.");
			setMessages((current) => [...current, { role: "assistant", content: text }]);
			setAiStatus("ready");
		} catch (cause) {
			setAiStatus("fallback");
			setMessages((current) => [...current, { role: "assistant", content: "I’m having trouble reaching the AI service right now. I can still help using your local roadmap context." }]);
			setError(cause instanceof Error ? cause.message : "AI unavailable.");
		} finally {
			setSending(false);
		}
	};

	const submit = (event: FormEvent<HTMLFormElement>) => {
		event.preventDefault();
		void sendMessage(input);
	};

	if (loading) {
		return (
			<AppShell title="AI Coach">
				<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
					<div className="h-4 w-28 animate-pulse rounded bg-slate-800" />
					<div className="mt-4 h-80 animate-pulse rounded-2xl bg-slate-800/70" />
				</div>
			</AppShell>
		);
	}

	if (error && messages.length === 0) {
		return (
			<AppShell title="AI Coach">
				<div className="mx-auto max-w-xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<CircleAlert className="mx-auto h-10 w-10 text-rose-400" />
					<h2 className="mt-4 text-2xl font-black text-white">Coach unavailable</h2>
					<p className="mt-2 text-sm text-slate-400">{error}</p>
				</div>
			</AppShell>
		);
	}

	return (
		<AppShell title="AI Coach">
			<div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
					<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Bot className="h-3.5 w-3.5" /> Context-aware coach</div>
					<h2 className="mt-3 text-3xl font-black text-white">Ask about your actual learning path</h2>
					<p className="mt-2 text-sm text-slate-400">The coach sees your goal, milestone, skill level, weak areas, roadmap, recent assessment, and recent mistakes.</p>

					<div className="mt-4 flex flex-wrap gap-2">
						{quickActions.map((action) => (
							<button key={action} onClick={() => void sendMessage(action)} className="rounded-full border border-slate-800 bg-slate-950/60 px-3 py-2 text-[10px] font-bold text-slate-300 hover:border-emerald-400 hover:text-white">
								{action}
							</button>
						))}
					</div>

					<div className="mt-5 space-y-3 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
						{messages.map((message, index) => (
							<div key={index} className={`rounded-xl border p-3 text-sm leading-relaxed ${message.role === "user" ? "border-indigo-500/20 bg-indigo-500/10 text-indigo-100 ml-8" : "border-slate-800 bg-slate-900/80 text-slate-200 mr-8"}`}>
								<p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-slate-500">{message.role === "user" ? "You" : "Coach"}</p>
								{message.content}
							</div>
						))}
						{sending ? <div className="text-xs text-slate-500">Thinking with your context...</div> : null}
					</div>

					<form onSubmit={submit} className="mt-4 flex gap-2">
						<input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask something about your route..." className="flex-1 rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-600" />
						<button type="submit" disabled={sending} className="rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950 disabled:opacity-50">
							Send
						</button>
					</form>
				</section>

				<aside className="space-y-4">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><Sparkles className="h-3.5 w-3.5" /> Context panel</div>
						<div className="mt-4 space-y-2 text-sm text-slate-300">
							<p><span className="text-slate-500">Goal:</span> {profile?.target_role?.replaceAll("_", " ") || "Unknown"}</p>
							<p><span className="text-slate-500">Milestone:</span> {context.current_milestone || "Unknown"}</p>
							<p><span className="text-slate-500">Current skill:</span> {context.current_skill || "Unknown"}</p>
							<p><span className="text-slate-500">Proficiency:</span> {context.skill_proficiency ?? "Unknown"}</p>
							<p><span className="text-slate-500">Weak areas:</span> {context.weak_areas.length ? context.weak_areas.join(", ") : "None recorded"}</p>
						</div>
					</div>

					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><RefreshCw className="h-3.5 w-3.5" /> Safe skip rule</div>
						<p className="mt-3 text-sm leading-relaxed text-slate-300">If you ask to skip a skill, the coach will explain why it is not recommended yet and point you to verification instead of changing the roadmap directly.</p>
					</div>

					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> Page links</div>
						<div className="mt-3 flex flex-wrap gap-2">
							<Link href="/home" className="inline-flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-xs text-slate-300">Home</Link>
							<Link href="/path" className="inline-flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-xs text-slate-300">My Path</Link>
							<Link href="/skills" className="inline-flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-xs text-slate-300">Skills</Link>
						</div>
					</div>
				</aside>
			</div>
		</AppShell>
	);
}
