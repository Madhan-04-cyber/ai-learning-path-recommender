"use client";

import React, { useState } from "react";
import { 
  BrainCircuit, 
  Target, 
  GitCommit, 
  Zap, 
  TrendingUp, 
  CheckCircle2, 
  Sparkles,
  ArrowRight,
  Github,
  Gauge,
  Code2
} from "lucide-react";

export default function Dashboard() {
  const [githubUser, setGithubUser] = useState("");
  const [targetRole, setTargetRole] = useState("Cloud AI Engineer");
  const [currentSkills, setCurrentSkills] = useState("Python, REST APIs");
  const [proofUrl, setProofUrl] = useState("");
  const [microMode, setMicroMode] = useState(false);
  
  const [loadingDiag, setLoadingDiag] = useState(false);
  const [loadingPath, setLoadingPath] = useState(false);
  
  const [diagResult, setDiagResult] = useState<any>(null);
  const [pathData, setPathData] = useState<any>(null);
  const [evalResult, setEvalResult] = useState<any>(null);

  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://ai-learning-path-recommender.onrender.com";

  // Trigger GitHub Auto-Scan Diagnostic
  const handleGithubScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!githubUser) return;
    setLoadingDiag(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/github-diagnostic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          github_username: githubUser,
          target_role: targetRole,
        }),
      });
      const data = await res.json();
      setDiagResult(data);
      if (data.detected_skills) {
        setCurrentSkills(data.detected_skills.join(", "));
      }
    } catch (err) {
      console.error("Error in GitHub diagnostic:", err);
    } finally {
      setLoadingDiag(false);
    }
  };

  // Generate Learning Path
  const handleGeneratePath = async () => {
    setLoadingPath(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/generate-path`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user_101",
          target_role: targetRole,
          current_skills: currentSkills.split(",").map((s) => s.trim()),
          hours_per_week: 12,
        }),
      });
      const data = await res.json();
      setPathData(data);
    } catch (err) {
      console.error("Error generating path:", err);
    } finally {
      setLoadingPath(false);
    }
  };

  // Evaluate Proof-of-Work GitHub Repo
  const handleVerifyProof = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${BACKEND_URL}/api/evaluate-proof-of-work`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          github_url: proofUrl,
          milestone_title: "Enterprise Architecture Microservice",
        }),
      });
      const data = await res.json();
      setEvalResult(data);
    } catch (err) {
      console.error("Error evaluating proof of work:", err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans selection:bg-emerald-500 selection:text-slate-950">
      
      {/* Top Header */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start md:items-center border-b border-emerald-900/40 pb-6 mb-8 gap-4">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs tracking-widest uppercase mb-1">
            <Sparkles className="w-4 h-4 text-emerald-400 animate-pulse" /> HCLTech AMPlified AI Prototype
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-indigo-400">
            Pathfinder AI Twin
          </h1>
        </div>
        <div className="flex items-center gap-3 bg-slate-900/90 border border-emerald-500/30 p-2 rounded-xl backdrop-blur-md shadow-lg shadow-emerald-950/20">
          <span className="text-xs font-medium text-slate-400 px-2">Mode:</span>
          <button
            onClick={() => setMicroMode(!microMode)}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all duration-300 ${
              microMode 
                ? "bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 shadow-md shadow-amber-500/20" 
                : "bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 shadow-md shadow-emerald-500/20"
            }`}
          >
            {microMode ? "⚡ Micro-Task (15 mins/day)" : "📚 Enterprise Deep-Dive"}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: GitHub Profiler & Readiness Metrics */}
        <div className="space-y-6">
          
          {/* GitHub Auto-Diagnostic Card */}
          <div className="bg-slate-900/80 border border-emerald-500/30 rounded-2xl p-6 shadow-xl relative overflow-hidden backdrop-blur-md">
            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
            <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              <Github className="w-5 h-5 text-emerald-400" /> Agentic GitHub Auto-Scan
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Directly parses your public GitHub footprint to calculate your real skill baseline.
            </p>

            <form onSubmit={handleGithubScan} className="space-y-3">
              <div>
                <input
                  type="text"
                  placeholder="Enter GitHub Username (e.g. Madhan-04-cyber)"
                  value={githubUser}
                  onChange={(e) => setGithubUser(e.target.value)}
                  className="w-full bg-slate-950/90 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={loadingDiag}
                className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold py-2 rounded-lg text-xs tracking-wider uppercase transition-all shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2"
              >
                {loadingDiag ? "Scanning Repositories..." : "Run Agentic Diagnostic"}
              </button>
            </form>

            {diagResult && (
              <div className="mt-4 pt-4 border-t border-slate-800 space-y-2 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Repos Analyzed:</span>
                  <span className="text-white font-mono font-bold">{diagResult.total_repos_analyzed}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Detected Skills:</span>
                  <span className="text-emerald-400 font-semibold">{diagResult.detected_skills?.join(", ")}</span>
                </div>
              </div>
            )}
          </div>

          {/* Job Readiness Index Card */}
          <div className="bg-slate-900/80 border border-indigo-500/30 rounded-2xl p-6 shadow-xl relative overflow-hidden backdrop-blur-md">
            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 rounded-full blur-2xl pointer-events-none" />
            <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              <Gauge className="w-5 h-5 text-indigo-400" /> Job Readiness Index
            </h2>
            
            <div className="flex items-center justify-between my-4 p-4 bg-slate-950/80 rounded-xl border border-indigo-900/40">
              <div>
                <p className="text-xs text-slate-400">Target Readiness</p>
                <p className="text-2xl font-black text-indigo-400">
                  {diagResult ? diagResult.job_readiness_index : "72%"}
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-indigo-400/80" />
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Target Enterprise Role</label>
                <input
                  type="text"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  className="w-full bg-slate-950/90 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <button
                onClick={handleGeneratePath}
                disabled={loadingPath}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 rounded-lg text-xs tracking-wider uppercase transition-all shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2"
              >
                {loadingPath ? "Generating Roadmap..." : "Generate AI Learning Path"} <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

        </div>

        {/* Center & Right Column: Roadmap & Proof-of-Work Verification */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* AI Recommended Path Output */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-emerald-400" /> AI Twin Path & XAI Rationale
            </h2>

            {pathData ? (
              <div className="space-y-4">
                <div className="p-4 bg-emerald-950/30 border border-emerald-800/40 rounded-xl text-xs text-emerald-300 font-mono">
                  Target Role: {pathData.target_role} | Readiness Score: {pathData.readiness_score || "Analyzed"}
                </div>
                <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl whitespace-pre-line text-xs text-slate-300 leading-relaxed font-mono">
                  {pathData.recommendation || JSON.stringify(pathData, null, 2)}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl">
                <Code2 className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-xs text-slate-500">Run the Agentic Diagnostic or click "Generate AI Learning Path" to view your customized roadmap.</p>
              </div>
            )}
          </div>

          {/* Proof-of-Work Code Reviewer */}
          <div className="bg-slate-900/80 border border-amber-500/30 rounded-2xl p-6 shadow-xl backdrop-blur-md">
            <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
              <GitCommit className="w-5 h-5 text-amber-400" /> Proof-of-Work Evaluator ("I've Built")
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Submit your project repository link for automated architectural review.
            </p>

            <form onSubmit={handleVerifyProof} className="flex gap-3 mb-4">
              <input
                type="url"
                required
                placeholder="https://github.com/username/project-repo"
                value={proofUrl}
                onChange={(e) => setProofUrl(e.target.value)}
                className="flex-1 bg-slate-950/90 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
              />
              <button
                type="submit"
                className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-xs uppercase transition-all shadow-md shadow-amber-500/20"
              >
                Audit Code
              </button>
            </form>

            {evalResult && (
              <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Status:</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> {evalResult.verification_status}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Code Quality:</span>
                  <span className="text-amber-400 font-bold font-mono">{evalResult.code_quality_score}</span>
                </div>
                <p className="text-slate-300 pt-2 border-t border-slate-800">
                  <span className="text-slate-400 font-semibold">Audit Feedback:</span> {evalResult.ai_feedback}
                </p>
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}