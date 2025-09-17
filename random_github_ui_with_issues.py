from __future__ import annotations
import os
import random
import webbrowser
import tkinter as tk
from tkinter import messagebox
from datetime import date, timedelta
from typing import Optional, Dict, Any, List
import requests

# ---------- Configuration ----------
GITHUB_SEARCH_REPOS = "https://api.github.com/search/repositories"
GITHUB_LIST_REPOS = "https://api.github.com/repositories"
GITHUB_SEARCH_ISSUES = "https://api.github.com/search/issues"
USER_AGENT = "random-github-opener/3.0"
MAX_SEARCH_ATTEMPTS = 6
MAX_FALLBACK_ATTEMPTS = 4
MAX_ISSUE_SEARCH_ATTEMPTS = 6
REQUEST_TIMEOUT = 10  # seconds

# label candidates to try (random order each run)
ISSUE_LABEL_CANDIDATES = [
    "good first issue",
    "good-first-issue",
    "good first bug",
    "good beginner",
    "beginner",
    "easy",
    "help wanted",
    "good first contribution",
]


# ---------- Helpers ----------
def get_auth_headers() -> Dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def random_date(start: date = date(2008, 1, 1), end: date = date.today()) -> date:
    days = (end - start).days
    return start + timedelta(days=random.randint(0, days))


def choose_random_item(items: List[Any]) -> Optional[Any]:
    if not items:
        return None
    return random.choice(items)


def is_valid_github_html_url(url: Optional[str]) -> bool:
    if not url:
        return False
    return url.startswith("https://github.com/") and len(url.split("/")) >= 5


def normalize_to_https(url: str) -> str:
    if url.startswith("http://"):
        return "https://" + url.split("://", 1)[1]
    return url


def is_pull_request(item: Dict[str, Any]) -> bool:
    return "pull_request" in item


