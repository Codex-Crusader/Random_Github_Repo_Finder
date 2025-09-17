# Random GitHub Repo & Beginner Issues Finder

A small, polished Python desktop app that helps you discover **random GitHub repositories** and **beginner-friendly issues** with one click.  
Built with `tkinter` and the GitHub REST API. Light and dark themes included.

---
## Demo

![github_Repo_random](https://github.com/user-attachments/assets/dfb33312-80dd-4903-8fa0-3306bc7eb54e)

---

## What is this project?
This app is a compact, demonstrable piece you can include in your portfolio to show:
- API integration (GitHub REST API)
- UI/UX considerations (themed Tkinter app)
- Practical automation for open-source contributors (find `good first issue`s)
- Clean, testable Python code and sensible defaults (no hard-coded repos)

It’s intentionally small and readable — good for showing in interviews or including as a quick demo in a GitHub README.

---

## Features
- Open a **random GitHub repository** in your default browser.
- Open a **random beginner-friendly issue** (tries labels like `good first issue`, text search, and repo fallbacks).
- **Light / Dark theme** toggle.
- UI shows repo/issue metadata: title, URL, description/excerpt, language, stars, labels.
- All final URLs normalized to **HTTPS**.
- Optional `GITHUB_TOKEN` environment variable support to increase API rate limits.
- Robust fallbacks to avoid hard-coding and increase randomness/diversity.

---

## Repo structure 
```bash
random-github/
├── random_github_ui_with_issues.py
├── requirements.txt
├── README.md 
├── LICENSE
├── .gitignore
```
---

## Requirements
- Python 3.8 or newer  
- `requests` library

---

## Installation

Open a terminal and run:

**Linux / macOS**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
**Windows (PowerShell)**
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
If you don't want a virtual environment:
```bash
pip install requests
```

---
## Usage 
From the project folder:
```bash
# run the GUI app
python random_github_ui_with_issues.py
```
Click Open Random Repo to find and preview a random repository in the details pane, then click Open Shown Link or let it open automatically.

Click Open Random Beginner Issue to find a likely entry-level issue (will show issue excerpt and labels).

---

## How it finds repos & issues

### Random Repo

1) Primary: search GitHub using a random date filter (created:YYYY-MM-DD) and pick a random repo from results.

2) Fallback: call the public /repositories endpoint with a random since id and pick randomly.

### Random Beginner Issue

1) Try label-based search (shuffles candidate labels like good first issue, help wanted, etc) with randomization in pages & date bounds.

2) Text-based search fallback (match phrases like "good first issue" in title/body).

3) Final fallback: pick random repos and scan their open issues, picking those with beginner-friendly labels.

4) All network calls use the requests library with timeouts and basic error handling.

---
## Environment variables / token

Without a token, GitHub API rate limits are much lower. To avoid hitting limits during testing, optionally set a personal access token.

Create token:

1) GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic).

2) No scopes required (just a token string).

**Set token (temporary for terminal session)**

**Linux / macOS**
```bash
export GITHUB_TOKEN="ghp_XXXXXXXXXXXXXXXX"
```
**Windows (PowerShell)**
```bash
$env:GITHUB_TOKEN="ghp_XXXXXXXXXXXXXXXX"
```

The script reads GITHUB_TOKEN from the environment and adds it to the Authorization header for higher rate limits.

---
## Troubleshooting & FAQ

**Q: The app shows “Failed to fetch repository” or rate limit errors.**

**A:** Set GITHUB_TOKEN (see above) or wait an hour for the unauthenticated rate limit to reset.

**Q: Tkinter window does not show on Linux.**

**A:** Install system package for Tk (example for Debian/Ubuntu):
```bash
sudo apt-get install python3-tk
```

**Q: Button clicked but nothing opens in browser**

**A:** Ensure a default browser is configured on your OS. The script uses Python’s webbrowser module to open links.

**Q: I only want a CLI version**

**A:** You can extract the fetch functions (they are modular) and call them from a small if __name__ == "__main__": CLI wrapper — ask me and I’ll provide a minimal CLI script.

---
Thank You for reading!

