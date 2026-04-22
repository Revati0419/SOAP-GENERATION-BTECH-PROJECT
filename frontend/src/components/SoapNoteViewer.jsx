import { ClipboardCheck, Download, Printer } from 'lucide-react';
import PropTypes from 'prop-types';

export default function SoapNoteViewer({ data }) {
  // Always use Marathi from the response
  const targetSoap = data.soap_marathi || {};

  const sectionMeta = [
    { key: 'cc',           id: '1', title: 'Chief Complaint', marathi: 'मुख्य तक्रार', color: 'text-red-600', bg: 'bg-red-50' },
    { key: 'hpi',          id: '2', title: 'HPI', marathi: 'सध्याच्या आजाराचा इतिहास', color: 'text-blue-600', bg: 'bg-blue-50' },
    { key: 'trauma',       id: '3', title: 'Trauma History', marathi: 'आघाताचा इतिहास', color: 'text-orange-600', bg: 'bg-orange-50' },
    { key: 'psychosocial', id: '4', title: 'Psychosocial', marathi: 'मनोसामाजिक इतिहास', color: 'text-purple-600', bg: 'bg-purple-50' },
    { key: 'functional',   id: '5', title: 'Functional Status', marathi: 'कार्यक्षम स्थिती', color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { key: 'medical',      id: '6', title: 'Medical History', marathi: 'वैद्यकीय इतिहास', color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { key: 'past_psych',   id: '7', title: 'Past Psych History', marathi: 'पूर्व मनोरुग्ण इतिहास', color: 'text-pink-600', bg: 'bg-pink-50' },
    { key: 'biological',   id: '8', title: 'Biological Obs', marathi: 'जैविक निरीक्षणे', color: 'text-yellow-600', bg: 'bg-yellow-50' },
    { key: 'mse',          id: '9', title: 'MSE', marathi: 'मानसिक स्थिती तपासणी', color: 'text-cyan-600', bg: 'bg-cyan-50' },
    { key: 'plan',         id: '10', title: 'Plan', marathi: 'उपचार योजना', color: 'text-teal-600', bg: 'bg-teal-50' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <h2 className="text-3xl font-black text-slate-900 flex items-center gap-3">
            <ClipboardCheck className="text-emerald-500" size={32} />
            क्लिनिकल रेकॉर्ड (Marathi)
          </h2>
          <p className="text-slate-500 font-medium mt-1">
            Session ID: <strong>{data.session_id || '—'}</strong> • 
            Processing: <strong>{data.metadata?.processing_time || '—'}</strong>
          </p>
        </div>

        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-50 transition">
            <Printer size={16} /> Print
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 rounded-xl text-sm font-bold text-white hover:bg-blue-700 shadow-lg transition">
            <Download size={16} /> Export PDF
          </button>
        </div>
      </div>

      {/* SOAP Sections */}
      <div className="space-y-6">
        {sectionMeta.map((sec) => (
          <div key={sec.key} className="group bg-white rounded-[2rem] border border-slate-100 shadow-sm overflow-hidden">
            {/* Section header */}
            <div className={`flex items-center gap-4 px-8 py-4 ${sec.bg}`}>
              <div className={`w-12 h-12 bg-white ${sec.color} rounded-xl flex items-center justify-center font-black text-xl shadow-sm`}>
                {sec.id}
              </div>
              <div>
                <h3 className="font-black text-slate-800 uppercase tracking-widest text-sm">
                   {sec.marathi} ({sec.title})
                </h3>
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{sec.desc}</p>
              </div>
            </div>

            {/* Content */}
            <div className="p-8">
              <p className="text-slate-700 leading-relaxed font-medium text-lg whitespace-pre-wrap">
                {targetSoap[sec.key] || <span className="italic text-slate-400">माहिती उपलब्ध नाही...</span>}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* NER Entities */}
      {data.entities && (
        <div className="bg-white rounded-[2rem] p-8 border border-slate-100 shadow-sm">
          <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">वैद्यकीय घटक (Detected Entities)</h4>
          <div className="flex flex-wrap gap-2">
            {data.entities.patient?.map((e, i) => (
              <span key={i} className="px-3 py-1 bg-blue-50 text-blue-700 text-[10px] font-bold rounded-full border border-blue-100 uppercase tracking-wider">
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
  data: PropTypes.object.isRequired
};