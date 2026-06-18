// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::{env, fs};
use std::path::{Path, PathBuf};
use std::process::Command as StdCommand;
use tauri::State;
use tauri::{
    menu::MenuEvent,
    menu::MenuBuilder,
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    webview::PageLoadEvent,
    AppHandle, Emitter, Listener, Manager, WindowEvent,
};
use tauri::utils::config::Color;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::ShellExt;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::process::CommandEvent;
#[cfg(target_os = "windows")]
use std::sync::{mpsc, OnceLock};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use std::time::{Duration, Instant};
#[cfg(target_os = "windows")]
use windows_sys::Win32::{
    Foundation::{COLORREF, HWND, LPARAM, LRESULT, RECT, WPARAM},
    Graphics::Gdi::{
        BeginPaint, CreateFontW, CreatePen, CreateSolidBrush, DeleteObject, DrawTextW, EndPaint,
        FillRect, InvalidateRect, Rectangle, SelectObject, SetBkMode, SetTextColor, TextOutW,
        UpdateWindow, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
        DEFAULT_CHARSET, DEFAULT_PITCH, DT_END_ELLIPSIS, DT_LEFT, DT_NOPREFIX, DT_SINGLELINE,
        DT_TOP, DT_WORDBREAK, FF_SWISS, FW_NORMAL, FW_SEMIBOLD, HGDIOBJ, OUT_DEFAULT_PRECIS,
        PAINTSTRUCT, PS_SOLID, TRANSPARENT,
    },
    System::LibraryLoader::GetModuleHandleW,
    UI::WindowsAndMessaging::{
        CreateWindowExW, DefWindowProcW, DestroyWindow, DispatchMessageW, GetSystemMetrics,
        KillTimer, LoadCursorW, PeekMessageW, PostQuitMessage, RegisterClassW, SetTimer,
        ShowWindow, TranslateMessage, CS_HREDRAW, CS_VREDRAW, IDC_ARROW, MSG, PM_REMOVE,
        SM_CXSCREEN, SM_CYSCREEN, SW_SHOW, WM_DESTROY, WM_PAINT, WM_TIMER, WNDCLASSW,
        WS_EX_TOOLWINDOW, WS_EX_TOPMOST, WS_POPUP, WS_VISIBLE,
    },
};
#[cfg(target_os = "windows")]
use windows_sys::Win32::UI::WindowsAndMessaging::{
    MessageBoxW, IDNO, IDYES, MB_ICONQUESTION, MB_TASKMODAL, MB_YESNOCANCEL,
};

#[derive(Clone)]
struct AppState {
    backend_child: Arc<Mutex<Option<tauri_plugin_shell::process::CommandChild>>>,
    api_base_url: Arc<Mutex<Option<String>>>,
    close_preference: Arc<Mutex<ClosePreference>>,
    data_directory: Arc<Mutex<DataDirectoryOverrideState>>,
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

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
struct DataLocationConfig {
    data_dir: Option<String>,
}

#[derive(Clone, Debug, Default, Serialize)]
struct DataDirectoryOverrideState {
    override_path: Option<String>,
    active_path: Option<String>,
    warning: Option<String>,
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
fn choose_data_directory() -> Result<Option<String>, String> {
    Ok(rfd::FileDialog::new()
        .set_title("选择活着为了讲述数据目录")
        .pick_folder()
        .map(|path| path.to_string_lossy().to_string()))
}

#[tauri::command]
fn choose_export_file(default_filename: String, format: String) -> Result<Option<String>, String> {
    let extension = export_extension(&format).unwrap_or("txt");
    let mut dialog = rfd::FileDialog::new()
        .set_title("导出文件")
        .set_file_name(sanitize_export_filename(&default_filename, extension));

    dialog = match extension {
        "md" => dialog.add_filter("Markdown", &["md"]),
        "txt" => dialog.add_filter("Text", &["txt"]),
        "docx" => dialog.add_filter("Word Document", &["docx"]),
        _ => dialog.add_filter("File", &[extension]),
    };

    Ok(dialog
        .save_file()
        .map(|path| ensure_export_extension(path, extension).to_string_lossy().to_string()))
}

#[tauri::command]
fn write_export_file(path: String, bytes: Vec<u8>) -> Result<(), String> {
    let target = PathBuf::from(path.trim());
    if target.as_os_str().is_empty() {
        return Err("Export path is empty".to_string());
    }
    if let Some(parent) = target.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create export directory: {e}"))?;
        }
    }
    fs::write(&target, bytes).map_err(|e| format!("Failed to write export file: {e}"))
}