# ---------- Repo fetching strategies ----------
def search_repos_by_random_day(headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    for _ in range(MAX_SEARCH_ATTEMPTS):
        d = random_date()
        q = f"created:{d.isoformat()}..{d.isoformat()}"
        params = {"q": q, "per_page": 100}
        try:
            resp = requests.get(GITHUB_SEARCH_REPOS, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                repo = choose_random_item(items)
                if repo:
                    return repo
            else:
                if resp.status_code in (403, 422):
                    break
        except requests.RequestException:
            continue
    return None


def list_public_repos_fallback(headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    for _ in range(MAX_FALLBACK_ATTEMPTS):
        since_id = random.randint(1, 100_000_000)
        params = {"since": since_id, "per_page": 100}
        try:
            resp = requests.get(GITHUB_LIST_REPOS, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                items = resp.json()
                repo = choose_random_item(items)
                if repo:
                    return repo
            else:
                if resp.status_code == 403:
                    break
        except requests.RequestException:
            continue
    return None


def fetch_random_github_repo() -> Optional[Dict[str, Any]]:
    headers = get_auth_headers()
    repo = search_repos_by_random_day(headers)
    if repo:
        return repo
    return list_public_repos_fallback(headers)


# ---------- Issue search strategies ----------
def search_issues_by_labels_or_text(headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    # try label-based searches first (random order)
    labels = ISSUE_LABEL_CANDIDATES[:]
    random.shuffle(labels)
    for label in labels:
        for _ in range(MAX_ISSUE_SEARCH_ATTEMPTS):
            # randomize created date to broaden the search scope
            d = random_date()
            q = f'label:"{label}" state:open'
            # sometimes add a date bound to increase variance
            if random.random() < 0.6:
                q += f" created:<={d.isoformat()}"
            params = {"q": q, "per_page": 100, "page": random.randint(1, 5)}
            try:
                resp = requests.get(GITHUB_SEARCH_ISSUES, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    # filter out pull requests if present
                    items = [it for it in items if not is_pull_request(it)]
                    chosen = choose_random_item(items)
                    if chosen:
                        return chosen
                else:
                    if resp.status_code == 403:
                        return None
            except requests.RequestException:
                continue

    # fallback: text-based search (match "good first issue" in title/body)
    text_patterns = ['"good first issue" in:title,body', '"good-first-issue" in:title,body', '"help wanted" in:title,body']
    for pat in text_patterns:
        for _ in range(3):
            params = {"q": f'{pat} state:open', "per_page": 100, "page": random.randint(1, 5)}
            try:
                resp = requests.get(GITHUB_SEARCH_ISSUES, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    items = [it for it in resp.json().get("items", []) if not is_pull_request(it)]
                    chosen = choose_random_item(items)
                    if chosen:
                        return chosen
                else:
                    if resp.status_code == 403:
                        return None
            except requests.RequestException:
                continue

    return None


def list_repo_issues_fallback(headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    # pick random repos and inspect their issues (label matching)
    for _ in range(MAX_FALLBACK_ATTEMPTS * 2):
        repo = list_public_repos_fallback(headers)
        if not repo:
            break
        owner = repo.get("owner", {}).get("login")
        name = repo.get("name")
        if not owner or not name:
            continue
        issues_url = f"https://api.github.com/repos/{owner}/{name}/issues"
        params = {"state": "open", "per_page": 100}
        try:
            resp = requests.get(issues_url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                items = resp.json()
                # filter out PRs and find labels that look "beginner-friendly"
                candidate_issues = []
                for it in items:
                    if is_pull_request(it):
                        continue
                    labels = [lbl.get("name", "").lower() for lbl in it.get("labels", [])]
                    label_text = " ".join(labels)
                    if any(k in label_text for k in ("good", "first", "beginner", "easy", "help")):
                        candidate_issues.append(it)
                chosen = choose_random_item(candidate_issues)
                if chosen:
                    return chosen
            else:
                if resp.status_code == 403:
                    break
        except requests.RequestException:
            continue
    return None


def fetch_random_beginner_issue() -> Optional[Dict[str, Any]]:
    headers = get_auth_headers()
    # primary: search labels/text
    issue = search_issues_by_labels_or_text(headers)
    if issue:
        return issue
    # fallback: inspect random repos' issues
    issue = list_repo_issues_fallback(headers)
    return issue


# ---------- UI/Theming ----------
THEMES = {
    "light": {
        "bg": "#f5f5f5",
        "fg": "#222222",
        "btn_bg": "#2e8b57",
        "btn_fg": "#ffffff",
        "secondary_bg": "#ffffff",
        "status_fg": "#333333",
        "info_fg": "#444444",
        "accent": "#3b82f6",
    },
    "dark": {
        "bg": "#1e1e2e",
        "fg": "#e6e6f0",
        "btn_bg": "#2563eb",
        "btn_fg": "#ffffff",
        "secondary_bg": "#2a2a37",
        "status_fg": "#d0d0e0",
        "info_fg": "#c8c8d8",
        "accent": "#7c3aed",
    },
}


class RandomRepoIssueApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Random GitHub Finder — Repo & Beginner Issues")
        self.root.geometry("720x380")
        self.current_url: Optional[str] = None
        self.theme = "light"

        # Main frames
        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True, padx=12, pady=12)

        # Title
        self.title_lbl = tk.Label(self.container, text="🎲 Random GitHub Finder", font=("Segoe UI", 16, "bold"))
        self.title_lbl.pack(pady=(0, 6))

        # Status
        self.status_lbl = tk.Label(self.container,
                                   text="Click a button to open a random repository or a beginner-friendly issue.",
                                   font=("Segoe UI", 11), wraplength=680, justify="center")
        self.status_lbl.pack(pady=(0, 10))

        # Buttons
        btn_frame = tk.Frame(self.container)
        btn_frame.pack(pady=(0, 10))

        self.repo_btn = tk.Button(btn_frame, text="Open Random Repo", command=self.handle_open_repo,
                                  width=20, height=2, relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"))
        self.repo_btn.grid(row=0, column=0, padx=8)

        self.issue_btn = tk.Button(btn_frame, text="Open Random Beginner Issue", command=self.handle_open_issue,
                                   width=28, height=2, relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"))
        self.issue_btn.grid(row=0, column=1, padx=8)

        self.open_link_btn = tk.Button(btn_frame, text="Open Shown Link", command=self.open_current_link,
                                       width=18, height=2, relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"))
        self.open_link_btn.grid(row=0, column=2, padx=8)
        self.open_link_btn.config(state="disabled")

        # Theme & Exit
        small_btn_frame = tk.Frame(self.container)
        small_btn_frame.pack(pady=(6, 8))

        self.theme_var = tk.BooleanVar(value=False)
        self.theme_chk = tk.Checkbutton(small_btn_frame, text="Dark Mode", variable=self.theme_var,
                                        command=self.toggle_theme, font=("Segoe UI", 9))
        self.theme_chk.grid(row=0, column=0, padx=8)

        exit_btn = tk.Button(small_btn_frame, text="Exit", command=self.root.destroy,
                             width=8, relief="flat", cursor="hand2", font=("Segoe UI", 9, "bold"))
        exit_btn.grid(row=0, column=1, padx=8)

        # Details box
        self.details_box = tk.Text(self.container, wrap="word", height=10, padx=10, pady=8, borderwidth=0,
                                   font=("Segoe UI", 10))
        self.details_box.pack(fill="both", expand=True, padx=6, pady=(6, 0))
        self.details_box.config(state="disabled")

        # apply initial theme
        self.apply_theme(self.theme)

    def apply_theme(self, theme_name: str):
        theme = THEMES.get(theme_name, THEMES["light"])
        bg = theme["bg"]
        fg = theme["fg"]
        btn_bg = theme["btn_bg"]
        btn_fg = theme["btn_fg"]
        sec_bg = theme["secondary_bg"]

        self.root.configure(bg=bg)
        self.container.configure(bg=bg)
        self.title_lbl.configure(bg=bg, fg=fg)
        self.status_lbl.configure(bg=bg, fg=theme["status_fg"])
        self.details_box.configure(bg=sec_bg, fg=theme["info_fg"], insertbackground=theme["info_fg"])
        # Buttons (note: on some platforms button background can't be styled)
        for btn in (self.repo_btn, self.issue_btn, self.open_link_btn):
            btn.configure(bg=btn_bg, fg=btn_fg, activebackground=theme["accent"], activeforeground=btn_fg)

        # theme checkbox
        self.theme_chk.configure(bg=bg, fg=fg, selectcolor=bg, activebackground=bg)

    def toggle_theme(self):
        self.theme = "dark" if self.theme_var.get() else "light"
        self.apply_theme(self.theme)

    # ---------- UI helpers ----------
    def set_status(self, text: str):
        self.status_lbl.config(text=text)
        self.root.update_idletasks()

    def set_details(self, lines: List[str]):
        text = "\n".join(lines)
        self.details_box.config(state="normal")
        self.details_box.delete("1.0", "end")
        self.details_box.insert("1.0", text)
        self.details_box.config(state="disabled")

    def enable_open_link(self, url: Optional[str]):
        if url and is_valid_github_html_url(url):
            self.current_url = normalize_to_https(url)
            self.open_link_btn.config(state="normal")
        else:
            self.current_url = None
            self.open_link_btn.config(state="disabled")

    def open_current_link(self):
        if not self.current_url:
            messagebox.showinfo("No link", "No valid link is available to open.")
            return
        try:
            webbrowser.open_new_tab(self.current_url)
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    # ---------- Actions ----------
    def handle_open_repo(self):
        self.repo_btn.config(state="disabled")
        self.issue_btn.config(state="disabled")
        self.set_status("🔎 Finding a random repository...")
        self.set_details(["Working..."])
        self.enable_open_link(None)

        repo = fetch_random_github_repo()
        if not repo:
            messagebox.showerror("Error", "Could not fetch a repository. Check your network or API rate limits.")
            self.set_status("❌ Failed to fetch repository.")
            self.set_details(["No repository found. Try again (or set GITHUB_TOKEN to increase rate limits)."])
            self.repo_btn.config(state="normal")
            self.issue_btn.config(state="normal")
            return

        # build display
        owner = repo.get("owner", {}).get("login")
        name = repo.get("name")
        full_name = repo.get("full_name") or (f"{owner}/{name}" if owner and name else "Unknown")
        html_url = repo.get("html_url") or f"https://github.com/{owner}/{name}" if owner and name else None
        html_url = normalize_to_https(html_url) if html_url else None
        description = (repo.get("description") or "").strip()
        stars = repo.get("stargazers_count")
        language = repo.get("language") or "unknown"

        lines = [
            f"Repository: {full_name}",
            f"URL: {html_url or 'N/A'}",
            f"Language: {language}    Stars: {stars}",
            "",
            "Description:",
            description or "No description available."
        ]
        self.set_details(lines)
        self.set_status(f"✅ Found repo: {full_name}")
        self.enable_open_link(html_url)

        self.repo_btn.config(state="normal")
        self.issue_btn.config(state="normal")

    def handle_open_issue(self):
        self.repo_btn.config(state="disabled")
        self.issue_btn.config(state="disabled")
        self.set_status("🔎 Searching for beginner-friendly issues...")
        self.set_details(["Working..."])
        self.enable_open_link(None)

        issue = fetch_random_beginner_issue()
        if not issue:
            messagebox.showerror("Error", "Could not find a suitable beginner issue. Try again later.")
            self.set_status("❌ No beginner-friendly issue found.")
            self.set_details(["No issue found. You can try again or set GITHUB_TOKEN for higher rate limits."])
            self.repo_btn.config(state="normal")
            self.issue_btn.config(state="normal")
            return

        # Compose issue info
        title = issue.get("title") or "Untitled"
        html_url = issue.get("html_url")
        html_url = normalize_to_https(html_url) if html_url else None
        repo_full_name = None
        # If search result, repository info may be in 'repository_url' or 'repository_url' needs parsing
        repo_url = issue.get("repository_url") or ""
        if repo_url.startswith("https://api.github.com/repos/"):
            repo_full_name = repo_url.split("https://api.github.com/repos/")[-1]
        else:
            # try to infer from html_url
            if html_url and html_url.startswith("https://github.com/"):
                parts = html_url.split("/")
                if len(parts) >= 5:
                    repo_full_name = f"{parts[3]}/{parts[4]}"

        labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]
        body_excerpt = (issue.get("body") or "").strip().splitlines()
        excerpt = "\n".join(body_excerpt[:6]).strip()
        if not excerpt:
            excerpt = "No description available."

        lines = [
            f"Issue: {title}",
            f"Repository: {repo_full_name or 'Unknown'}",
            f"URL: {html_url or 'N/A'}",
            "",
            "Labels: " + (", ".join(labels) if labels else "None"),
            "",
            "Excerpt:",
            excerpt
        ]
        self.set_details(lines)
        self.set_status(f"✅ Found issue: {title}")
        self.enable_open_link(html_url)

        self.repo_btn.config(state="normal")
        self.issue_btn.config(state="normal")


# ---------- Main ----------
def main():
    root = tk.Tk()
    RandomRepoIssueApp(root)  # instantiate without assigning to an unused variable
    root.mainloop()


if __name__ == "__main__":
    main()