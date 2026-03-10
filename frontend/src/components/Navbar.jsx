import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Mic, History, Stethoscope, Bell } from 'lucide-react';

export default function Navbar() {
  const location = useLocation();
  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/upload', label: 'New Session', icon: Mic },
    { path: '/history', label: 'Records', icon: History },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-white/70 backdrop-blur-lg border-b border-slate-200 px-6 py-4">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <Link to="/" className="flex items-center gap-2">
          <div className="bg-brand-600 p-2 rounded-xl text-white shadow-lg shadow-brand-200">
            <Stethoscope size={24} />
          </div>
          <span className="font-black text-2xl tracking-tighter">SOAP<span className="text-brand-600">.ai</span></span>
        </Link>

        <div className="flex bg-slate-100 p-1 rounded-2xl gap-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-2 px-6 py-2 rounded-xl text-sm font-bold transition-all ${
                location.pathname === item.path ? 'bg-white text-brand-600 shadow-sm' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <item.icon size={18} /> {item.label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-4">
          <button className="p-2 text-slate-400 hover:text-brand-600 transition"><Bell size={20}/></button>
          <div className="h-10 w-10 rounded-full bg-brand-100 border-2 border-white shadow-sm overflow-hidden">
             <img src="https://ui-avatars.com/api/?name=Dr+Arjun&background=e0effe&color=2563eb" alt="avatar" />
          </div>
        </div>
      </div>
    </nav>
  );
}