fn export_extension(format: &str) -> Option<&'static str> {
    match format.trim().to_ascii_lowercase().as_str() {
        "md" | "markdown" => Some("md"),
        "txt" | "text" => Some("txt"),
        "docx" => Some("docx"),
        _ => None,
    }
}

fn sanitize_export_filename(filename: &str, extension: &str) -> String {
    let mut safe = filename
        .chars()
        .map(|ch| match ch {
            '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*' => '_',
            _ => ch,
        })
        .collect::<String>()
        .trim()
        .trim_matches('.')
        .to_string();
    if safe.is_empty() {
        safe = format!("export.{extension}");
    }
    if Path::new(&safe).extension().is_none() {
        safe.push('.');
        safe.push_str(extension);
    }
    safe
}

fn ensure_export_extension(mut path: PathBuf, extension: &str) -> PathBuf {
    if path.extension().is_none() {
        path.set_extension(extension);
    }
    path
}

#[tauri::command]
fn open_path(path: String) -> Result<(), String> {
    let target = PathBuf::from(path.trim());
    if target.as_os_str().is_empty() {
        return Err("Path is empty".to_string());
    }
    if !target.exists() {
        return Err(format!("Path does not exist: {}", target.display()));
    }
    open_path_with_system(&target)
}

#[tauri::command]
fn get_data_directory_override(
    state: State<'_, AppState>,
) -> Result<DataDirectoryOverrideState, String> {
    Ok(state.data_directory.lock().map_err(|e| e.to_string())?.clone())
}

#[tauri::command]
fn set_data_directory_override(
    path: String,
    state: State<'_, AppState>,
    app: AppHandle,
) -> Result<DataDirectoryOverrideState, String> {
    let next = validate_data_directory_override(Some(path))?;
    persist_data_location_config(&app, next.active_path.clone())?;
    *state.data_directory.lock().map_err(|e| e.to_string())? = next.clone();
    Ok(next)
}

#[tauri::command]
fn clear_data_directory_override(
    state: State<'_, AppState>,
    app: AppHandle,
) -> Result<DataDirectoryOverrideState, String> {
    persist_data_location_config(&app, None)?;
    let next = DataDirectoryOverrideState::default();
    *state.data_directory.lock().map_err(|e| e.to_string())? = next.clone();
    Ok(next)
}

