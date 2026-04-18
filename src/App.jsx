import React, { useState, useEffect } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { 
  CheckCircle2, RefreshCcw, LogOut, Plus,
  HardDrive, X, Minus, ArrowLeft, Zap, Database, Activity,
  Image as ImageIcon, FileText, Video, Globe,
  Star, Monitor 
} from 'lucide-react';

const appWindow = getCurrentWindow();
const API_BASE = "http://127.0.0.1:8000";

const apiFetch = async (url, method = 'GET') => {
  try {
    const res = await fetch(`${API_BASE}${url}`, { method });
    return res.ok ? await res.json() : null;
  } catch (e) { return null; }
};

const App = () => {
  const [view, setView] = useState('main'); 
  const [activeCloud, setActiveCloud] = useState('YANDEX');
  const [cacheLimit, setCacheLimit] = useState(25); 
  const [isDisco, setIsDisco] = useState(false); 
  
  // Состояние облаков (Yandex теперь реально проверяется)
  const [cloudStatus, setCloudStatus] = useState({ YANDEX: false, NEXTCLOUD: true });
  const [realStats, setRealStats] = useState(null);

  // Проверка статуса авторизации и загрузка статистики
  const refreshAppData = async () => {
    const auth = await apiFetch('/api/auth/status');
    if (auth) setCloudStatus(prev => ({ ...prev, YANDEX: auth.connected }));
    
    const stats = await apiFetch('/api/stats');
    if (stats) setRealStats(stats);
  };

  useEffect(() => {
    refreshAppData();
    const interval = setInterval(refreshAppData, 5000); // Обновляем раз в 5 сек
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (isDisco) {
      document.body.classList.add('disco-theme');
    } else {
      document.body.classList.remove('disco-theme');
    }
  }, [isDisco]);

  const clouds = {
    YANDEX: { used: '30GB', total: '260GB', percent: 11, ping: '42ms', types: { img: 40, doc: 25, vid: 35 }, savedGb: '1.2GB', color: 'bg-retro-yellow' },
    NEXTCLOUD: { used: '552GB', total: '600GB', percent: 92, ping: '115ms', types: { img: 20, doc: 60, vid: 20 }, savedGb: '14.8GB', color: 'bg-retro-blue' }
  };

  const handleDrag = () => appWindow.startDragging();
  const handleMinimize = () => appWindow.minimize();
  const handleClose = () => appWindow.hide();

  const retroBox = "retro-border shadow-retro rounded-retro transition-all duration-200";

  const renderMain = () => (
    <div className="flex flex-col h-full animate-in fade-in slide-in-from-bottom-2 duration-300">
      <section onMouseDown={e => e.stopPropagation()} className="mb-6 space-y-4">
        {Object.entries(clouds).map(([key, data]) => {
          const isLinked = cloudStatus[key];
          return (
            <div key={key} className={`${retroBox} ${isLinked ? data.color : 'bg-white/50 border-dashed'} p-4 flex items-center justify-between`}>
              {isLinked ? (
                <>
                  <div className="flex flex-col gap-1 cursor-help" title={`Хранилище ${key}`}>
                    <span className="font-black text-sm uppercase tracking-tight">{key}.DISK</span>
                    <span className="text-[10px] font-bold bg-white/40 px-1 border border-retro-dark w-fit">{data.used} / {data.total}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xl font-black ${data.percent > 90 ? 'text-retro-red animate-pulse' : ''}`}>{data.percent}%</span>
                    <div className={`${retroBox} bg-white p-2 rounded-full cursor-help`} title="Синхронизация">
                      {data.percent < 90 ? <CheckCircle2 className="text-retro-green" size={18} /> : <RefreshCcw className="text-retro-purple animate-spin" size={18} />}
                    </div>
                    <button 
                    onClick={async () => {
                      if (key === 'YANDEX') {
                        await apiFetch('/api/auth/logout', 'POST');
                        refreshAppData();
                      } else {
                        setCloudStatus(p => ({...p, [key]: false}));
                      }
                    }} 
                    className={`${retroBox} bg-retro-red text-white p-2 rounded-full hover:scale-110 active:translate-y-0.5 active:shadow-none`}
                  >
                    <LogOut size={14} />
                  </button>
                  </div>
                </>
              ) : (
                
                <button 
                  onClick={() => {
                    if (key === 'YANDEX') {
                      window.open(`${API_BASE}/api/auth/login`, '_blank');
                    } else {
                      setCloudStatus(p => ({...p, [key]: true}));
                    }
                  }} 
                  className="w-full py-2 flex items-center justify-center gap-3 group"
                >
                  <span className="font-black text-sm uppercase">Подключить {key}</span>
                  <Plus className="group-hover:rotate-90 transition-transform" />
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
          <span className="bg-white px-3 py-1 retro-border font-black text-sm italic shadow-sm">{cacheLimit} GB</span>
        </div>
        <input 
          type="range" min="1" max="100" value={cacheLimit} onChange={(e) => setCacheLimit(parseInt(e.target.value))}
          className="w-full h-10 appearance-none bg-white retro-border cursor-pointer accent-retro-purple"
          style={{ backgroundImage: `linear-gradient(to right, var(--color-retro-purple) ${cacheLimit}%, transparent ${cacheLimit}%)` }}
        />
      </section>

      <button onClick={() => setView('stats')} onMouseDown={e => e.stopPropagation()} className={`${retroBox} bg-retro-purple text-white w-full py-4 font-black flex items-center justify-center gap-3 active:translate-y-1 active:shadow-none hover:opacity-90 transition-all`}>
        <HardDrive size={20} /> СТАТИСТИКА
      </button>
    </div>
  );

const renderStats = () => {
    const efficiency = (activeCloud === 'YANDEX' && realStats && realStats.total_files_count > 0)
      ? Math.round((realStats.cached_files_count / realStats.total_files_count) * 100)
      : 86;

    return (
      <div onMouseDown={e => e.stopPropagation()} className="animate-in fade-in zoom-in-95 duration-200">
        <div className="flex justify-between items-center mb-6">
          <button onClick={() => setView('main')} className={`${retroBox} bg-white px-4 py-2 font-black text-[10px] flex items-center gap-2 hover:bg-retro-yellow`}>
            <ArrowLeft size={14} /> НАЗАД
          </button>
          <div className={`${retroBox} bg-retro-green text-white px-3 py-2 text-[10px] font-black flex items-center gap-1 cursor-help`} title="Задержка API">
            <Globe size={12} /> PING: {clouds[activeCloud].ping}
          </div>
        </div>

        <div className="flex gap-2 mb-6">
          {Object.keys(clouds).map(name => (
            <button key={name} onClick={() => setActiveCloud(name)}
              className={`flex-1 py-3 font-black text-[11px] retro-border transition-all ${activeCloud === name ? 'bg-retro-purple text-white shadow-retro -translate-y-1' : 'bg-white text-retro-dark'}`}>
              {name}
            </button>
          ))}
        </div>

        <section className={`${retroBox} bg-white p-5 mb-6 cursor-help`} title={`Занятый объём диска ${activeCloud}`}>
          <div className="flex justify-between items-end mb-3">
             <h2 className="font-black text-[10px] uppercase opacity-50 italic underline decoration-retro-purple tracking-tighter">Занято в облаке</h2>
             <span className="font-black text-xl leading-none">
               {activeCloud === 'YANDEX' && realStats 
                 ? `${(realStats.used_space / (1024**3)).toFixed(1)}GB` 
                 : clouds[activeCloud].used} 
               <span className="text-xs opacity-30"> / {clouds[activeCloud].total}</span>
             </span>
          </div>
          <div className={`h-8 retro-border bg-retro-bg flex overflow-hidden p-1 ${!isDisco ? 'rounded-full' : ''}`}>
            <div 
              className={`h-full bg-retro-purple transition-all duration-1000 ${!isDisco ? 'rounded-full' : ''}`} 
              style={{ 
                width: `${activeCloud === 'YANDEX' && realStats 
                  ? (realStats.used_space / realStats.total_space * 100) 
                  : clouds[activeCloud].percent}%` 
              }}
            ></div>
          </div>
        </section>

        <div className="grid grid-cols-3 gap-3 mb-6">
          {[{ icon: ImageIcon, val: clouds[activeCloud].types.img, color: 'bg-retro-yellow/20', label: 'Медиа' },
            { icon: Video, val: clouds[activeCloud].types.vid, color: 'bg-retro-blue/20', label: 'Аудио' },
            { icon: FileText, val: clouds[activeCloud].types.doc, color: 'bg-retro-pink/20', label: 'Документы' }
          ].map((t, i) => (
            <div key={i} className={`${retroBox} ${t.color} p-4 text-center cursor-help`} title={t.label}>
               <t.icon size={20} className="mx-auto mb-2 opacity-70" />
               <div className="text-[14px] font-black leading-none">{t.val}%</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className={`${retroBox} bg-retro-yellow p-4 cursor-help`} title="Локальный кэш">
            <Zap size={20} className="mb-2 text-retro-dark" />
            <div className="text-[10px] font-black uppercase mb-1 opacity-60">Кэш</div>
            <div className="text-2xl font-black italic text-retro-dark leading-none">
              {activeCloud === 'YANDEX' && realStats 
                ? `${(realStats.used_cache_size / (1024**2)).toFixed(1)} MB` 
                : '14.2 GB'}
            </div>
          </div>

          <div className={`${retroBox} bg-white p-4 cursor-help`} title="Эффективность LRU">
            <Activity size={20} className="mb-2 text-retro-purple" />
            <div className="text-[10px] font-black uppercase mb-1 opacity-60">Эффективность</div>
            <div className="text-2xl font-black text-retro-green leading-none">
              {efficiency}%
            </div>
            <div className="text-[8px] mt-1 opacity-40 font-bold">
              {activeCloud === 'YANDEX' && realStats 
                ? `${realStats.cached_files_count} из ${realStats.total_files_count} файлов` 
                : 'АНАЛИЗ...'}
            </div>
          </div>
        </div>
      </div>
    );
  };
  
const efficiency = (activeCloud === 'YANDEX' && realStats && realStats.total_files_count > 0)
    ? Math.round((realStats.cached_files_count / realStats.total_files_count) * 100)
    : 86;

  return (
    <div onMouseDown={handleDrag} className="w-full min-h-screen bg-retro-bg p-6 font-mono select-none overflow-hidden retro-border transition-all duration-300">
      <header className="flex justify-between items-start mb-8 border-b-2 border-retro-dark pb-6">
        <div className="flex flex-col">
           <div className="flex items-center gap-3">
              <h1 className="text-2xl font-black tracking-tighter border-b-4 border-retro-purple leading-none italic uppercase">Cloudfusion</h1>
              <button 
                onMouseDown={e => e.stopPropagation()} 
                onClick={() => setIsDisco(!isDisco)}
                className={`${retroBox} bg-white p-2 hover:scale-110 active:scale-95 transition-all cursor-pointer flex items-center justify-center`}
                title={isDisco ? "Включить Linux Theme" : "Включить Disco 2026"}
              >
                {!isDisco ? <Star size={18} fill="currentColor" className="text-retro-yellow" /> : <Monitor size={18} />}
              </button>
           </div>
           <span className="text-[10px] font-bold opacity-50 uppercase mt-2 italic tracking-[0.3em]">
             {view === 'main' ? 'VFS Nodes Control' : 'Storage Analytics'}
           </span>
        </div>
        <div className="flex gap-3" onMouseDown={e => e.stopPropagation()}>
          <button onClick={handleMinimize} className={`${retroBox} bg-white p-1.5 hover:bg-retro-bg`}><Minus size={16} /></button>
          <button onClick={handleClose} className={`${retroBox} bg-retro-red p-1.5 text-white hover:opacity-80`}><X size={16} /></button>
        </div>
      </header>
      
      <main className="h-full">
        {view === 'main' ? renderMain() : renderStats()}
      </main>
    </div>
  );
};

export default App;