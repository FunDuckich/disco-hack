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
  PathBuf::from("/usr/libexec/cloudfusion/cloudfusion-daemon")
}

#[cfg(target_os = "linux")]
fn forward_daemon_env(cmd: &mut Command) {
  for (k, v) in std::env::vars() {
    if k.starts_with("YANDEX_")
      || k.starts_with("NC_")
      || k == "ENABLE_FUSE"
      || k == "MOUNTPOINT"
      || k == "CACHE_DIR"
      || k == "DB_PATH"
      || k == "MAX_CACHE_GB"
      || k == "YANDEX_REDIRECT_URI"
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
    .stdout(Stdio::piped())
    .stderr(Stdio::piped());
  forward_daemon_env(&mut cmd);
  let mut child = cmd.spawn()?;

  if !wait_for_daemon_ready(Duration::from_secs(45)) {
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
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
