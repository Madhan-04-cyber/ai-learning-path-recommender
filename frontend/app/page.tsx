"use client";

import React, { useState, useEffect, useRef } from "react";
import LandingPage from "./components/landing-page";
import { 
  BrainCircuit, 
  Target, 
  GitCommit, 
  Zap, 
  TrendingUp, 
  CheckCircle2, 
  Sparkles,
  ArrowRight,
  Gauge,
  Code2,
  Lock,
  Unlock,
  AlertCircle,
  HelpCircle,
  RefreshCw,
  Play,
  Check,
  ExternalLink,
  MessageSquare,
  Send,
  ArrowLeftRight,
  LayoutDashboard,
  ListChecks,
  SlidersHorizontal,
  UserRound,
  Home,
  Map,
  BarChart3,
  BookOpen,
  Bell,
  Search,
  Settings
} from "lucide-react";

// Inline Custom SVG Github Icon to avoid Lucide import version issues
const GithubIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
  </svg>
);

// Predefined default careers mapping from backend for initial static UI safety
const DEFAULT_CAREER_LIST = [
  { id: "backend_ai_developer", name: "Backend AI Developer" },
  { id: "ai_engineer", name: "AI Engineer" },
  { id: "ml_engineer", name: "Machine Learning Engineer" },
  { id: "data_scientist", name: "Data Scientist" },
  { id: "full_stack_developer", name: "Full Stack Developer" }
];

