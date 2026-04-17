import React, { useState } from "react";
import { LayoutDashboard, HardDrive, RefreshCw, Settings, Cloud, Share2, Trash2 } from "lucide-react";

function App() {
  const [cacheLimit, setCacheLimit] = useState(5); // Размер кэша в ГБ

  return (
    <div className="h-screen w-full flex flex-col bg-disco-dark relative overflow-hidden select-none text-slate-100">
      <div className="absolute inset-0 bg-noise pointer-events-none" />

      {/* ШАПКА */}
      <header className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-white/5 backdrop-blur-xl z-10">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-disco-cyan animate-pulse shadow-glow-cyan" />
          <h1 className="font-black text-lg tracking-tighter bg-gradient-to-r from-disco-cyan to-disco-magenta bg-clip-text text-transparent italic">
            CLOUDFUSION
          </h1>
        </div>
        <div className="flex gap-4 items-center">
           <span className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">Alt Linux Edition</span>
           <Settings size={18} className="text-slate-400 hover:text-disco-magenta transition-colors cursor-pointer" />
        </div>
      </header>

      {/* КОНТЕНТ */}
      <main className="flex-1 p-5 space-y-6 z-10 overflow-y-auto">
        
        {/* КАРТОЧКА ОБЛАКА */}
        <section className="p-4 rounded-2xl bg-white/5 border border-white/10 shadow-xl border-l-disco-cyan border-l-2">
          <div className="flex justify-between items-start mb-3">
            <div className="flex items-center gap-3">
              <Cloud className="text-disco-cyan" size={24} />
              <div>
                <h2 className="font-bold text-sm">Яндекс Диск</h2>
                <p className="text-[10px] text-slate-500 uppercase tracking-widest italic font-semibold">Статус: Подключено</p>
              </div>
            </div>
            <RefreshCw size={16} className="text-slate-600 cursor-pointer hover:text-disco-cyan hover:rotate-180 transition-all duration-700" />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-[10px] font-mono text-slate-400">
              <span>ЗАНЯТО: 42.5 ГБ</span>
              <span>ВСЕГО: 100 ГБ</span>
            </div>
            <div className="h-1.5 w-full bg-black/40 rounded-full overflow-hidden border border-white/5">
              <div className="h-full bg-gradient-to-r from-disco-cyan to-disco-purple" style={{ width: '42.5%' }} />
            </div>
          </div>
        </section>

        {/* НАСТРОЙКА LRU-КЭША (Требование ТЗ) */}
        <section className="p-4 rounded-2xl bg-white/5 border border-white/10 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-2 opacity-10">
             <HardDrive size={60} className="text-disco-magenta" />
          </div>
          
          <h2 className="text-xs font-bold uppercase tracking-[3px] text-disco-magenta mb-4">Настройка кэша (LRU)</h2>
          
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-4">
                 <span className="text-[10px] text-slate-400 font-mono uppercase">Лимит размера:</span>
                 <span className="text-sm font-black text-disco-magenta drop-shadow-[0_0_8px_rgba(255,0,255,0.6)]">{cacheLimit} ГБ</span>
              </div>
              
              <input 
                type="range" 
                min="1" 
                max="50" 
                value={cacheLimit} 
                onChange={(e) => setCacheLimit(e.target.value)}
                className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-disco-magenta"
              />
            </div>

            <div className="flex justify-between items-center bg-black/30 p-3 rounded-lg border border-white/5">
               <div className="flex flex-col">
                  <span className="text-[9px] text-slate-500 font-mono italic">Кэш очистится при превышении</span>
               </div>
               <button className="p-2 bg-disco-magenta/10 hover:bg-disco-magenta/20 text-disco-magenta rounded-lg transition-all border border-disco-magenta/20">
                  <Trash2 size={14} />
               </button>
            </div>
          </div>
        </section>

      </main>

      {/* ПОДВАЛ СТАТУСА */}
      <footer className="px-6 py-3 border-t border-white/5 bg-black/60 text-[9px] flex justify-between items-center text-slate-600 font-mono tracking-widest uppercase z-10">
        <div className="flex items-center gap-1.5 text-disco-cyan">
          <div className="w-1.5 h-1.5 rounded-full bg-disco-cyan animate-pulse shadow-[0_0_8px_#00ffff]" />
          <span>Система активна</span>
        </div>
        <div className="flex gap-4 italic font-bold">
           <span>v 1.0.0-DEV</span>
        </div>
      </footer>
    </div>
  );
}

export default App;