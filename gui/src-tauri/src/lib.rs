use std::process::Command;
use std::sync::Mutex;
use tauri::{Emitter, State};

struct AppState {
    showrunner_path: Mutex<String>,
}

#[tauri::command]
fn validate_episode(path: String, state: State<AppState>) -> Result<String, String> {
    let showrunner = state.showrunner_path.lock().map_err(|e| e.to_string())?;

    let output = Command::new(&*showrunner)
        .args(["validate", &path, "--strict"])
        .output()
        .map_err(|e| format!("Failed to run showrunner: {e}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Validation failed: {stderr}"));
    }

    // Read the episode JSON to extract metadata
    let ep_content =
        std::fs::read_to_string(&path).map_err(|e| format!("Failed to read episode file: {e}"))?;
    let ep_json: serde_json::Value =
        serde_json::from_str(&ep_content).map_err(|e| format!("Invalid JSON: {e}"))?;

    Ok(serde_json::to_string(&ep_json).map_err(|e| e.to_string())?)
}

#[tauri::command]
async fn run_pipeline(
    app: tauri::AppHandle,
    path: String,
    output_dir: String,
    workers: u32,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let showrunner = state.showrunner_path.lock().map_err(|e| e.to_string())?;

    let mut cmd = Command::new(&*showrunner);
    cmd.args(["run", &path, "-w", &workers.to_string()]);

    if !output_dir.is_empty() {
        cmd.args(["-o", &output_dir]);
    }

    let mut child = cmd
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start pipeline: {e}"))?;

    let stdout = child.stdout.take().unwrap();
    let stderr = child.stderr.take().unwrap();
    let app_handle = app.clone();

    // Stream stdout lines
    let app_for_stdout = app_handle.clone();
    tauri::async_runtime::spawn(async move {
        use std::io::{BufRead, BufReader};
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            if let Ok(line) = line {
                let _ = app_for_stdout.emit("pipeline-log", &line);
            }
        }
    });

    // Stream stderr lines
    tauri::async_runtime::spawn(async move {
        use std::io::{BufRead, BufReader};
        let reader = BufReader::new(stderr);
        for line in reader.lines() {
            if let Ok(line) = line {
                let _ = app_handle.emit("pipeline-log", &format!("[stderr] {line}"));
            }
        }
    });

    let output = child
        .wait()
        .map_err(|e| format!("Pipeline process error: {e}"))?;

    if !output.success() {
        return Err("Pipeline exited with errors".to_string());
    }

    let result = serde_json::json!({
        "status": "completed",
        "video_path": ""
    });

    Ok(serde_json::to_string(&result).map_err(|e| e.to_string())?)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AppState {
            showrunner_path: Mutex::new("showrunner".to_string()),
        })
        .invoke_handler(tauri::generate_handler![validate_episode, run_pipeline])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
