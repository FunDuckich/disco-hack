import React from 'react';
import { LayoutDashboard, HardDrive, RefreshCw, Settings, Cloud, Share2 } from 'lucide-react';

function App() {
  return (
    <div className="h-screen w-full flex flex-col bg-disco-dark relative overflow-hidden select-none">
      <div className="absolute inset-0 bg-noise pointer-events-none" />

      <header className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-white/5 backdrop-blur-xl z-10">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-disco-cyan animate-pulse shadow-glow-cyan" />
          <h1 className="font-black text-xl tracking-tighter bg-gradient-to-r from-disco-cyan to-disco-magenta bg-clip-text text-transparent italic">
            CLOUDFUSION
          </h1>
        </div>
        <button className="text-slate-400 hover:text-disco-magenta transition-colors">
          <Settings size={20} />
        </button>
      </header>

      <main className="flex-1 p-6 space-y-6 z-10">
        
        <section className="p-5 rounded-2xl bg-white/5 border border-white/10 hover:border-disco-cyan/50 transition-all duration-500 shadow-xl group">
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-disco-cyan/10 text-disco-cyan">
                <Cloud size={24} />
              </div>
              <div>
                <h2 className="font-bold text-slate-200">Yandex Disk</h2>
                <p className="text-xs text-slate-500 uppercase tracking-widest italic">Connected</p>
              </div>
            </div>
            <RefreshCw size={18} className="text-slate-600 cursor-pointer hover:text-disco-cyan hover:rotate-180 transition-all duration-700" />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-mono">
              <span className="text-disco-cyan">42.5 GB USED</span>
              <span className="text-slate-500">100 GB TOTAL</span>
            </div>
            <div className="h-2.5 w-full bg-slate-900 rounded-full overflow-hidden border border-white/5">
              <div 
                className="h-full bg-gradient-to-r from-disco-cyan to-disco-purple shadow-glow-cyan transition-all duration-1000"
                style={{ width: '42.5%' }}
              />
            </div>
          </div>
        </section>

        <div className="grid grid-cols-2 gap-4">
           <button className="flex flex-col items-center gap-2 p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-disco-magenta/10 hover:border-disco-magenta/40 transition-all text-slate-400 hover:text-disco-magenta">
              <Share2 size={24} />
              <span className="text-[10px] font-bold uppercase tracking-widest">Get Link</span>
           </button>
           <button className="flex flex-col items-center gap-2 p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-disco-cyan/10 hover:border-disco-cyan/40 transition-all text-slate-400 hover:text-disco-cyan">
              <HardDrive size={24} />
              <span className="text-[10px] font-bold uppercase tracking-widest">Cache Mgr</span>
           </button>
        </div>

      </main>

      <footer className="px-6 py-3 border-t border-white/5 bg-black/40 text-[9px] flex justify-between text-slate-600 font-mono tracking-widest uppercase z-10">
        <span>Kernel status: v.4.0-stable</span>
        <span className="text-disco-magenta">sync active</span>
      </footer>
    </div>
  );
}

export default App;