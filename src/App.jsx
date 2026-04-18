import React, { useState, useEffect } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { 
  CheckCircle2, RefreshCcw, LogOut, Plus,
  HardDrive, X, Minus, ArrowLeft, Zap, Database, Activity,
  Image as ImageIcon, FileText, Video, Globe,
  Star, Monitor, AlertCircle
} from 'lucide-react';

const appWindow = getCurrentWindow();
const API_BASE = "http://127.0.0.1:8000";

const apiFetch = async (endpoint, method = 'GET') => {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1500);
    const res = await fetch(`${API_BASE}${endpoint}`, { method, signal: controller.signal });
    clearTimeout(timeoutId);
    return res.ok ? await res.json() : null;
  } catch (e) { return null; }
};

const App = () => {
  const [view, setView] = useState('main'); 
  const [activeCloud, setActiveCloud] = useState('YANDEX');
  const [isDisco, setIsDisco] = useState(false); 
  const [cacheLimit, setCacheLimit] = useState(25);
  
  const [isBackendLive, setIsBackendLive] = useState(false);
  const [cloudStatus, setCloudStatus] = useState({ YANDEX: false, NEXTCLOUD: false });
  const [realStats, setRealStats] = useState(null);

  const refreshAppData = async () => {
    const health = await apiFetch('/health'); // Исправлено на health
    const isLive = !!health;
    setIsBackendLive(isLive);

    if (isLive) {
      const auth = await apiFetch('/api/auth/status');
      if (auth) {
         // Если бек шлет объект providers, берем его, иначе по старинке
         if (auth.providers) setCloudStatus(auth.providers);
         else setCloudStatus(prev => ({ ...prev, YANDEX: auth.connected }));
      }
      
      const stats = await apiFetch('/api/stats');
      if (stats) setRealStats(stats);

      const settings = await apiFetch('/api/settings');
      if (settings && settings.cache_limit) setCacheLimit(settings.cache_limit);
    } else {
      setRealStats(null);
      setCloudStatus({ YANDEX: false, NEXTCLOUD: false });
    }
  }; // <--- СКОБКА ТЕПЕРЬ НА МЕСТЕ

  const updateCacheLimit = async (newLimit) => {
    if (newLimit < 5 || newLimit > 500) return;
    setCacheLimit(newLimit);
    try {
      await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cache_limit: newLimit })
      });
    } catch (e) { console.error("Error saving settings"); }
  };

  useEffect(() => {
    refreshAppData();
    const interval = setInterval(refreshAppData, 5000); 
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    document.body.classList.toggle('disco-theme', isDisco);
  }, [isDisco]);

  const handleDrag = () => appWindow.startDragging();
  const handleMinimize = () => appWindow.minimize();
  const handleClose = () => appWindow.hide();

  const retroBox = "retro-border shadow-retro rounded-retro transition-all duration-200";

  const renderMain = () => (
    <div className="flex flex-col h-full animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className={`mb-6 p-2 retro-border flex items-center justify-center gap-2 font-black text-[10px] ${isBackendLive ? 'bg-retro-green text-white' : 'bg-retro-red text-white animate-pulse'}`}>
        {isBackendLive ? <CheckCircle2 size={12}/> : <AlertCircle size={12}/>}
        STATUS: {isBackendLive ? 'BACKEND ONLINE' : 'BACKEND OFFLINE (WAITING...)'}
      </div>

      <section className="mb-6 space-y-4">
        {Object.keys(cloudStatus).map((key) => {
          const isLinked = cloudStatus[key];
          return (
            <div key={key} className={`${retroBox} ${isLinked ? 'bg-retro-yellow' : 'bg-white/40 border-dashed'} p-4 flex items-center justify-between`}>
              <div className="flex flex-col gap-1">
                <span className="font-black text-sm uppercase tracking-tight">{key}.DISK</span>
                <span className="text-[10px] font-bold opacity-60">
                  {isLinked ? 'СИНХРОНИЗИРОВАНО' : 'НЕ ПОДКЛЮЧЕНО'}
                </span>
              </div>
              
              {isLinked ? (
                <button 
                  onClick={() => apiFetch(`/api/auth/logout?provider=${key}`, 'POST').then(refreshAppData)}
                  className={`${retroBox} bg-retro-red text-white p-2 rounded-full hover:scale-110`}
                >
                  <LogOut size={14} />
                </button>
              ) : (
                <button 
                  disabled={!isBackendLive}
                  onClick={() => window.open(`${API_BASE}/api/auth/login?provider=${key}`, '_blank')}
                  className={`flex items-center gap-2 font-black text-[10px] uppercase p-2 retro-border bg-white hover:bg-retro-bg disabled:opacity-30`}
                >
                  Вход <Plus size={14} />
                </button>
              )}
            </div>
          );
        })}
      </section>

      {/* Твой блок управления кэшем, аккуратно вписанный в дизайн */}
      <div className={`${retroBox} bg-white p-4 mb-6`}>
        <div className="flex justify-between items-center mb-2">
           <span className="text-[10px] font-black uppercase italic">Лимит кэша: {cacheLimit}GB</span>
           <div className="flex gap-1">
              <button onClick={() => updateCacheLimit(cacheLimit - 5)} className="p-1 retro-border bg-retro-bg text-[10px] font-bold">-5</button>
              <button onClick={() => updateCacheLimit(cacheLimit + 5)} className="p-1 retro-border bg-retro-bg text-[10px] font-bold">+5</button>
           </div>
        </div>
        <input 
          type="range" min="5" max="100" step="5"
          value={cacheLimit} 
          onChange={(e) => updateCacheLimit(parseInt(e.target.value))}
          className="w-full h-2 bg-retro-bg rounded-lg appearance-none cursor-pointer accent-retro-purple"
        />
      </div>

      <button 
        onClick={() => setView('stats')} 
        className={`${retroBox} ${isBackendLive ? 'bg-retro-purple' : 'bg-gray-400'} text-white w-full py-4 font-black flex items-center justify-center gap-3 active:translate-y-1 transition-all`}
      >
        <HardDrive size={20} /> СТАТИСТИКА
      </button>
    </div>
  );

  const renderStats = () => {
    // Выбираем статы именно для активного облака
    const currentStats = realStats ? (realStats[activeCloud] || realStats) : null;
    const hasData = !!currentStats;
    
    const efficiency = hasData && currentStats.total_files_count > 0
      ? Math.round((currentStats.cached_files_count / currentStats.total_files_count) * 100)
      : 0;

    return (
      <div className="animate-in fade-in zoom-in-95 duration-200">
        <div className="flex justify-between items-center mb-6">
          <button onClick={() => setView('main')} className={`${retroBox} bg-white px-4 py-2 font-black text-[10px] flex items-center gap-2`}>
            <ArrowLeft size={14} /> НАЗАД
          </button>
          <div className={`${retroBox} bg-white px-3 py-2 text-[10px] font-black flex items-center gap-1`}>
            <Globe size={12} /> {isBackendLive ? 'API: CONNECTED' : 'API: DISCONNECTED'}
          </div>
        </div>

        <div className="flex gap-2 mb-6">
          {Object.keys(cloudStatus).map(name => (
            <button key={name} onClick={() => setActiveCloud(name)}
              className={`flex-1 py-3 font-black text-[11px] retro-border ${activeCloud === name ? 'bg-retro-purple text-white shadow-retro' : 'bg-white text-retro-dark opacity-50'}`}>
              {name}
            </button>
          ))}
        </div>

        <section className={`${retroBox} bg-white p-5 mb-6`}>
          <div className="flex justify-between items-end mb-3">
             <h2 className="font-black text-[10px] uppercase opacity-50 italic">Занято в {activeCloud}</h2>
             <span className="font-black text-xl leading-none">
               {hasData ? `${(currentStats.used_space / (1024**3)).toFixed(1)}GB` : '--'} 
               <span className="text-xs opacity-30"> / {hasData ? `${(currentStats.total_space / (1024**3)).toFixed(0)}GB` : '--'}</span>
             </span>
          </div>
          <div className="h-8 retro-border bg-retro-bg flex overflow-hidden p-1">
            <div 
              className="h-full bg-retro-purple transition-all duration-1000" 
              style={{ width: `${hasData ? (currentStats.used_space / currentStats.total_space * 100) : 0}%` }}
            ></div>
          </div>
        </section>

        <div className="grid grid-cols-2 gap-4">
          <div className={`${retroBox} bg-retro-yellow p-4`}>
            <Zap size={20} className="mb-2" />
            <div className="text-[10px] font-black uppercase mb-1 opacity-60">Локальный кэш</div>
            <div className="text-2xl font-black italic">
              {hasData ? `${(currentStats.used_cache_size / (1024**2)).toFixed(1)} MB` : '0.0'}
            </div>
          </div>
          <div className={`${retroBox} bg-white p-4`}>
            <Activity size={20} className="mb-2 text-retro-purple" />
            <div className="text-[10px] font-black uppercase mb-1 opacity-60">Эффективность</div>
            <div className="text-2xl font-black text-retro-green">
              {hasData ? `${efficiency}%` : '--'}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div onMouseDown={handleDrag} className="w-full min-h-screen bg-retro-bg p-6 font-mono select-none overflow-hidden retro-border transition-all duration-300">
      <header className="flex justify-between items-start mb-8 border-b-2 border-retro-dark pb-6">
        <div className="flex flex-col">
           <div className="flex items-center gap-3">
              <h1 className="text-2xl font-black tracking-tighter border-b-4 border-retro-purple leading-none italic uppercase">Cloudfusion</h1>
              <button 
                onMouseDown={e => e.stopPropagation()} 
                onClick={() => setIsDisco(!isDisco)}
                className={`${retroBox} bg-white p-2 hover:scale-110 active:scale-95 transition-all cursor-pointer`}
              >
                {!isDisco ? <Star size={18} fill="currentColor" className="text-retro-yellow" /> : <Monitor size={18} />}
              </button>
           </div>
        </div>
        <div className="flex gap-3" onMouseDown={e => e.stopPropagation()}>
          <button onClick={handleMinimize} className={`${retroBox} bg-white p-1.5`}><Minus size={16} /></button>
          <button onClick={handleClose} className={`${retroBox} bg-retro-red p-1.5 text-white`}><X size={16} /></button>
        </div>
      </header>
      
      <main className="h-full">
        {view === 'main' ? renderMain() : renderStats()}
      </main>
    </div>
  );
};

export default App;