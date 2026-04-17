import { getCurrentWindow } from '@tauri-apps/api/window';
import { CheckCircle2, RefreshCcw, FolderOpen, ChevronRight, HardDrive, X, Minus, Info } from 'lucide-react';

const appWindow = getCurrentWindow();

const App = () => {
  const handleDrag = async () => await appWindow.startDragging();
  const handleMinimize = async () => await appWindow.minimize();
  const handleClose = async () => await appWindow.hide();

  const connections = [
    { id: 'ya', name: 'YANDEX.DISK', percent: 11, used: '30GB', total: '260GB', status: 'synced', color: 'bg-retro-yellow' },
    { id: 'nc', name: 'NEXTCLOUD', percent: 92, used: '552GB', total: '600GB', status: 'syncing', color: 'bg-retro-blue' },
  ];

  const retroBox = "border-2 border-retro-dark shadow-retro transition-all duration-100";

  return (
    <div 
      onMouseDown={handleDrag}
      className="w-full min-h-screen bg-retro-bg p-5 font-mono select-none overflow-hidden border-2 border-retro-dark"
    >
      {/* HEADER */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex flex-col">
           <h1 className="text-xl font-black tracking-tighter border-b-4 border-retro-purple leading-none">CLOUDFUSION</h1>
           <span className="text-[10px] font-bold opacity-50 uppercase mt-1">Native Alt Linux Integrator</span>
        </div>
        <div className="flex gap-2" onMouseDown={e => e.stopPropagation()}>
          <button onClick={handleMinimize} title="Свернуть" className={`${retroBox} bg-white p-1 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-retro-hover`}>
            <Minus size={16} />
          </button>
          <button onClick={handleClose} title="Закрыть (в трей)" className={`${retroBox} bg-retro-red p-1 text-white hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-retro-hover`}>
            <X size={16} />
          </button>
        </div>
      </div>

      {/* STORAGE CONNECTIONS */}
      <section onMouseDown={e => e.stopPropagation()} className="mb-6 space-y-4">
        {connections.map((conn) => {
          const isCritical = conn.percent > 90;
          return (
            <div key={conn.id} className={`${retroBox} ${conn.color} p-4 flex items-center justify-between`}>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-black opacity-60 uppercase leading-none">Cloud Storage</span>
                <span className="font-black text-sm tracking-tight leading-none">{conn.name}</span>
                {/* ДАННЫЕ В ГБ */}
                <span className="text-[11px] font-bold bg-white/40 px-1 border border-retro-dark w-fit mt-1">
                  {conn.used} / {conn.total}
                </span>
              </div>
              
              <div className="flex items-center gap-3">
                <div 
                  className="text-right cursor-help" 
                  title={isCritical ? "Место почти закончилось! Скоро сработает LRU-очистка кэша." : `Занято ${conn.percent}% облачного пространства.`}
                >
                  <span className={`text-2xl font-black leading-none ${isCritical ? 'text-retro-red animate-pulse' : 'text-retro-dark'}`}>
                    {conn.percent}%
                  </span>
                </div>
                
                <div 
                  className={`${retroBox} bg-white p-2 rounded-full cursor-help`}
                  title={conn.status === 'synced' ? "Все файлы актуальны (Синхронизировано)" : "Облако проверяет изменения..."}
                >
                   {conn.status === 'synced' ? 
                    <CheckCircle2 className="text-retro-green" size={20} /> : 
                    <RefreshCcw className="text-retro-purple animate-spin" size={20} />
                   }
                </div>
              </div>
            </div>
          );
        })}
      </section>

      {/* ACTION BUTTON */}
      <button 
        onMouseDown={e => e.stopPropagation()}
        title="Настройка кэша, лимитов LRU и детальная статистика трафика"
        className={`${retroBox} bg-retro-purple text-white w-full py-4 font-black flex items-center justify-center gap-3 mb-6 active:translate-x-[2px] active:translate-y-[2px] active:shadow-retro-hover hover:bg-opacity-90 cursor-pointer`}
      >
        <HardDrive size={20} /> СТАТИСТИКА И КЭШ
      </button>

      {/* HISTORY / ACTIVITY */}
      <section onMouseDown={e => e.stopPropagation()} className={`${retroBox} bg-white p-4`}>
        <div className="flex justify-between items-center mb-4 border-b-2 border-retro-dark pb-2">
          <div className="flex items-center gap-2">
            <h2 className="font-black text-sm uppercase">Активность</h2>
            <Info size={14} className="opacity-30 cursor-help" title="Список последних измененных файлов в вашей системе" />
          </div>
          <span className="bg-retro-pink text-[10px] font-black px-2 py-1 border border-retro-dark animate-pulse">LIVE</span>
        </div>
        
        <div className="flex flex-col gap-2">
          {[
            { name: "very_long_filename_backup_final_v2.iso", date: "07.08" },
            { name: "retro_vibes.png", date: "07.08" },
            { name: "config.yaml", date: "06.08" }
          ].map((file, i) => (
            <div key={i} className="flex items-center justify-between group hover:bg-retro-bg p-1 px-2 border-b border-dashed border-retro-dark/20 last:border-0">
              <div className="flex flex-col min-w-0 mr-2">
                <span 
                  className="text-[11px] font-black truncate uppercase italic tracking-tighter" 
                  title={file.name} // ПОЛНОЕ ИМЯ ПРИ НАВЕДЕНИИ
                >
                  {file.name}
                </span>
                <span className="text-[9px] font-bold opacity-40 italic">UPDATED: {file.date}</span>
              </div>
              <button 
                title="Открыть расположение файла в Dolphin"
                className="text-retro-dark opacity-50 group-hover:opacity-100 hover:text-retro-blue transition-all"
              >
                <FolderOpen size={18} />
              </button>
            </div>
          ))}
        </div>

        <button className="w-full mt-4 text-[10px] font-black flex items-center justify-center gap-1 hover:text-retro-purple transition-colors border-t border-retro-dark pt-3">
          ПОКАЗАТЬ ВСЕ СОБЫТИЯ <ChevronRight size={14} />
        </button>
      </section>
    </div>
  );
};

export default App;