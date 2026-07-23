use serde::Deserialize;
use std::env;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};

#[derive(Debug, PartialEq, Eq)]
pub(crate) struct RuntimeLaunchSpec {
    pub program: PathBuf,
    pub args: Vec<String>,
    pub env: Vec<(String, String)>,
}

pub(crate) fn runtime_launch_spec(
    program: PathBuf,
    mcp: bool,
    python_path: Option<PathBuf>,
    host: Option<String>,
) -> RuntimeLaunchSpec {
    let mut args = Vec::new();
    // Bundled mode: -P prevents CWD from shadowing the bundled raven package
    if python_path.is_some() {
        args.push("-P".into());
    }
    args.push("-m".into());
    args.push("raven.desktop.runtime".into());
    if let Some(h) = &host {
        args.push("--host".into());
        args.push(h.clone());
    }
    if mcp {
        args.push("--mcp".into());
    }
    let mut env = Vec::new();
    if let Some(pp) = python_path {
        env.push(("PYTHONPATH".into(), pp.to_string_lossy().into_owned()));
    }
    RuntimeLaunchSpec { program, args, env }
}

#[derive(Deserialize)]
struct ReadyMessage {
    host: String,
    port: u16,
    #[serde(default)]
    mcp_port: Option<u16>,
}

pub(crate) struct ManagedCore {
    child: Child,
    pub endpoint: String,
    pub mcp_endpoint: Option<String>,
}

impl ManagedCore {
    pub(crate) fn start(mcp: bool, resource_dir: Option<PathBuf>) -> Result<Self, String> {
        let (python, python_path) = resolve_python(resource_dir.as_deref());
        let host = env::var("RAVEN_DESKTOP_HOST")
            .ok()
            .filter(|h| !h.is_empty());
        let spec = runtime_launch_spec(python, mcp, python_path, host);
        let mut cmd = Command::new(&spec.program);
        cmd.args(&spec.args)
            .current_dir(workspace_root())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit());
        for (key, value) in &spec.env {
            cmd.env(key, value);
        }
        let mut child = cmd.spawn().map_err(|error| {
            format!(
                "Python Core 시작 실패 ({}): {error}",
                spec.program.display()
            )
        })?;

        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "Python Core readiness stream을 열 수 없습니다".to_string())?;
        let mut line = String::new();
        BufReader::new(stdout)
            .read_line(&mut line)
            .map_err(|error| format!("Python Core readiness 읽기 실패: {error}"))?;
        let ready: ReadyMessage = serde_json::from_str(&line)
            .map_err(|error| format!("Python Core readiness 형식 오류: {error}"))?;

        if ready.host != "127.0.0.1" || ready.port == 0 {
            return Err("Python Core가 유효한 loopback endpoint를 보고하지 않았습니다".to_string());
        }

        let mcp_endpoint = ready
            .mcp_port
            .map(|p| format!("http://{}:{}", ready.host, p));

        Ok(Self {
            child,
            endpoint: format!("http://{}:{}", ready.host, ready.port),
            mcp_endpoint,
        })
    }

    pub(crate) fn stop(&mut self) {
        if self.child.try_wait().ok().flatten().is_none() {
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
    }
}

impl Drop for ManagedCore {
    fn drop(&mut self) {
        self.stop();
    }
}

/// Resolve the Python interpreter and optional PYTHONPATH.
///
/// Priority: RAVEN_PYTHON env → bundled resources → dev venv.
fn resolve_python(resource_dir: Option<&Path>) -> (PathBuf, Option<PathBuf>) {
    if let Some(p) = env::var_os("RAVEN_PYTHON") {
        return (PathBuf::from(p), None);
    }

    // Bundled mode: Resources/resources/python/bin/python3 + Resources/resources/raven/
    if let Some(res) = resource_dir {
        let bundled_python = res
            .join("resources")
            .join("python")
            .join("bin")
            .join("python3");
        let bundled_raven = res.join("resources").join("raven");
        if bundled_python.exists() && bundled_raven.exists() {
            return (bundled_python, Some(bundled_raven));
        }
    }

    // Dev mode: scripts/.venv/bin/python, raven importable from CWD
    (workspace_root().join("scripts/.venv/bin/python"), None)
}

fn workspace_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .expect("desktop/src-tauri must be nested under the Raven workspace")
        .to_path_buf()
}
