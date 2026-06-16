# Writer Tauri MVP

Writer 的 Tauri 版本正在把桌面端迁移到更轻量的 Vue + FastAPI + Tauri 架构。当前版本与现有 Writer 数据库共享数据，方便在不丢失旧内容的前提下验证新界面。

## 功能

- **文章写作**：文章列表、正文编辑、自动保存、全文搜索、查找替换、标签、统计与右侧上下文栏；专注模式可隐藏所有辅助界面，只保留正文写作区。
- **题记编辑**：文章开头题记会独立显示和编辑，Markdown / DOCX 导出会按题记样式排版。
- **文章导出**：单篇文章支持导出 Markdown / TXT / DOCX。
- **作品集**：创建合集、批量加入文章、拖拽调整阅读顺序、预览正文，并按顺序导出 Markdown / TXT / DOCX。
- **AI 工作台**：工具页支持润色、扩写、续写、摘要、大纲、标题等任务；对话页支持围绕全局、单篇文章或作品集持续讨论。
- **AI 配置**：支持 OpenAI 兼容接口、Codex 本地登录、Gemini API、本地 Gemini 配置和 Gemini CLI / OAuth；只保存凭据来源，不保存明文 API Key。
- **AI Card**：内置作家风格样例，用户可新建、编辑、删除风格卡、角色卡和场景卡，并按类型、来源、关键词和排序方式筛选。
- **文脉标本库**：管理摘录、出处、用途类型和标签；支持按书籍或按用途浏览，并可复制正文或带出处的完整引用。
- **日期视图**：按日期浏览文章和每日统计；每日精句可跳转到文脉库对应标本；空日期可一键开始写作。
- **备份与检查点**：创建备份、检查点并支持恢复。
- **关闭行为**：可选择关闭窗口时直接退出、每次询问或最小化到系统托盘。
- **桌面打包**：Release 包内置 Python 后端 sidecar，启动应用时自动启动后端。

## 开发运行

```powershell
# 后端
cd tauri-mvp\backend
$env:WRITER_USE_DEV_DB = "1"
D:\anaconda\envs\writer\python.exe run.py --dev

# 前端
cd tauri-mvp\frontend
npm install
npm run dev
```

开发模式默认连接 `http://127.0.0.1:8000`。Release 模式由 Tauri sidecar 自动分配后端端口，前端会通过 Tauri command 获取真实 API 地址。

## 构建

```powershell
cd tauri-mvp
.\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe
```

脚本会先构建 Python 后端 sidecar，再复制到 Tauri `externalBin` 目录，最后生成 Windows 安装包。后端 sidecar 位于：

```text
tauri-mvp\frontend\src-tauri\binaries\writer-backend-x86_64-pc-windows-msvc.exe
```

Windows 安装包输出位置：

```text
tauri-mvp\frontend\src-tauri\target\release\bundle\nsis\
tauri-mvp\frontend\src-tauri\target\release\bundle\msi\
```

## 验证

```powershell
D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py
D:\anaconda\envs\writer\python.exe -m pytest
cd tauri-mvp\frontend
npm test
npm run build
cargo check --manifest-path src-tauri\Cargo.toml
```

核心 smoke 覆盖：

- 每日精句返回完整文脉标本并可深链定位。
- 单篇文章导出支持 TXT / Markdown / DOCX，题记不会在 Markdown / DOCX 中重复。
- AI scoped 对话能按文章或作品集恢复同一条会话。
- AI 设置会保存到后端配置，并支持 OpenAI / Gemini / Gemini CLI 凭据来源检查。
- AI Card 内置样例不会重复生成，CRUD 和筛选数据正常。
- 作品集可以加入文章、重排、查询文章所属作品集、导出和移除文章。
- 前端 TypeScript/Vite 构建通过。
- Tauri Rust sidecar 编译通过。

## 更新记录与计划

- [CHANGELOG](CHANGELOG.md)
- [公开 TODO](docs/TODO.md)

## 数据

默认使用现有 Writer 数据目录。开发测试建议设置：

```powershell
$env:WRITER_USE_DEV_DB = "1"
```

这样会使用 `tauri-mvp\backend\.data\writer.sqlite3`，避免影响真实写作数据库。
