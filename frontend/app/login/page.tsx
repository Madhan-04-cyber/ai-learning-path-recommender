"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ArrowRight, LockKeyhole, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

type StoredProfile = {
	name?: string;
	email?: string;
	[target: string]: unknown;
};

function readProfile(): StoredProfile {
	try {
		const saved = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null");
		return saved && typeof saved === "object" ? saved as StoredProfile : {};
	} catch {
		return {};
	}
}

export default function LoginPage() {
	const router = useRouter();
	const [name, setName] = useState("");
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");

	const submit = (event: FormEvent<HTMLFormElement>) => {
		event.preventDefault();
		const cleanName = name.trim();
		const cleanEmail = email.trim().toLowerCase();
		if (!cleanName || !cleanEmail || !password) {
			setError("Enter your name, email, and password to continue.");
			return;
		}
		if (!/^\S+@\S+\.\S+$/.test(cleanEmail)) {
			setError("Enter a valid email address.");
			return;
		}

		const profile = readProfile();
		window.localStorage.setItem("pathmind_profile", JSON.stringify({ ...profile, name: cleanName, email: cleanEmail }));
		window.localStorage.setItem("pathmind_session", JSON.stringify({ authenticated: true, email: cleanEmail }));
		router.push("/profile");
	};

	return (
		<main className="min-h-screen bg-slate-950 px-5 py-6 text-slate-100 sm:px-8">
			<div className="mx-auto max-w-md">
				<header className="flex items-center justify-between border-b border-slate-800 pb-5">
					<Link href="/" className="flex items-center gap-2 text-sm font-black text-white">
						<Sparkles className="h-4 w-4 text-emerald-400" /> PATHMIND AI
					</Link>
					<Link href="/" className="text-xs font-bold text-slate-500 hover:text-white">Back home</Link>
				</header>

				<section className="py-16 sm:py-24">
					<div className="mb-8 text-center">
						<div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-400/30 bg-emerald-400/10 text-emerald-400">
							<LockKeyhole className="h-6 w-6" />
						</div>
						<p className="mt-6 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Your learning workspace</p>
						<h1 className="mt-3 text-3xl font-black text-white">Log in to PathMind</h1>
						<p className="mt-3 text-sm leading-relaxed text-slate-400">Use your details to personalize your learner profile and continue your path.</p>
					</div>

					<form onSubmit={submit} className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl">
						<label className="block text-xs font-bold text-slate-300">
							Full name
							<input aria-label="Full name" value={name} onChange={(event) => setName(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none transition focus:border-emerald-400" placeholder="Alex Morgan" autoComplete="name" />
						</label>
						<label className="block text-xs font-bold text-slate-300">
							Email address
							<input aria-label="Email address" type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none transition focus:border-emerald-400" placeholder="alex@example.com" autoComplete="email" />
						</label>
						<label className="block text-xs font-bold text-slate-300">
							Password
							<input aria-label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none transition focus:border-emerald-400" placeholder="Enter your password" autoComplete="current-password" />
						</label>
						{error ? <p role="alert" className="text-sm text-rose-400">{error}</p> : null}
						<button type="submit" className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-950 hover:bg-emerald-300">
							Continue to profile <ArrowRight className="h-4 w-4" />
						</button>
					</form>
				</section>
			</div>
		</main>
	);
}