#[tauri::command]
fn restart_app(state: State<'_, AppState>, app: AppHandle) -> Result<(), String> {
    kill_backend_child(&state);
    app.request_restart();
    Ok(())
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

fn data_location_config_path(app: &AppHandle) -> Result<PathBuf, String> {
    let base = app
        .path()
        .app_config_dir()
        .map_err(|e| format!("Failed to resolve app config dir: {e}"))?;
    Ok(base.join("data-location.json"))
}

fn load_data_directory_override(app: &AppHandle) -> DataDirectoryOverrideState {
    let path = match data_location_config_path(app) {
        Ok(path) => path,
        Err(error) => {
            return DataDirectoryOverrideState {
                warning: Some(error),
                ..Default::default()
            }
        }
    };
    let config = fs::read_to_string(path)
        .ok()
        .and_then(|body| serde_json::from_str::<DataLocationConfig>(&body).ok())
        .unwrap_or_default();
    let configured_path = config.data_dir.clone();
    validate_data_directory_override(config.data_dir)
        .unwrap_or_else(|warning| DataDirectoryOverrideState {
            override_path: configured_path.map(|value| value.trim().to_string()),
            active_path: None,
            warning: Some(warning),
        })
}

fn validate_data_directory_override(
    data_dir: Option<String>,
) -> Result<DataDirectoryOverrideState, String> {
    let Some(raw_path) = data_dir else {
        return Ok(DataDirectoryOverrideState::default());
    };
    let trimmed = raw_path.trim();
    if trimmed.is_empty() {
        return Ok(DataDirectoryOverrideState::default());
    }
    let path = PathBuf::from(trimmed);
    if !path.is_absolute() {
        return Err(format!("Custom data directory must be absolute: {trimmed}"));
    }
    if path.exists() && !path.is_dir() {
        return Err(format!("Custom data directory is not a directory: {}", path.display()));
    }
    if let Err(error) = fs::create_dir_all(&path) {
        return Err(format!(
            "Custom data directory is unavailable, using the default location for this launch: {error}"
        ));
    }
    let probe = path.join(".living-to-tell-write-test");
    if let Err(error) = fs::write(&probe, b"ok") {
        return Err(format!(
            "Custom data directory is not writable, using the default location for this launch: {error}"
        ));
    }
    let _ = fs::remove_file(probe);
    let canonical = path.canonicalize().unwrap_or(path);
    let active = canonical.to_string_lossy().to_string();
    Ok(DataDirectoryOverrideState {
        override_path: Some(active.clone()),
        active_path: Some(active),
        warning: None,
    })
}

fn persist_data_location_config(
    app: &AppHandle,
    data_dir: Option<String>,
) -> Result<(), String> {
    let path = data_location_config_path(app)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("Failed to create config dir: {e}"))?;
    }
    if let Some(data_dir) = data_dir {
        let payload = DataLocationConfig {
            data_dir: Some(data_dir),
        };
        fs::write(
            path,
            serde_json::to_vec_pretty(&payload)
                .map_err(|e| format!("Failed to serialize data location: {e}"))?,
        )
        .map_err(|e| format!("Failed to write data location: {e}"))?;
    } else if path.exists() {
        fs::remove_file(path).map_err(|e| format!("Failed to clear data location: {e}"))?;
    }
    Ok(())
}

fn open_path_with_system(path: &Path) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    let mut command = {
        let mut command = StdCommand::new("explorer");
        command.arg(path);
        command
    };
    #[cfg(target_os = "macos")]
    let mut command = {
        let mut command = StdCommand::new("open");
        command.arg(path);
        command
    };
    #[cfg(all(unix, not(target_os = "macos")))]
    let mut command = {
        let mut command = StdCommand::new("xdg-open");
        command.arg(path);
        command
    };
    command
        .spawn()
        .map_err(|e| format!("Failed to open path: {e}"))?;
    Ok(())
}

#[cfg(target_os = "windows")]
fn show_data_directory_warning(state: &DataDirectoryOverrideState) {
    let Some(warning) = &state.warning else {
        return;
    };
    let body = format!("{warning}\n\n原自定义目录没有被删除。");
    let title = "数据目录不可用";
    let body_wide: Vec<u16> = body.encode_utf16().chain(std::iter::once(0)).collect();
    let title_wide: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();
    unsafe {
        MessageBoxW(
            std::ptr::null_mut(),
            body_wide.as_ptr(),
            title_wide.as_ptr(),
            MB_ICONQUESTION | MB_TASKMODAL,
        );
    }
}

#[cfg(not(target_os = "windows"))]
fn show_data_directory_warning(state: &DataDirectoryOverrideState) {
    if let Some(warning) = &state.warning {
        eprintln!("{warning}");
    }
}

#[cfg(all(target_os = "windows", not(debug_assertions)))]
fn terminate_stale_backend_processes() {
    let _ = StdCommand::new("cmd")
        .args([
            "/C",
            "taskkill /F /T /IM living-to-tell-backend.exe >NUL 2>NUL",
        ])
        .status();
    std::thread::sleep(Duration::from_millis(350));
}

#[cfg(target_os = "windows")]
static NATIVE_SPLASH_STARTED_AT: OnceLock<Instant> = OnceLock::new();

#[cfg(target_os = "windows")]
#[derive(Clone)]
struct NativeSplashHandle {
    close_requested: Arc<AtomicBool>,
}

#[cfg(not(target_os = "windows"))]
#[derive(Clone)]
struct NativeSplashHandle;

