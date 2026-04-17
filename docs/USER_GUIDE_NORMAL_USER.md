# CIA — User Guide (Standard Users)

**Construction Insight Agent (CIA)** is a web application for organizing construction projects, browsing ordinance reference documents, and using an AI assistant that is scoped to your project files. This guide is for accounts with the **user** role.

A one-page **system overview graphic** is available as [`cia-system-infographic.png`](./cia-system-infographic.png) in this folder.

---

## 1. Getting started

### 1.1 Sign up and sign in

1. Open the CIA web app in your browser.
2. Use **Sign up** to register with your email and password. New accounts are created as standard **users**.
3. Use **Log in** when you return. Your session uses a secure token stored in the browser.

If you see **Account disabled**, an administrator has deactivated your account; contact your admin.

### 1.2 Main navigation

After you log in, the sidebar includes:

| Area | Purpose |
|------|--------|
| **Dashboard** | Summary counts and shortcuts to recent projects. |
| **My Projects** | Workspace folders, project list, and project detail. |
| **Ordinance** | Browse folders and ordinance documents (view and preview). |
| **AI Assistant** | Project-scoped chat, presets, annotations, and report exports. |

Use **Logout** at the bottom of the sidebar when you finish.

### 1.3 Profile and preferences

- Click your **profile** area in the sidebar to open **Edit Profile**.
- You can update **display name**, **email**, **avatar** (URL, file upload, or camera capture), and **password**.
- Changing password requires your **current password**.
- Use **Light / Dark mode** and **sidebar collapse** as you prefer; these are remembered on your device.

---

## 2. Dashboard

The home page shows:

- Counts for **your** projects, **drawings**, **uploaded project files**, and **total ordinance documents** in the system.
- **Recent projects** with links to each project.

Use the stat cards to jump to **My Projects** or **Ordinance**.

---

## 3. My Projects

### 3.1 Workspace folders

Projects live inside **workspace folders** (for example, by client or site). You can:

- Create new folders.
- Rename folders.
- Delete **empty** folders (folders that still contain projects cannot be deleted until you move or delete those projects).

### 3.2 Creating a project

1. Choose a **workspace folder**.
2. Enter a **project name** and create the project.
3. Open the project from the list to manage files and ordinance selection.

### 3.3 Project detail — what to configure

On a project page you typically:

1. **Upload drawings** — at least one drawing is required before the AI Assistant can run for this project. Supported types include common raster images and PDFs (each file up to **10 MB**).
2. **Upload project files** (optional) — specifications, schedules, photos, PDFs, etc. (same size limit).
3. **Select ordinance documents** — pick one or more documents from the library that apply to this project. The assistant **requires** at least one selected ordinance for that project.
4. Optionally **move** the project to another workspace folder.

You can remove individual drawing or file uploads, preview files, and delete the whole project when no longer needed.

---

## 4. Ordinance (standard user)

Standard users can:

- Browse **folders** and **documents**.
- **Preview** document content when available.

You **cannot** create folders, upload ordinance files, rename library entries, or delete ordinance content; those actions are reserved for **administrators** (see the admin guide).

---

## 5. AI Assistant

The assistant answers in the context of **one selected project** at a time. It uses:

- That project’s **drawings** and **project files** (filenames listed in context).
- The **ordinance documents you selected** for that project.

### 5.1 Before you can chat

The status line under the project selector must show **Ready**. That requires:

- At least **one drawing** uploaded to the project.
- At least **one ordinance document** selected on the project page.

If **OpenRouter** is not configured on the server, chat will not work; your organization must set `OPENROUTER_API_KEY` on the backend.

### 5.2 Chatting

- Type a question and press **Send** (or use Enter as configured).
- Replies are formatted as Markdown (headings, lists, tables).
- **Chat history** for the project is stored in your **browser** (local storage), not only on the server—clearing site data will remove it.

You can **delete** individual exchanges or **clear all chat** for the project.

### 5.3 Preset prompts and Quick Report

- **Preset prompts** are shortcuts you can click to fill or send common questions. You can add your own, remove some, or **reload built-in prompts**.
- **Generate Quick Report** builds a **Standard AI Assistant Report** using your presets, chat history, and any saved annotations, and offers **HTML**, **PDF**, and **Word** downloads.

### 5.4 Annotating drawings

For each **drawing** or annotatable **project file** (image or PDF):

1. Click **Annotate** to open the viewer.
2. Choose **Deficiency** (red) or **Discrepancy** (amber) and click the image to place markers; edit labels as needed.
3. **Save Drawing** attaches the snapshot for reports; **Download PNG** saves a copy locally.

Annotated snapshots for reports are also kept in **browser storage** (per project). Use **Clear saved** if you need to free space.

### 5.5 Custom Report

1. Use the **list / collect** control on a chat exchange to add that prompt and AI reply to the **Custom Report** list.
2. Optionally check **Include Drawing** to append saved annotated images at the end of the report.
3. **Generate Custom Report** runs on the **server**; you can leave the page while it processes. When complete, download **HTML**, **PDF**, or **Word** from the download menu.

Duplicate prompts cannot be collected twice for the same report list unless you remove the existing block first.

### 5.6 Per-exchange downloads

Each chat exchange can be exported as **TXT**, **Markdown**, or **HTML** for your records.

---

## 6. Tips and limitations

- **Privacy:** Projects and uploads are **yours**; other users do not see your project list or files unless your deployment adds sharing (not in the default app).
- **AI accuracy:** Treat outputs as **draft assistance**. Always verify against official drawings and regulations before relying on them for compliance or safety.
- **File size:** Keep each upload under **10 MB** to avoid rejection.
- **Inactive account:** You cannot log in if an admin disables your account.

---

## 7. Who to contact

- **Access or role changes** — administrator.
- **Ordinance library updates** — administrator.
- **AI or report failures** — administrator or whoever maintains server configuration (API keys, models).
