mod core;

use std::sync::Mutex;
use tauri::{command, Manager, RunEvent, State, WindowEvent};
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;

#[derive(Default)]
struct CoreState(Mutex<Option<core::ManagedCore>>);

impl CoreState {
    fn start(&self, mcp: bool, resource_dir: Option<std::path::PathBuf>) -> Result<(), String> {
        let core = core::ManagedCore::start(mcp, resource_dir)?;
        eprintln!("Raven Python Core ready at {}", core.endpoint);
        if let Some(ref mcp_ep) = core.mcp_endpoint {
            eprintln!("Raven MCP endpoint at {mcp_ep}");
        }
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
#[command]
fn core_endpoint(state: State<'_, CoreState>) -> String {
    state
        .0
        .lock()
        .ok()
        .and_then(|guard| guard.as_ref().map(|core| core.endpoint.clone()))
        .unwrap_or_default()
}

/// Exposes the MCP HTTP endpoint to the webview (empty string if disabled).
#[command]
fn mcp_endpoint(state: State<'_, CoreState>) -> String {
    state
        .0
        .lock()
        .ok()
        .and_then(|guard| guard.as_ref().and_then(|core| core.mcp_endpoint.clone()))
        .unwrap_or_default()
}

pub fn run() {
    let mcp_enabled = std::env::var("RAVEN_DESKTOP_MCP")
        .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
        .unwrap_or(false);

    let app = tauri::Builder::default()
        .manage(CoreState::default())
        .invoke_handler(tauri::generate_handler![core_endpoint, mcp_endpoint])
        .setup(move |app| {
            let resource_dir = app.path().resource_dir().ok();
            app.state::<CoreState>()
                .start(mcp_enabled, resource_dir)
                .map_err(std::io::Error::other)?;

            let show_i = MenuItem::with_id(app, "show", "Open Dashboard", true, None::<&str>)?;
            let restart_i = MenuItem::with_id(app, "restart", "Restart Backend", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit Raven", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_i, &restart_i, &quit_i])?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "quit" => app.exit(0),
                    "restart" => {
                        let state = app.state::<CoreState>();
                        state.stop();
                        let resource_dir = app.path().resource_dir().ok();
                        let mcp_enabled = std::env::var("RAVEN_DESKTOP_MCP")
                            .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
                            .unwrap_or(false);
                        if let Err(e) = state.start(mcp_enabled, resource_dir) {
                            eprintln!("Failed to restart core: {}", e);
                        }
                    }
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            window.show().unwrap();
                            window.set_focus().unwrap();
                        }
                    }
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                window.hide().unwrap();
            }
        })
        .build(tauri::generate_context!());

    match app {
        Ok(app) => app.run(|app, event| {
            match event {
                RunEvent::Exit | RunEvent::ExitRequested { .. } => {
                    app.state::<CoreState>().stop();
                }
                RunEvent::Reopen { has_visible_windows, .. } => {
                    if !has_visible_windows {
                        if let Some(window) = app.get_webview_window("main") {
                            window.show().unwrap();
                            window.set_focus().unwrap();
                        }
                    }
                }
                _ => {}
            }
        }),
        Err(e) => {
            let msg = format!("Raven failed to start:\n{e}");
            eprintln!("{msg}");
            // Native macOS dialog instead of panic → abort
            let _ = std::process::Command::new("osascript")
                .args([
                    "-e",
                    &format!(
                        "display dialog \"{}\" with title \"Raven\" buttons {{\"OK\"}} default button \"OK\" with icon stop",
                        msg.replace('"', "\\\"").replace('\n', "\\n")
                    ),
                ])
                .status();
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::core::runtime_launch_spec;
    use std::path::PathBuf;

    #[test]
    fn runtime_launch_spec_invokes_python_desktop_module() {
        let python = PathBuf::from("/tmp/python");
        let spec = runtime_launch_spec(python.clone(), false, None, None);
        assert_eq!(spec.program, python);
        assert_eq!(spec.args, vec!["-m", "raven.desktop.runtime"]);
        assert!(spec.env.is_empty());
    }

    #[test]
    fn runtime_launch_spec_with_mcp_adds_flag() {
        let python = PathBuf::from("/tmp/python");
        let spec = runtime_launch_spec(python.clone(), true, None, None);
        assert_eq!(spec.args, vec!["-m", "raven.desktop.runtime", "--mcp"]);
    }

    #[test]
    fn runtime_launch_spec_with_python_path_sets_env() {
        let python = PathBuf::from("/tmp/python");
        let pp = PathBuf::from("/app/Resources/raven");
        let spec = runtime_launch_spec(python, false, Some(pp.clone()), None);
        assert_eq!(spec.args, vec!["-P", "-m", "raven.desktop.runtime"]);
        assert_eq!(
            spec.env,
            vec![("PYTHONPATH".to_string(), pp.to_string_lossy().into_owned())]
        );
    }

    #[test]
    fn runtime_launch_spec_with_host_adds_flag() {
        let python = PathBuf::from("/tmp/python");
        let spec = runtime_launch_spec(python, false, None, Some("0.0.0.0".to_string()));
        assert_eq!(
            spec.args,
            vec!["-m", "raven.desktop.runtime", "--host", "0.0.0.0"]
        );
    }
}
