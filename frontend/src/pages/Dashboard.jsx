import { useCallback, useEffect, useState } from 'react';
import { Users, FileText, Activity, Search, Plus, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { createPatient, fetchPatients, fetchStats } from '../services/clinicApi';

const emptyPatientForm = {
  full_name: '',
  age: '',
  gender: 'unknown',
  phone: '',
  notes: '',
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [patients, setPatients] = useState([]);
  const [stats, setStats] = useState({
    total_patients: 0,
    total_sessions: 0,
    active_sessions_last_7_days: 0,
  });
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);
  const [error, setError] = useState(null);
  const [showNewPatientModal, setShowNewPatientModal] = useState(false);
  const [patientForm, setPatientForm] = useState(emptyPatientForm);
  const [creatingPatient, setCreatingPatient] = useState(false);

  const loadPatients = useCallback(async (query) => {
    setLoadingPatients(true);
    setError(null);
    try {
      const data = await fetchPatients(query, 50);
      setPatients(data.patients || []);
    } catch {
      setError('Failed to load patients. Is backend running?');
    } finally {
      setLoadingPatients(false);
    }
  }, []);

  const loadStats = useCallback(async () => {
    setLoadingStats(true);
    try {
      const data = await fetchStats();
      setStats(data || {
        total_patients: 0,
        total_sessions: 0,
        active_sessions_last_7_days: 0,
      });
    } catch {
      // non-blocking
    } finally {
      setLoadingStats(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadPatients(searchText);
    }, 250);

    return () => clearTimeout(timer);
  }, [searchText, loadPatients]);

  useEffect(() => {
    loadPatients('');
    loadStats();
  }, [loadPatients, loadStats]);

  const handleCreatePatient = async (e) => {
    e.preventDefault();
    if (!patientForm.full_name.trim()) {
      setError('Patient full name is required.');
      return;
    }

    setCreatingPatient(true);
    setError(null);
    try {
      const payload = {
        ...patientForm,
        age: patientForm.age === '' ? null : Number(patientForm.age),
      };
      const data = await createPatient(payload);
      const createdPatientId = data.patient?.id;

      setShowNewPatientModal(false);
      setPatientForm(emptyPatientForm);
      await loadPatients(searchText);
      await loadStats();

      if (createdPatientId) {
        navigate(`/upload?patient_id=${createdPatientId}`);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Unable to create patient.');
    } finally {
      setCreatingPatient(false);
    }
  };

  const statCards = [
    { label: 'Total Patients', value: stats.total_patients, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'SOAP Records', value: stats.total_sessions, icon: FileText, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Active (7 Days)', value: stats.active_sessions_last_7_days, icon: Activity, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  ];

  return (
    <div className="mx-auto w-full max-w-7xl space-y-8">
      <div className="surface-card relative overflow-hidden p-8">
        <div className="absolute -right-16 -top-16 h-44 w-44 rounded-full bg-brand-100/60 blur-2xl" />
        <div className="relative flex flex-col justify-between gap-6 md:flex-row md:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-brand-600">Operations Console</p>
          <h1 className="mt-2 text-4xl font-black tracking-tight text-slate-900">Clinical Overview</h1>
          <p className="mt-2 max-w-2xl font-medium text-slate-600">
            Search patients, start new sessions, and review records with a cleaner, faster workflow.
          </p>
        </div>
        <button
          onClick={() => setShowNewPatientModal(true)}
          className="inline-flex items-center gap-2 rounded-2xl bg-brand-600 px-6 py-3 font-bold text-white shadow-lg shadow-brand-200 transition hover:bg-brand-700"
        >
          <Plus size={20} /> New Patient
        </button>
      </div>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {statCards.map((s) => (
          <div
            key={s.label}
            className="surface-card p-6 transition hover:-translate-y-0.5 hover:shadow-[0_14px_34px_rgba(15,23,42,0.08)]"
          >
            <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-2xl ${s.bg} ${s.color}`}>
              <s.icon size={24} />
            </div>
            <p className="text-xs font-black uppercase tracking-widest text-slate-500">{s.label}</p>
            <p className="mt-1 text-3xl font-black text-slate-800">{loadingStats ? '…' : s.value}</p>
          </div>
        ))}
      </div>

      <div className="surface-card rounded-[2rem] p-8">
        <div className="mb-6 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h3 className="text-xl font-black text-slate-900">Quick Patient Access</h3>
          <p className="text-sm text-slate-500">Open a patient and begin documentation in one click.</p>
        </div>

        <div className="relative mb-8">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search by patient name..."
            className="w-full rounded-2xl border border-slate-200 bg-slate-50/80 py-4 pl-12 pr-6 text-slate-800 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-200"
          />
        </div>

        {loadingPatients ? (
          <div className="flex items-center justify-center gap-2 py-10 font-medium text-slate-500">
            <Loader2 className="animate-spin" size={18} /> Loading patients...
          </div>
        ) : patients.length === 0 ? (
          <div className="rounded-3xl border-2 border-dashed border-slate-200 bg-slate-50/70 py-10 text-center font-medium italic text-slate-400">
            No patients found. Create your first patient.
          </div>
        ) : (
          <div className="space-y-3">
            {patients.map((p) => (
              <div
                key={p.id}
                className="flex flex-col gap-3 rounded-2xl border border-slate-200/70 bg-white p-4 transition hover:border-brand-200 hover:bg-brand-50/30 md:flex-row md:items-center md:justify-between"
              >
                <div>
                  <p className="font-black text-slate-800">{p.full_name}</p>
                  <p className="text-xs text-slate-500">
                    ID #{p.id} • {p.gender || 'unknown'} • {p.age ?? '—'} years • {p.session_count || 0} sessions
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => navigate(`/upload?patient_id=${p.id}`)}
                    className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700"
                  >
                    New Session
                  </button>
                  <button
                    onClick={() => navigate(`/history?patient_id=${p.id}`)}
                    className="rounded-xl bg-slate-100 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-200"
                  >
                    History
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 font-semibold text-red-700">
          {error}
        </div>
      )}

      {showNewPatientModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form onSubmit={handleCreatePatient} className="w-full max-w-xl space-y-4 rounded-3xl bg-white p-8 shadow-2xl">
            <h4 className="text-2xl font-black text-slate-900">Create New Patient</h4>

            <div>
              <label className="block text-sm font-bold text-slate-600 mb-2">Full Name</label>
              <input
                value={patientForm.full_name}
                onChange={(e) => setPatientForm((prev) => ({ ...prev, full_name: e.target.value }))}
                className="w-full p-3 border rounded-xl"
                placeholder="Patient full name"
                required
              />
            </div>

            <div className="grid md:grid-cols-3 gap-3">
              <div>
                <label className="block text-sm font-bold text-slate-600 mb-2">Age</label>
                <input
                  value={patientForm.age}
                  onChange={(e) => setPatientForm((prev) => ({ ...prev, age: e.target.value }))}
                  className="w-full p-3 border rounded-xl"
                  placeholder="e.g. 42"
                  type="number"
                  min="0"
                  max="130"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-600 mb-2">Gender</label>
                <select
                  value={patientForm.gender}
                  onChange={(e) => setPatientForm((prev) => ({ ...prev, gender: e.target.value }))}
                  className="w-full p-3 border rounded-xl"
                >
                  <option value="unknown">Unknown</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-600 mb-2">Phone</label>
                <input
                  value={patientForm.phone}
                  onChange={(e) => setPatientForm((prev) => ({ ...prev, phone: e.target.value }))}
                  className="w-full p-3 border rounded-xl"
                  placeholder="Optional"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-600 mb-2">Notes</label>
              <textarea
                value={patientForm.notes}
                onChange={(e) => setPatientForm((prev) => ({ ...prev, notes: e.target.value }))}
                className="w-full p-3 border rounded-xl"
                rows={3}
                placeholder="Optional notes"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowNewPatientModal(false)}
                className="px-5 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creatingPatient}
                className="px-5 py-3 rounded-xl bg-brand-600 text-white font-bold hover:bg-brand-700 disabled:opacity-60"
              >
                {creatingPatient ? 'Creating...' : 'Create Patient'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}