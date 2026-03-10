import React from 'react';
import { Users, FileText, Activity, TrendingUp, Search, Plus } from 'lucide-react';

export default function Dashboard() {
  const stats = [
    { label: 'Total Patients', value: '1,284', icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'SOAP Records', value: '842', icon: FileText, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Active Sessions', value: '12', icon: Activity, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Growth', value: '+14%', icon: TrendingUp, color: 'text-orange-600', bg: 'bg-orange-50' },
  ];

  return (
    <div className="max-w-7xl mx-auto p-8 space-y-10">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Clinical Overview</h1>
          <p className="text-slate-500 font-medium">Welcome back, Dr. Arjun Sharma.</p>
        </div>
        <button className="bg-brand-600 text-white px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-brand-700 transition shadow-xl shadow-brand-100">
          <Plus size={20}/> New Patient
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {stats.map((s, i) => (
          <div key={i} className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm hover:shadow-md transition">
            <div className={`w-12 h-12 ${s.bg} ${s.color} rounded-2xl flex items-center justify-center mb-4`}>
              <s.icon size={24} />
            </div>
            <p className="text-slate-400 text-xs font-black uppercase tracking-widest">{s.label}</p>
            <p className="text-3xl font-black text-slate-800 mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-[2.5rem] p-8 border border-slate-100 shadow-sm">
        <h3 className="font-bold text-lg mb-6">Quick Patient Access</h3>
        <div className="relative mb-8">
           <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
           <input type="text" placeholder="Search by name, ID or diagnosis..." className="w-full pl-12 pr-6 py-4 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-brand-600" />
        </div>
        {/* Placeholder for patient list */}
        <div className="text-center py-10 text-slate-400 italic font-medium border-2 border-dashed border-slate-100 rounded-3xl">
          Search results will appear here...
        </div>
      </div>
    </div>
  );
}