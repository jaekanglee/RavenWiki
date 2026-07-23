use serde::Deserialize;
use std::env;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};

#[derive(Debug, PartialEq, Eq)]
pub(crate) struct RuntimeLaunchSpec {
    pub program: PathBuf,
    pub args: Vec<String>,
}

pub(crate) fn runtime_launch_spec(program: PathBuf, mcp: bool) -> RuntimeLaunchSpec {
    let mut args = vec!["-m".into(), "raven.desktop.runtime".into()];
    if mcp {
        args.push("--mcp".into());
    }
    RuntimeLaunchSpec { program, args }
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
    pub(crate) fn start(mcp: bool) -> Result<Self, String> {
        let spec = runtime_launch_spec(resolve_python(), mcp);
        let mut child = Command::new(&spec.program)
            .args(&spec.args)
            .current_dir(workspace_root())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .map_err(|error| {
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

fn resolve_python() -> PathBuf {
    env::var_os("RAVEN_PYTHON")
        .map(PathBuf::from)
        .unwrap_or_else(|| workspace_root().join("scripts/.venv/bin/python"))
}

fn workspace_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .expect("desktop/src-tauri must be nested under the Raven workspace")
        .to_path_buf()
}
