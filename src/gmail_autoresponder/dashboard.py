from __future__ import annotations

import subprocess
from collections import Counter

from pathlib import Path

from flask import Flask, flash, redirect, render_template_string, request, url_for

from .config import AppConfig
from .gmail_client import GmailClient
from .responder import AutoResponder
from .storage import RunStore

TEMPLATE = """
<!doctype html>
<html lang="en" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gmail Auto Reply Dashboard</title>
  <style>
    :root {
      --bg:#f5efe7; --bg2:#efe2d4; --panel:rgba(255,250,244,.88); --panel2:#fff8ef; --text:#1d2a30;
      --muted:#66747b; --line:rgba(36,42,44,.12); --accent:#0e907a; --accent2:#d8863d; --danger:#d35b5b;
      --shadow:0 24px 60px rgba(22,29,33,.12); --radius:22px;
    }
    :root[data-theme="dark"] {
      --bg:#10171a; --bg2:#162025; --panel:rgba(22,31,36,.92); --panel2:#18242a; --text:#edf3f3;
      --muted:#99acb3; --line:rgba(237,243,243,.10); --accent:#25c9b0; --accent2:#f0a65d; --danger:#ef7b7b;
      --shadow:0 30px 70px rgba(0,0,0,.32);
    }
    * { box-sizing:border-box; }
    body {
      margin:0; color:var(--text); font-family:"Segoe UI",Tahoma,sans-serif;
      background:radial-gradient(circle at top left, rgba(14,144,122,.16), transparent 28%),
      radial-gradient(circle at top right, rgba(216,134,61,.16), transparent 24%), linear-gradient(180deg,var(--bg),var(--bg2));
    }
    a { color:inherit; }
    .shell { width:min(1360px, calc(100% - 24px)); margin:0 auto; padding:24px 0 40px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); backdrop-filter:blur(14px); }
    .topbar, .hero, .toolbar, .grid, .mini-grid, .stats, .control-grid { display:grid; gap:16px; }
    .topbar { grid-template-columns:1fr auto; align-items:start; margin-bottom:16px; }
    .hero { grid-template-columns:1.45fr 1fr; margin-bottom:16px; }
    .toolbar { grid-template-columns:1.2fr 1fr; margin-bottom:16px; }
    .grid { grid-template-columns:1.15fr .85fr; align-items:start; }
    .mini-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .stats { grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:18px; }
    .control-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .card { padding:22px; }
    .hero-main { padding:28px; }
    .hero-side { padding:24px; display:grid; gap:14px; }
    .eyebrow, .badge {
      display:inline-flex; align-items:center; gap:8px; padding:7px 12px; border-radius:999px; font-size:.8rem; font-weight:700;
    }
    .eyebrow { background:rgba(14,144,122,.12); color:var(--accent); text-transform:uppercase; letter-spacing:.06em; }
    h1,h2,h3,p { margin:0; }
    h1 { font-size:clamp(2rem,4vw,3.5rem); line-height:.95; letter-spacing:-.04em; max-width:10ch; margin-top:10px; }
    h2 { font-size:1.08rem; letter-spacing:-.03em; }
    .sub { color:var(--muted); line-height:1.55; margin-top:10px; max-width:60ch; }
    .top-actions, .toolbar-row, .inline { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
    .top-actions { justify-content:flex-end; }
    .brandmark {
      width:50px; height:50px; border-radius:16px; background:linear-gradient(135deg,var(--accent),var(--accent2)); box-shadow:var(--shadow);
      margin-bottom:8px;
    }
    .stat { padding:18px; border-radius:18px; border:1px solid var(--line); background:rgba(255,255,255,.34); }
    html[data-theme="dark"] .stat { background:rgba(255,255,255,.03); }
    .stat small, .note { color:var(--muted); }
    .stat strong { display:block; margin-top:8px; font-size:2rem; letter-spacing:-.04em; }
    .btn, .input, select {
      border-radius:999px; font:inherit; padding:12px 14px;
    }
    .btn {
      border:1px solid transparent; cursor:pointer; font-weight:700;
      background:var(--panel2); color:var(--text);
    }
    .btn:hover { opacity:.95; }
    .btn-primary { background:var(--accent); color:white; }
    .btn-secondary { background:var(--accent2); color:white; }
    .btn-danger { background:rgba(211,91,91,.14); color:var(--danger); border-color:rgba(211,91,91,.2); }
    .btn-wide { min-width: 190px; }
    .input, select { width:100%; border:1px solid var(--line); background:var(--panel2); color:var(--text); }
    .flash-stack { display:grid; gap:10px; margin-bottom:16px; }
    .flash { padding:14px 16px; border-radius:16px; background:rgba(216,134,61,.12); border:1px solid rgba(216,134,61,.22); }
    .status-card, .chart-card { padding:18px; border-radius:18px; border:1px solid var(--line); background:var(--panel2); }
    .upload-box { padding:18px; border-radius:18px; border:1px dashed var(--line); background:var(--panel2); }
    .list { display:grid; gap:10px; }
    .status-card strong { display:block; margin-bottom:6px; }
    .file-list { display:grid; gap:10px; margin-top:14px; }
    .file-item { display:flex; justify-content:space-between; gap:12px; align-items:center; padding:12px 14px; border:1px solid var(--line); border-radius:14px; background:var(--panel2); }
    .table-wrap { overflow:auto; border:1px solid var(--line); border-radius:18px; background:var(--panel2); }
    .row-button {
      width: 100%;
      background: transparent;
      border: 0;
      color: inherit;
      font: inherit;
      text-align: left;
      padding: 0;
      cursor: pointer;
    }
    .row-button:hover { opacity: .9; }
    table { width:100%; border-collapse:collapse; min-width:720px; }
    th, td { padding:14px 12px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top; }
    th { font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); background:rgba(127,127,127,.05); }
    tr:last-child td { border-bottom:0; }
    .badge { background:rgba(14,144,122,.12); color:var(--accent); }
    .warn { background:rgba(216,134,61,.14); color:var(--accent2); }
    .danger { background:rgba(211,91,91,.14); color:var(--danger); }
    .neutral { background:rgba(127,127,127,.14); color:var(--muted); }
    .bar-row { display:grid; grid-template-columns:84px 1fr 40px; gap:10px; align-items:center; font-size:.92rem; margin-top:12px; }
    .track { height:10px; border-radius:999px; background:rgba(127,127,127,.14); overflow:hidden; }
    .fill { height:100%; border-radius:inherit; background:linear-gradient(90deg,var(--accent),var(--accent2)); }
    .donut-wrap { display:grid; grid-template-columns:180px 1fr; gap:16px; align-items:center; }
    .donut {
      width:180px; height:180px; border-radius:50%;
      background:conic-gradient(var(--accent) 0deg {{ mail_segments.business_deg }}deg, #4b78ff {{ mail_segments.business_deg }}deg {{ mail_segments.promotional_deg }}deg, var(--accent2) {{ mail_segments.promotional_deg }}deg {{ mail_segments.social_deg }}deg, var(--danger) {{ mail_segments.social_deg }}deg 360deg);
      position:relative; margin:0 auto;
    }
    .donut::after {
      content:"{{ mail_total }} mails"; position:absolute; inset:22px; border-radius:50%; background:var(--panel2);
      display:grid; place-items:center; font-weight:800; text-align:center; padding:20px;
    }
    .legend { display:grid; gap:10px; }
    .legend-item { display:flex; justify-content:space-between; gap:10px; align-items:center; padding:12px 14px; border-radius:14px; background:var(--panel2); border:1px solid var(--line); }
    .legend-left { display:inline-flex; align-items:center; gap:10px; }
    .swatch { width:12px; height:12px; border-radius:50%; }
    .empty { padding:28px; text-align:center; color:var(--muted); }
    .helper-grid { display:grid; gap:10px; margin-top:14px; }
    .helper-item { padding:12px 14px; border:1px dashed var(--line); border-radius:14px; background:var(--panel2); }
    .viewer {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,.45);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 24px;
      z-index: 50;
    }
    .viewer.open { display: flex; }
    .viewer-card {
      width: min(920px, 100%);
      max-height: 88vh;
      overflow: auto;
      border-radius: 24px;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      padding: 22px;
    }
    .viewer-head {
      display:flex;
      justify-content:space-between;
      gap:16px;
      align-items:flex-start;
      margin-bottom:16px;
    }
    .viewer-meta {
      display:grid;
      gap:8px;
      color: var(--muted);
      font-size:.95rem;
    }
    .viewer-body {
      white-space: pre-wrap;
      line-height: 1.6;
      padding: 18px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: var(--panel2);
    }
    code { font-family:Consolas,monospace; }
    @media (max-width:1180px) { .hero,.toolbar,.grid { grid-template-columns:1fr; } }
    @media (max-width:900px) {
      .topbar,.stats,.mini-grid,.control-grid { grid-template-columns:1fr; }
      .donut-wrap { grid-template-columns:1fr; }
      .shell { width:min(100% - 16px, 1360px); }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div>
        <div class="brandmark"></div>
        <div class="eyebrow">Smart Mail Control</div>
        <h1>Inbox activity in one clear view.</h1>
        <p class="sub">Monitor replies, filter activity, review mail types, and control the scheduler from a cleaner dashboard.</p>
      </div>
      <div class="top-actions">
        <button type="button" class="btn" id="themeToggle" title="Switch the dashboard between dark mode and light mode.">Dark / Light</button>
        <a class="btn" href="{{ dashboard_url }}" target="_blank" rel="noreferrer" title="Open the dashboard URL in a new browser tab.">Open link</a>
      </div>
    </div>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="flash-stack">
          {% for message in messages %}
            <div class="flash">{{ message }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <div class="hero">
      <section class="panel hero-main">
        <div class="eyebrow">Live Overview</div>
        <h2>Scheduler is {{ scheduler_label }}</h2>
        <p class="sub">Current Gmail query: <code>{{ query_text }}</code></p>
        <div class="stats">
          <div class="stat"><small>Total runs</small><strong>{{ summary.total_runs }}</strong></div>
          <div class="stat"><small>Replies created</small><strong>{{ summary.total_replied }}</strong></div>
          <div class="stat"><small>Skipped mails</small><strong>{{ summary.total_skipped }}</strong></div>
          <div class="stat"><small>Failed actions</small><strong>{{ summary.total_failed }}</strong></div>
        </div>
      </section>

      <aside class="panel hero-side">
        <div>
          <h2>Quick controls</h2>
          <p class="sub">Run tests, send replies, or pause the task while you adjust rules.</p>
        </div>
        <form method="post" action="{{ url_for('trigger_run') }}" class="control-grid">
          <button class="btn btn-primary" type="submit" name="mode" value="dry-run" title="Scan matching emails and preview the action without sending anything.">Dry run</button>
          <button class="btn" type="submit" name="mode" value="draft" title="Create Gmail drafts so you can review the reply before sending.">Create drafts</button>
          <button class="btn btn-secondary" type="submit" name="mode" value="send" title="Send the matching replies immediately from the connected Gmail account.">Send replies</button>
        </form>
        <form method="post" action="{{ url_for('scheduler_action') }}" class="toolbar-row">
          {% if scheduler_running %}
            <button class="btn btn-danger btn-wide" type="submit" name="action" value="stop_all" title="Stop the scheduled background auto-reply task so it no longer runs automatically.">Stop background task</button>
            <button class="btn btn-danger" type="submit" name="action" value="pause" title="Pause the scheduled auto-reply task. This keeps the dashboard open but stops timed email processing.">Pause auto replies</button>
          {% else %}
            <button class="btn btn-primary btn-wide" type="submit" name="action" value="start_all" title="Start the scheduled background auto-reply task again.">Start background task</button>
            <button class="btn btn-primary" type="submit" name="action" value="resume" title="Resume the scheduled auto-reply task after it has been paused.">Resume auto replies</button>
          {% endif %}
        </form>
        <p class="note">Task: <code>{{ task_name }}</code><br>Dashboard: <a href="{{ dashboard_url }}">{{ dashboard_url }}</a></p>
        <div class="helper-grid">
          <div class="helper-item" title="Dry run shows what the bot would do without creating drafts or sending mail."><strong>Dry run</strong><br><span class="note">Safe preview mode.</span></div>
          <div class="helper-item" title="Create drafts saves a reply draft in Gmail, including attachments when a matching rule asks for them."><strong>Create drafts</strong><br><span class="note">Review before sending.</span></div>
          <div class="helper-item" title="Send replies uses the live Gmail account and sends responses immediately."><strong>Send replies</strong><br><span class="note">Live sending mode.</span></div>
          <div class="helper-item" title="Stop/Start background task controls the Windows scheduled task that runs the auto-reply system in the background."><strong>Background task</strong><br><span class="note">Controls the scheduler only.</span></div>
        </div>
      </aside>
    </div>

    <div class="toolbar">
      <section class="panel card">
        <h2>Search and filter</h2>
        <p class="sub">Filter by keyword, action, or mail type.</p>
        <form method="get" action="{{ url_for('home') }}">
          <div class="toolbar-row" style="margin-top:14px;">
            <input class="input" type="text" name="search" value="{{ filters.search }}" placeholder="Search sender, subject, preview, status">
          </div>
          <div class="toolbar-row" style="margin-top:10px;">
            <select name="action">
              <option value="">All actions</option>
              {% for action in filter_options.actions %}
                <option value="{{ action }}" {% if filters.action == action %}selected{% endif %}>{{ action }}</option>
              {% endfor %}
            </select>
            <select name="mail_type">
              <option value="">All mail types</option>
              {% for mail_type in filter_options.mail_types %}
                <option value="{{ mail_type }}" {% if filters.mail_type == mail_type %}selected{% endif %}>{{ mail_type }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="toolbar-row" style="margin-top:10px;">
            <button class="btn btn-primary" type="submit" title="Apply the selected search and filter options to the dashboard tables.">Apply filters</button>
            <a class="btn" href="{{ url_for('home') }}" title="Clear the search box and all active filters.">Reset</a>
          </div>
        </form>
      </section>

      <section class="panel card">
        <h2>Mail type counters</h2>
        <p class="sub">Quick view of sent/business, promotional, social, and spam/other style mails.</p>
        <div class="mini-grid" style="margin-top:14px;">
          <div class="status-card"><strong>Sent / Business</strong><span>{{ mail_counts.business }}</span></div>
          <div class="status-card"><strong>Promotional</strong><span>{{ mail_counts.promotional }}</span></div>
          <div class="status-card"><strong>Social</strong><span>{{ mail_counts.social }}</span></div>
          <div class="status-card"><strong>Spam / Other</strong><span>{{ mail_counts.spam_other }}</span></div>
        </div>
        <div class="upload-box" style="margin-top:14px;">
          <h3>Attachment storage</h3>
          <p class="sub">Upload approved files here, then reference them from your reply rules.</p>
          <form method="post" action="{{ url_for('upload_attachment') }}" enctype="multipart/form-data">
            <div class="toolbar-row" style="margin-top:12px;">
              <input class="input" type="file" name="attachment_file" required title="Choose a local file to store in the project's attachments folder.">
              <button class="btn btn-primary" type="submit" title="Upload the selected file into the attachment storage folder.">Add attachment</button>
            </div>
          </form>
          <div class="file-list">
            {% for file in attachment_files %}
              <div class="file-item">
                <span><strong>{{ file.name }}</strong><br><span class="note">{{ file.size_label }}</span></span>
                <span class="badge">{{ file.rule_path }}</span>
              </div>
            {% else %}
              <div class="empty">No stored attachment files yet.</div>
            {% endfor %}
          </div>
        </div>
      </section>
    </div>

    <div class="grid">
      <div class="panel card">
        <h2>Summary charts</h2>
        <p class="sub">Run outcomes and current mail mix.</p>
        <div class="mini-grid" style="margin-top:14px;">
          <div class="chart-card">
            <h3>Run outcomes</h3>
            {% for item in run_chart %}
              <div class="bar-row">
                <span>{{ item.label }}</span>
                <div class="track"><div class="fill" style="width: {{ item.percent }}%"></div></div>
                <strong>{{ item.value }}</strong>
              </div>
            {% endfor %}
          </div>
          <div class="chart-card">
            <h3>Mail categories</h3>
            <div class="donut-wrap" style="margin-top:14px;">
              <div class="donut"></div>
              <div class="legend">
                {% for item in mail_legend %}
                  <div class="legend-item">
                    <span class="legend-left"><span class="swatch" style="background: {{ item.color }}"></span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                  </div>
                {% endfor %}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="panel card">
        <h2>System status</h2>
        <p class="sub">Core files and scheduler details.</p>
        <div class="mini-grid" style="margin-top:14px;">
          {% for item in status_items %}
            <div class="status-card"><strong>{{ item.label }}</strong><span class="note">{{ item.value }}</span></div>
          {% endfor %}
        </div>
      </div>
    </div>

    <div class="grid" style="margin-top:16px;">
      <div class="panel card">
        <div class="toolbar-row" style="justify-content:space-between; align-items:flex-end;">
          <div>
            <h2>Recent message activity</h2>
            <p class="sub">{{ filtered_events|length }} items shown.</p>
          </div>
        </div>
        <div class="table-wrap" style="margin-top:14px;">
          <table>
            <thead>
              <tr><th>Time</th><th>From</th><th>Subject</th><th>Mail type</th><th>Action</th><th>Preview</th></tr>
            </thead>
            <tbody>
              {% for event in filtered_events %}
                <tr>
                  <td>{{ event.created_at }}</td>
                  <td>{{ event.from_email }}</td>
                  <td>
                    <button
                      type="button"
                      class="row-button"
                      data-open-message
                      data-message-id="{{ event.message_id }}"
                      title="Open this email inside the dashboard.">
                      <strong>{{ event.subject }}</strong><br>
                      <span class="note">Click to open full mail content</span>
                    </button>
                  </td>
                  <td><span class="badge {{ event.mail_badge }}">{{ event.mail_type }}</span></td>
                  <td><span class="badge {{ event.action_badge }}">{{ event.action }}</span></td>
                  <td>{{ event.preview }}</td>
                </tr>
              {% else %}
                <tr><td colspan="6" class="empty">No message activity matched the current filters.</td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="panel card">
        <h2>Recent runs</h2>
        <p class="sub">{{ filtered_runs|length }} runs shown.</p>
        <div class="table-wrap" style="margin-top:14px;">
          <table>
            <thead>
              <tr><th>ID</th><th>Started</th><th>Mode</th><th>Status</th><th>Counts</th></tr>
            </thead>
            <tbody>
              {% for run in filtered_runs %}
                <tr>
                  <td>#{{ run.id }}</td>
                  <td>{{ run.started_at }}</td>
                  <td>{{ run.mode }}</td>
                  <td><span class="badge {{ run.status_badge }}">{{ run.status }}</span></td>
                  <td>{{ run.replied }} replied / {{ run.skipped }} skipped / {{ run.failed }} failed</td>
                </tr>
              {% else %}
                <tr><td colspan="5" class="empty">No runs matched the current filters.</td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <p class="note" style="margin-top:16px;">Tip: use dry run after changing rules, then return to live send once the previews look correct.</p>
  </div>

  <div class="viewer" id="messageViewer" aria-hidden="true">
    <div class="viewer-card">
      <div class="viewer-head">
        <div>
          <div class="eyebrow">Mail Viewer</div>
          <h2 id="viewerSubject">Loading...</h2>
        </div>
        <button type="button" class="btn" id="closeViewer" title="Close the mail viewer.">Close</button>
      </div>
      <div class="viewer-meta">
        <div><strong>From:</strong> <span id="viewerFrom">-</span></div>
        <div><strong>To:</strong> <span id="viewerTo">-</span></div>
        <div><strong>Date:</strong> <span id="viewerDate">-</span></div>
      </div>
      <div class="viewer-body" id="viewerBody" style="margin-top:16px;">Choose a message from the activity table.</div>
    </div>
  </div>

  <script>
    (function () {
      const root = document.documentElement;
      const key = "gmail-dashboard-theme";
      const saved = localStorage.getItem(key);
      if (saved) root.setAttribute("data-theme", saved);
      const button = document.getElementById("themeToggle");
      if (!button) return;
      button.addEventListener("click", function () {
        const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        localStorage.setItem(key, next);
      });
    }());

    (function () {
      const viewer = document.getElementById("messageViewer");
      const close = document.getElementById("closeViewer");
      const subject = document.getElementById("viewerSubject");
      const from = document.getElementById("viewerFrom");
      const to = document.getElementById("viewerTo");
      const date = document.getElementById("viewerDate");
      const body = document.getElementById("viewerBody");
      if (!viewer) return;

      function openViewer() {
        viewer.classList.add("open");
        viewer.setAttribute("aria-hidden", "false");
      }

      function closeViewer() {
        viewer.classList.remove("open");
        viewer.setAttribute("aria-hidden", "true");
      }

      async function loadMessage(messageId) {
        subject.textContent = "Loading...";
        from.textContent = "-";
        to.textContent = "-";
        date.textContent = "-";
        body.textContent = "Loading message content...";
        openViewer();
        try {
          const response = await fetch(`/message/${encodeURIComponent(messageId)}`);
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.error || "Unable to open message.");
          }
          subject.textContent = payload.subject || "(no subject)";
          from.textContent = payload.from || "-";
          to.textContent = payload.to || "-";
          date.textContent = payload.date || "-";
          body.textContent = payload.body || "No plain text body found for this email.";
        } catch (error) {
          subject.textContent = "Could not open message";
          body.textContent = error.message || "Unknown error";
        }
      }

      document.querySelectorAll("[data-open-message]").forEach(function (button) {
        button.addEventListener("click", function () {
          loadMessage(button.getAttribute("data-message-id"));
        });
      });

      close.addEventListener("click", closeViewer);
      viewer.addEventListener("click", function (event) {
        if (event.target === viewer) closeViewer();
      });
      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") closeViewer();
      });
    }());
  </script>
</body>
</html>
"""


