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
    <div className="max-w-7xl mx-auto p-8 space-y-10">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Clinical Overview</h1>
          <p className="text-slate-500 font-medium">Search patients, start sessions, and review history.</p>
        </div>
        <button
          onClick={() => setShowNewPatientModal(true)}
          className="bg-brand-600 text-white px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-brand-700 transition shadow-xl shadow-brand-100"
        >
          <Plus size={20} /> New Patient
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {statCards.map((s) => (
          <div key={s.label} className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm hover:shadow-md transition">
            <div className={`w-12 h-12 ${s.bg} ${s.color} rounded-2xl flex items-center justify-center mb-4`}>
              <s.icon size={24} />
            </div>
            <p className="text-slate-400 text-xs font-black uppercase tracking-widest">{s.label}</p>
            <p className="text-3xl font-black text-slate-800 mt-1">{loadingStats ? '…' : s.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-[2.5rem] p-8 border border-slate-100 shadow-sm">
        <h3 className="font-bold text-lg mb-6">Quick Patient Access</h3>
        <div className="relative mb-8">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search by patient name..."
            className="w-full pl-12 pr-6 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-brand-600"
          />
        </div>

        {loadingPatients ? (
          <div className="text-center py-10 text-slate-500 font-medium flex items-center justify-center gap-2">
            <Loader2 className="animate-spin" size={18} /> Loading patients...
          </div>
        ) : patients.length === 0 ? (
          <div className="text-center py-10 text-slate-400 italic font-medium border-2 border-dashed border-slate-100 rounded-3xl">
            No patients found. Create your first patient.
          </div>
        ) : (
          <div className="space-y-3">
            {patients.map((p) => (
              <div key={p.id} className="p-4 border border-slate-100 rounded-2xl flex flex-col md:flex-row md:items-center md:justify-between gap-3 hover:bg-slate-50 transition">
                <div>
                  <p className="font-black text-slate-800">{p.full_name}</p>
                  <p className="text-xs text-slate-500">
                    ID #{p.id} • {p.gender || 'unknown'} • {p.age ?? '—'} years • {p.session_count || 0} sessions
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => navigate(`/upload?patient_id=${p.id}`)}
                    className="px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-bold hover:bg-brand-700"
                  >
                    New Session
                  </button>
                  <button
                    onClick={() => navigate(`/history?patient_id=${p.id}`)}
                    className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-sm font-bold hover:bg-slate-200"
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
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl px-5 py-4 font-semibold">
          {error}
        </div>
      )}

      {showNewPatientModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form onSubmit={handleCreatePatient} className="w-full max-w-xl bg-white rounded-3xl p-8 shadow-2xl space-y-4">
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