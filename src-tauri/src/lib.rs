#[cfg(target_os = "linux")]
use std::net::{SocketAddr, TcpStream};
#[cfg(target_os = "linux")]
use std::path::PathBuf;
#[cfg(target_os = "linux")]
use std::process::{Child, Command, Stdio};
#[cfg(target_os = "linux")]
use std::sync::Mutex;
#[cfg(target_os = "linux")]
use std::thread;
#[cfg(target_os = "linux")]
use std::time::{Duration, Instant};

use tauri::Manager;

#[cfg(target_os = "linux")]
struct DaemonSlot(Mutex<Option<Child>>);

#[cfg(target_os = "linux")]
impl DaemonSlot {
  fn set(&self, child: Child) {
    *self.0.lock().expect("daemon mutex") = Some(child);
  }

  fn stop(&self) {
    if let Ok(mut g) = self.0.lock() {
      if let Some(mut c) = g.take() {
        let _ = c.kill();
        let _ = c.wait();
      }
    }
  }
}

#[cfg(target_os = "linux")]
fn daemon_executable() -> PathBuf {
  if let Ok(p) = std::env::var("CLOUDFUSION_DAEMON_BIN") {
    return PathBuf::from(p);
  }
  if let Ok(exe) = std::env::current_exe() {
    if let Some(dir) = exe.parent() {
      let sidecar = dir.join("cloudfusion-daemon");
      if sidecar.exists() {
        return sidecar;
      }
    }
  }
  for p in [
    PathBuf::from("/usr/libexec/cloudfusion/cloudfusion-daemon"),
    PathBuf::from("/usr/lib/cloudfusion/cloudfusion-daemon"),
  ] {
    if p.exists() {
      return p;
    }
  }
  PathBuf::from("/usr/libexec/cloudfusion/cloudfusion-daemon")
}

#[cfg(target_os = "linux")]
fn forward_daemon_env(cmd: &mut Command) {
  for (k, v) in std::env::vars() {
    if k.starts_with("YANDEX_")
      || k.starts_with("NC_")
      || k.starts_with("CLOUDFUSION_")
        && k != "CLOUDFUSION_DAEMON_BIN"
        && k != "CLOUDFUSION_DAEMON_READY_SEC"
      || k == "ENABLE_FUSE"
      || k == "MOUNTPOINT"
      || k == "CACHE_DIR"
      || k == "DB_PATH"
      || k == "MAX_CACHE_GB"
      || k == "YANDEX_REDIRECT_URI"
      || k == "ALLOWED_ORIGINS"
      || k == "CORS_ORIGIN_REGEX"
      || k == "XDG_DATA_HOME"
      || k == "XDG_CONFIG_HOME"
      || k == "XDG_CACHE_HOME"
    {
      cmd.env(k, v);
    }
  }
}

#[cfg(target_os = "linux")]
fn wait_for_daemon_ready(timeout: Duration) -> bool {
  let addr: SocketAddr = "127.0.0.1:8000".parse().expect("127.0.0.1:8000");
  let deadline = Instant::now() + timeout;
  while Instant::now() < deadline {
    if TcpStream::connect_timeout(&addr, Duration::from_millis(400)).is_ok() {
      return true;
    }
    thread::sleep(Duration::from_millis(150));
  }
  false
}

#[cfg(target_os = "linux")]
fn spawn_sidecar(app: &tauri::AppHandle) -> std::io::Result<()> {
  let bin = daemon_executable();
  if !bin.exists() {
    log::warn!(
      "cloudfusion-daemon not found at {:?}. Start the API manually, e.g. `python -m daemon.main` from the repo root.",
      bin
    );
    return Ok(());
  }

  let mut cmd = Command::new(&bin);
  cmd.stdin(Stdio::null())
    .stdout(Stdio::inherit())
    .stderr(Stdio::inherit());
  forward_daemon_env(&mut cmd);
  let mut child = cmd.spawn()?;

  let ready_secs: u64 = std::env::var("CLOUDFUSION_DAEMON_READY_SEC")
    .ok()
    .and_then(|s| s.parse().ok())
    .unwrap_or(90)
    .clamp(1, 600);

  if !wait_for_daemon_ready(Duration::from_secs(ready_secs)) {
    let _ = child.kill();
    let _ = child.wait();
    return Err(std::io::Error::new(
      std::io::ErrorKind::TimedOut,
      "daemon did not open 127.0.0.1:8000 in time",
    ));
  }

  if let Some(slot) = app.try_state::<DaemonSlot>() {
    slot.set(child);
  } else {
    let _ = child.kill();
    return Err(std::io::Error::new(
      std::io::ErrorKind::Other,
      "internal error: DaemonSlot state missing",
    ));
  }
  Ok(())
}

#[cfg(target_os = "linux")]
fn stop_sidecar(app: &tauri::AppHandle) {
  let Some(slot) = app.try_state::<DaemonSlot>() else {
    return;
  };
  slot.stop();
}

/// WebKit 2.42+ в ВМ без DRM часто зацикливается на «failed to get GBM device».
/// Отключаем DMA-BUF-рендерер, если пользователь сам ничего не задал.
#[cfg(target_os = "linux")]
fn webkit_vm_defaults() {
  use std::env;
  if env::var_os("WEBKIT_DISABLE_DMABUF_RENDERER").is_none() {
    env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
  }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  #[cfg(target_os = "linux")]
  webkit_vm_defaults();

  tauri::Builder::default()
    .on_window_event(|window, event| {
      #[cfg(target_os = "linux")]
      if window.label() == "main" && matches!(event, tauri::WindowEvent::Destroyed) {
        stop_sidecar(window.app_handle());
      }
    })
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      #[cfg(target_os = "linux")]
      {
        app.manage(DaemonSlot(Mutex::new(None)));
        if let Err(e) = spawn_sidecar(app.handle()) {
          log::error!("failed to start cloudfusion-daemon: {e}");
          eprintln!("CloudFusion: failed to start cloudfusion-daemon: {e}");
        }
      }

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
