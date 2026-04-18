import React, { useEffect, useMemo, useState } from 'react';
import { Brain, FileText, Sparkles, Activity, CheckCircle } from 'lucide-react';
import PropTypes from 'prop-types';

export default function LoadingAnimation({ isOpen }) {
  const [step, setStep] = useState(0);

  const steps = useMemo(() => [
    {
      icon: FileText,
      text: '🧾 Preparing session context...',
      detail: 'Structuring transcript/session data for SOAP processing',
      duration: 1600,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    { 
      icon: Brain,
      text: '🔍 Extracting medical entities (NER)...',
      detail: 'Identifying symptoms, conditions, medications',
      duration: 2600,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
    },
    { 
      icon: Sparkles,
      text: '📚 Querying medical knowledge (RAG)...',
      detail: 'Retrieving relevant clinical context',
      duration: 2200,
      color: 'text-yellow-600',
      bg: 'bg-yellow-50',
    },
    { 
      icon: Activity,
      text: '🤖 Generating SOAP note...',
      detail: 'Creating Subjective, Objective, Assessment, and Plan',
      duration: 4800,
      color: 'text-green-600',
      bg: 'bg-green-50',
    }
  ], []);

  useEffect(() => {
    if (!isOpen) {
      setStep(0);
      return;
    }

    const stepTimer = setTimeout(() => {
      if (step < steps.length - 1) {
        setStep(step + 1);
      }
    }, steps[step].duration);

    return () => {
      clearTimeout(stepTimer);
    };
  }, [isOpen, step, steps]);

  if (!isOpen) return null;

  const currentStep = steps[step];
  const totalDuration = steps.reduce((acc, s) => acc + s.duration, 0);
  const elapsedDuration = steps.slice(0, step).reduce((acc, s) => acc + s.duration, 0);
  const remainingMs = Math.max(0, totalDuration - elapsedDuration);
  const remainingSeconds = Math.ceil(remainingMs / 1000);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl p-8 max-w-xl w-full mx-4 shadow-2xl animate-in slide-in-from-bottom-4 duration-500">

        <div className="flex justify-center mb-6">
          <div className="relative w-32 h-32">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-full animate-ping"></div>
            <div className="absolute inset-4 bg-gradient-to-r from-blue-500/40 to-purple-500/40 rounded-full animate-pulse"></div>

            <div className={`absolute inset-0 flex items-center justify-center ${currentStep.bg} rounded-full border-4 border-white shadow-lg`}>
              {React.createElement(currentStep.icon, {
                size: 48,
                className: `${currentStep.color} animate-bounce`,
                strokeWidth: 2.5,
              })}
            </div>
          </div>
        </div>

        <h3 className="text-2xl font-bold text-center mb-2 text-slate-800">
          {currentStep.text}
        </h3>

        <p className="text-sm text-center text-slate-500 mb-6">
          {currentStep.detail}
        </p>

        <div className="w-full bg-gray-200 rounded-full h-3 mb-4 overflow-hidden shadow-inner">
          <div
            className="bg-gradient-to-r from-blue-500 via-purple-500 to-indigo-500 h-3 rounded-full transition-all duration-300 relative overflow-hidden"
            style={{ width: `${((step + 1) / steps.length) * 100}%` }}
          />
        </div>

        <div className="flex justify-between items-center mb-6">
          {steps.map((s, idx) => (
            <div key={idx} className="flex flex-col items-center gap-2">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 ${
                  idx < step
                    ? 'bg-green-500 scale-100'
                    : idx === step
                    ? `${s.bg} scale-110 ring-4 ring-slate-200`
                    : 'bg-gray-200 scale-90'
                }`}
              >
                {idx < step ? (
                  <CheckCircle className="text-white" size={20} />
                ) : (
                  React.createElement(s.icon, {
                    size: 20,
                    className: idx === step ? s.color : 'text-gray-400',
                  })
                )}
              </div>

              {(idx <= step) && (
                <span className={`text-xs font-semibold ${idx === step ? currentStep.color : 'text-gray-400'}`}>
                  Step {idx + 1}
                </span>
              )}
            </div>
          ))}
        </div>

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
            <strong>Processing Pipeline:</strong> Session Setup → NER → RAG → SOAP Generation
          </div>
        </div>

        <div className="mt-4 text-center">
          <p className="text-xs text-slate-400 italic">
            {step === 0 && '💡 Step 1 prepares the conversation into clinical session format.'}
            {step === 1 && '💡 NER helps retain key medical entities in SOAP sections.'}
            {step === 2 && '💡 RAG brings evidence-backed clinical context for better notes.'}
            {step === 3 && '💡 Final step structures output into SOAP format for review.'}
          </p>
        </div>
      </div>
    </div>
  );
}

LoadingAnimation.propTypes = {
  isOpen: PropTypes.bool,
};
