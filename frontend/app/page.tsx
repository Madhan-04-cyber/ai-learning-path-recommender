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
  ArrowRight
} from "lucide-react";

export default function Dashboard() {
  const [targetRole, setTargetRole] = useState("Cloud AI Engineer");
  const [currentSkills, setCurrentSkills] = useState("Python, Basic SQL");
  const [githubUrl, setGithubUrl] = useState("");
  const [microMode, setMicroMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pathData, setPathData] = useState<any>(null);
  const [evalResult, setEvalResult] = useState<any>(null);

  // Backend URL (Use Render live URL or fallback to localhost)
  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://ai-learning-path-recommender.onrender.com";

  const handleGeneratePath = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/generate-path`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user_101",
          target_role: targetRole,
          current_skills: currentSkills.split(",").map((s) => s.trim()),
          hours_per_week: 10,
        }),
      });
      const data = await res.json();
      setPathData(data);
    } catch (err) {
      console.error("Error generating path:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyProofOfWork = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${BACKEND_URL}/api/evaluate-proof-of-work`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          github_url: githubUrl,
          milestone_title: "Foundational Micro-Architecture Project",
        }),
      });
      const data = await res.json();
      setEvalResult(data);
    } catch (err) {
      console.error("Error evaluating proof of work:", err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      {/* Top Header */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800 pb-6 mb-8 gap-4">
        <div>
          <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm tracking-wide uppercase mb-1">
            <Sparkles className="w-4 h-4" /> HCLTech AMPlified AI Prototype
          </div>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white">
            Pathfinder: AI Learning Twin & Skill Velocity Platform
          </h1>
        </div>
        <div className="flex items-center gap-3 bg-slate-900 border border-slate-800 p-2 rounded-xl">
          <span className="text-xs font-medium text-slate-400 px-2">Mode:</span>
          <button
            onClick={() => setMicroMode(!microMode)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              microMode ? "bg-amber-500/20 text-amber-300 border border-amber-500/30" : "bg-indigo-600 text-white"
            }`}
          >
            {microMode ? "⚡ Micro-Learning (15 mins)" : "📚 Deep-Dive Path"}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Input Controls & Velocity Analytics */}
        <div className="space-y-6">
          {/* Career & Skill Input */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-indigo-400" /> Career Goal & Diagnostic
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Target Enterprise Role</label>
                <input
                  type="text"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Existing Skills (Comma separated)</label>
                <input
                  type="text"
                  value={currentSkills}
                  onChange={(e) => setCurrentSkills(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                onClick={handleGeneratePath}
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5 rounded-lg text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-600/20"
              >
                {loading ? "Analyzing Skills..." : "Generate AI Learning Path"} <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Velocity Predictor Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-400" /> Velocity Predictor
            </h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-2 border-b border-slate-800">
                <span className="text-slate-400">Current Velocity:</span>
                <span className="font-semibold text-emerald-400">0.45 skills/day</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-800">
                <span className="text-slate-400">Target Skill Gap:</span>
                <span className="font-semibold text-amber-400">5 Key Modules</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-slate-400">Est. Readiness Date:</span>
                <span className="font-semibold text-indigo-400">11 Days (High Confidence)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Center & Right Column: Learning Path & Proof-of-Work Engine */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* AI Recommended Path */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-indigo-400" /> AI Twin Path & XAI Rationale
            </h2>

            {pathData ? (
              <div className="space-y-4">
                <div className="p-4 bg-indigo-950/40 border border-indigo-800/50 rounded-xl text-sm text-indigo-200">
                  <span className="font-semibold text-indigo-300">Target Role:</span> {pathData.target_role}
                </div>
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl whitespace-pre-line text-sm text-slate-300 leading-relaxed">
                  {pathData.recommendation || JSON.stringify(pathData, null, 2)}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl">
                <Zap className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-sm text-slate-500">Configure your goal and click "Generate AI Learning Path" to begin.</p>
              </div>
            )}
          </div>

          {/* Proof-of-Work GitHub Evaluator */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
              <GitCommit className="w-5 h-5 text-amber-400" /> Proof-of-Work Evaluator ("I've Built")
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Submit your GitHub repository link to verify project completion with automated code analysis.
            </p>

            <form onSubmit={handleVerifyProofOfWork} className="flex gap-3 mb-4">
              <input
                type="url"
                required
                placeholder="https://github.com/username/project-repo"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500"
              />
              <button
                type="submit"
                className="bg-amber-600 hover:bg-amber-500 text-white font-medium px-4 py-2 rounded-lg text-sm transition-all shadow-lg shadow-amber-600/20"
              >
                Evaluate Code
              </button>
            </form>

            {evalResult && (
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Verification Status:</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> {evalResult.verification_status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Code Quality Score:</span>
                  <span className="text-amber-400 font-bold">{evalResult.code_quality_score}</span>
                </div>
                <p className="text-xs text-slate-300 pt-2 border-t border-slate-800">
                  <span className="text-slate-400 font-semibold">AI Feedback:</span> {evalResult.ai_feedback}
                </p>
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}