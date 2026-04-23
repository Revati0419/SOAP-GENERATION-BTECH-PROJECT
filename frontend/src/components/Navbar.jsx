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
    <nav className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/70 px-4 py-3 backdrop-blur-xl md:px-8">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-3">
          <div className="rounded-2xl bg-brand-600 p-2.5 text-white shadow-lg shadow-brand-200/70">
            <Stethoscope size={24} />
          </div>
          <div>
            <span className="block text-2xl font-black tracking-tighter text-slate-900">
              SOAP<span className="text-brand-600">.ai</span>
            </span>
            <span className="block text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Clinical Assistant
            </span>
          </div>
        </Link>

        <div className="hidden gap-1 rounded-2xl border border-slate-200 bg-white/80 p-1.5 shadow-sm md:flex">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-2 rounded-xl px-5 py-2 text-sm font-bold transition-all ${
                location.pathname === item.path
                  ? 'bg-brand-600 text-white shadow-lg shadow-brand-200/60'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <item.icon size={18} /> {item.label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition hover:text-brand-600">
            <Bell size={18} />
          </button>
          <div className="hidden text-right md:block">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Signed in</p>
            <p className="text-sm font-bold text-slate-800">Dr. Arjun</p>
          </div>
          <div className="h-10 w-10 overflow-hidden rounded-full border-2 border-white bg-brand-100 shadow-sm">
            <img src="https://ui-avatars.com/api/?name=Dr+Arjun&background=e0effe&color=2563eb" alt="avatar" />
          </div>
        </div>
      </div>

      <div className="mx-auto mt-3 flex w-full max-w-7xl gap-1 rounded-2xl border border-slate-200 bg-white p-1 md:hidden">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`flex flex-1 items-center justify-center gap-1 rounded-xl px-2 py-2 text-xs font-bold transition ${
              location.pathname === item.path
                ? 'bg-brand-600 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <item.icon size={15} />
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}