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

// Логика из Второго компонента: более надежный fetch с таймаутом
const apiFetch = async (endpoint, method = 'GET', body = null) => {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1500);
    const config = { 
      method, 
      signal: controller.signal,
      headers: body ? { 'Content-Type': 'application/json' } : {}
    };
    if (body) config.body = JSON.stringify(body);
    
    const res = await fetch(`${API_BASE}${endpoint}`, config);
    clearTimeout(timeoutId);
    return res.ok ? await res.json() : null;
  } catch (e) { return null; }
};

const App = () => {
  // Состояния из обоих компонентов
  const [view, setView] = useState('main'); 
  const [activeCloud, setActiveCloud] = useState('YANDEX');
  const [isDisco, setIsDisco] = useState(false); 
  const [cacheLimit, setCacheLimit] = useState(25);
  
  const [isBackendLive, setIsBackendLive] = useState(false);
  const [cloudStatus, setCloudStatus] = useState({ YANDEX: false, NEXTCLOUD: false });
  const [realStats, setRealStats] = useState(null);

  // Константа стилей из Первого компонента
  const retroBox = "retro-border shadow-retro rounded-retro transition-all duration-200";

  // Статические данные для оформления (цвета и иконки) из Первого компонента
  const cloudUIData = {
    YANDEX: { color: 'bg-retro-yellow', ping: '42ms' },
    NEXTCLOUD: { color: 'bg-retro-blue', ping: '115ms' }
  };

  // Обновление данных (Логика из Второго компонента)
  const refreshAppData = async () => {
    const health = await apiFetch('/health');
    const isLive = !!health;
    setIsBackendLive(isLive);

    if (isLive) {
      const auth = await apiFetch('/api/auth/status');
      if (auth) {
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
  };

const updateCacheLimit = async (newLimit) => {
  // Теперь минимум 1 ГБ, максимум 500 ГБ
  if (newLimit < 1 || newLimit > 500) return; 
  setCacheLimit(newLimit);
  await apiFetch('/api/settings', 'POST', { cache_limit: newLimit });
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


  const renderMain = () => (
    <div className="flex flex-col h-full animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Статус бэкенда (Стиль карточки из дизайна 1, логика из 2) */}
      <div className={`mb-6 p-2 ${retroBox} flex items-center justify-center gap-2 font-black text-[10px] ${isBackendLive ? 'bg-retro-green text-white' : 'bg-retro-red text-white animate-pulse'}`}>
        {isBackendLive ? <CheckCircle2 size={12}/> : <AlertCircle size={12}/>}
        STATUS: {isBackendLive ? 'BACKEND ONLINE' : 'BACKEND OFFLINE (WAITING...)'}
      </div>

      <section onMouseDown={e => e.stopPropagation()} className="mb-6 space-y-4">
        {Object.keys(cloudStatus).map((key) => {
          const isLinked = cloudStatus[key];
          const ui = cloudUIData[key] || { color: 'bg-retro-purple', ping: '???' };
          const stats = realStats ? (realStats[key] || realStats) : null;
          
          // Расчет процентов для прогресс-бара
          const percent = stats ? Math.round((stats.used_space / stats.total_space) * 100) : 0;

          return (
            <div key={key} className={`${retroBox} ${isLinked ? ui.color : 'bg-white/50 border-dashed'} p-4 flex items-center justify-between`}>
              {isLinked ? (
                <>
                  <div className="flex flex-col gap-1 cursor-help" title={`Хранилище ${key}`}>
                    <span className="font-black text-sm uppercase tracking-tight">{key}.DISK</span>
                    <span className="text-[10px] font-bold bg-white/40 px-1 border border-retro-dark w-fit">
                      {stats ? `${(stats.used_space / 1024**3).toFixed(1)}GB / ${(stats.total_space / 1024**3).toFixed(0)}GB` : 'Загрузка...'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xl font-black ${percent > 90 ? 'text-retro-red animate-pulse' : ''}`}>{percent}%</span>
                    <div className={`${retroBox} bg-white p-2 rounded-full cursor-help`} title="Синхронизация">
                      {percent < 90 ? <CheckCircle2 className="text-retro-green" size={18} /> : <RefreshCcw className="text-retro-purple animate-spin" size={18} />}
                    </div>
                    <button 
                      onClick={() => apiFetch(`/api/auth/logout?provider=${key}`, 'POST').then(refreshAppData)}
                      className={`${retroBox} bg-retro-red text-white p-2 rounded-full hover:scale-110 active:translate-y-0.5 active:shadow-none`}
                    >
                      <LogOut size={14} />
                    </button>
                  </div>
                </>
              ) : (
                <button 
                  disabled={!isBackendLive}
                  onClick={() => window.open(`${API_BASE}/api/auth/login?provider=${key}`, '_blank')}
                  className="w-full py-2 flex items-center justify-center gap-3 group disabled:opacity-30"
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
          {/* Оставили только отображение текущего числа */}
          <span className="bg-white px-3 py-1 retro-border font-black text-sm italic shadow-sm">{cacheLimit} GB</span>
        </div>
        
        <input 
          type="range" 
          min="1"            // Минимальное смещение 1 ГБ
          max="100"          // Максимум (можешь поставить 200 или 500)
          step="1"           // Шаг перемещения — строго 1 ГБ
          value={cacheLimit} 
          onChange={(e) => updateCacheLimit(parseInt(e.target.value))}
          className="w-full h-10 appearance-none bg-white retro-border cursor-pointer accent-retro-purple"
          // Эта строка закрашивает полоску прогресса (делим на max значение, тут 100)
          style={{ backgroundImage: `linear-gradient(to right, var(--color-retro-purple) ${cacheLimit}%, transparent ${cacheLimit}%)` }}
        />
      </section>

      <button 
      disabled={!isBackendLive}
        onClick={() => setView('stats')} 
        onMouseDown={e => e.stopPropagation()} 
        className={`${retroBox} ${isBackendLive ? 'bg-retro-purple' : 'bg-gray-400'} text-white w-full py-4 font-black flex items-center justify-center gap-3 active:translate-y-1 active:shadow-none hover:opacity-90 transition-all`}
      >
        <HardDrive size={20} /> СТАТИСТИКА
      </button>
    </div>
  );

  const renderStats = () => {
    const currentStats = realStats ? (realStats[activeCloud] || realStats) : null;
    const hasData = !!currentStats;
    
    const efficiency = hasData && currentStats.total_files_count > 0
      ? Math.round((currentStats.cached_files_count / currentStats.total_files_count) * 100)
      : 0;

    return (
      <div onMouseDown={e => e.stopPropagation()} className="animate-in fade-in zoom-in-95 duration-200">
        <div className="flex justify-between items-center mb-6">
          <button onClick={() => setView('main')} className={`${retroBox} bg-white px-4 py-2 font-black text-[10px] flex items-center gap-2 hover:bg-retro-yellow`}>
            <ArrowLeft size={14} /> НАЗАД
          </button>
          <div className={`${retroBox} ${isBackendLive ? 'bg-retro-green' : 'bg-retro-red'} text-white px-3 py-2 text-[10px] font-black flex items-center gap-1 cursor-help`} title="Статус API">
            <Globe size={12} /> {isBackendLive ? `PING: ${cloudUIData[activeCloud]?.ping || 'OK'}` : 'OFFLINE'}
          </div>
        </div>

        <div className="flex gap-2 mb-6">
          {Object.keys(cloudStatus).map(name => (
            <button key={name} onClick={() => setActiveCloud(name)}
              className={`flex-1 py-3 font-black text-[11px] retro-border transition-all ${activeCloud === name ? 'bg-retro-purple text-white shadow-retro -translate-y-1' : 'bg-white text-retro-dark opacity-60 hover:opacity-100'}`}>
              {name}
            </button>
          ))}
        </div>

        <section className={`${retroBox} bg-white p-5 mb-6 cursor-help`} title={`Занятый объём диска ${activeCloud}`}>
          <div className="flex justify-between items-end mb-3">
             <h2 className="font-black text-[10px] uppercase opacity-50 italic underline decoration-retro-purple tracking-tighter">Занято в облаке</h2>
             <span className="font-black text-xl leading-none">
               {hasData ? `${(currentStats.used_space / (1024**3)).toFixed(1)}GB` : '--'} 
               <span className="text-xs opacity-30"> / {hasData ? `${(currentStats.total_space / (1024**3)).toFixed(0)}GB` : '--'}</span>
             </span>
          </div>
          <div className={`h-8 retro-border bg-retro-bg flex overflow-hidden p-1 ${!isDisco ? 'rounded-full' : ''}`}>
            <div 
              className={`h-full bg-retro-purple transition-all duration-1000 ${!isDisco ? 'rounded-full' : ''}`} 
              style={{ width: `${hasData ? (currentStats.used_space / currentStats.total_space * 100) : 0}%` }}
            ></div>
          </div>
        </section>



        <div className="grid grid-cols-2 gap-4">
          <div className={`${retroBox} bg-retro-yellow p-4 cursor-help`} title="Локальный кэш">
            <Zap size={20} className="mb-2 text-retro-dark" />
            <div className="text-[10px] font-black uppercase mb-1 opacity-60">Кэш</div>
            <div className="text-2xl font-black italic text-retro-dark leading-none">
              {hasData ? `${(currentStats.used_cache_size / (1024**2)).toFixed(1)} MB` : '0.0 MB'}
            </div>
          </div>

            <div className={`${retroBox} bg-white p-4 cursor-help`} title="Процент файлов, находящихся в локальном кэше">
    <FileText size={20} className="mb-2 text-retro-purple" />
    <div className="text-[10px] font-black uppercase mb-1 opacity-60">Файлы в кэше</div>
    <div className="text-2xl font-black text-retro-purple leading-none">
      {hasData ? `${efficiency}%` : '--'}
    </div>
    <div className="text-[8px] mt-1 opacity-40 font-bold uppercase">
      {hasData 
        ? `${currentStats.cached_files_count} из ${currentStats.total_files_count} объектов` 
        : 'АНАЛИЗ...'}
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
      </header>
      
      <main className="h-full">
        {view === 'main' ? renderMain() : renderStats()}
      </main>
    </div>
  );
};

export default App;