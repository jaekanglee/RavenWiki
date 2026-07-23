mod core;

use std::sync::Mutex;
use tauri::{command, Manager, RunEvent, State};

#[derive(Default)]
struct CoreState(Mutex<Option<core::ManagedCore>>);

impl CoreState {
    fn start(&self) -> Result<(), String> {
        let core = core::ManagedCore::start()?;
        eprintln!("Raven Python Core ready at {}", core.endpoint);
        *self
            .0
            .lock()
            .map_err(|_| "Python Core 상태 lock이 손상되었습니다".to_string())? = Some(core);
        Ok(())
    }

    fn stop(&self) {
        if let Ok(mut state) = self.0.lock() {
            if let Some(mut core) = state.take() {
                core.stop();
            }
        }
    }
}

/// Exposes the managed Python Core endpoint to the webview.
/// Returns an empty string if the Core is not running (should not happen
/// after a successful setup, but the frontend falls back gracefully).
#[command]
fn core_endpoint(state: State<'_, CoreState>) -> String {
    state
        .0
        .lock()
        .ok()
        .and_then(|guard| guard.as_ref().map(|core| core.endpoint.clone()))
        .unwrap_or_default()
}

pub fn run() {
    tauri::Builder::default()
        .manage(CoreState::default())
        .invoke_handler(tauri::generate_handler![core_endpoint])
        .setup(|app| {
            app.state::<CoreState>()
                .start()
                .map_err(std::io::Error::other)?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Raven desktop application error")
        .run(|app, event| {
            if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
                app.state::<CoreState>().stop();
            }
        });
}

#[cfg(test)]
mod tests {
    use super::core::runtime_launch_spec;
    use std::path::PathBuf;

    #[test]
    fn runtime_launch_spec_invokes_python_desktop_module() {
        let python = PathBuf::from("/tmp/python");

        let spec = runtime_launch_spec(python.clone());

        assert_eq!(spec.program, python);
        assert_eq!(spec.args, vec!["-m", "raven.desktop.runtime"]);
    }
}
