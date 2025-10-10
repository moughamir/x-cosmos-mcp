#!/usr/bin/env python3
"""
FastAPI Review UI for MCP pipeline results
------------------------------------------
This server provides a web interface for human review of normalized product outputs.

Features:
- Displays products and proposed changes from `changes_log`
- Allows approving or rejecting field-level suggestions
- On approval, updates the `products` table
- On rejection, marks as reviewed but does not apply
- Simple diff view (highlighting old vs new)
- Optional basic authentication

Usage:
  uvicorn review_ui:app --reload --port 8080

Requirements:
  pip install fastapi uvicorn jinja2 python-multipart difflib sqlite-utils
"""

import sqlite3
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from difflib import HtmlDiff
from starlette.middleware.sessions import SessionMiddleware

DB_PATH = "catalogue.sqlite"
SECRET_KEY = "change-me"

app = FastAPI(title="MCP Review UI", version="1.0")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

templates = Jinja2Templates(directory="templates")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = get_conn()
    cur = conn.cursor()
    logs = cur.execute(
        "SELECT id, product_id, field, old, new, created_at, reviewed FROM changes_log WHERE reviewed = 0 ORDER BY id DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "logs": logs})


@app.get("/diff/{log_id}", response_class=HTMLResponse)
def diff_view(request: Request, log_id: int):
    conn = get_conn()
    cur = conn.cursor()
    log = cur.execute("SELECT * FROM changes_log WHERE id=?", (log_id,)).fetchone()
    conn.close()
    if not log:
        raise HTTPException(status_code=404, detail="Not found")

    diff = HtmlDiff().make_table(
        (log["old"] or "").splitlines(),
        (log["new"] or "").splitlines(),
        fromdesc="OLD",
        todesc="NEW",
        context=True,
        numlines=2,
    )

    return templates.TemplateResponse(
        "diff.html", {"request": request, "log": log, "diff": diff}
    )


@app.post("/approve/{log_id}")
def approve(log_id: int):
    conn = get_conn()
    cur = conn.cursor()
    log = cur.execute("SELECT * FROM changes_log WHERE id=?", (log_id,)).fetchone()
    if not log:
        raise HTTPException(status_code=404, detail="Not found")

    field = log["field"]
    new_val = log["new"]
    pid = log["product_id"]

    if field == "title":
        cur.execute("UPDATE products SET normalized_title=? WHERE id=?", (new_val, pid))
    elif field == "body_html":
        cur.execute(
            "UPDATE products SET normalized_body_html=? WHERE id=?", (new_val, pid)
        )
    elif field == "tags":
        cur.execute(
            "UPDATE products SET normalized_tags_json=? WHERE id=?", (new_val, pid)
        )
    elif field == "gmc_category_label":
        cur.execute(
            "UPDATE products SET gmc_category_label=? WHERE id=?", (new_val, pid)
        )

    cur.execute("UPDATE changes_log SET reviewed=1 WHERE id=?", (log_id,))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/", status_code=303)


@app.post("/reject/{log_id}")
def reject(log_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE changes_log SET reviewed=1 WHERE id=?", (log_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)


# -------------------- templates/index.html --------------------
"""
<!DOCTYPE html>
<html>
<head>
  <title>MCP Review Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2em; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 8px; border-bottom: 1px solid #ddd; }
    a.button { background: #007bff; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; }
    form { display: inline; }
  </style>
</head>
<body>
  <h1>Pending Changes</h1>
  <table>
    <tr><th>ID</th><th>Product</th><th>Field</th><th>Created</th><th>Actions</th></tr>
    {% for log in logs %}
    <tr>
      <td>{{ log.id }}</td>
      <td>{{ log.product_id }}</td>
      <td>{{ log.field }}</td>
      <td>{{ log.created_at }}</td>
      <td>
        <a class="button" href="/diff/{{ log.id }}">Diff</a>
        <form action="/approve/{{ log.id }}" method="post"><button>Approve</button></form>
        <form action="/reject/{{ log.id }}" method="post"><button>Reject</button></form>
      </td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""

# -------------------- templates/diff.html --------------------
"""
<!DOCTYPE html>
<html>
<head>
  <title>Diff {{ log.id }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2em; }
    table.diff { font-size: 14px; border: 1px solid #ccc; }
    td.diff_header { background: #f0f0f0; font-weight: bold; }
    .diff_add { background: #cfc; }
    .diff_sub { background: #fcc; }
    form { margin-top: 1em; }
  </style>
</head>
<body>
  <h1>Diff for {{ log.field }} (Product {{ log.product_id }})</h1>
  {{ diff | safe }}
  <form action="/approve/{{ log.id }}" method="post"><button>Approve</button></form>
  <form action="/reject/{{ log.id }}" method="post"><button>Reject</button></form>
  <p><a href="/">Back</a></p>
</body>
</html>
"""