#[cfg(target_os = "windows")]
fn spawn_native_startup_splash(startup_at: Instant) -> Option<NativeSplashHandle> {
    let close_requested = Arc::new(AtomicBool::new(false));
    let thread_close_requested = close_requested.clone();
    let (ready_tx, ready_rx) = mpsc::channel();

    std::thread::spawn(move || {
        let _ = NATIVE_SPLASH_STARTED_AT.set(startup_at);
        run_native_splash_window(thread_close_requested, startup_at, ready_tx);
    });

    match ready_rx.recv_timeout(Duration::from_millis(700)) {
        Ok(false) => None,
        Ok(true) => Some(NativeSplashHandle { close_requested }),
        Err(_) => Some(NativeSplashHandle { close_requested }),
    }
}

#[cfg(not(target_os = "windows"))]
fn spawn_native_startup_splash(_startup_at: Instant) -> Option<NativeSplashHandle> {
    None
}

#[cfg(target_os = "windows")]
fn close_native_startup_splash(handle: &Option<NativeSplashHandle>) {
    if let Some(handle) = handle {
        handle.close_requested.store(true, Ordering::Release);
    }
}

#[cfg(not(target_os = "windows"))]
fn close_native_startup_splash(_handle: &Option<NativeSplashHandle>) {}

