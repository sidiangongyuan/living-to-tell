// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, WindowEvent};
use tauri::State;
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

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![get_api_base_url])
        .setup(|app| {
            let app_state = AppState {
                backend_child: Arc::new(Mutex::new(None)),
                api_base_url: Arc::new(Mutex::new(None)),
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
            if let WindowEvent::CloseRequested { .. } = event {
                // Kill backend on window close
                if let Some(app_state) = window.try_state::<AppState>() {
                    if let Ok(mut child) = app_state.backend_child.lock() {
                        if let Some(backend) = child.take() {
                            let _ = backend.kill();
                            println!("Backend terminated");
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
