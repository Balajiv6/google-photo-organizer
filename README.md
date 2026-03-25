# google-photos-organizer

A Python tool that automatically organises your Google Photos library by:

1. **Tagging construction photos** — any photo whose filename or description contains a construction-related keyword (or falls within a configured date range) is added to a dedicated album (*Cauvery Nagar Home* by default).
2. **Catching unalbumized photos** — every photo that does not belong to any album is collected into an *Uncategorized* album.

All changes are **non-destructive** (photos are only added to albums, never deleted) and the tool defaults to **dry-run mode**, so you can preview what would happen before committing.

---

## Prerequisites

- **Python 3.8 or later**
- A Google account with Google Photos
- A Google Cloud Platform (GCP) project with the Photos Library API enabled

> **GitHub Pages trigger site:**  
> Once pushed and Pages is enabled, the web UI is live at  
> **https://Balajiv6.github.io/google-photo-organizer/**

---

## GCP Setup (step-by-step)

### 1. Create a GCP project

1. Go to <https://console.cloud.google.com/>.
2. Click **Select a project → New Project**, give it a name (e.g. `photos-organizer`), and click **Create**.

### 2. Enable the Photos Library API

1. In your project, open **APIs & Services → Library**.
2. Search for **Photos Library API** and click **Enable**.

### 3. Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**.
2. Choose **External** and click **Create**.
3. **App information page** — fill in:
   - *App name* (e.g. `photos-organizer`)
   - *User support email* (your Gmail address)
   - *Developer contact information* email at the bottom
   - Click **Save and Continue**.
4. **Scopes page** — leave everything blank, click **Save and Continue**.
5. **Test users page** — this is where most people get stuck:

   > **If you see the page but no "+ Add Users" button:**  
   > Scroll down — the button is below the description text, not at the top.

   > **If the wizard skipped straight to "Summary":**  
   > Go back to **APIs & Services → OAuth consent screen** in the left sidebar.  
   > You will now see the consent screen dashboard. Look for the  
   > **"Test users"** section — it has its own **+ ADD USERS** button  
   > (separate from the wizard). Click it, type your Google account email,  
   > press **Enter**, then click **Save**.

   > **If you only see a "Publish App" button and no test users section:**  
   > Your app may already be in *Testing* status (shown near the top of the  
   > consent screen page). That's correct — stay in Testing. Click the  
   > **"+ ADD USERS"** button that appears under the *Test users* heading.

   Add the Gmail address that owns the Google Photos library you want to organise, then click **Save and Continue** (or **Save**).

6. **Summary page** — click **Back to Dashboard**. You're done with the consent screen.

### 4. Create OAuth Desktop credentials

1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. Select **Desktop app** as the application type and give it a name.
4. Click **Create**, then **Download JSON**.
5. Rename the downloaded file to **`credentials.json`** and place it in the project root directory (alongside `main.py`).

> **Security note:** `credentials.json` contains your app's client secret.  
> Never commit it to source control — add it to `.gitignore`.

---

## Installation

```bash
# Clone or download the project, then:
pip install -r requirements.txt
```

---

## Usage

### Dry run (default — safe preview, no changes made)

```bash
python main.py
```

The first time you run this, a browser window will open asking you to authorise the app with your Google account.  After granting access a `token.json` file is created locally so subsequent runs skip the browser step.

The tool will print a summary of what it *would* do without actually modifying any albums.

### Apply changes

Open `config.py` and set:

```python
DRY_RUN = False
```

Then run:

```bash
python main.py
```

The tool will create the albums (if they don't already exist) and add the identified photos to them.

---

## Customisation

### Keywords (`CONSTRUCTION_KEYWORDS`)

Edit the `CONSTRUCTION_KEYWORDS` list in `config.py` to add or remove terms that identify a construction photo.  Matching is case-insensitive and checks both the filename and the photo's description field.

```python
CONSTRUCTION_KEYWORDS: list[str] = [
    "construction",
    "cement",
    # … add your own terms here
]
```

### Date ranges (`CONSTRUCTION_DATE_RANGES`)

If your construction work happened during known periods you can restrict (or expand) detection to those dates:

```python
CONSTRUCTION_DATE_RANGES: list[tuple[str, str]] = [
    ("2023-01-01", "2023-06-30"),   # first phase
    ("2024-03-15", "2024-09-01"),   # second phase
]
```

Each tuple is an **inclusive** `("YYYY-MM-DD", "YYYY-MM-DD")` range.  
Leave the list empty (the default) to skip date-range filtering and rely on keywords alone.

### Album titles

Change `CONSTRUCTION_ALBUM_TITLE` or `UNCATEGORIZED_ALBUM_TITLE` in `config.py` to use different album names.

---

## File overview

| File | Purpose |
|---|---|
| `config.py` | All user-configurable settings |
| `auth.py` | OAuth 2.0 token lifecycle |
| `albums.py` | Google Photos REST API client |
| `detector.py` | Photo classification heuristics |
| `main.py` | Workflow orchestration entry point |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `FileNotFoundError: credentials.json` | Download OAuth credentials from GCP Console and place `credentials.json` in the project root |
| `Access blocked: … has not completed verification` | Add your Google account as a **test user** on the OAuth consent screen (step 3.5 above) |
| `Token has been expired or revoked` | Delete `token.json` and re-run — a new browser auth flow will start |
| Albums created but photos not appearing | Photos Library API access tokens can take a few minutes to propagate; wait and refresh the Google Photos app |
