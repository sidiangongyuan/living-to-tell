# Tutorial GIFs

These GIFs are generated from a clean Playwright demo profile, not from real
writing data.

Regenerate them from the repository root:

```powershell
node .\tauri-mvp\scripts\record-tutorials.cjs
```

The script starts or reuses the Vite dev server on `127.0.0.1:1420`, mocks all
backend API responses, captures step frames, and composes GIFs with Python
Pillow. Intermediate frames are deleted after each GIF is written.

The current seven-flow set is:

1. Sample project.
2. Article writing.
3. Collection planning.
4. Reference Library and Motif Star Map.
5. AI profiles and article-edit context.
6. Collection Agent.
7. Export and backup.
