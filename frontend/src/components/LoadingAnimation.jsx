import React, { useState, useEffect } from 'react';
import { Brain, Languages, FileText, Sparkles, Activity, CheckCircle } from 'lucide-react';

export default function LoadingAnimation({ isOpen }) {
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);
  
  const steps = [
    { 
      icon: Languages, 
      text: "🌍 Detecting language...", 
      detail: "Analyzing input script (Devanagari/Latin)",
      duration: 2000,
      color: "text-blue-600",
      bg: "bg-blue-50"
    },
    { 
      icon: Brain, 
      text: "🔍 Extracting medical entities (NER)...", 
      detail: "IndicNER analyzing symptoms, conditions, medications",
      duration: 3500,
      color: "text-purple-600",
      bg: "bg-purple-50"
    },
    { 
      icon: Sparkles, 
      text: "📚 Querying medical knowledge (RAG)...", 
      detail: "Retrieving ICD-10 codes, DSM-5 criteria",
      duration: 2500,
      color: "text-yellow-600",
      bg: "bg-yellow-50"
    },
    { 
      icon: Activity, 
      text: "🤖 Generating SOAP note (Gemma 2B)...", 
      detail: "LLM creating structured clinical documentation",
      duration: 8000,
      color: "text-green-600",
      bg: "bg-green-50"
    },
    { 
      icon: Languages, 
      text: "🔄 Translating to target language...", 
      detail: "NLLB-200 translating with entity preservation",
      duration: 3000,
      color: "text-indigo-600",
      bg: "bg-indigo-50"
    }
  ];
  
  useEffect(() => {
    if (!isOpen) return;
    
    // Progress animation
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) return 100;
        return prev + (100 / steps.length / (steps[step].duration / 100));
      });
    }, 100);
    
    // Step progression
    const stepTimer = setTimeout(() => {
      if (step < steps.length - 1) {
        setStep(step + 1);
      }
    }, steps[step].duration);
    
    return () => {
      clearInterval(progressInterval);
      clearTimeout(stepTimer);
    };
  }, [step, isOpen]);
  
  if (!isOpen) return null;
  
  const currentStep = steps[step];
  const totalDuration = steps.reduce((acc, s) => acc + s.duration, 0);
  const elapsedDuration = steps.slice(0, step).reduce((acc, s) => acc + s.duration, 0);
  const remainingSeconds = Math.ceil((totalDuration - elapsedDuration - (Date.now() % 1000)) / 1000);
  
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl p-8 max-w-xl w-full mx-4 shadow-2xl animate-in slide-in-from-bottom-4 duration-500">
        
        {/* Medical Animation */}
        <div className="flex justify-center mb-6">
          <div className="relative w-32 h-32">
            {/* Pulsing circles */}
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-full animate-ping"></div>
            <div className="absolute inset-4 bg-gradient-to-r from-blue-500/40 to-purple-500/40 rounded-full animate-pulse"></div>
            
            {/* Icon Container */}
            <div className={`absolute inset-0 flex items-center justify-center ${currentStep.bg} rounded-full border-4 border-white shadow-lg`}>
              {React.createElement(currentStep.icon, {
                size: 48,
                className: `${currentStep.color} animate-bounce`,
                strokeWidth: 2.5
              })}
            </div>
          </div>
        </div>
        
        {/* Progress Text */}
        <h3 className="text-2xl font-bold text-center mb-2 text-slate-800">
          {currentStep.text}
        </h3>
        
        <p className="text-sm text-center text-slate-500 mb-6">
          {currentStep.detail}
        </p>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-3 mb-4 overflow-hidden shadow-inner">
          <div 
            className="bg-gradient-to-r from-blue-500 via-purple-500 to-indigo-500 h-3 rounded-full transition-all duration-300 relative overflow-hidden"
            style={{ width: `${((step + 1) / steps.length) * 100}%` }}
          >
            {/* Shimmer effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"></div>
          </div>
        </div>
        
        {/* Step Indicators */}
        <div className="flex justify-between items-center mb-6">
          {steps.map((s, idx) => (
            <div key={idx} className="flex flex-col items-center gap-2">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 ${
                  idx < step 
                    ? 'bg-green-500 scale-100' 
                    : idx === step 
                    ? `${s.bg} scale-110 ring-4 ring-${s.color.split('-')[1]}-200` 
                    : 'bg-gray-200 scale-90'
                }`}
              >
                {idx < step ? (
                  <CheckCircle className="text-white" size={20} />
                ) : (
                  React.createElement(s.icon, {
                    size: 20,
                    className: idx === step ? s.color : 'text-gray-400'
                  })
                )}
              </div>
              
              {/* Step label - only show for current and completed */}
              {(idx <= step) && (
                <span className={`text-xs font-semibold ${idx === step ? currentStep.color : 'text-gray-400'}`}>
                  Step {idx + 1}
                </span>
              )}
            </div>
          ))}
        </div>
        
        {/* Estimated Time */}
        <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100">
          <div className="flex justify-between items-center text-sm">
            <span className="text-slate-600 font-medium">
              ⏱️ Estimated time remaining:
            </span>
            <span className="text-slate-900 font-bold text-lg">
              {remainingSeconds}s
            </span>
          </div>
          
          <div className="mt-3 text-xs text-slate-500">
            <strong>Processing Pipeline:</strong> Language Detection → NER → RAG → LLM → Translation
          </div>
        </div>
        
        {/* Fun medical facts (changes with step) */}
        <div className="mt-4 text-center">
          <p className="text-xs text-slate-400 italic">
            {step === 0 && "💡 Did you know? IndicNER supports 11 Indian languages!"}
            {step === 1 && "💡 Extracting symptoms helps improve clinical accuracy by 30%"}
            {step === 2 && "💡 RAG retrieves from 500+ ICD-10 & DSM-5 criteria"}
            {step === 3 && "💡 Gemma 2B processes 2 billion parameters for accuracy"}
            {step === 4 && "💡 Translation preserves medical terminology integrity"}
          </p>
        </div>
      </div>
      
      {/* CSS for shimmer animation */}
      <style jsx>{`
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
      `}</style>
    </div>
  );
}