def create_app(config: AppConfig | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = "gmail-autoresponder-dashboard"
    cfg = config or AppConfig.from_env()
    store = RunStore(cfg.db_file)

    @app.get("/")
    def home():
        search = request.args.get("search", "").strip()
        action_filter = request.args.get("action", "").strip().lower()
        mail_type_filter = request.args.get("mail_type", "").strip().lower()

        runs = [_decorate_run(run) for run in store.recent_runs()]
        events = [_decorate_event(event) for event in store.recent_events(limit=50)]
        filtered_runs = _filter_runs(runs, search)
        filtered_events = _filter_events(events, search, action_filter, mail_type_filter)

        status_items = [
            {"label": "Gmail credentials", "value": "present" if cfg.credentials_file.exists() else "missing"},
            {"label": "Gmail token", "value": "present" if cfg.token_file.exists() else "missing"},
            {"label": "Rules file", "value": "present" if cfg.rules_file.exists() else "missing"},
            {"label": "Attachments folder", "value": str(cfg.attachments_dir)},
            {"label": "Reply engine", "value": "local rules"},
            {"label": "Schedule interval", "value": f"every {cfg.schedule_interval_minutes} minutes"},
        ]
        cfg.attachments_dir.mkdir(parents=True, exist_ok=True)
        counts = _mail_counts(filtered_events)
        summary = store.summary()
        scheduler_running = _scheduler_running(cfg.schedule_task_name)
        return render_template_string(
            TEMPLATE,
            summary=summary,
            filtered_runs=filtered_runs,
            filtered_events=filtered_events,
            status_items=status_items,
            dashboard_url=f"http://{cfg.dashboard_host}:{cfg.dashboard_port}",
            scheduler_running=scheduler_running,
            scheduler_label="running" if scheduler_running else "paused",
            task_name=cfg.schedule_task_name,
            query_text=cfg.query,
            filters={"search": search, "action": action_filter, "mail_type": mail_type_filter},
            filter_options={
                "actions": sorted({event["action"] for event in events}),
                "mail_types": sorted({event["mail_type"] for event in events}),
            },
            run_chart=_build_run_chart(summary),
            mail_counts=counts,
            mail_total=max(sum(counts.values()), 1),
            mail_segments=_build_mail_segments(counts),
            mail_legend=[
                {"label": "Business", "value": counts["business"], "color": "var(--accent)"},
                {"label": "Promotional", "value": counts["promotional"], "color": "#4b78ff"},
                {"label": "Social", "value": counts["social"], "color": "var(--accent2)"},
                {"label": "Spam / Other", "value": counts["spam_other"], "color": "var(--danger)"},
            ],
            attachment_files=_list_attachment_files(cfg.attachments_dir),
        )

    @app.post("/run")
    def trigger_run():
        mode = request.form.get("mode", "dry-run")
        dry_run = mode == "dry-run"
        send_now = mode == "send" and not cfg.draft_only
        try:
            result = AutoResponder(cfg).run(dry_run=dry_run, send_now=send_now)
            flash(
                f"Run finished. scanned={result.scanned} replied={result.replied} "
                f"skipped={result.skipped} failed={result.failed} mode={result.mode}"
            )
        except Exception as exc:
            flash(f"Run failed: {exc}")
        return redirect(url_for("home"))

    @app.post("/scheduler")
    def scheduler_action():
        action = request.form.get("action", "").strip().lower()
        try:
            if action in {"pause", "stop_all"}:
                _set_scheduler_state(cfg.schedule_task_name, enabled=False)
                flash("Background auto-reply task stopped.")
            elif action in {"resume", "start_all"}:
                _set_scheduler_state(cfg.schedule_task_name, enabled=True)
                flash("Background auto-reply task started.")
            else:
                flash("Unknown scheduler action.")
        except Exception as exc:
            flash(f"Scheduler update failed: {exc}")
        return redirect(url_for("home"))

    @app.post("/attachments/upload")
    def upload_attachment():
        uploaded = request.files.get("attachment_file")
        if uploaded is None or not uploaded.filename:
            flash("Choose a file first.")
            return redirect(url_for("home"))
        cfg.attachments_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(uploaded.filename).name.strip()
        if not safe_name:
            flash("Invalid attachment name.")
            return redirect(url_for("home"))
        destination = cfg.attachments_dir / safe_name
        uploaded.save(destination)
        flash(f"Attachment uploaded: {safe_name}")
        return redirect(url_for("home"))

    @app.get("/message/<message_id>")
    def message_detail(message_id: str):
        try:
            gmail = GmailClient(cfg.credentials_file, cfg.token_file)
            message = gmail.get_message(message_id)
            return {
                "subject": message.subject,
                "from": message.from_header or message.from_email,
                "to": message.to_header,
                "date": message.date_header,
                "body": message.body,
            }
        except Exception as exc:
            return {"error": str(exc)}, 500

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


def _decorate_run(run) -> dict[str, str | int]:
    payload = dict(run)
    payload["status_badge"] = _status_badge(str(payload["status"]))
    return payload


def _decorate_event(event) -> dict[str, str]:
    payload = dict(event)
    mail_type = _classify_mail(payload["from_email"], payload["subject"], payload["preview"])
    payload["mail_type"] = mail_type
    payload["mail_badge"] = _mail_badge(mail_type)
    payload["action_badge"] = _status_badge(payload["action"])
    return payload


def _filter_runs(runs: list[dict], search: str) -> list[dict]:
    if not search:
        return runs
    needle = search.lower()
    return [run for run in runs if needle in f'{run["id"]} {run["started_at"]} {run["mode"]} {run["status"]}'.lower()]


def _filter_events(events: list[dict], search: str, action_filter: str, mail_type_filter: str) -> list[dict]:
    filtered = events
    if search:
        needle = search.lower()
        filtered = [event for event in filtered if needle in f'{event["from_email"]} {event["subject"]} {event["preview"]} {event["action"]} {event["mail_type"]}'.lower()]
    if action_filter:
        filtered = [event for event in filtered if event["action"].lower() == action_filter]
    if mail_type_filter:
        filtered = [event for event in filtered if event["mail_type"].lower() == mail_type_filter]
    return filtered


def _mail_counts(events: list[dict]) -> dict[str, int]:
    counter = Counter(event["mail_type"] for event in events)
    return {
        "business": counter.get("business", 0),
        "promotional": counter.get("promotional", 0),
        "social": counter.get("social", 0),
        "spam_other": counter.get("spam/other", 0),
    }


def _build_run_chart(summary: dict[str, int]) -> list[dict[str, int | str]]:
    rows = [
        {"label": "Replies", "value": summary["total_replied"]},
        {"label": "Skipped", "value": summary["total_skipped"]},
        {"label": "Failed", "value": summary["total_failed"]},
    ]
    top = max((int(row["value"]) for row in rows), default=0) or 1
    for row in rows:
        row["percent"] = max(8, round((int(row["value"]) / top) * 100))
    return rows


def _build_mail_segments(counts: dict[str, int]) -> dict[str, int]:
    total = max(sum(counts.values()), 1)
    business = round((counts["business"] / total) * 360)
    promotional = business + round((counts["promotional"] / total) * 360)
    social = promotional + round((counts["social"] / total) * 360)
    return {
        "business_deg": business,
        "promotional_deg": promotional,
        "social_deg": social,
    }


def _classify_mail(sender: str, subject: str, preview: str) -> str:
    haystack = f"{sender} {subject} {preview}".lower()
    if any(term in haystack for term in ("instagram", "facebook", "linkedin", "twitter", "x.com", "notification")):
        return "social"
    if any(term in haystack for term in ("sale", "discount", "offer", "promo", "promotion", "newsletter", "off")):
        return "promotional"
    if any(term in haystack for term in ("no-reply", "noreply", "casino", "bonus", "free money", "claim now")):
        return "spam/other"
    return "business"


def _status_badge(value: str) -> str:
    normalized = value.lower()
    if normalized in {"sent", "completed", "previewed"}:
        return ""
    if normalized in {"failed", "error"}:
        return "danger"
    if normalized in {"skipped", "paused"}:
        return "neutral"
    return "warn"


def _mail_badge(value: str) -> str:
    if value == "business":
        return ""
    if value == "promotional":
        return "warn"
    if value == "spam/other":
        return "danger"
    return "neutral"


def _scheduler_running(task_name: str) -> bool:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"(Get-ScheduledTask -TaskName '{task_name}').State"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip().lower() == "ready"


def _set_scheduler_state(task_name: str, enabled: bool) -> None:
    command = "Enable-ScheduledTask" if enabled else "Disable-ScheduledTask"
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"{command} -TaskName '{task_name}' | Out-Null"],
        capture_output=True,
        text=True,
        check=True,
    )


def _list_attachment_files(attachments_dir: Path) -> list[dict[str, str]]:
    if not attachments_dir.exists():
        return []
    files = []
    for item in sorted(attachments_dir.iterdir(), key=lambda path: path.name.lower()):
        if not item.is_file():
            continue
        files.append(
            {
                "name": item.name,
                "size_label": _format_bytes(item.stat().st_size),
                "rule_path": f"attachments/{item.name}",
            }
        )
    return files


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def run_dashboard(config: AppConfig | None = None) -> None:
    cfg = config or AppConfig.from_env()
    create_app(cfg).run(host=cfg.dashboard_host, port=cfg.dashboard_port, debug=False)


def main() -> int:
    run_dashboard()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
