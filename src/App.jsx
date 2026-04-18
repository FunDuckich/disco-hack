import React, { useState, useEffect, useRef } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { 
  CheckCircle2, RefreshCcw, LogOut, Plus,
  HardDrive, X, Minus, ArrowLeft, Zap, Database, Activity,
  Image as ImageIcon, FileText, Video, Globe
} from 'lucide-react';

const appWindow = getCurrentWindow();
const API_BASE_URL = "http://localhost:8000";

const App = () => {
  const [view, setView] = useState('main'); 
  const [activeCloud, setActiveCloud] = useState('YANDEX');
  const [cacheLimit, setCacheLimit] = useState(25); 
  
  const [cloudStatus, setCloudStatus] = useState({
    YANDEX: true,
    NEXTCLOUD: true
  });
  
  const [isAuthLoading, setIsAuthLoading] = useState(null); 
  const pollIntervalRef = useRef(null);

  const clouds = {
    YANDEX: { used: '30GB', total: '260GB', percent: 11, ping: '42ms', types: { img: 40, doc: 25, vid: 35 }, savedGb: '1.2GB', color: 'bg-retro-yellow' },
    NEXTCLOUD: { used: '552GB', total: '600GB', percent: 92, ping: '115ms', types: { img: 20, doc: 60, vid: 20 }, savedGb: '14.8GB', color: 'bg-retro-blue' }
  };

  const handleDrag = () => appWindow.startDragging();
  const handleMinimize = () => appWindow.minimize();
  const handleClose = () => appWindow.hide();

  useEffect(() => {
    return () => { if (pollIntervalRef.current) clearInterval(pollIntervalRef.current); };
  }, []);

  const handleConnect = async (provider) => {
    if (isAuthLoading) return;
    setIsAuthLoading(provider);
    try {
      await fetch(`${API_BASE_URL}/api/auth/login?provider=${provider.toLowerCase()}`);
      pollIntervalRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}/api/auth/status?provider=${provider.toLowerCase()}`);
          const data = await res.json();
          if (data.connected) {
            setCloudStatus(prev => ({ ...prev, [provider]: true }));
            setIsAuthLoading(null);
            clearInterval(pollIntervalRef.current);
          }
        } catch (e) { console.error(e); }
      }, 2000);
    } catch (e) { setIsAuthLoading(null); }
  };

  const handleLogout = (provider) => setCloudStatus(prev => ({ ...prev, [provider]: false }));

  const retroBox = "border-2 border-retro-dark shadow-retro transition-all duration-100";

  const renderMain = () => (
    <div className="flex flex-col h-full animate-in fade-in slide-in-from-bottom-2 duration-300">
      <section onMouseDown={e => e.stopPropagation()} className="mb-6 space-y-4">
        {Object.entries(clouds).map(([key, data]) => {
          const isLinked = cloudStatus[key];
          return (
            <div key={key} className={`${retroBox} ${isLinked ? data.color : 'bg-white/50 border-dashed'} p-4 flex items-center justify-between transition-all`}>
              {isLinked ? (
                <>
                  <div className="flex flex-col gap-1 cursor-help" title={`Хранилище ${key}`}>
                    <span className="font-black text-sm uppercase tracking-tight">{key}.DISK</span>
                    <span className="text-[10px] font-bold bg-white/40 px-1 border border-retro-dark w-fit">{data.used} / {data.total}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xl font-black ${data.percent > 90 ? 'text-retro-red animate-pulse' : 'text-retro-dark'}`}>{data.percent}%</span>
                    <div className={`${retroBox} bg-white p-2 rounded-full cursor-help`} title="Статус синхронизации">
                      {data.percent < 90 ? <CheckCircle2 className="text-retro-green" size={18} /> : <RefreshCcw className="text-retro-purple animate-spin" size={18} />}
                    </div>
                    <button onClick={() => handleLogout(key)} className={`${retroBox} bg-retro-red text-white p-2 rounded-full hover:scale-110 active:translate-y-0.5 active:shadow-none transition-all`}>
                      <LogOut size={14} />
                    </button>
                  </div>
                </>
              ) : (
                <button 
                  onClick={() => handleConnect(key)}
                  disabled={isAuthLoading === key}
                  className="w-full py-2 flex items-center justify-center gap-3 group"
                >
                  <div className="flex flex-col items-start">
                    <span className="text-[10px] font-black opacity-40 uppercase leading-none">{key} DISK</span>
                    <span className="font-black text-sm uppercase group-hover:text-retro-purple transition-colors">
                      {isAuthLoading === key ? 'Установка связи...' : `Подключить ${key} Cloud`}
                    </span>
                  </div>
                  <Plus className={`transition-transform ${isAuthLoading === key ? 'animate-spin text-retro-purple' : 'group-hover:rotate-90'}`} />
                </button>
              )}
            </div>
          );
        })}
      </section>

      <section onMouseDown={e => e.stopPropagation()} className={`${retroBox} bg-retro-pink p-5 mb-6`}>
        <div className="flex justify-between items-center mb-3">
          <h2 className="font-black text-[11px] uppercase flex items-center gap-2 cursor-help" title="Лимит папки ~/.cache/cloudfusion">
            <Database size={14}/> Лимит LRU кэша
          </h2>
          <span className="bg-white px-3 py-1 border-2 border-retro-dark font-black text-sm italic shadow-sm">{cacheLimit} GB</span>
        </div>
        <input 
          type="range" min="1" max="100" value={cacheLimit} onChange={(e) => setCacheLimit(parseInt(e.target.value))}
          className="w-full h-10 appearance-none bg-white border-2 border-retro-dark cursor-pointer accent-retro-purple"
          style={{ backgroundImage: `linear-gradient(to right, #552CB7 ${cacheLimit}%, transparent ${cacheLimit}%)` }}
        />
      </section>

      <button onClick={() => setView('stats')} onMouseDown={e => e.stopPropagation()} className={`${retroBox} bg-retro-purple text-white w-full py-4 font-black flex items-center justify-center gap-3 active:translate-y-1 active:shadow-none hover:bg-[#452496] transition-all`}>
        <HardDrive size={20} /> СТАТИСТИКА
      </button>
    </div>
  );

  const renderStats = () => (
    <div onMouseDown={e => e.stopPropagation()} className="animate-in fade-in zoom-in-95 duration-200">
      <div className="flex justify-between items-center mb-6">
        <button onClick={() => setView('main')} className={`${retroBox} bg-white px-4 py-2 font-black text-[10px] flex items-center gap-2 hover:bg-retro-yellow active:translate-y-0.5`}>
          <ArrowLeft size={14} /> НАЗАД
        </button>
        <div className={`${retroBox} bg-retro-green text-white px-3 py-2 text-[10px] font-black flex items-center gap-1 shadow-sm cursor-help`} title="Задержка API">
          <Globe size={12} /> PING: {clouds[activeCloud].ping}
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        {Object.keys(clouds).map(name => (
          <button key={name} onClick={() => setActiveCloud(name)}
            className={`flex-1 py-3 font-black text-[11px] border-2 border-retro-dark transition-all ${activeCloud === name ? 'bg-retro-purple text-white shadow-retro -translate-x-1 -translate-y-1' : 'bg-white text-retro-dark hover:bg-retro-bg'}`}>
            {name}
          </button>
        ))}
      </div>

      <section className={`${retroBox} bg-white p-5 mb-6 cursor-help`} title={`Детальный разбор хранилища ${activeCloud}`}>
        <div className="flex justify-between items-end mb-3">
           <h2 className="font-black text-[10px] uppercase opacity-50 italic underline decoration-retro-purple tracking-tighter">Занято в облаке</h2>
           <span className="font-black text-xl leading-none">
             {clouds[activeCloud].used} 
             <span className="text-xs opacity-30 tracking-tighter"> / {clouds[activeCloud].total}</span>
           </span>
        </div>
        <div className="h-8 border-2 border-retro-dark bg-retro-bg flex overflow-hidden shadow-inner p-1">
          <div className="h-full bg-retro-purple transition-all duration-1000 ease-out" style={{ width: `${clouds[activeCloud].percent}%` }}></div>
        </div>
      </section>

      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { icon: ImageIcon, color: 'bg-retro-yellow/20', val: clouds[activeCloud].types.img},
          { icon: Video, color: 'bg-retro-blue/20', val: clouds[activeCloud].types.vid},
          { icon: FileText, color: 'bg-retro-pink/20', val: clouds[activeCloud].types.doc}
        ].map((t, idx) => (
          <div key={idx} className={`${retroBox} ${t.color} p-4 text-center`}>
             <t.icon size={20} className="mx-auto mb-2 opacity-70" />
             <div className="text-[14px] font-black leading-none">{t.val}%</div>
             <div className="text-[8px] font-bold uppercase mt-1 opacity-40 tracking-tighter">{t.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className={`${retroBox} bg-retro-yellow p-4 cursor-help`} title="Объем данных в локальном кэше">
          <Zap size={20} className="mb-2 text-retro-dark" />
          <div className="text-[10px] font-black uppercase mb-1 opacity-60">Локальный кэш</div>
          <div className="text-2xl font-black italic tracking-tighter text-retro-dark leading-none">14.2 GB</div>
        </div>
        <div className={`${retroBox} bg-white p-4 cursor-help`} title="Процент запросов без скачивания">
          <Activity size={20} className="mb-2 text-retro-purple" />
          <div className="text-[10px] font-black uppercase mb-1 leading-none text-retro-purple opacity-60">Эффективность</div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-black text-retro-green leading-none">86%</span>
            <span className="text-[10px] font-bold opacity-40">({clouds[activeCloud].savedGb})</span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div onMouseDown={handleDrag} className="w-full min-h-screen bg-retro-bg p-6 font-mono select-none overflow-hidden border-2 border-retro-dark">
      <header className="flex justify-between items-start mb-8 border-b-2 border-retro-dark pb-6">
        <div className="flex flex-col">
           <h1 className="text-2xl font-black tracking-tighter border-b-4 border-retro-purple leading-none italic uppercase">Cloudfusion</h1>
           <span className="text-[10px] font-bold opacity-50 uppercase mt-2 italic tracking-[0.3em]">
             {view === 'main' ? 'VFS Nodes Control' : 'Storage Analytics'}
           </span>
        </div>
        <div className="flex gap-3" onMouseDown={e => e.stopPropagation()}>
          <button onClick={handleMinimize} className={`${retroBox} bg-white p-1.5 hover:bg-retro-bg transition-colors`}><Minus size={16} /></button>
          <button onClick={handleClose} className={`${retroBox} bg-retro-red p-1.5 text-white hover:opacity-80 transition-opacity`}><X size={16} /></button>
        </div>
      </header>
      
      <main className="h-full">
        {view === 'main' ? renderMain() : renderStats()}
      </main>
    </div>
  );
};

export default App;