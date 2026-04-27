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
    <div className="mx-auto w-full max-w-6xl space-y-8">
      <div className="surface-card rounded-[2rem] p-7">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-brand-600">Documentation Archive</p>
          <h1 className="mt-2 text-3xl font-black text-slate-900">Session History</h1>
          <p className="mt-1 font-medium text-slate-600">
            {patient ? `Showing records for ${patient.full_name}` : 'Showing recent sessions across all patients'}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/" className="rounded-xl bg-slate-100 px-4 py-2 font-bold text-slate-700 hover:bg-slate-200">
            Back to Dashboard
          </Link>
          <Link to={patient ? `/upload?patient_id=${patient.id}` : '/upload'} className="rounded-xl bg-brand-600 px-4 py-2 font-bold text-white hover:bg-brand-700">
            New Session
          </Link>
        </div>
      </div>
      </div>

      {loading ? (
        <div className="surface-card flex items-center justify-center gap-2 p-10 font-medium text-slate-600">
          <Loader2 className="animate-spin" size={18} /> Loading history...
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 font-semibold text-red-700">
          {error}
        </div>
      ) : sessions.length === 0 ? (
        <div className="surface-card rounded-3xl border-2 border-dashed border-slate-200 bg-white py-10 text-center font-medium italic text-slate-400">
          No sessions yet.
        </div>
      ) : (
        <div className="space-y-4">
          {sessions.map((s) => (
            <div key={s.id} className="surface-card relative overflow-hidden rounded-[1.6rem] p-5">
              <div className="absolute inset-y-0 left-0 w-1.5 bg-gradient-to-b from-brand-400 to-brand-700" />
              <div className="ml-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-black text-slate-800">{s.patient_name}</p>
                  <p className="text-xs text-slate-500">
                    Session #{s.id} • Source: {s.source_type} • Target: {s.target_lang || 'marathi'}
                  </p>
                </div>
                <div className="flex items-center gap-1 text-xs text-slate-500">
                  <Clock3 size={14} /> {formatDateTime(s.created_at)}
                </div>
              </div>

              <div className="ml-3 mt-4 grid gap-4 md:grid-cols-2">
                <div className="rounded-xl border border-slate-200/80 bg-slate-50/90 p-3">
                  <p className="mb-1 text-[10px] font-black uppercase tracking-widest text-slate-500">SOAP Snapshot</p>
                  <p className="whitespace-pre-wrap text-sm text-slate-700">
                    {(s.soap_target?.assessment || s.soap_target?.subjective || s.soap_english?.assessment || s.soap_english?.subjective || '').trim() || 'No SOAP summary available.'}
                  </p>
                </div>
                <div className="rounded-xl border border-amber-200/70 bg-amber-50/70 p-3">
                  <p className="mb-1 text-[10px] font-black uppercase tracking-widest text-amber-700">Transcript Snapshot</p>
                  <p className="whitespace-pre-wrap text-sm text-slate-700">
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