#[cfg(target_os = "windows")]
fn run_native_splash_window(
    close_requested: Arc<AtomicBool>,
    startup_at: Instant,
    ready_tx: mpsc::Sender<bool>,
) {
    unsafe {
        let instance = GetModuleHandleW(std::ptr::null());
        let class_name = wide_null("LivingToTellNativeStartupSplash");
        let title = wide_null("活着为了讲述");
        let window_class = WNDCLASSW {
            style: CS_HREDRAW | CS_VREDRAW,
            lpfnWndProc: Some(native_splash_wnd_proc),
            cbClsExtra: 0,
            cbWndExtra: 0,
            hInstance: instance,
            hIcon: std::ptr::null_mut(),
            hCursor: LoadCursorW(std::ptr::null_mut(), IDC_ARROW),
            hbrBackground: std::ptr::null_mut(),
            lpszMenuName: std::ptr::null(),
            lpszClassName: class_name.as_ptr(),
        };
        let _ = RegisterClassW(&window_class);

        let width = 560;
        let height = 360;
        let screen_width = GetSystemMetrics(SM_CXSCREEN);
        let screen_height = GetSystemMetrics(SM_CYSCREEN);
        let x = (screen_width - width).max(0) / 2;
        let y = (screen_height - height).max(0) / 2;
        let hwnd = CreateWindowExW(
            WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
            class_name.as_ptr(),
            title.as_ptr(),
            WS_POPUP | WS_VISIBLE,
            x,
            y,
            width,
            height,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            instance,
            std::ptr::null(),
        );
        if hwnd.is_null() {
            eprintln!("[startup] native_splash_create_failed");
            let _ = ready_tx.send(false);
            return;
        }

        SetTimer(hwnd, 1, 33, None);
        ShowWindow(hwnd, SW_SHOW);
        UpdateWindow(hwnd);
        log_startup(startup_at, "native_splash_shown");
        let _ = ready_tx.send(true);

        let mut destroyed = false;
        let mut msg: MSG = std::mem::zeroed();
        loop {
            while PeekMessageW(&mut msg, std::ptr::null_mut(), 0, 0, PM_REMOVE) != 0 {
                if msg.message == WM_DESTROY {
                    destroyed = true;
                }
                TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
            if close_requested.load(Ordering::Acquire) && !destroyed {
                DestroyWindow(hwnd);
                destroyed = true;
            }
            if destroyed {
                break;
            }
            std::thread::sleep(Duration::from_millis(16));
        }
    }
}

#[cfg(target_os = "windows")]
unsafe extern "system" fn native_splash_wnd_proc(
    hwnd: HWND,
    msg: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    match msg {
        WM_PAINT => {
            paint_native_splash(hwnd);
            0
        }
        WM_TIMER => {
            InvalidateRect(hwnd, std::ptr::null(), 0);
            0
        }
        WM_DESTROY => {
            KillTimer(hwnd, 1);
            PostQuitMessage(0);
            0
        }
        _ => DefWindowProcW(hwnd, msg, wparam, lparam),
    }
}

#[cfg(target_os = "windows")]
unsafe fn paint_native_splash(hwnd: HWND) {
    let mut paint: PAINTSTRUCT = std::mem::zeroed();
    let hdc = BeginPaint(hwnd, &mut paint);
    if hdc.is_null() {
        return;
    }

    let background = CreateSolidBrush(rgb(248, 250, 252));
    FillRect(hdc, &paint.rcPaint, background);
    DeleteObject(background as HGDIOBJ);
    SetBkMode(hdc, TRANSPARENT as i32);

    let accent = rgb(45, 127, 249);
    let ink = rgb(31, 41, 51);
    let muted = rgb(101, 115, 133);
    let body = rgb(57, 73, 92);

    let mark_bg = CreateSolidBrush(rgb(255, 255, 255));
    let mark_rect = RECT {
        left: 52,
        top: 44,
        right: 92,
        bottom: 84,
    };
    FillRect(hdc, &mark_rect, mark_bg);
    DeleteObject(mark_bg as HGDIOBJ);

    let border_pen = CreatePen(PS_SOLID, 1, rgb(220, 228, 238));
    let old_pen = SelectObject(hdc, border_pen as HGDIOBJ);
    Rectangle(hdc, 52, 44, 92, 84);
    SelectObject(hdc, old_pen);
    DeleteObject(border_pen as HGDIOBJ);

    let mark_font = create_native_font(22, FW_SEMIBOLD as i32);
    let old_font = SelectObject(hdc, mark_font as HGDIOBJ);
    SetTextColor(hdc, accent);
    draw_text_line(hdc, 61, 52, "讲");
    SelectObject(hdc, old_font);
    DeleteObject(mark_font as HGDIOBJ);

    let title_font = create_native_font(30, FW_SEMIBOLD as i32);
    let old_font = SelectObject(hdc, title_font as HGDIOBJ);
    SetTextColor(hdc, ink);
    draw_text_line(hdc, 52, 108, "活着为了讲述");
    SelectObject(hdc, old_font);
    DeleteObject(title_font as HGDIOBJ);

    let small_font = create_native_font(13, FW_NORMAL as i32);
    let old_font = SelectObject(hdc, small_font as HGDIOBJ);
    SetTextColor(hdc, muted);
    draw_text_line(hdc, 52, 150, "Living to Tell");

    SetTextColor(hdc, body);
    let mut slogan_rect = RECT {
        left: 52,
        top: 184,
        right: 462,
        bottom: 248,
    };
    draw_text_block(
        hdc,
        "写作、拍照、唱歌、讲话，都是为了讲述。活着，就是为了讲述。",
        &mut slogan_rect,
        DT_LEFT | DT_TOP | DT_WORDBREAK | DT_NOPREFIX,
    );

    draw_progress_bar(hdc);

    SetTextColor(hdc, rgb(88, 103, 122));
    let status = if native_splash_elapsed().as_secs() >= 5 {
        "正在启动后台服务..."
    } else {
        "正在打开写作空间..."
    };
    let mut status_rect = RECT {
        left: 178,
        top: 302,
        right: 508,
        bottom: 326,
    };
    draw_text_block(
        hdc,
        status,
        &mut status_rect,
        DT_LEFT | DT_TOP | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX,
    );

    SelectObject(hdc, old_font);
    DeleteObject(small_font as HGDIOBJ);
    EndPaint(hwnd, &paint);
}

#[cfg(target_os = "windows")]
unsafe fn draw_progress_bar(hdc: windows_sys::Win32::Graphics::Gdi::HDC) {
    let track_rect = RECT {
        left: 52,
        top: 310,
        right: 164,
        bottom: 314,
    };
    let track_brush = CreateSolidBrush(rgb(212, 228, 255));
    FillRect(hdc, &track_rect, track_brush);
    DeleteObject(track_brush as HGDIOBJ);

    let elapsed = native_splash_elapsed().as_millis() as i32;
    let cycle = 1180;
    let phase = elapsed % cycle;
    let travel = 112 + 46;
    let x = 52 - 42 + (phase * travel / cycle);
    let fill_rect = RECT {
        left: x.clamp(52, 164),
        top: 310,
        right: (x + 46).clamp(52, 164),
        bottom: 314,
    };
    if fill_rect.right > fill_rect.left {
        let fill_brush = CreateSolidBrush(rgb(45, 127, 249));
        FillRect(hdc, &fill_rect, fill_brush);
        DeleteObject(fill_brush as HGDIOBJ);
    }
}

#[cfg(target_os = "windows")]
unsafe fn create_native_font(point_size: i32, weight: i32) -> windows_sys::Win32::Graphics::Gdi::HFONT {
    let face = wide_null("Microsoft YaHei UI");
    CreateFontW(
        -point_size,
        0,
        0,
        0,
        weight,
        0,
        0,
        0,
        DEFAULT_CHARSET as u32,
        OUT_DEFAULT_PRECIS as u32,
        CLIP_DEFAULT_PRECIS as u32,
        CLEARTYPE_QUALITY as u32,
        (DEFAULT_PITCH | FF_SWISS) as u32,
        face.as_ptr(),
    )
}

#[cfg(target_os = "windows")]
unsafe fn draw_text_line(hdc: windows_sys::Win32::Graphics::Gdi::HDC, x: i32, y: i32, text: &str) {
    let wide = wide_text(text);
    TextOutW(hdc, x, y, wide.as_ptr(), wide.len() as i32);
}

#[cfg(target_os = "windows")]
unsafe fn draw_text_block(
    hdc: windows_sys::Win32::Graphics::Gdi::HDC,
    text: &str,
    rect: &mut RECT,
    format: u32,
) {
    let wide = wide_text(text);
    DrawTextW(hdc, wide.as_ptr(), wide.len() as i32, rect, format);
}

#[cfg(target_os = "windows")]
fn native_splash_elapsed() -> Duration {
    NATIVE_SPLASH_STARTED_AT
        .get()
        .map(Instant::elapsed)
        .unwrap_or_default()
}

#[cfg(target_os = "windows")]
fn wide_text(value: &str) -> Vec<u16> {
    value.encode_utf16().collect()
}

#[cfg(target_os = "windows")]
fn wide_null(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(std::iter::once(0)).collect()
}

#[cfg(target_os = "windows")]
fn rgb(red: u8, green: u8, blue: u8) -> COLORREF {
    red as u32 | ((green as u32) << 8) | ((blue as u32) << 16)
}

fn startup_background_color() -> Color {
    Color(248, 250, 252, 255)
}

fn log_startup(start: Instant, label: &str) {
    println!("[startup] {label}={}ms", start.elapsed().as_millis());
}

fn apply_startup_window_background(app: &AppHandle) {
    for label in ["main", "splash"] {
        if let Some(window) = app.get_webview_window(label) {
            let _ = window.set_background_color(Some(startup_background_color()));
        }
    }
}

fn close_splash_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("splash") {
        let _ = window.close();
    }
}

