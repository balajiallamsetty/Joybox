# Export Google Stitch UI Designs into This Project

Your original Stitch exports were not attached to this chat, so this starter includes folders and a workflow rather than inventing your design files.

## Workflow
1. Open the project in Google Stitch and select the screen/design.
2. Use the export/share options available in your current Stitch UI. Prefer source/code export if it fits React; otherwise export screenshots and download assets separately.
3. Save originals under `designs/stitch/raw/`, screenshots under `designs/stitch/reference/`, and original assets under `designs/stitch/assets/`.
4. Copy approved production assets (logo, images, illustrations, icons, fonts) into `frontend/public/assets/`.
5. Keep the original export unchanged. Inspect its framework/dependencies before merging code into this React/Vite project.
6. Replace the sample `frontend/src/App.jsx` and CSS with the exported screens, factoring repeated sections into components.
7. Replace placeholder hero artwork with the approved Stitch artwork or authentic venue photos.
8. Check mobile, tablet and desktop layouts; test every button/form; run `npm run build`.

## Suggested folders
```text
designs/stitch/
  raw/        original export/code/archive
  reference/  screenshots of screens
  assets/     exported image/icon/font assets
frontend/public/assets/  approved runtime assets
```

If Stitch exports only screenshots, treat them as visual references and rebuild the interface in React; screenshots are not functional UI. Do not use customer/children photos without permission. Stitch export options can change: attach the export-menu screenshot or exported ZIP/code/assets and I can map the exact contents into this folder.
