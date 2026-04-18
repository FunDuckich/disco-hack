import React, { useState } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { 
  CheckCircle2, RefreshCcw, FolderOpen, ChevronRight, 
  HardDrive, X, Minus, ArrowLeft, Zap, Database, Activity,
  Image as ImageIcon, FileText, Video, Globe, HelpCircle
} from 'lucide-react';

const appWindow = getCurrentWindow();

const App = () => {
  const [view, setView] = useState('main'); 
  const [activeCloud, setActiveCloud] = useState('YANDEX');
  const [cacheLimit, setCacheLimit] = useState(25); 

  const handleDrag = async () => await appWindow.startDragging();
  const handleMinimize = async () => await appWindow.minimize();
  const handleClose = async () => await appWindow.hide();

  const retroBox = "border-2 border-retro-dark shadow-retro transition-all duration-100";

  const clouds = {
    YANDEX: { used: '30GB', total: '260GB', percent: 11, ping: '42ms', types: { img: 40, doc: 25, vid: 35 }, savedGb: '1.2GB' },
    NEXTCLOUD: { used: '552GB', total: '600GB', percent: 92, ping: '115ms', types: { img: 20, doc: 60, vid: 20 }, savedGb: '14.8GB' }
  };

  const renderMain = () => (
    <>
      <section onMouseDown={e => e.stopPropagation()} className="mb-6 space-y-4">
        {Object.entries(clouds).map(([key, data]) => (
          <div 
            key={key} 
            title="Ваше подключенное облако. Кликните 'Статистика', чтобы увидеть детали."
            className={`${retroBox} ${key === 'YANDEX' ? 'bg-retro-yellow' : 'bg-retro-blue'} p-4 flex items-center justify-between cursor-help`}
          >
            <div className="flex flex-col gap-1">
              <span className="font-black text-sm uppercase">{key}.DISK</span>
              <span className="text-[11px] font-bold bg-white/40 px-1 border border-retro-dark w-fit tracking-tighter">
                {data.used} / {data.total}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-2xl font-black ${data.percent > 90 ? 'text-retro-red animate-pulse' : 'text-retro-dark'}`}>
                {data.percent}%
              </span>
              <div 
                className={`${retroBox} bg-white p-2 rounded-full`}
                title={data.percent < 90 ? "Синхронизировано: файлы в облаке и в VFS совпадают" : "В процессе: высокая нагрузка или синхронизация изменений"}
              >
                {data.percent < 90 ? <CheckCircle2 className="text-retro-green" size={20} /> : <RefreshCcw className="text-retro-purple animate-spin" size={20} />}
              </div>
            </div>
          </div>
        ))}
      </section>

      <button onClick={() => setView('stats')} onMouseDown={e => e.stopPropagation()} className={`${retroBox} bg-retro-purple text-white w-full py-4 font-black flex items-center justify-center gap-3 mb-6 active:translate-y-1 active:shadow-none transition-all`}>
        <HardDrive size={20} /> СТАТИСТИКА И КЭШ
      </button>

      <section onMouseDown={e => e.stopPropagation()} className={`${retroBox} bg-white p-4`}>
        <div className="flex items-center gap-2 mb-4 border-b-2 border-retro-dark pb-2">
           <h2 className="font-black text-sm uppercase italic text-retro-purple">История FUSE</h2>
        </div>
        <div className="flex flex-col gap-2">
          {["backup_sys.iso", "presentation_final.pdf", "image_01.png"].map((file, i) => (
            <div key={i} className="flex items-center justify-between p-1 border-b border-dashed border-retro-dark/10 last:border-0 group">
              <div className="flex flex-col min-w-0">
                <span className="text-[10px] font-black truncate uppercase italic tracking-tighter" title={file}>
                  {file.length > 24 ? file.slice(0, 24) + '...' : file}
                </span>
                <span className="text-[8px] font-bold opacity-40">открыт</span>
              </div>
              <FolderOpen size={16} className="opacity-0 group-hover:opacity-100 text-retro-blue cursor-pointer transition-opacity" title="Показать в проводнике ALT Linux (Dolphin)" />
            </div>
          ))}
        </div>
      </section>
    </>
  );

  const renderStats = () => (
    <div onMouseDown={e => e.stopPropagation()} className="animate-in fade-in zoom-in-95 duration-200">
      <div className="flex justify-between items-center mb-4">
        <button onClick={() => setView('main')} className={`${retroBox} bg-white px-3 py-1 font-black text-[10px] flex items-center gap-2 hover:bg-retro-yellow`}>
          <ArrowLeft size={12} /> НАЗАД
        </button>
        <div 
           className={`${retroBox} bg-retro-green text-white px-2 py-1 text-[10px] font-black flex items-center gap-1 cursor-help shadow-sm`}
           title="Текущая задержка ответа API облачного провайдера. Влияет на скорость отрисовки папок."
        >
          <Globe size={10} /> PING: {clouds[activeCloud].ping}
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        {Object.keys(clouds).map(name => (
          <button 
            key={name}
            onClick={() => setActiveCloud(name)}
            className={`flex-1 py-2 font-black text-[10px] border-2 border-retro-dark transition-all ${activeCloud === name ? 'bg-retro-purple text-white shadow-retro translate-x-[-2px] translate-y-[-2px]' : 'bg-white text-retro-dark hover:bg-retro-bg'}`}
          >
            {name}
          </button>
        ))}
      </div>

      <section READ
        className={`${retroBox} bg-white p-4 mb-4 cursor-help`} 
        title={`Детальный разбор хранилища ${activeCloud}. Показывает соотношение реальных данных к общему лимиту.`}
      >
        <div className="flex justify-between items-end mb-2">
           <h2 className="font-black text-[10px] uppercase opacity-50 italic underline decoration-retro-purple">Облачная память</h2>
           <span className="font-black text-lg leading-none">{clouds[activeCloud].used} <span className="text-xs opacity-30 tracking-tighter">/ {clouds[activeCloud].total}</span></span>
        </div>
        <div className="h-6 border-2 border-retro-dark bg-retro-bg flex overflow-hidden shadow-inner">
          <div className="h-full bg-retro-purple transition-all duration-700 ease-out" style={{ width: `${clouds[activeCloud].percent}%` }}></div>
        </div>
      </section>

      <div className="grid grid-cols-3 gap-2 mb-6 text-center">
        {[
          { icon: ImageIcon, color: 'bg-retro-yellow/20', val: clouds[activeCloud].types.img, label: 'Медиа' },
          { icon: Video, color: 'bg-retro-blue/20', val: clouds[activeCloud].types.vid, label: 'Видео' },
          { icon: FileText, color: 'bg-retro-pink/20', val: clouds[activeCloud].types.doc, label: 'Документы' }
        ].map((t, idx) => (
          <div key={idx} className={`${retroBox} ${t.color} p-2 cursor-help`} title={`Файлы типа '${t.label}' занимают ${t.val}% от всех данных в этом облаке.`}>
             <t.icon size={14} className="mx-auto mb-1 opacity-70" />
             <div className="text-[10px] font-black">{t.val}%</div>
          </div>
        ))}
      </div>

      <section className={`${retroBox} bg-retro-pink p-4 mb-6`}>
        <div className="flex justify-between items-center mb-2">
          <h2 className="font-black text-[11px] uppercase flex items-center gap-1 cursor-help" title="Максимальный объем папки ~/.cache/cloudfusion. При превышении старые файлы удаляются.">
            <Database size={12}/> Лимит LRU кэша
          </h2>
          <span className="bg-white px-2 border-2 border-retro-dark font-black text-xs italic shadow-sm">{cacheLimit} GB</span>
        </div>
        <input 
          type="range" min="1" max="100" value={cacheLimit} onChange={(e) => setCacheLimit(e.target.value)}
          className="w-full h-8 appearance-none bg-white border-2 border-retro-dark cursor-pointer accent-retro-purple"
          style={{ backgroundImage: `linear-gradient(to right, #552CB7 ${cacheLimit}%, transparent ${cacheLimit}%)` }}
        />
        <div className="flex justify-between text-[8px] font-black uppercase mt-1 opacity-50 italic">
          <span>1GB</span>
          <span className="text-retro-purple">MAX 100GB</span>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-4">
        <div className={`${retroBox} bg-retro-yellow p-3 cursor-help`} title="Объем данных, которые уже скачаны в ваш локальный кэш для мгновенного доступа офлайн.">
          <Zap size={16} className="mb-1" />
          <div className="text-[9px] font-black uppercase leading-none mb-1">Кэшировано</div>
          <div className="text-lg font-black italic tracking-tighter">14.2 GB</div>
        </div>
        <div className={`${retroBox} bg-white p-3 cursor-help`} title="Процент запросов, обслуженных из кэша без скачивания из интернета, и общий объем спасенного трафика.">
          <Activity size={16} className="mb-1 text-retro-purple" />
          <div className="text-[9px] font-black uppercase leading-none mb-1 text-retro-purple">Экономия</div>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-black text-retro-green">86%</span>
            <span className="text-[10px] font-bold opacity-50">({clouds[activeCloud].savedGb})</span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div onMouseDown={handleDrag} className="w-full min-h-screen bg-retro-bg p-5 font-mono select-none overflow-hidden border-2 border-retro-dark">
      <div className="flex justify-between items-center mb-6 border-b-2 border-retro-dark pb-4 shadow-[0_4px_0_0_rgba(26,26,26,0.05)]">
        <div className="flex flex-col">
           <h1 className="text-xl font-black tracking-tighter border-b-4 border-retro-purple leading-none italic">CLOUDFUSION</h1>
           <span className="text-[9px] font-bold opacity-50 uppercase mt-1 italic tracking-widest">
             {view === 'main' ? 'VFS Active Nodes' : 'System Cache Engine'}
           </span>
        </div>
        <div className="flex gap-2" onMouseDown={e => e.stopPropagation()}>
          <button onClick={handleMinimize} title="Свернуть в панель" className={`${retroBox} bg-white p-1 hover:translate-y-[2px] hover:shadow-none transition-all`}><Minus size={14} /></button>
          <button onClick={handleClose} title="Закрыть (продолжит работу в фоне)" className={`${retroBox} bg-retro-red p-1 text-white hover:translate-y-[2px] hover:shadow-none transition-all`}><X size={14} /></button>
        </div>
      </div>
      {view === 'main' ? renderMain() : renderStats()}
    </div>
  );
};

export default App;