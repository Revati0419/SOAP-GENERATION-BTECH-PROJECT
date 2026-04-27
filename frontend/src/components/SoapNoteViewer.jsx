import { ClipboardCheck, Download, Printer } from 'lucide-react';
import PropTypes from 'prop-types';

const IMPORTANT_PATTERNS = [
  /\bPHQ-?8\b/gi,
  /\bdiagnosis\b/gi,
  /\brisk\b/gi,
  /\bsafety\b/gi,
  /\bsuicide\b/gi,
  /\bself-harm\b/gi,
  /\bmedication\b/gi,
  /\bfollow-?up\b/gi,
  /\bmood\b/gi,
  /\bsleep\b/gi,
  /\bappetite\b/gi,
  /जोखीम/gi,
  /आत्महत्या/gi,
  /उपचार/gi,
  /औषध/gi,
  /अनुवर्ती/gi,
  /थकवा/gi,
  /मानसिक स्थिती/gi,
];

const fallbackSubsection = 'Key Clinical Points';

const PARAM_LABELS = {
  subjective: {
    chief_complaint: 'मुख्य तक्रार',
    hpi: 'सध्याच्या आजाराचा इतिहास',
    trauma_history: 'आघाताचा इतिहास',
    psychosocial_history: 'मनोसामाजिक इतिहास',
    functional_status: 'कार्यक्षम स्थिती',
  },
  objective: {
    medical_history: 'वैद्यकीय इतिहास',
    past_psych_history: 'पूर्व मनोरुग्ण इतिहास',
    biological_observations: 'जैविक निरीक्षणे',
    mental_status_exam: 'मानसिक स्थिती तपासणी',
    structured_scores: 'PHQ-8 गुण',
  },
  assessment: {
    diagnostic_formulation: 'निदान',
    risk_formulation: 'जोखीम मूल्यांकन',
    contributing_factors: 'योगदान देणारे घटक',
  },
  plan: {
    treatment_safety_plan: 'उपचार आणि सुरक्षा योजना',
    therapy_plan: 'मानसोपचार योजना',
    medication_considerations: 'औषधोपचार',
    followup_monitoring: 'पाठपुरावा',
  },
};

function emphasizeImportant(text, keyPrefix = 'txt') {
  if (!text) return null;

  const ranges = [];
  IMPORTANT_PATTERNS.forEach((pattern) => {
    const re = new RegExp(pattern.source, pattern.flags);
    let match = re.exec(text);
    while (match) {
      ranges.push([match.index, match.index + match[0].length]);
      match = re.exec(text);
    }
  });

  if (!ranges.length) return text;

  ranges.sort((a, b) => a[0] - b[0]);
  const merged = [];
  ranges.forEach((curr) => {
    if (!merged.length || curr[0] > merged[merged.length - 1][1]) {
      merged.push(curr);
    } else {
      merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], curr[1]);
    }
  });

  const nodes = [];
  let cursor = 0;
  merged.forEach(([start, end], idx) => {
    if (start > cursor) {
      nodes.push(<span key={`${keyPrefix}-plain-${idx}`}>{text.slice(cursor, start)}</span>);
    }
    nodes.push(
      <strong key={`${keyPrefix}-bold-${idx}`} className="font-extrabold text-slate-900">
        {text.slice(start, end)}
      </strong>
    );
    cursor = end;
  });

  if (cursor < text.length) {
    nodes.push(<span key={`${keyPrefix}-tail`}>{text.slice(cursor)}</span>);
  }

  return nodes;
}

