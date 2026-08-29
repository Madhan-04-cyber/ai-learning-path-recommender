"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Mail, Sparkles, UserRound } from "lucide-react";
import { AppShell } from "../components/app-shell";

type Profile = {
	name?: string;
	email?: string;
	target_role?: string;
	interest?: string;
	goal?: string;
	assessmentResults?: unknown[];
	user_skills?: Record<string, unknown>;
};

function titleize(value?: string) {
	return value ? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) : "Not set yet";
}

export default function ProfilePage() {
	const [profile, setProfile] = useState<Profile | null>(null);
	const [loaded, setLoaded] = useState(false);

	useEffect(() => {
		const timer = window.setTimeout(() => {
			try {
				const saved = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as Profile | null;
				setProfile(saved && typeof saved === "object" ? saved : null);
			} catch {
				setProfile(null);
			} finally {
				setLoaded(true);
			}
		}, 0);
		return () => window.clearTimeout(timer);
	}, []);

	if (!loaded) {
		return <AppShell title="Profile"><div className="h-48 animate-pulse rounded-2xl border border-slate-800 bg-slate-900/70" /></AppShell>;
	}

	if (!profile?.name && !profile?.email) {
		return (
			<AppShell title="Profile">
				<section className="mx-auto max-w-xl rounded-3xl border border-slate-800 bg-slate-900/70 p-8 text-center">
					<UserRound className="mx-auto h-10 w-10 text-emerald-400" />
					<h2 className="mt-5 text-2xl font-black text-white">Create your learner profile</h2>
					<p className="mt-3 text-sm text-slate-400">Log in to add your details and keep them with your PathMind learning workspace.</p>
					<Link href="/login" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950">Log in <ArrowRight className="h-4 w-4" /></Link>
				</section>
			</AppShell>
		);
	}

	const skillCount = Object.keys(profile.user_skills || {}).length;
	return (
		<AppShell title="Profile">
			<div className="mx-auto max-w-3xl space-y-5">
				<section className="rounded-3xl border border-emerald-500/20 bg-[radial-gradient(circle_at_top_right,_rgba(52,211,153,0.12),_transparent_35%),linear-gradient(180deg,rgba(15,23,42,0.95),rgba(9,17,31,0.98))] p-6 sm:p-8">
					<div className="flex flex-wrap items-start justify-between gap-5">
						<div className="flex items-center gap-4">
							<div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-400 text-xl font-black text-slate-950">{(profile.name || "L").charAt(0).toUpperCase()}</div>
							<div><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Learner profile</p><h2 className="mt-2 text-3xl font-black text-white">{profile.name || "Learner"}</h2><p className="mt-1 flex items-center gap-2 text-sm text-slate-400"><Mail className="h-3.5 w-3.5" /> {profile.email || "No email added"}</p></div>
						</div>
						<Link href="/login" className="rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300 hover:border-emerald-400 hover:text-white">Update details</Link>
					</div>
				</section>

				<section className="grid gap-4 sm:grid-cols-3">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"><p className="text-[10px] uppercase tracking-wider text-slate-500">Career target</p><p className="mt-2 break-words text-lg font-black text-white">{titleize(profile.target_role)}</p></div>
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"><p className="text-[10px] uppercase tracking-wider text-slate-500">Interest</p><p className="mt-2 break-words text-lg font-black text-white">{profile.interest || "Not set yet"}</p></div>
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"><p className="text-[10px] uppercase tracking-wider text-slate-500">Skills tracked</p><p className="mt-2 text-lg font-black text-white">{skillCount}</p></div>
				</section>

				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
					<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Sparkles className="mr-2 inline h-3.5 w-3.5" /> Keep moving</p>
					<h3 className="mt-3 text-xl font-black text-white">Your profile powers your learning path.</h3>
					<p className="mt-2 text-sm leading-relaxed text-slate-400">Assessment results, interests, and verified skills are used by the deterministic roadmap and project engines.</p>
					<Link href="/path" className="mt-5 inline-flex items-center gap-2 text-xs font-black uppercase text-emerald-400 hover:text-emerald-300">View my path <ArrowRight className="h-4 w-4" /></Link>
				</section>
			</div>
		</AppShell>
	);
}