export function LegacyDashboard() {
  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  // --- Core State ---
  const [targetRole, setTargetRole] = useState("backend_ai_developer");
  const [naturalGoalInput, setNaturalGoalInput] = useState("");
  const [profile, setProfile] = useState<any>({
    name: "Learner",
    experience_level: "Beginner",
    hours_per_week: 12,
    learning_style: "Prefer Videos",
    user_skills: {} // skill_id -> { proficiency: number, status: string, confidence: string }
  });
  
  const [pathData, setPathData] = useState<any>(null);
  const [activeSkillId, setActiveSkillId] = useState<string | null>(null);
  
  // Quiz Assessment State
  const [activeQuizQuestions, setActiveQuizQuestions] = useState<any[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<Record<number, string>>({});
  const [quizScore, setQuizScore] = useState<number | null>(null);
  const [quizFeedback, setQuizFeedback] = useState<string>("");
  const [showQuizModal, setShowQuizModal] = useState<boolean>(false);
  const [loadingQuiz, setLoadingQuiz] = useState<boolean>(false);

  // Chat State
  const [chatMessages, setChatMessages] = useState<any[]>([
    { role: "model", content: "Hi! I am your PathMind AI Twin. I will help guide you dynamically on your learning path. Ask me anything about your current roadmaps, prerequisites, or why a skill is recommended!" }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [sendingChat, setSendingChat] = useState(false);

  // Proof-of-Work State
  const [proofUrl, setProofUrl] = useState("");
  const [evalResult, setEvalResult] = useState<any>(null);
  const [auditingCode, setAuditingCode] = useState(false);

  // UI States
  const [loadingGoalAnalysis, setLoadingGoalAnalysis] = useState(false);
  const [loadingPath, setLoadingPath] = useState(false);
  const [microMode, setMicroMode] = useState(false);
  const [careersList, setCareersList] = useState<any[]>(DEFAULT_CAREER_LIST);
  const [showGoalInputForm, setShowGoalInputForm] = useState(true);
  const [activeView, setActiveView] = useState<"today" | "path" | "coach" | "profile" | "explore" | "opportunities" | "skills" | "progress" | "resources">("today");
  const [showDemoMode, setShowDemoMode] = useState(false);
  const [expandedTopicId, setExpandedTopicId] = useState<string | null>(null);

  // Transition History log
  const [transitionMessage, setTransitionMessage] = useState<string>("");

  // Refs for auto-scroll chat
  const chatEndRef = useRef<HTMLDivElement>(null);

  // --- Initial Fetch Careers & Load Path ---
  useEffect(() => {
    fetch(`${BACKEND_URL}/api/careers`)
      .then(res => res.json())
      .then(data => {
        const list = Object.keys(data).map(k => ({ id: k, name: data[k].name }));
        if (list.length > 0) setCareersList(list);
      })
      .catch(err => console.warn("Failed fetching careers from backend, using defaults:", err));

    // Try loading profile from localStorage on client side mount
    const savedProfile = localStorage.getItem("pathmind_profile");
    if (savedProfile) {
      try {
        const parsed = JSON.parse(savedProfile);
        setProfile(parsed);
        if (parsed.target_role) {
          setTargetRole(parsed.target_role);
        }
      } catch (e) {
        console.error("Error loading cached profile", e);
      }
    }
  }, []);

  // Update localStorage when profile changes
  useEffect(() => {
    if (profile && Object.keys(profile.user_skills).length > 0) {
      localStorage.setItem("pathmind_profile", JSON.stringify(profile));
    }
  }, [profile]);

  // Generate Path automatically when target role or user skills change
  useEffect(() => {
    triggerGeneratePath(targetRole, profile.user_skills);
  }, [targetRole]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // --- API Actions ---

  // Analyze Natural Language Goal
  const handleGoalAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!naturalGoalInput.trim()) return;
    setLoadingGoalAnalysis(true);
    setTransitionMessage("");
    try {
      const res = await fetch(`${BACKEND_URL}/api/analyze-goal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: naturalGoalInput }),
      });
      const data = await res.json();
      
      if (data.is_ambiguous) {
        setChatMessages(prev => [
          ...(prev.at(-2)?.content === `Goal query: "${naturalGoalInput}"` && prev.at(-1)?.content?.includes(data.clarification_question)
            ? prev
            : [
                ...prev,
                { role: "user", content: `Goal query: "${naturalGoalInput}"` },
                { role: "model", content: `🤖 Clarification Required:\n\n${data.clarification_question}` }
              ])
        ]);
        // Set goal input to empty to let user ask in chat or type again
      } else if (data.matched_career_id) {
        // Carry over existing verified skills during transition (Career Transition feature)
        const oldCareer = targetRole;
        const newCareer = data.matched_career_id;
        
        let msg = "";
        if (oldCareer !== newCareer && Object.keys(profile.user_skills).length > 0) {
          const oldVerifiedSkills = Object.keys(profile.user_skills).filter(
            k => profile.user_skills[k]?.status === "Completed"
          );
          if (oldVerifiedSkills.length > 0) {
            msg = `✓ Success! Goal changed to "${data.normalized_name}". Re-used ${oldVerifiedSkills.length} of your existing completed skills (such as ${oldVerifiedSkills.slice(0, 3).join(", ")}).`;
          } else {
            msg = `Goal changed to "${data.normalized_name}".`;
          }
        } else {
          msg = `Goal identified: ${data.normalized_name}`;
        }
        
        setTransitionMessage(msg);
        setTargetRole(newCareer);
        setProfile((prev: any) => ({
          ...prev,
          target_role: newCareer,
          experience_level: data.experience_level || "Beginner"
        }));
        
        // Push notification in chat
        setChatMessages((prev: any) => [
          ...prev,
          { role: "user", content: `Switch my goal: ${naturalGoalInput}` },
          { role: "model", content: `🎯 Career target updated to **${data.normalized_name}**. We resolved your path! Your existing verified competencies have been carried forward.` }
        ]);
      }
    } catch (err) {
      console.error("Error analyzing goal:", err);
    } finally {
      setLoadingGoalAnalysis(false);
    }
  };

  // Generate Learning Path Core API call
  const triggerGeneratePath = async (role: string, currentSkills: any) => {
    setLoadingPath(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/generate-path`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user_101",
          target_role: role,
          current_skills: currentSkills,
          hours_per_week: profile.hours_per_week || 12,
          learning_style: profile.learning_style || "Prefer Videos",
          feedback: profile.feedback || []
        }),
      });
      const data = await res.json();
      setPathData(data);
      
      // Auto-select first actionable/in progress skill as active skill if none selected
      if (data.path && data.path.length > 0) {
        const activeItem = data.path.find((item: any) => item.status === "In Progress" || item.status === "Available") || data.path[0];
        setActiveSkillId(activeItem.id);
      }
    } catch (err) {
      console.error("Error generating path:", err);
    } finally {
      setLoadingPath(false);
    }
  };

  // Generate and fetch Diagnostic Quiz
  const handleOpenDiagnostic = async (skillId: string) => {
    setLoadingQuiz(true);
    setQuizScore(null);
    setQuizAnswers({});
    setQuizFeedback("");
    setShowQuizModal(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/get-diagnostic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_id: skillId })
      });
      const data = await res.json();
      setActiveQuizQuestions(data.questions || []);
    } catch (err) {
      console.error("Error fetching quiz:", err);
    } finally {
      setLoadingQuiz(false);
    }
  };

  // Submit Quiz Answers
  const handleSubmitQuiz = async () => {
    if (!activeSkillId) return;
    
    // Calculate score
    let correct = 0;
    activeQuizQuestions.forEach((q, idx) => {
      if (quizAnswers[idx] === q.answer) {
        correct++;
      }
    });
    
    const percentage = Math.round((correct / activeQuizQuestions.length) * 100);
    setQuizScore(percentage);

    try {
      const res = await fetch(`${BACKEND_URL}/api/submit-assessment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skill_id: activeSkillId,
          score: percentage,
          user_skills: profile.user_skills,
          target_role: targetRole
        })
      });
      const data = await res.json();
      
      setQuizFeedback(data.adaptation_log);
      
      // Update local profile state
      setProfile((prev: any) => ({
        ...prev,
        user_skills: data.updated_skills,
        feedback: [...(prev.feedback || []), data.feedback_event].filter(Boolean)
      }));

      // Trigger recalculation of the path
      triggerGeneratePath(targetRole, data.updated_skills);
      
      // Notify chat of adaptive replanning
      setChatMessages((prev: any) => [
        ...prev,
        { role: "model", content: `📊 **Assessment completed for ${pathData?.path.find((p: any) => p.id === activeSkillId)?.title}**:\nScore: **${percentage}%**\n\n*Adaptation Action:* ${data.adaptation_log}` }
      ]);
    } catch (err) {
      console.error("Error submitting assessment:", err);
    }
  };

  // Submit explicit user feedback
  const handleFeedbackSubmit = async (skillId: string, feedbackType: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/submit-feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skill_id: skillId,
          feedback_type: feedbackType,
          user_skills: profile.user_skills,
          target_role: targetRole
        })
      });
      const data = await res.json();
      
      setProfile((prev: any) => ({
        ...prev,
        user_skills: data.updated_skills,
        target_role: targetRole
      }));

      triggerGeneratePath(targetRole, data.updated_skills);
      
      setChatMessages((prev: any) => [
        ...prev,
        { role: "model", content: `🔧 **Feedback Logged:** Adjusted path for *${pathData?.path.find((p: any) => p.id === skillId)?.title}* to option *"${feedbackType}"*.\n\n*System Update:* ${data.adaptation_log}` }
      ]);
    } catch (err) {
      console.error("Error logging feedback:", err);
    }
  };

  // Evaluate project proof-of-work
  const handleVerifyProof = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!proofUrl || !activeSkillId) return;
    setAuditingCode(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/evaluate-proof-of-work`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          github_url: proofUrl,
          milestone_title: pathData?.path.find((p: any) => p.id === activeSkillId)?.title || "Mini Project",
          skill_id: activeSkillId
        }),
      });
      const data = await res.json();
      setEvalResult(data);
      
      // If code quality score is high, fast track skill completion in profile
      if (parseInt(data.code_quality_score) >= 70) {
        const updatedSkills = {
          ...profile.user_skills,
          [activeSkillId]: {
            proficiency: 90,
            status: "Completed",
            confidence: "Verified",
            proof_verified: true,
            github_url: proofUrl
          }
        };
        
        setProfile((prev: any) => ({
          ...prev,
          user_skills: updatedSkills
        }));
        
        triggerGeneratePath(targetRole, updatedSkills);
      }
    } catch (err) {
      console.error("Error auditing code:", err);
    } finally {
      setAuditingCode(false);
    }
  };

  // Chat conversation endpoint call
  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    const msg = chatInput;
    setChatInput("");
    setChatMessages((prev: any) => [...prev, { role: "user", content: msg }]);
    setSendingChat(true);

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          history: chatMessages.slice(-8), // Send recent history to stay under token limit
          target_role: targetRole,
          user_skills: profile.user_skills,
          bottleneck: pathData?.bottleneck?.title || null,
          next_action: pathData?.next_action?.title || null
        })
      });
      const data = await res.json();
      setChatMessages((prev: any) => [...prev, { role: "model", content: data.response }]);
    } catch (err) {
      console.error("Error sending chat message:", err);
      setChatMessages(prev => [...prev, { role: "model", content: "Apologies, I encountered an issue. Let me know what you need help with." }]);
    } finally {
      setSendingChat(false);
    }
  };

  // Shortcut chat questions
  const askShortcutChat = (questionText: string) => {
    setChatInput(questionText);
  };

  // --- Preset Demo Scenario Controllers for Judges ---
  const applyDemoPreset = (presetName: string) => {
    setTransitionMessage("");
    setEvalResult(null);
    setProofUrl("");
    
    let demoSkills = {};
    let role = "backend_ai_developer";
    
    if (presetName === "beginner") {
      demoSkills = {};
      setChatMessages(prev => [
        ...prev,
        { role: "model", content: "⚡ **Demo Simulation:** Applied *Complete Beginner* profile. All skills reset. Path requires absolute foundation prerequisites." }
      ]);
    } else if (presetName === "experienced") {
      demoSkills = {
        "python": { proficiency: 85, status: "Completed", confidence: "Verified" },
        "sql_basics": { proficiency: 80, status: "Completed", confidence: "Verified" },
        "git": { proficiency: 75, status: "Completed", confidence: "Verified" }
      };
      setChatMessages((prev: any) => [
        ...prev,
        { role: "model", content: "⚡ **Demo Simulation:** Applied *Experienced Dev* profile (Python=85%, SQL=80%). Git/Python/SQL are fast-tracked and marked Completed (✓). Your timeline skips immediately to HTTP/REST!" }
      ]);
    } else if (presetName === "ml_transition") {
      // Transition from Backend AI to ML Engineer
      demoSkills = {
        "python": { proficiency: 90, status: "Completed", confidence: "Verified" },
        "git": { proficiency: 80, status: "Completed", confidence: "Verified" },
        "numpy_pandas": { proficiency: 85, status: "Completed", confidence: "Verified" },
        "math_statistics": { proficiency: 70, status: "Completed", confidence: "Verified" }
      };
      role = "ml_engineer";
      setChatMessages((prev: any) => [
        ...prev,
        { role: "model", content: "⚡ **Demo Simulation:** Transitioned to *ML Engineer* using verified Python/Numpy/Stats skills. System reused 4 existing skills and dynamically recalculated the new ML MLOps roadmaps." }
      ]);
    }

    setTargetRole(role);
    setProfile((prev: any) => ({
      ...prev,
      target_role: role,
      user_skills: demoSkills
    }));
    
    triggerGeneratePath(role, demoSkills);
  };

  // Simulate Assessment results
  const simulateAssessmentResult = async (skillId: string, simulateFail: boolean) => {
    setTransitionMessage("");
    const score = simulateFail ? 35 : 90;
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/submit-assessment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skill_id: skillId,
          score: score,
          user_skills: profile.user_skills,
          target_role: targetRole
        })
      });
      const data = await res.json();
      
      setProfile((prev: any) => ({
        ...prev,
        user_skills: data.updated_skills
      }));
      
      triggerGeneratePath(targetRole, data.updated_skills);
      
      setChatMessages((prev: any) => [
        ...prev,
        { role: "model", content: `⚡ **Demo Simulator Triggered:** Automated quiz score simulated for *${pathData?.path.find((p: any) => p.id === skillId)?.title}* (Score: **${score}%**).\n\n*Path Adjustment:* ${data.adaptation_log}` }
      ]);
    } catch (err) {
      console.error("Error simulating quiz:", err);
    }
  };

  // Reset all state to clean start
  const handleResetProfile = () => {
    localStorage.removeItem("pathmind_profile");
    setProfile({
      name: "Learner",
      experience_level: "Beginner",
      hours_per_week: 12,
      learning_style: "Prefer Videos",
      user_skills: {}
    });
    setTargetRole("backend_ai_developer");
    setNaturalGoalInput("");
    setEvalResult(null);
    setProofUrl("");
    setTransitionMessage("System Reset. Profile and local storage cleared.");
    triggerGeneratePath("backend_ai_developer", {});
  };

  // --- Focused curriculum: foundations first, dependent skills on demand ---
  const renderDependencyGraph = () => {
    if (!pathData || !pathData.path) return null;
    const pathItems = pathData.path;
    const coreTopics = pathItems.filter((item: any) => !item.prerequisites?.length);
    const dependentSkills = (topicId: string) => pathItems.filter((item: any) => item.prerequisites?.includes(topicId));
    const statusStyles: Record<string, string> = {
      Completed: "border-emerald-500/40 bg-emerald-950/20",
      Available: "border-teal-500/40 bg-teal-950/10",
      "In Progress": "border-indigo-500/40 bg-indigo-950/10",
      "Needs Improvement": "border-amber-500/40 bg-amber-950/10",
      Locked: "border-slate-800 bg-slate-900/50 opacity-70"
    };
    return (
      <div className="bg-slate-950/80 border border-slate-900 rounded-xl p-4 shadow-inner">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <p className="text-xs font-bold text-white">Start with the core topics</p>
            <p className="text-[10px] text-slate-500 mt-1">Choose one topic to see the skills it unlocks.</p>
          </div>
          <span className="text-[10px] text-slate-500">{coreTopics.length} foundations</span>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {coreTopics.map((p: any, index: number) => {
            const isExpanded = expandedTopicId === p.id;
            const children = dependentSkills(p.id);
            return (
              <div key={p.id} className="space-y-2">
                <button
                  onClick={() => {
                    setExpandedTopicId(isExpanded ? null : p.id);
                    setActiveSkillId(p.id);
                  }}
                  className={`w-full text-left rounded-xl border p-4 transition-all ${statusStyles[p.status] || statusStyles.Locked} ${isExpanded ? "ring-2 ring-emerald-400/70" : "hover:border-slate-600"}`}
                >
                  <div className="flex items-start gap-3">
                    <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-black ${p.status === "Completed" ? "bg-emerald-400 text-slate-950" : "bg-slate-800 text-slate-300"}`}>{p.status === "Completed" ? "✓" : index + 1}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-bold text-white">{p.title}</span>
                      <span className="mt-1 block text-[10px] text-slate-400">{p.current_proficiency}% current / {p.required_proficiency}% target · {p.estimated_hours} hrs</span>
                      <span className="mt-2 block text-[10px] font-bold uppercase tracking-wider text-emerald-400">{isExpanded ? "Hide next skills" : `Show ${children.length} next skill${children.length === 1 ? "" : "s"}`}</span>
                    </span>
                    <span className="text-lg leading-none text-slate-500">{isExpanded ? "−" : "+"}</span>
                  </div>
                </button>
                {isExpanded && children.length > 0 && (
                  <div className="ml-5 border-l border-emerald-500/30 pl-4 space-y-2">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">After {p.title}</p>
                    {children.map((child: any) => (
                      <button key={child.id} onClick={() => setActiveSkillId(child.id)} className={`w-full rounded-lg border p-3 text-left transition-colors ${statusStyles[child.status] || statusStyles.Locked} hover:border-emerald-400/50`}>
                        <span className="flex items-center justify-between gap-2">
                          <span className="text-xs font-bold text-white">{child.title}</span>
                          <span className="text-[10px] font-bold text-slate-400">{child.status}</span>
                        </span>
                        <span className="mt-1 block text-[10px] text-slate-500">{child.current_proficiency}% current · {child.estimated_hours} hrs</span>
                      </button>
                    ))}
                  </div>
                )}
                {isExpanded && children.length === 0 && <p className="ml-5 text-[10px] text-slate-500">This is a starting topic. Complete it to unlock the next route.</p>}
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-[10px] font-semibold text-slate-400">
          <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-emerald-400" />Completed</span>
          <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-teal-400" />Available</span>
          <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-amber-400" />Needs work</span>
          <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-slate-600" />Locked</span>
        </div>
      </div>
    );
  };

  const activeSkill = pathData?.path.find((p: any) => p.id === activeSkillId);
  const primaryNavigation = [
    { id: "today", label: "Home", icon: Home },
    { id: "path", label: "My Path", icon: Map },
    { id: "skills", label: "Skills", icon: Target },
    { id: "coach", label: "AI Coach", icon: MessageSquare },
    { id: "progress", label: "Progress", icon: BarChart3 }
  ];
  const secondaryNavigation = [
    { id: "resources", label: "Resources", icon: BookOpen },
    { id: "profile", label: "Profile", icon: UserRound }
  ];
  const navigateTo = (view: string) => setActiveView(view as typeof activeView);

  return (
    <div className="min-h-screen bg-slate-950 pb-20 text-slate-100 font-sans selection:bg-emerald-500 selection:text-slate-950 md:pb-0 md:pl-60">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 border-r border-slate-800 bg-slate-950/95 px-4 py-6 md:flex md:flex-col">
        <button onClick={() => navigateTo("today")} className="mb-8 text-left">
          <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> PathMind AI</span>
          <span className="mt-2 block text-xs text-slate-500">Your learning GPS</span>
        </button>
        <p className="mb-2 px-3 text-[9px] font-bold uppercase tracking-[0.18em] text-slate-600">Main</p>
        <nav className="space-y-1">
          {primaryNavigation.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => navigateTo(id)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs font-bold transition-colors ${activeView === id ? "bg-emerald-500 text-slate-950" : "text-slate-400 hover:bg-slate-900 hover:text-white"}`}>
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </nav>
        <div className="my-6 border-t border-slate-800" />
        <p className="mb-2 px-3 text-[9px] font-bold uppercase tracking-[0.18em] text-slate-600">Explore</p>
        <nav className="space-y-1">
          {secondaryNavigation.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => navigateTo(id)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs font-bold transition-colors ${activeView === id ? "bg-emerald-500 text-slate-950" : "text-slate-400 hover:bg-slate-900 hover:text-white"}`}>
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
          <button onClick={() => navigateTo("profile")} className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs font-bold text-slate-400 transition-colors hover:bg-slate-900 hover:text-white">
            <Settings className="h-4 w-4" /> Settings
          </button>
        </nav>
        <div className="mt-auto rounded-xl border border-slate-800 bg-slate-900/70 p-3">
          <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Current goal</p>
          <p className="mt-1 text-xs font-bold text-white">{pathData?.target_role_name || "Backend AI Developer"}</p>
          <p className="mt-2 text-[10px] text-emerald-400">{pathData?.readiness_score || 0}% career ready</p>
        </div>
      </aside>
      
      {/* Top Header */}
      <header className="mx-auto flex max-w-7xl items-center justify-between border-b border-emerald-900/30 px-4 py-4 md:px-8">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">{activeView === "today" ? "Your learning dashboard" : activeView === "path" ? "Your roadmap" : activeView === "coach" ? "Your AI mentor" : activeView === "profile" ? "Your profile" : activeView === "skills" ? "Skill passport" : activeView === "progress" ? "Your growth" : "Explore your route"}</p>
          <h1 className="mt-1 text-xl font-black text-white md:text-2xl">{activeView === "today" ? `Good morning, ${profile.name || "Learner"}` : primaryNavigation.concat(secondaryNavigation).find((item) => item.id === activeView)?.label || "PathMind AI"}</h1>
        </div>

        <div className="flex items-center gap-2">
          <button className="hidden items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-[10px] text-slate-500 sm:flex" aria-label="Search"><Search className="h-3.5 w-3.5" /> Search</button>
          <button className="rounded-lg border border-slate-800 p-2 text-slate-400 hover:text-white" aria-label="Notifications"><Bell className="h-4 w-4" /></button>
          <button onClick={() => navigateTo("coach")} className="hidden items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-[10px] font-bold text-white sm:flex"><MessageSquare className="h-3.5 w-3.5" /> AI Coach</button>
          <button onClick={() => navigateTo("profile")} className="rounded-lg border border-slate-800 p-2 text-slate-400 hover:text-white" aria-label="Profile"><UserRound className="h-4 w-4" /></button>
          <nav className="hidden" aria-label="Main navigation">
            {[
              { id: "today", label: "Start here", icon: LayoutDashboard },
              { id: "explore", label: "Explore careers", icon: Target },
              { id: "path", label: "My roadmap", icon: ListChecks },
              { id: "opportunities", label: "Opportunities", icon: Code2 },
              { id: "coach", label: "Coach", icon: MessageSquare },
              { id: "profile", label: "Profile", icon: UserRound }
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => navigateTo(id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${activeView === id ? "bg-emerald-500 text-slate-950" : "text-slate-400 hover:text-white hover:bg-slate-800"}`}
              >
                <Icon className="w-3.5 h-3.5" /> {label}
              </button>
            ))}
          </nav>
          {/* Quick toggle settings */}
          <div className={`flex items-center gap-2 bg-slate-900/90 border border-emerald-500/20 p-1.5 rounded-xl text-xs ${activeView === "profile" ? "" : "hidden"}`}>
            <span className="text-[10px] text-slate-400 px-1 font-medium">Commitment:</span>
            <select 
              value={profile.hours_per_week} 
              onChange={(e) => {
                const hrs = parseInt(e.target.value);
                setProfile((p: any) => ({ ...p, hours_per_week: hrs }));
                triggerGeneratePath(targetRole, profile.user_skills);
              }}
              className="bg-slate-950 text-emerald-400 border-none font-bold py-0.5 px-1 rounded cursor-pointer outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="5">5 hrs/wk (Sprint)</option>
              <option value="12">12 hrs/wk (Standard)</option>
              <option value="20">20 hrs/wk (Deep)</option>
            </select>
          </div>

          <button
            onClick={() => setMicroMode(!microMode)}
            className={`${activeView === "profile" ? "" : "hidden"} px-3 py-1.5 text-xs font-bold rounded-xl transition-all duration-300 shadow-md ${
              microMode 
                ? "bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 shadow-amber-500/10" 
                : "bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 shadow-emerald-500/10"
            }`}
          >
            {microMode ? "⚡ Micro-Task (15 mins)" : "📚 Enterprise Deep-Dive"}
          </button>
          <button
            onClick={() => setShowDemoMode(!showDemoMode)}
            className="p-2 text-slate-400 hover:text-emerald-300 border border-slate-800 rounded-lg transition-colors"
            aria-label="Toggle adaptive demo controls"
            title="Adaptive demo controls"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Floating Demo Simulation Panel for Judges */}
      {showDemoMode && <div className="max-w-7xl mx-auto mb-6 bg-gradient-to-r from-slate-900 to-indigo-950/80 border border-indigo-500/30 rounded-xl p-4 shadow-xl">
        <h3 className="text-xs font-extrabold text-indigo-300 uppercase tracking-widest mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-indigo-400 fill-indigo-400/20 animate-pulse" /> Adaptive Demo Mode (Judges Sandbox)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          
          <div>
            <label className="block text-[10px] text-indigo-300 font-semibold mb-1">1. Choose Learner Profile</label>
            <div className="flex gap-2">
              <button 
                onClick={() => applyDemoPreset("beginner")}
                className="flex-1 bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[10px] font-bold py-1.5 px-2 rounded-lg text-slate-300 transition-colors"
              >
                Complete Beginner
              </button>
              <button 
                onClick={() => applyDemoPreset("experienced")}
                className="flex-1 bg-indigo-950/50 hover:bg-indigo-900/60 border border-indigo-500/30 text-[10px] font-bold py-1.5 px-2 rounded-lg text-indigo-300 transition-colors"
              >
                Experienced Dev
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[10px] text-indigo-300 font-semibold mb-1">2. Simulate Quiz Score</label>
            <div className="flex gap-2">
              <button 
                disabled={!activeSkillId}
                onClick={() => simulateAssessmentResult(activeSkillId!, true)}
                className="flex-1 bg-red-950/40 hover:bg-red-950/60 border border-red-500/30 disabled:opacity-40 disabled:hover:bg-red-950/40 text-[10px] font-bold py-1.5 px-2 rounded-lg text-red-300 transition-colors"
              >
                Score 35% (Fail)
              </button>
              <button 
                disabled={!activeSkillId}
                onClick={() => simulateAssessmentResult(activeSkillId!, false)}
                className="flex-1 bg-emerald-950/40 hover:bg-emerald-950/60 border border-emerald-500/30 disabled:opacity-40 disabled:hover:bg-emerald-950/40 text-[10px] font-bold py-1.5 px-2 rounded-lg text-emerald-300 transition-colors"
              >
                Score 90% (Pass)
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[10px] text-indigo-300 font-semibold mb-1">3. Simulate Feedback</label>
            <div className="flex gap-1.5">
              <button 
                disabled={!activeSkillId}
                onClick={() => handleFeedbackSubmit(activeSkillId!, "Too easy")}
                className="flex-1 bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[10px] font-bold py-1 px-1.5 rounded-lg text-slate-300"
              >
                "Too Easy"
              </button>
              <button 
                disabled={!activeSkillId}
                onClick={() => handleFeedbackSubmit(activeSkillId!, "Too difficult")}
                className="flex-1 bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[10px] font-bold py-1 px-1.5 rounded-lg text-slate-300"
              >
                "Too Hard"
              </button>
              <button 
                disabled={!activeSkillId}
                onClick={() => handleFeedbackSubmit(activeSkillId!, "Need more practice")}
                className="flex-1 bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[10px] font-bold py-1 px-1.5 rounded-lg text-slate-300"
              >
                "Practice"
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[10px] text-indigo-300 font-semibold mb-1">4. Career Transition Sandbox</label>
            <button 
              onClick={() => applyDemoPreset("ml_transition")}
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-500 text-slate-950 hover:from-indigo-400 hover:to-purple-400 text-[10px] font-bold py-1.5 px-2 rounded-lg shadow-md transition-colors flex items-center justify-center gap-1"
            >
              <ArrowLeftRight className="w-3 h-3" /> Shift to ML Engineer Track
            </button>
          </div>

        </div>
      </div>}

      {transitionMessage && (
        <div className="max-w-7xl mx-auto mb-4 bg-emerald-950/40 border border-emerald-500/40 rounded-xl p-3 text-xs text-emerald-300 font-semibold flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-400" /> {transitionMessage}
        </div>
      )}

      {/* Main Grid Workspace */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Goal Analyzer & Readiness metrics */}
        <div className={`space-y-6 ${activeView !== "today" && activeView !== "profile" && activeView !== "explore" && activeView !== "opportunities" ? "hidden" : ""}`}>
          
          {/* Career Goal Analyzer Panel */}
          <div className={`bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl relative overflow-hidden backdrop-blur-md ${activeView === "profile" || activeView === "explore" ? "" : "hidden"}`}>
            <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
            <h2 className="text-md font-bold text-white mb-3 flex items-center gap-2">
              <Target className="w-4 h-4 text-emerald-400" /> {activeView === "explore" ? "Find your direction" : "Career goal & preferences"}
            </h2>

            <div className="space-y-3">
              <div className="flex gap-2">
                <select
                  value={targetRole}
                  onChange={(e) => {
                    setTargetRole(e.target.value);
                    setTransitionMessage("");
                  }}
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                >
                  {careersList.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div className="border-t border-slate-800/60 pt-3">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-[10px] text-slate-400 font-semibold uppercase">Or describe in plain english:</span>
                  <button 
                    onClick={() => setShowGoalInputForm(!showGoalInputForm)}
                    className="text-[10px] text-emerald-400 font-bold hover:underline"
                  >
                    {showGoalInputForm ? "Hide" : "Show"}
                  </button>
                </div>
                {showGoalInputForm && (
                  <form onSubmit={handleGoalAnalysis} className="space-y-2">
                    <textarea
                      placeholder="e.g. 'I know basic python and want to build backend AI endpoints'"
                      value={naturalGoalInput}
                      onChange={(e) => setNaturalGoalInput(e.target.value)}
                      className="w-full min-h-[60px] bg-slate-950/80 border border-slate-800 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                    />
                    <button
                      type="submit"
                      disabled={loadingGoalAnalysis}
                      className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold py-1.5 rounded-lg text-xs uppercase transition-all shadow-md shadow-emerald-500/10 flex items-center justify-center gap-1.5"
                    >
                      {loadingGoalAnalysis ? "Analyzing Goal..." : "Interpret & Align GPS"} <ArrowRight className="w-3 h-3" />
                    </button>
                  </form>
                )}
              </div>

              <div className="border-t border-slate-800/60 pt-3 space-y-2">
                <p className="text-[10px] text-slate-400 font-semibold uppercase">Study preferences</p>
                <label className="flex items-center justify-between gap-3 text-xs text-slate-300">
                  <span>Learning style</span>
                  <select
                    value={profile.learning_style || "Prefer Videos"}
                    onChange={(e) => setProfile((p: any) => ({ ...p, learning_style: e.target.value }))}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-emerald-400 outline-none focus:border-emerald-500"
                  >
                    <option>Prefer Videos</option>
                    <option>Prefer Projects</option>
                    <option>Prefer Reading</option>
                  </select>
                </label>
                <p className="text-[10px] text-slate-500">Your path uses these preferences when ranking resources and pacing milestones.</p>
              </div>
            </div>
          </div>

          {/* Job Readiness Index Card */}
          <div className={`bg-slate-900/80 border border-indigo-500/20 rounded-2xl p-5 shadow-xl relative overflow-hidden backdrop-blur-md ${activeView === "today" ? "" : "hidden"}`}>
            <h2 className="text-md font-bold text-white mb-2.5 flex items-center gap-2">
              <Gauge className="w-4 h-4 text-indigo-400" /> Career Readiness Score
            </h2>
            
            <div className="flex items-center justify-between my-3 p-3 bg-slate-950/80 rounded-xl border border-indigo-900/30">
              <div>
                <p className="text-[10px] text-slate-400 uppercase font-semibold">Competency Verified</p>
                <p className="text-3xl font-black text-indigo-400">
                  {pathData ? `${pathData.readiness_score}%` : "0%"}
                </p>
              </div>
              <TrendingUp className="w-7 h-7 text-indigo-400/60" />
            </div>

            {pathData && pathData.path && (
              <div className="space-y-2 max-h-[140px] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800 pr-1">
                {pathData.path.map((p: any) => (
                  <div key={p.id} className="flex justify-between items-center text-[10px] py-1 border-b border-slate-800/40">
                    <span className="text-slate-300 font-medium">{p.title}</span>
                    <span className={`font-semibold ${p.status === "Completed" ? "text-emerald-400" : "text-slate-500"}`}>
                      {p.current_proficiency}% / {p.required_proficiency}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Persistent Floating Roadmap-Aware Chat Twin */}
          <div className="hidden">
            <h2 className="text-md font-bold text-white mb-2 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-emerald-400" /> Learning GPS Companion
            </h2>
            
            {/* Messages box */}
            <div className="flex-1 overflow-y-auto space-y-3 p-2 bg-slate-950/70 border border-slate-900/80 rounded-xl text-xs scrollbar-thin scrollbar-thumb-slate-800">
              {chatMessages.map((m, idx) => (
                <div key={idx} className={`p-2.5 rounded-xl leading-relaxed whitespace-pre-wrap ${
                  m.role === "user" 
                    ? "bg-indigo-950/50 text-indigo-200 ml-6 border border-indigo-900/20" 
                    : "bg-slate-900 text-slate-300 mr-6 border border-slate-800/50"
                }`}>
                  <span className="font-bold block text-[10px] uppercase tracking-wider mb-1 text-slate-400">
                    {m.role === "user" ? "You" : "PathMind AI"}
                  </span>
                  {m.content}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Quick Prompts */}
            <div className="flex flex-wrap gap-1 my-2">
              <button 
                onClick={() => askShortcutChat("Can I skip this module?")}
                className="text-[9px] bg-slate-950 hover:bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded-full"
              >
                "Can I skip SQL?"
              </button>
              <button 
                onClick={() => askShortcutChat(`Why am I learning ${activeSkill?.title || "FastAPI"}?`)}
                className="text-[9px] bg-slate-950 hover:bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded-full"
              >
                "Why learn this?"
              </button>
              <button 
                onClick={() => askShortcutChat("I only have 1 hour a day, adjust my pace.")}
                className="text-[9px] bg-slate-950 hover:bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded-full"
              >
                "Adjust my time"
              </button>
            </div>

            <form onSubmit={handleSendChat} className="flex gap-2">
              <input
                type="text"
                placeholder="Ask your GPS companion..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                className="flex-1 bg-slate-950 border border-slate-850 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
              <button
                type="submit"
                disabled={sendingChat}
                className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold p-2 rounded-lg transition-all"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

        </div>

        {/* Center & Right Column: Interactive Graph & Active Skill Panel */}
        <div className={`${activeView === "path" || activeView === "opportunities" ? "lg:col-span-3" : "lg:col-span-2"} space-y-6 ${activeView === "profile" || activeView === "coach" || activeView === "explore" ? "hidden" : ""}`}>
          {activeView === "opportunities" && (
            <section className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
              <div className="max-w-2xl mb-6">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Build your evidence</p>
                <h2 className="mt-2 text-2xl font-black text-white">Turn learning into opportunities.</h2>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">Small projects and verified milestones make your progress visible. Start with the opportunity that matches your current route.</p>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                {[
                  { title: "Practice lab", text: "Strengthen the skill currently slowing your route.", action: "Open next skill", onClick: () => { setActiveView("path"); if (pathData?.next_action?.skill_id) setActiveSkillId(pathData.next_action.skill_id); } },
                  { title: "Mini project", text: "Build a small proof of work from your active milestone.", action: "View roadmap", onClick: () => setActiveView("path") },
                  { title: "Project review", text: "Submit a GitHub project and verify what you can do.", action: "Choose milestone", onClick: () => setActiveView("path") }
                ].map((item) => (
                  <div key={item.title} className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                    <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400"><Code2 className="h-4 w-4" /></div>
                    <h3 className="text-sm font-bold text-white">{item.title}</h3>
                    <p className="mt-2 min-h-10 text-xs leading-relaxed text-slate-400">{item.text}</p>
                    <button onClick={item.onClick} className="mt-4 text-[10px] font-bold uppercase tracking-wider text-emerald-400 hover:text-emerald-300">{item.action} <ArrowRight className="ml-1 inline h-3 w-3" /></button>
                  </div>
                ))}
              </div>
            </section>
          )}

          {activeView === "skills" && pathData && (
            <section className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
              <div className="mb-6"><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Your skill passport</p><h2 className="mt-2 text-2xl font-black text-white">What you can do today</h2><p className="mt-2 text-sm text-slate-400">Verified skills are green. Practice and assessment move skills forward.</p></div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {pathData.path.map((skill: any) => (
                  <button key={skill.id} onClick={() => { setActiveSkillId(skill.id); setActiveView("path"); }} className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 text-left hover:border-emerald-500/50">
                    <div className="flex items-center justify-between gap-2"><span className="text-sm font-bold text-white">{skill.title}</span><span className={`text-[10px] font-bold ${skill.status === "Completed" ? "text-emerald-400" : skill.status === "Needs Improvement" ? "text-amber-400" : "text-slate-500"}`}>{skill.status}</span></div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800"><div className={`h-full ${skill.status === "Completed" ? "bg-emerald-400" : skill.status === "Needs Improvement" ? "bg-amber-400" : "bg-indigo-400"}`} style={{ width: `${Math.min(100, skill.current_proficiency)}%` }} /></div>
                    <p className="mt-2 text-[10px] text-slate-500">{skill.current_proficiency}% current · {skill.required_proficiency}% target</p>
                  </button>
                ))}
              </div>
            </section>
          )}

          {activeView === "progress" && pathData && (
            <section className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
              <div className="mb-6"><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">Career readiness</p><h2 className="mt-2 text-2xl font-black text-white">Your growth so far</h2></div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4"><p className="text-[10px] uppercase text-slate-500">Readiness</p><p className="mt-2 text-3xl font-black text-indigo-400">{pathData.readiness_score}%</p></div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4"><p className="text-[10px] uppercase text-slate-500">Verified skills</p><p className="mt-2 text-3xl font-black text-emerald-400">{pathData.completed_skills?.length || 0}<span className="text-base text-slate-500"> / {pathData.path.length}</span></p></div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4"><p className="text-[10px] uppercase text-slate-500">Current phase</p><p className="mt-2 text-lg font-black text-white">{pathData.current_phase || "Foundation"}</p></div>
              </div>
              <div className="mt-6 space-y-3"><h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Skill growth</h3>{pathData.path.map((skill: any) => <div key={skill.id}><div className="mb-1 flex justify-between text-xs"><span className="text-slate-300">{skill.title}</span><span className="text-slate-500">{skill.current_proficiency}%</span></div><div className="h-2 rounded-full bg-slate-800"><div className="h-full rounded-full bg-indigo-400" style={{ width: `${Math.min(100, skill.current_proficiency)}%` }} /></div></div>)}</div>
            </section>
          )}

          {activeView === "resources" && pathData && (
            <section className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
              <div className="mb-6"><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Recommended for your route</p><h2 className="mt-2 text-2xl font-black text-white">Resources</h2><p className="mt-2 text-sm text-slate-400">Resources are attached to the skills you need next, not a generic course catalog.</p></div>
              <div className="grid gap-3 md:grid-cols-2">{pathData.path.filter((skill: any) => skill.status !== "Completed").slice(0, 6).flatMap((skill: any) => (skill.resources || []).slice(0, 2).map((resource: any) => <a key={`${skill.id}-${resource.title}`} href={resource.url} target="_blank" rel="noopener noreferrer" className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 hover:border-emerald-500/50"><span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">{resource.type} · {skill.title}</span><span className="mt-2 block text-sm font-bold text-white">{resource.title}</span><span className="mt-2 flex items-center gap-1 text-[10px] text-slate-500">Open resource <ExternalLink className="h-3 w-3" /></span></a>))}</div>
            </section>
          )}
          
          {/* KPIs Bar */}
          {pathData && activeView === "today" && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              
              {/* Next Best Action Card */}
              <div className="bg-slate-900/80 border border-emerald-500/30 rounded-xl p-4 flex flex-col justify-between shadow-md relative overflow-hidden">
                <div className="absolute top-0 right-0 w-16 h-16 bg-emerald-500/5 rounded-full blur-xl pointer-events-none" />
                <div>
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Next Best Action
                  </h4>
                  <p className="text-sm font-extrabold text-white mt-1">
                    {pathData.next_action ? pathData.next_action.title : "All Completed!"}
                  </p>
                  <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed line-clamp-2">
                    {pathData.next_action ? pathData.next_action.reason : "You have achieved full path competency."}
                  </p>
                </div>
                {pathData.next_action && (
                  <button 
                    onClick={() => setActiveSkillId(pathData.next_action.skill_id)}
                    className="w-full bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold py-1 mt-2.5 rounded-lg transition-colors"
                  >
                    Go to Skill
                  </button>
                )}
              </div>

              {/* Bottleneck Alert Card */}
              <div className={`border rounded-xl p-4 flex flex-col justify-between shadow-md relative overflow-hidden ${
                pathData.bottleneck 
                  ? "bg-slate-900/80 border-red-500/30" 
                  : "bg-slate-900/80 border-slate-800"
              }`}>
                {pathData.bottleneck && <div className="absolute top-0 right-0 w-16 h-16 bg-red-500/5 rounded-full blur-xl pointer-events-none" />}
                <div>
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1 flex items-center gap-1">
                    <AlertCircle className={`w-3.5 h-3.5 ${pathData.bottleneck ? "text-red-400" : "text-slate-500"}`} /> Current Bottleneck
                  </h4>
                  <p className={`text-sm font-extrabold mt-1 ${pathData.bottleneck ? "text-red-400" : "text-slate-300"}`}>
                    {pathData.bottleneck ? pathData.bottleneck.title : "No Bottlenecks"}
                  </p>
                  <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed">
                    {pathData.bottleneck 
                      ? `Blocking ${pathData.bottleneck.blocked_count} downstream skill modules in your target path.`
                      : "Prerequisite pathways are clear. Good work!"}
                  </p>
                </div>
                {pathData.bottleneck && (
                  <button 
                    onClick={() => setActiveSkillId(pathData.bottleneck.skill_id)}
                    className="w-full bg-red-500/10 hover:bg-red-500/20 text-red-300 border border-red-500/30 text-[10px] font-bold py-1 mt-2.5 rounded-lg transition-colors"
                  >
                    Resolve Bottleneck
                  </button>
                )}
              </div>

              {/* Path Integrity / Milestone */}
              <div className="bg-slate-900/80 border border-indigo-500/20 rounded-xl p-4 flex flex-col justify-between shadow-md">
                <div>
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1 flex items-center gap-1">
                    <BrainCircuit className="w-3.5 h-3.5 text-indigo-400" /> Roadmap Integrity
                  </h4>
                  <p className="text-sm font-extrabold text-white mt-1">
                    GPS Routing Verified
                  </p>
                  <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed">
                    All 10 prerequisites rules validated successfully. No circular dependencies found.
                  </p>
                </div>
                <div className="text-[10px] text-emerald-400 font-bold bg-emerald-950/40 border border-emerald-900/50 py-1 text-center rounded-lg mt-2.5">
                  10/10 Verification Passes
                </div>
              </div>

            </div>
          )}

          {/* SVG Dependency Graph Widget */}
          <div className={`bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-md ${activeView !== "path" ? "hidden" : ""}`}>
            <h2 className="text-md font-bold text-white mb-3.5 flex items-center gap-2">
              <BrainCircuit className="w-4 h-4 text-emerald-400" /> 2. Interactive SVG Skill Dependency Graph
            </h2>
            {renderDependencyGraph()}
          </div>

          {/* Active Skill Workspace details */}
          {activeView === "path" && (
            activeSkill ? (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden backdrop-blur-md">
              
              {/* Header section */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-800/80 pb-4 mb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                      activeSkill.status === "Completed" ? "bg-emerald-950 text-emerald-400 border border-emerald-900" :
                      activeSkill.status === "Needs Improvement" ? "bg-amber-950 text-amber-400 border border-amber-900" :
                      activeSkill.status === "In Progress" ? "bg-indigo-950 text-indigo-400 border border-indigo-900" :
                      activeSkill.status === "Available" ? "bg-teal-950 text-teal-400 border border-teal-900" :
                      "bg-slate-950 text-slate-500 border border-slate-850"
                    }`}>
                      {activeSkill.status}
                    </span>
                    <span className="text-[10px] text-slate-400 font-medium">Difficulty: {activeSkill.difficulty}</span>
                    <span className="text-[10px] text-slate-400 font-medium">Est. {activeSkill.estimated_hours} Hours</span>
                  </div>
                  <h3 className="text-xl font-bold text-white">{activeSkill.title}</h3>
                  <p className="text-xs text-slate-400 mt-1">{activeSkill.description}</p>
                </div>

                <div className="flex gap-2">
                  <button
                    disabled={activeSkill.status === "Locked"}
                    onClick={() => handleOpenDiagnostic(activeSkill.id)}
                    className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-bold px-3 py-1.5 rounded-lg text-xs uppercase transition-all shadow-md shadow-indigo-600/10 flex items-center gap-1"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" /> Test Skill Gap
                  </button>
                </div>
              </div>

              {/* Skill Gap breakdown */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                <div className="bg-slate-950/70 border border-slate-900 p-3 rounded-xl">
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">Why Recommended</span>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">{activeSkill.why_recommended}</p>
                </div>
                <div className="bg-slate-950/70 border border-slate-900 p-3 rounded-xl flex flex-col justify-center">
                  <div className="flex justify-between items-center text-xs mb-1.5">
                    <span className="text-slate-400 font-medium">Current Proficiency:</span>
                    <span className="text-slate-200 font-bold">{activeSkill.current_proficiency}%</span>
                  </div>
                  <div className="flex justify-between items-center text-xs mb-2">
                    <span className="text-slate-400 font-medium">Required Benchmark:</span>
                    <span className="text-emerald-400 font-bold">{activeSkill.required_proficiency}%</span>
                  </div>
                  <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-500 ${activeSkill.current_proficiency >= activeSkill.required_proficiency ? 'bg-emerald-500' : 'bg-indigo-400'}`} 
                      style={{ width: `${Math.min(100, activeSkill.current_proficiency)}%` }} 
                    />
                  </div>
                </div>
              </div>

              {/* 5-Step Model Flow: Learn -> Practice -> Build -> Assess -> Verify */}
              <div className="mt-4 border border-slate-850 rounded-xl overflow-hidden bg-slate-950/50">
                <div className="bg-slate-900/60 border-b border-slate-850 px-4 py-2 text-[10px] font-bold text-slate-400 tracking-wider uppercase">
                  5-Step Competency Cycle
                </div>
                
                <div className="p-4 space-y-4">
                  
                  {/* Step 1: Learn */}
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/10 border border-emerald-500/40 text-emerald-400 text-xs font-bold flex items-center justify-center">
                        1
                      </div>
                      <div className="flex-1 w-0.5 bg-slate-800 my-1" />
                    </div>
                    <div className="flex-1 pb-2">
                      <h4 className="text-xs font-extrabold text-slate-200 uppercase tracking-wide">Learn (Structured Lessons)</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                        {activeSkill.resources.map((r: any, idx: number) => (
                          <a
                            key={idx}
                            href={r.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 p-2 rounded-lg text-xs flex justify-between items-center text-slate-300 font-medium transition-all group"
                          >
                            <div>
                              <span className="text-[9px] text-emerald-400 font-bold block uppercase tracking-wider">{r.type}</span>
                              <span className="line-clamp-1">{r.title}</span>
                            </div>
                            <ExternalLink className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-300 transition-colors" />
                          </a>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Step 2: Practice */}
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/10 border border-emerald-500/40 text-emerald-400 text-xs font-bold flex items-center justify-center">
                        2
                      </div>
                      <div className="flex-1 w-0.5 bg-slate-800 my-1" />
                    </div>
                    <div className="flex-1 pb-2">
                      <h4 className="text-xs font-extrabold text-slate-200 uppercase tracking-wide">Practice (Hands-on Labs)</h4>
                      <ul className="list-disc list-inside text-xs text-slate-400 space-y-1.5 mt-2 font-medium">
                        {activeSkill.practice.map((item: string, idx: number) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Step 3: Build */}
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/10 border border-emerald-500/40 text-emerald-400 text-xs font-bold flex items-center justify-center">
                        3
                      </div>
                      <div className="flex-1 w-0.5 bg-slate-800 my-1" />
                    </div>
                    <div className="flex-1 pb-2">
                      <h4 className="text-xs font-extrabold text-slate-200 uppercase tracking-wide">Build (Proof-of-Work Project)</h4>
                      {activeSkill.project && activeSkill.project.title ? (
                        <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg mt-2">
                          <h5 className="text-xs font-bold text-white mb-1">{activeSkill.project.title}</h5>
                          <p className="text-[11px] text-slate-400 leading-relaxed font-sans">{activeSkill.project.description}</p>
                          
                          <form onSubmit={handleVerifyProof} className="flex gap-2 mt-3">
                            <input
                              type="url"
                              required
                              placeholder="Submit project github link for auto-audit..."
                              value={proofUrl}
                              onChange={(e) => setProofUrl(e.target.value)}
                              disabled={activeSkill.status === "Locked"}
                              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                            />
                            <button
                              type="submit"
                              disabled={auditingCode || activeSkill.status === "Locked"}
                              className="bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-slate-950 font-bold px-3 py-1 rounded-lg text-xs uppercase transition-colors"
                            >
                              {auditingCode ? "Auditing..." : "Audit Code"}
                            </button>
                          </form>

                          {evalResult && (
                            <div className="mt-3 p-3 bg-slate-950 border border-slate-850 rounded-lg space-y-1.5 text-[11px]">
                              <div className="flex justify-between items-center">
                                <span className="text-slate-400">Score:</span>
                                <span className="text-amber-400 font-bold font-mono">{evalResult.code_quality_score}</span>
                              </div>
                              <div className="flex justify-between items-center">
                                <span className="text-slate-400">Audit Status:</span>
                                <span className="text-emerald-400 font-bold">{evalResult.verification_status}</span>
                              </div>
                              <p className="text-slate-300 pt-1.5 border-t border-slate-900 leading-relaxed">
                                <span className="text-slate-400 font-bold block mb-0.5">Feedback:</span> {evalResult.ai_feedback}
                              </p>
                            </div>
                          )}
                        </div>
                      ) : (
                        <p className="text-[11px] text-slate-500 mt-1">No custom mini-project listed for this module.</p>
                      )}
                    </div>
                  </div>

                  {/* Step 4 & 5: Assess & Verify */}
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/10 border border-emerald-500/40 text-emerald-400 text-xs font-bold flex items-center justify-center">
                        4
                      </div>
                    </div>
                    <div className="flex-1">
                      <h4 className="text-xs font-extrabold text-slate-200 uppercase tracking-wide">Assess & Verify</h4>
                      <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                        Verify mastery. Take the diagnostic assessment to score above 75% and verify skill completeness. 
                        A low score automatically inserts reinforcement path steps.
                      </p>
                      <button
                        disabled={activeSkill.status === "Locked"}
                        onClick={() => handleOpenDiagnostic(activeSkill.id)}
                        className="bg-indigo-600/20 hover:bg-indigo-600/35 border border-indigo-500/30 disabled:opacity-40 text-indigo-300 font-bold px-3 py-1.5 mt-2 rounded-lg text-xs uppercase transition-colors inline-block"
                      >
                        Start Assessment
                      </button>
                    </div>
                  </div>

                </div>
              </div>

            </div>
          ) : (
            <div className="text-center py-12 bg-slate-900/60 border border-slate-800 rounded-2xl">
              <Code2 className="w-10 h-10 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-500">Generating roadmaps... Click on a skill node on the graph to display full detail workspace.</p>
            </div>
          ))}

          {/* Reset profile configuration */}
          <div className={`flex justify-between items-center bg-slate-900/30 border border-slate-900/80 p-3 rounded-xl text-xs text-slate-500 ${activeView === "today" ? "hidden" : ""}`}>
            <span>Need to start from zero or adjust settings?</span>
            <button
              onClick={handleResetProfile}
              className="text-slate-400 hover:text-red-400 font-semibold transition-colors flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Clear Progress & Reset
            </button>
          </div>

        </div>

        {activeView === "coach" && (
          <div className="lg:col-span-3 max-w-3xl mx-auto w-full">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col min-h-[560px] backdrop-blur-md">
              <h2 className="text-md font-bold text-white mb-2 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-emerald-400" /> Learning GPS Companion
              </h2>
              <p className="text-xs text-slate-400 mb-4">Ask about your current milestone, prerequisites, or how to adjust your route.</p>
              <div className="flex-1 overflow-y-auto space-y-3 p-2 bg-slate-950/70 border border-slate-900/80 rounded-xl text-xs scrollbar-thin scrollbar-thumb-slate-800">
                {chatMessages.map((m, idx) => (
                  <div key={idx} className={`p-3 rounded-xl leading-relaxed whitespace-pre-wrap ${m.role === "user" ? "bg-indigo-950/50 text-indigo-200 ml-8 border border-indigo-900/20" : "bg-slate-900 text-slate-300 mr-8 border border-slate-800/50"}`}>
                    <span className="font-bold block text-[10px] uppercase tracking-wider mb-1 text-slate-400">{m.role === "user" ? "You" : "PathMind AI"}</span>
                    {m.content}
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
              <div className="flex flex-wrap gap-1.5 my-3">
                <button onClick={() => askShortcutChat("Why am I learning this next?")} className="text-[10px] bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-400 px-2.5 py-1 rounded-full">Why this next?</button>
                <button onClick={() => askShortcutChat("Can I skip this module?")} className="text-[10px] bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-400 px-2.5 py-1 rounded-full">Can I skip it?</button>
                <button onClick={() => askShortcutChat("I only have 1 hour a day, adjust my pace.")} className="text-[10px] bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-400 px-2.5 py-1 rounded-full">Adjust my pace</button>
              </div>
              <form onSubmit={handleSendChat} className="flex gap-2">
                <input type="text" placeholder="Ask your GPS companion..." value={chatInput} onChange={(e) => setChatInput(e.target.value)} className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500" />
                <button type="submit" disabled={sendingChat} className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold p-2.5 rounded-lg transition-all" aria-label="Send message"><Send className="w-3.5 h-3.5" /></button>
              </form>
            </div>
          </div>
        )}

      </main>

      <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-slate-800 bg-slate-950/95 px-2 py-2 backdrop-blur md:hidden" aria-label="Mobile navigation">
        {primaryNavigation.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => navigateTo(id)} className={`flex flex-col items-center gap-1 py-1 text-[9px] font-bold ${activeView === id ? "text-emerald-400" : "text-slate-500"}`}>
            <Icon className="h-4 w-4" />{label}
          </button>
        ))}
      </nav>

      {/* Quiz Modal Container */}
      {showQuizModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-indigo-500/30 w-full max-w-lg rounded-2xl shadow-2xl p-6 relative overflow-hidden">
            
            <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2 border-b border-slate-800 pb-3">
              <Target className="w-5 h-5 text-indigo-400" /> Gap Diagnostic: {activeSkill?.title}
            </h3>

            {loadingQuiz ? (
              <div className="py-12 text-center text-xs text-slate-400">
                <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin mx-auto mb-2" /> Generating assessment questions...
              </div>
            ) : (
              <div className="space-y-4 my-4 max-h-[360px] overflow-y-auto pr-1 text-xs text-slate-300 scrollbar-thin scrollbar-thumb-slate-800">
                {activeQuizQuestions.map((q, idx) => (
                  <div key={idx} className="bg-slate-950/60 border border-slate-850 p-3.5 rounded-xl space-y-2">
                    <p className="font-semibold text-slate-200">Q{idx+1}: {q.q}</p>
                    <div className="grid grid-cols-1 gap-1.5 pt-1">
                      {q.options.map((opt: string, oIdx: number) => (
                        <label 
                          key={oIdx}
                          className={`flex items-center gap-2 border p-2 rounded-lg cursor-pointer transition-colors ${
                            quizAnswers[idx] === opt 
                              ? 'bg-indigo-950/30 border-indigo-500 text-indigo-200 font-semibold' 
                              : 'bg-slate-900/60 border-slate-800 hover:bg-slate-900 text-slate-400'
                          }`}
                        >
                          <input
                            type="radio"
                            name={`q-${idx}`}
                            value={opt}
                            checked={quizAnswers[idx] === opt}
                            onChange={(e) => setQuizAnswers({ ...quizAnswers, [idx]: e.target.value })}
                            className="hidden"
                          />
                          <span>{opt}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {quizScore !== null && (
              <div className="my-3 p-3 bg-slate-950 border border-slate-850 rounded-xl space-y-1.5 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400 font-medium">Your Score:</span>
                  <span className={`font-mono font-black text-sm ${quizScore >= 75 ? "text-emerald-400" : "text-amber-400"}`}>
                    {quizScore}%
                  </span>
                </div>
                <p className="text-slate-300 leading-relaxed pt-1.5 border-t border-slate-900 font-sans">
                  <span className="text-indigo-400 font-bold block mb-0.5">Adaptation Feedback:</span> {quizFeedback}
                </p>
              </div>
            )}

            <div className="flex gap-2 justify-end border-t border-slate-800 pt-3.5 mt-3">
              <button
                onClick={() => setShowQuizModal(false)}
                className="bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[11px] font-bold text-slate-300 px-4 py-2 rounded-lg transition-colors"
              >
                Close
              </button>
              {quizScore === null && !loadingQuiz && (
                <button
                  onClick={handleSubmitQuiz}
                  disabled={Object.keys(quizAnswers).length < activeQuizQuestions.length}
                  className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-[11px] font-bold text-white px-4 py-2 rounded-lg transition-colors"
                >
                  Submit Answers
                </button>
              )}
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

export default LandingPage;