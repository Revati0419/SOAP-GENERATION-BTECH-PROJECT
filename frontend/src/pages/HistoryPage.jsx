import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Loader2, Clock3 } from 'lucide-react';
import { fetchPatientSessions, fetchRecentSessions } from '../services/clinicApi';

const formatDateTime = (unixSeconds) => {
  if (!unixSeconds) return '—';
  return new Date(unixSeconds * 1000).toLocaleString();
};

export default function HistoryPage() {
  const [searchParams] = useSearchParams();
  const patientId = searchParams.get('patient_id');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [patient, setPatient] = useState(null);
  const [sessions, setSessions] = useState([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (patientId) {
        const data = await fetchPatientSessions(Number(patientId), 200);
        setPatient(data.patient || null);
        setSessions(data.sessions || []);
      } else {
        const data = await fetchRecentSessions(200);
        setPatient(null);
        setSessions(data.sessions || []);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load session history.');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <h1 className="text-3xl font-black text-slate-900">Session History</h1>
          <p className="text-slate-500 font-medium">
            {patient ? `Showing records for ${patient.full_name}` : 'Showing recent sessions across all patients'}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/" className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200">
            Back to Dashboard
          </Link>
          <Link to={patient ? `/upload?patient_id=${patient.id}` : '/upload'} className="px-4 py-2 rounded-xl bg-brand-600 text-white font-bold hover:bg-brand-700">
            New Session
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center gap-2 p-10 text-slate-600 font-medium">
          <Loader2 className="animate-spin" size={18} /> Loading history...
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl px-5 py-4 font-semibold">
          {error}
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-10 text-slate-400 italic font-medium border-2 border-dashed border-slate-100 rounded-3xl bg-white">
          No sessions yet.
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((s) => (
            <div key={s.id} className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                <div>
                  <p className="font-black text-slate-800">{s.patient_name}</p>
                  <p className="text-xs text-slate-500">
                    Session #{s.id} • Source: {s.source_type} • Target: {s.target_lang || 'marathi'}
                  </p>
                </div>
                <div className="text-xs text-slate-500 flex items-center gap-1">
                  <Clock3 size={14} /> {formatDateTime(s.created_at)}
                </div>
              </div>

              <div className="mt-4 grid md:grid-cols-2 gap-4">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1">English SOAP</p>
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">
                    {(s.soap_english?.assessment || s.soap_english?.subjective || '').trim() || 'No SOAP summary available.'}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-amber-50 border border-amber-100">
                  <p className="text-[10px] font-black uppercase tracking-widest text-amber-700 mb-1">Transcript Snapshot</p>
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">
                    {(s.transcript || '').slice(0, 240) || 'No transcript saved.'}
                    {(s.transcript || '').length > 240 ? '…' : ''}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
