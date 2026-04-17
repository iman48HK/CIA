# CIA — Administrator User Guide

This guide is for accounts with the **admin** role in **Construction Insight Agent (CIA)**. Admins have everything a standard user has, plus controls for **users** and the **ordinance document library**.

See also [`cia-system-infographic.png`](./cia-system-infographic.png) for a high-level architecture diagram.

---

## 1. Admin capabilities overview

| Capability | Where in the app | Notes |
|------------|------------------|--------|
| **User management** | Sidebar → **User Management** (`/admin/users`) | List users, change **role** (`user` / `admin`), toggle **active**. |
| **Ordinance library** | **Ordinance** page | Create/rename/delete **folders**; add/rename/delete **files**; **bulk upload** into a folder. |
| Everything a **user** can do | Dashboard, My Projects, AI Assistant | Same workflows as the [normal user guide](./USER_GUIDE_NORMAL_USER.md). |

**Important:** Public **Sign up** only creates **user** accounts. Promoting someone to **admin** is done on the User Management screen (or via API with an existing admin token).

---

## 2. User Management

### 2.1 Opening the screen

1. Log in as an admin.
2. In the sidebar, select **User Management**.

Non-admins are redirected away from this route.

### 2.2 Managing users

The table lists all users with:

- **Email**
- **Role** — `user` or `admin`
- **Active** — whether the account can log in

**Changing role**

- Use the **Role** dropdown for a user and pick `user` or `admin`.
- The change saves automatically (you may see **Saving…** briefly).

**Disabling or enabling an account**

- Toggle the **Active** checkbox.
- Inactive users receive **403 Account disabled** on login and cannot use the app.

### 2.3 Operational guidance

- Avoid removing the **last active admin** without another way to recover access (for example, database or seed credentials in development).
- When offboarding someone, set **Active** off rather than deleting the row (the default UI does not expose user deletion).
- **Signup** always creates **user** role; grant **admin** only to trusted operators.

---

## 3. Ordinance library administration

Ordinance content is shared: **all authenticated users** can browse and preview. Only **admins** can change the library.

### 3.1 Folders

Admins see extra controls on the **Ordinance** page:

- **Add folder** — supply a unique **code** (short identifier) and a **display name**.
- **Rename folder** — update the display name (code is set at creation).
- **Delete folder** — removes the folder and its associated data per server rules; ensure users are not relying on documents in that folder for active projects.

Standard users only see folders and files for browsing.

### 3.2 Files within a folder

Admins can:

- **Create** a document record (metadata) with a title.
- **Upload files** into a folder (multiple files in one action; each file up to **10 MB**).
- **Rename** a document title.
- **Delete** a document (removes metadata and stored file where applicable).

After updating the library, remind project owners to **refresh ordinance selections** on projects if document IDs changed or documents were removed.

---

## 4. What admins do *not* control in the default app

The following are **not** admin-only in the current application:

- **Other users’ projects, drawings, or project files** — each user owns their own projects; admins do not get a special “view all projects” screen in the default UI.
- **AI model or API keys** — configured on the **backend** (environment / `.env`), not in the web UI.
- **Report file storage** — generated reports live under server storage paths; maintenance (cleanup, backups) is a deployment concern.

---

## 5. Environment and dependencies (for whoever runs the server)

Admins should coordinate with operators on:

| Setting / dependency | Effect |
|----------------------|--------|
| `OPENROUTER_API_KEY` | Required for **AI Assistant** chat and for **Quick Report** preset regeneration paths that call the model. |
| `OPENROUTER_MODEL` / fallback model | Which models are used (see backend config). |
| CORS / frontend URL | Must allow the browser origin to call the API. |
| Database and `storage/` directories | Persist users, projects, uploads, ordinance files, and generated reports. |

Refer to backend `README` or deployment docs if present in your fork.

---

## 6. Security practices

- Use **strong passwords** for admin accounts; enforce password updates via profile as needed.
- **Deactivate** instead of sharing one admin account across many people; assign each person their own user, then **promote** only as needed.
- **Ordinance uploads** may contain sensitive or licensed material; restrict admin role accordingly.

---

## 7. Related documentation

- [User Guide — Standard Users](./USER_GUIDE_NORMAL_USER.md) — Dashboard, projects, assistant, reports, and ordinance **browsing**.
