// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::State;
use tauri::{
    menu::MenuEvent,
    menu::MenuBuilder,
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, WindowEvent,
};
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::ShellExt;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::process::CommandEvent;
use std::sync::{Arc, Mutex};
use std::time::Duration;

#[derive(Clone)]
struct AppState {
    backend_child: Arc<Mutex<Option<tauri_plugin_shell::process::CommandChild>>>,
    api_base_url: Arc<Mutex<Option<String>>>,
    close_preference: Arc<Mutex<ClosePreference>>,
    tray_available: bool,
}

#[derive(Clone, Copy, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
enum ClosePreference {
    #[default]
    Ask,
    Tray,
    Exit,
}

#[derive(Clone, Serialize)]
struct CloseConfirmPayload {
    preference: String,
}

#[tauri::command]
async fn get_api_base_url(state: State<'_, AppState>) -> Result<Option<String>, String> {
    for _ in 0..100 {
        if let Some(url) = state.api_base_url.lock().map_err(|e| e.to_string())?.clone() {
            return Ok(Some(url));
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    Ok(None)
}

#[tauri::command]
fn get_close_preference(state: State<'_, AppState>) -> Result<String, String> {
    let pref = *state.close_preference.lock().map_err(|e| e.to_string())?;
    Ok(pref.as_str().to_string())
}

#[tauri::command]
fn set_close_preference(
    preference: String,
    state: State<'_, AppState>,
    app: AppHandle,
) -> Result<String, String> {
    let requested = ClosePreference::parse(&preference)?;
    let effective = normalize_close_preference(requested, state.tray_available);
    persist_close_preference(&app, effective)?;
    *state.close_preference.lock().map_err(|e| e.to_string())? = effective;
    Ok(effective.as_str().to_string())
}

#[tauri::command]
fn resolve_close_action(
    action: String,
    remember: bool,
    state: State<'_, AppState>,
    app: AppHandle,
) -> Result<String, String> {
    let requested = ClosePreference::parse(&action)?;
    let effective = normalize_close_preference(requested, state.tray_available);
    if remember {
        persist_close_preference(&app, effective)?;
        *state.close_preference.lock().map_err(|e| e.to_string())? = effective;
    }
    match effective {
        ClosePreference::Ask => {}
        ClosePreference::Tray => hide_main_window(&app)?,
        ClosePreference::Exit => {
            kill_backend_child(&state);
            app.exit(0);
        }
    }
    Ok(effective.as_str().to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_api_base_url,
            get_close_preference,
            set_close_preference,
            resolve_close_action
        ])
        .setup(|app| {
            let tray_available = match build_tray(app.handle()) {
                Ok(value) => value,
                Err(error) => {
                    eprintln!("Failed to initialize tray icon: {error}");
                    false
                }
            };
            let app_state = AppState {
                backend_child: Arc::new(Mutex::new(None)),
                api_base_url: Arc::new(Mutex::new(None)),
                close_preference: Arc::new(Mutex::new(
                    load_close_preference(app.handle(), tray_available),
                )),
                tray_available,
            };

            // Start backend sidecar
            #[cfg(not(debug_assertions))]
            {
                let backend_child_clone = app_state.backend_child.clone();
                let api_base_url_clone = app_state.api_base_url.clone();
                let app_handle = app.handle().clone();

                tauri::async_runtime::spawn(async move {
                    match app_handle.shell().sidecar("writer-backend") {
                        Ok(cmd) => {
                            match cmd.spawn() {
                                Ok((mut rx, child)) => {
                                    println!("Backend started");
                                    *backend_child_clone.lock().unwrap() = Some(child);
                                    while let Some(event) = rx.recv().await {
                                        if let CommandEvent::Stdout(bytes) = event {
                                            let text = String::from_utf8_lossy(&bytes);
                                            for line in text.lines() {
                                                if let Some(port) = line.strip_prefix("WRITER_PORT=") {
                                                    let url = format!("http://127.0.0.1:{}", port.trim());
                                                    *api_base_url_clone.lock().unwrap() = Some(url);
                                                }
                                            }
                                        }
                                    }
                                }
                                Err(e) => eprintln!("Failed to spawn backend: {}", e),
                            }
                        }
                        Err(e) => eprintln!("Failed to get sidecar command: {}", e),
                    }
                });
            }

            #[cfg(debug_assertions)]
            {
                *app_state.api_base_url.lock().unwrap() = Some("http://127.0.0.1:8000".to_string());
            }

            app.manage(app_state);
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                if let Some(app_state) = window.try_state::<AppState>() {
                    let preference = app_state
                        .close_preference
                        .lock()
                        .map(|pref| *pref)
                        .unwrap_or(ClosePreference::Exit);
                    match normalize_close_preference(preference, app_state.tray_available) {
                        ClosePreference::Ask => {
                            api.prevent_close();
                            let _ = window.emit(
                                "writer-confirm-close",
                                CloseConfirmPayload {
                                    preference: ClosePreference::Ask.as_str().to_string(),
                                },
                            );
                        }
                        ClosePreference::Tray => {
                            api.prevent_close();
                            let _ = window.hide();
                        }
                        ClosePreference::Exit => {
                            kill_backend_child(&app_state);
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

impl ClosePreference {
    fn parse(value: &str) -> Result<Self, String> {
        match value.trim().to_ascii_lowercase().as_str() {
            "ask" => Ok(Self::Ask),
            "tray" => Ok(Self::Tray),
            "exit" => Ok(Self::Exit),
            _ => Err(format!("Unknown close preference: {value}")),
        }
    }

    fn as_str(self) -> &'static str {
        match self {
            Self::Ask => "ask",
            Self::Tray => "tray",
            Self::Exit => "exit",
        }
    }
}

fn normalize_close_preference(preference: ClosePreference, tray_available: bool) -> ClosePreference {
    if preference == ClosePreference::Tray && !tray_available {
        ClosePreference::Exit
    } else {
        preference
    }
}

fn preferences_path(app: &AppHandle) -> Result<PathBuf, String> {
    let base = app
        .path()
        .app_config_dir()
        .map_err(|e| format!("Failed to resolve app config dir: {e}"))?;
    Ok(base.join("ui-preferences.json"))
}

fn load_close_preference(app: &AppHandle, tray_available: bool) -> ClosePreference {
    let path = match preferences_path(app) {
        Ok(path) => path,
        Err(_) => return normalize_close_preference(ClosePreference::Ask, tray_available),
    };
    let raw = fs::read_to_string(path).ok();
    let loaded = raw
        .as_deref()
        .and_then(|body| serde_json::from_str::<serde_json::Value>(body).ok())
        .and_then(|json| {
            json.get("close_preference")
                .and_then(|value| value.as_str())
                .map(str::to_owned)
        })
        .and_then(|value| ClosePreference::parse(&value).ok())
        .unwrap_or(ClosePreference::Ask);
    normalize_close_preference(loaded, tray_available)
}

fn persist_close_preference(app: &AppHandle, preference: ClosePreference) -> Result<(), String> {
    let path = preferences_path(app)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("Failed to create config dir: {e}"))?;
    }
    let payload = serde_json::json!({
        "close_preference": preference.as_str(),
    });
    fs::write(
        path,
        serde_json::to_vec_pretty(&payload).map_err(|e| format!("Failed to serialize preferences: {e}"))?,
    )
    .map_err(|e| format!("Failed to write preferences: {e}"))?;
    Ok(())
}

fn hide_window(window: &tauri::WebviewWindow) -> Result<(), String> {
    window.hide().map_err(|e| format!("Failed to hide window: {e}"))
}

fn hide_main_window(app: &AppHandle) -> Result<(), String> {
    let window = app
        .get_webview_window("main")
        .ok_or_else(|| "Main window not found".to_string())?;
    hide_window(&window)
}

fn show_main_window(app: &AppHandle) -> Result<(), String> {
    let window = app
        .get_webview_window("main")
        .ok_or_else(|| "Main window not found".to_string())?;
    if window.is_minimized().unwrap_or(false) {
        let _ = window.unminimize();
    }
    window.show().map_err(|e| format!("Failed to show window: {e}"))?;
    window
        .set_focus()
        .map_err(|e| format!("Failed to focus window: {e}"))?;
    Ok(())
}

fn kill_backend_child(state: &AppState) {
    if let Ok(mut child) = state.backend_child.lock() {
        if let Some(backend) = child.take() {
            let _ = backend.kill();
            println!("Backend terminated");
        }
    }
}

fn build_tray(app: &AppHandle) -> Result<bool, tauri::Error> {
    let icon = match app.default_window_icon().cloned() {
        Some(icon) => icon,
        None => return Ok(false),
    };
    let menu = MenuBuilder::new(app)
        .text("show", "打开 Writer")
        .text("exit", "退出")
        .build()?;
    let app_handle = app.clone();
    let tray = TrayIconBuilder::with_id("writer-main-tray")
        .icon(icon)
        .menu(&menu)
        .tooltip("Writer")
        .show_menu_on_left_click(false)
        .on_menu_event(move |app, event: MenuEvent| match event.id().as_ref() {
            "show" => {
                let _ = show_main_window(app);
            }
            "exit" => {
                if let Some(state) = app.try_state::<AppState>() {
                    kill_backend_child(&state);
                }
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(move |_tray, event| {
            if matches!(
                event,
                TrayIconEvent::Click {
                    button: MouseButton::Left,
                    button_state: MouseButtonState::Up,
                    ..
                }
            ) || matches!(
                event,
                TrayIconEvent::DoubleClick {
                    button: MouseButton::Left,
                    ..
                }
            ) {
                let _ = show_main_window(&app_handle);
            }
        })
        .build(app)?;
    tray.set_visible(true)?;
    Ok(true)
}