fn reveal_main_window(app: &AppHandle, native_splash: &Option<NativeSplashHandle>) {
    if let Err(error) = show_main_window(app) {
        eprintln!("Failed to reveal main window after startup: {error}");
    }
    close_native_startup_splash(native_splash);
    close_splash_window(app);
}

fn reveal_main_window_once(
    app: &AppHandle,
    native_splash: &Option<NativeSplashHandle>,
    revealed: &Arc<AtomicBool>,
    startup_at: Instant,
    label: &str,
) {
    if revealed.swap(true, Ordering::AcqRel) {
        return;
    }
    log_startup(startup_at, label);
    reveal_main_window(app, native_splash);
}

fn install_frontend_ready_handler(
    app: &AppHandle,
    startup_at: Instant,
    native_splash: Option<NativeSplashHandle>,
    startup_revealed: Arc<AtomicBool>,
) {
    let ready_app: AppHandle = app.clone();
    let ready_native_splash = native_splash.clone();
    let ready_revealed = startup_revealed.clone();
    app.listen("frontend_ready", move |_| {
        reveal_main_window_once(
            &ready_app,
            &ready_native_splash,
            &ready_revealed,
            startup_at,
            "frontend_ready",
        );
    });

    let timeout_app: AppHandle = app.clone();
    let timeout_native_splash = native_splash;
    let timeout_revealed = startup_revealed;
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_secs(5));
        if !timeout_revealed.load(Ordering::Acquire) {
            log_startup(startup_at, "frontend_waiting_over_5s");
        }

        std::thread::sleep(Duration::from_secs(10));
        if !timeout_revealed.load(Ordering::Acquire) {
            eprintln!(
                "[startup] frontend_ready was not received after {}ms; revealing main window fallback",
                startup_at.elapsed().as_millis()
            );
            reveal_main_window_once(
                &timeout_app,
                &timeout_native_splash,
                &timeout_revealed,
                startup_at,
                "frontend_ready_timeout_fallback",
            );
        }
    });
}