function normalizeForStructuredParsing(rawText) {
  if (!rawText) return '';

  return rawText
    .replace(/\r/g, '\n')
    .replace(/\s*#{1,6}\s*/g, '\n')
    .replace(/\s+([^:\n-][^:\n]{2,110}:)\s*-\s+/g, '\n$1\n- ')
    .replace(/\s+-\s+/g, '\n- ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function parseStructuredSoap(rawText) {
  const text = normalizeForStructuredParsing(rawText);
  if (!text) return [];

  const lines = text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  const headingRegex = /^[^:\n-][^:\n]{2,120}:$/;
  const subsections = [];
  let current = null;

  lines.forEach((line) => {
    if (headingRegex.test(line) && !line.startsWith('-')) {
      current = { title: line.slice(0, -1), points: [] };
      subsections.push(current);
      return;
    }

    const bullet = line.startsWith('-') ? line.replace(/^-+\s*/, '').trim() : line;
    if (!bullet) return;

    if (!current) {
      current = { title: fallbackSubsection, points: [] };
      subsections.push(current);
    }

    current.points.push(bullet);
  });

  return subsections.filter((sub) => sub.points.length > 0);
}

function parseParametricSection(sectionKey, structured) {
  if (!structured || typeof structured !== 'object') return [];
  const labels = PARAM_LABELS[sectionKey] || {};
  return Object.entries(structured)
    .map(([field, raw]) => {
      const lines = String(raw || '')
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => line.replace(/^-+\s*/, '').trim())
        .filter(Boolean);
      return {
        title: labels[field] || field.replace(/_/g, ' '),
        points: lines,
      };
    })
    .filter((sub) => sub.points.length > 0);
}

function SectionContent({ content, sectionKey, structured, languageLabel, tone = 'default' }) {
  const parsedFromParametric = parseParametricSection(sectionKey, structured);
  const subsections = parsedFromParametric.length ? parsedFromParametric : parseStructuredSoap(content);

  if (!subsections.length) {
    return <span className="italic text-slate-400">Extraction in progress…</span>;
  }

  const keyPoints = subsections.flatMap((s) => s.points).slice(0, 3);

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200/70 bg-slate-50/80 p-4">
        <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Priority clinical points</p>
        <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-slate-700">
          {keyPoints.map((point, idx) => (
            <li key={`kp-${idx}`} className="flex gap-2">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-brand-600" />
              <span>{emphasizeImportant(point, `key-${languageLabel}-${idx}`)}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-3">
        {subsections.map((sub, idx) => (
          <div
            key={`${sub.title}-${idx}`}
            className={`rounded-xl border p-4 ${tone === 'translated' ? 'border-amber-200/80 bg-amber-50/40' : 'border-slate-200/80 bg-white'}`}
          >
            <h5 className="text-sm font-extrabold text-slate-800">{sub.title}</h5>
            <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-slate-700">
              {sub.points.map((point, pIdx) => (
                <li key={`${sub.title}-${pIdx}`} className="flex gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400" />
                  <span>{emphasizeImportant(point, `pt-${languageLabel}-${idx}-${pIdx}`)}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

SectionContent.propTypes = {
  content: PropTypes.string,
  sectionKey: PropTypes.oneOf(['subjective', 'objective', 'assessment', 'plan']).isRequired,
  structured: PropTypes.object,
  languageLabel: PropTypes.string.isRequired,
  tone: PropTypes.oneOf(['default', 'translated']),
};

export default function SoapNoteViewer({ data }) {
  const targetLang = 'marathi';
  const langLabel = 'मराठी';
  const primarySoap = data.soap_marathi || {};
  const primaryParametric = data.soap_marathi_parametric || {};

  const sectionMeta = [
    { key: 'subjective', id: 'S', title: 'Subjective', color: 'text-blue-600',    bg: 'bg-blue-50',    desc: 'Patient concerns and history' },
    { key: 'objective',  id: 'O', title: 'Objective',  color: 'text-indigo-600',  bg: 'bg-indigo-50',  desc: 'Vitals and physical findings' },
    { key: 'assessment', id: 'A', title: 'Assessment', color: 'text-purple-600',  bg: 'bg-purple-50',  desc: 'Diagnosis and clinical logic' },
    { key: 'plan',       id: 'P', title: 'Plan',       color: 'text-emerald-600', bg: 'bg-emerald-50', desc: 'Treatments and follow-ups' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Header */}
      <div className="surface-card flex flex-col justify-between gap-4 rounded-[2rem] p-6 md:flex-row md:items-center">
        <div>
          <h2 className="flex items-center gap-3 text-3xl font-black text-slate-900">
            <ClipboardCheck className="text-emerald-500" size={32} />
            Clinical Record
          </h2>
          <p className="mt-1 font-medium text-slate-500">
            Generated by NER-RAG Pipeline •
            Session: <strong>{data.session_id || '—'}</strong> •
            Lang: <strong>{data.input_language || data.metadata?.input_language || '—'}</strong> →
            <strong> Marathi</strong> •
            Time:
            <strong className="ml-2">{data.metadata?.processing_time || '—'}</strong>
            {data.metadata?.client_processing_time && (
              <span className="text-xs text-slate-400 ml-3">(client: {data.metadata.client_processing_time})</span>
            )}
            {data.metadata?.server_processing_time && (
              <span className="text-xs text-slate-400 ml-3">(server: {data.metadata.server_processing_time})</span>
            )}
          </p>
        </div>

        <div className="flex gap-2">
          <button className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-600 transition hover:bg-slate-50">
            <Printer size={16} /> Print
          </button>
          <button className="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white shadow-lg shadow-brand-100 transition hover:bg-brand-700">
            <Download size={16} /> Export PDF
          </button>
        </div>
      </div>

      {/* SOAP Sections */}
      <div className="space-y-6">
        {sectionMeta.map((sec) => (
          <div key={sec.key} className="surface-card group overflow-hidden rounded-[2rem] transition-all duration-300 hover:shadow-md">
            {/* Section header */}
            <div className={`flex items-center gap-4 px-8 py-4 ${sec.bg}`}>
              <div className={`w-12 h-12 bg-white ${sec.color} rounded-xl flex items-center justify-center font-black text-xl shadow-sm group-hover:scale-110 transition-transform`}>
                {sec.id}
              </div>
              <div>
                <h3 className="font-black text-slate-800 uppercase tracking-[0.15em] text-sm">{sec.title}</h3>
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{sec.desc}</p>
              </div>
            </div>

            {/* Content: Marathi-only */}
            <div className="grid grid-cols-1 divide-x divide-slate-200/70">
              <div className="p-8">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">{langLabel}</p>
                <SectionContent
                  content={primarySoap[sec.key]}
                  sectionKey={sec.key}
                  structured={primaryParametric[sec.key]}
                  languageLabel={langLabel}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* NER Entities */}
      {data.entities && (
        <div className="surface-card rounded-[2rem] p-8">
          <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">NER Medical Entities Detected</h4>
          <div className="flex flex-wrap gap-2">
            {data.entities.patient?.map((e, i) => (
              <span key={i} className="px-3 py-1 bg-brand-50 text-brand-700 text-[10px] font-bold rounded-full border border-brand-100 uppercase tracking-wider">
                💊 {e.text || e}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

SoapNoteViewer.propTypes = {
  data: PropTypes.shape({
    target_language: PropTypes.string,
    session_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    input_language: PropTypes.string,
    soap_marathi: PropTypes.shape({
      subjective: PropTypes.string,
      objective: PropTypes.string,
      assessment: PropTypes.string,
      plan: PropTypes.string,
    }),
    soap_marathi_parametric: PropTypes.shape({
      subjective: PropTypes.object,
      objective: PropTypes.object,
      assessment: PropTypes.object,
      plan: PropTypes.object,
    }),
    metadata: PropTypes.shape({
      input_language: PropTypes.string,
      target_language: PropTypes.string,
      processing_time: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      client_processing_time: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      server_processing_time: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    }),
    entities: PropTypes.shape({
      patient: PropTypes.arrayOf(
        PropTypes.oneOfType([
          PropTypes.string,
          PropTypes.shape({
            text: PropTypes.string,
          }),
        ])
      ),
    }),
  }).isRequired,
};