fn main() {
    let startup_at = Instant::now();
    let native_splash = spawn_native_startup_splash(startup_at);
    let startup_revealed = Arc::new(AtomicBool::new(false));
    let page_load_native_splash = native_splash.clone();
    let page_load_revealed = startup_revealed.clone();
    log_startup(startup_at, "app_start");
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_api_base_url,
            choose_data_directory,
            choose_export_file,
            write_export_file,
            open_path,
            get_data_directory_override,
            set_data_directory_override,
            clear_data_directory_override,
            restart_app,
            get_close_preference,
            set_close_preference,
            resolve_close_action
        ])
        .on_page_load(move |webview, payload| {
            if webview.label() == "main" && matches!(payload.event(), PageLoadEvent::Finished) {
                let app_handle = webview.app_handle().clone();
                reveal_main_window_once(
                    &app_handle,
                    &page_load_native_splash,
                    &page_load_revealed,
                    startup_at,
                    "main_page_load_finished",
                );
            }
        })
        .setup(move |app| {
            log_startup(startup_at, "setup_start");
            apply_startup_window_background(app.handle());
            install_frontend_ready_handler(
                app.handle(),
                startup_at,
                native_splash.clone(),
                startup_revealed.clone(),
            );
            let tray_available = match build_tray(app.handle()) {
                Ok(value) => value,
                Err(error) => {
                    eprintln!("Failed to initialize tray icon: {error}");
                    false
                }
            };
            let data_directory_state = load_data_directory_override(app.handle());
            show_data_directory_warning(&data_directory_state);
            #[cfg(not(debug_assertions))]
            let active_data_dir = data_directory_state.active_path.clone();
            let app_state = AppState {
                backend_child: Arc::new(Mutex::new(None)),
                api_base_url: Arc::new(Mutex::new(None)),
                close_preference: Arc::new(Mutex::new(
                    load_close_preference(app.handle(), tray_available),
                )),
                data_directory: Arc::new(Mutex::new(data_directory_state)),
                tray_available,
            };

            // Start backend sidecar
            #[cfg(not(debug_assertions))]
            {
                #[cfg(target_os = "windows")]
                terminate_stale_backend_processes();

                let backend_child_clone = app_state.backend_child.clone();
                let api_base_url_clone = app_state.api_base_url.clone();
                let app_handle = app.handle().clone();
                let backend_data_dir = active_data_dir.clone();
                let backend_startup_at = startup_at;

                tauri::async_runtime::spawn(async move {
                    match app_handle.shell().sidecar("living-to-tell-backend") {
                        Ok(cmd) => {
                            let cmd = match backend_data_dir {
                                Some(path) => cmd.env("WRITER_DATA_DIR", path),
                                None => cmd,
                            };
                            match cmd.spawn() {
                                Ok((mut rx, child)) => {
                                    println!("Backend started");
                                    *backend_child_clone.lock().unwrap() = Some(child);
                                    let mut logged_port_ready = false;
                                    while let Some(event) = rx.recv().await {
                                        if let CommandEvent::Stdout(bytes) = event {
                                            let text = String::from_utf8_lossy(&bytes);
                                            for line in text.lines() {
                                                if let Some(port) = line.strip_prefix("WRITER_PORT=") {
                                                    let url = format!("http://127.0.0.1:{}", port.trim());
                                                    *api_base_url_clone.lock().unwrap() = Some(url);
                                                    if !logged_port_ready {
                                                        log_startup(backend_startup_at, "backend_port_ready");
                                                        logged_port_ready = true;
                                                    }
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
                log_startup(startup_at, "debug_backend_url_ready");
            }

            app.manage(app_state);
            log_startup(startup_at, "setup_done");
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                if window.label() != "main" {
                    return;
                }
                if let Some(app_state) = window.try_state::<AppState>() {
                    let preference = app_state
                        .close_preference
                        .lock()
                        .map(|pref| *pref)
                        .unwrap_or(ClosePreference::Exit);
                    match normalize_close_preference(preference, app_state.tray_available) {
                        ClosePreference::Ask => {
                            api.prevent_close();
                            match ask_close_action_native(app_state.tray_available) {
                                Some(ClosePreference::Tray) => {
                                    let _ = window.hide();
                                }
                                Some(ClosePreference::Exit) => {
                                    kill_backend_child(&app_state);
                                    window.app_handle().exit(0);
                                }
                                Some(ClosePreference::Ask) | None => {
                                    let payload = CloseConfirmPayload {
                                        preference: ClosePreference::Ask.as_str().to_string(),
                                    };
                                    let _ = window.emit("writer-confirm-close", payload.clone());
                                    let _ = window.app_handle().emit("writer-confirm-close", payload);
                                }
                            }
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

#[cfg(target_os = "windows")]
fn ask_close_action_native(tray_available: bool) -> Option<ClosePreference> {
    let body = if tray_available {
        "活着为了讲述 要最小化到系统托盘吗？\n\n是：最小化到托盘\n否：直接退出\n取消：继续使用"
    } else {
        "活着为了讲述 要退出吗？\n\n是：直接退出\n取消：继续使用"
    };
    let title = "关闭活着为了讲述";
    let body_wide: Vec<u16> = body.encode_utf16().chain(std::iter::once(0)).collect();
    let title_wide: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();
    let answer = unsafe {
        MessageBoxW(
            std::ptr::null_mut(),
            body_wide.as_ptr(),
            title_wide.as_ptr(),
            MB_YESNOCANCEL | MB_ICONQUESTION | MB_TASKMODAL,
        )
    };
    match answer {
        IDYES if tray_available => Some(ClosePreference::Tray),
        IDYES => Some(ClosePreference::Exit),
        IDNO if tray_available => Some(ClosePreference::Exit),
        _ => None,
    }
}

#[cfg(not(target_os = "windows"))]
fn ask_close_action_native(_tray_available: bool) -> Option<ClosePreference> {
    None
}

fn preferences_path(app: &AppHandle) -> Result<PathBuf, String> {
    let base = app
        .path()
        .app_config_dir()
        .map_err(|e| format!("Failed to resolve app config dir: {e}"))?;
    Ok(base.join("ui-preferences.json"))
}

fn legacy_preferences_path() -> Option<PathBuf> {
    env::var_os("APPDATA")
        .map(PathBuf::from)
        .map(|base| base.join("com.writer.desktop").join("ui-preferences.json"))
}

fn copy_legacy_preferences_if_needed(app: &AppHandle) {
    let Ok(path) = preferences_path(app) else {
        return;
    };
    if path.exists() {
        return;
    }
    let Some(legacy_path) = legacy_preferences_path() else {
        return;
    };
    if !legacy_path.exists() {
        return;
    }
    if let Some(parent) = path.parent() {
        if fs::create_dir_all(parent).is_ok() {
            let _ = fs::copy(legacy_path, path);
        }
    }
}

fn load_close_preference(app: &AppHandle, tray_available: bool) -> ClosePreference {
    copy_legacy_preferences_if_needed(app);
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
        .text("show", "打开活着为了讲述")
        .text("exit", "退出")
        .build()?;
    let app_handle = app.clone();
    let tray = TrayIconBuilder::with_id("writer-main-tray")
        .icon(icon)
        .menu(&menu)
        .tooltip("活着为了讲述")
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
