// =====================================================================
//   Library Management — Frontend logic (vanilla JS)
//   Talks to FastAPI on http://localhost:8000
// =====================================================================

const API_BASE = window.LIBRARY_API_BASE || "http://localhost:8000/api/v1";

const state = {
  token: localStorage.getItem("lib_token") || null,
  user: JSON.parse(localStorage.getItem("lib_user") || "null"),
};

// ─── DOM helpers ─────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const show = (el) => el.classList.remove("hidden");
const hide = (el) => el.classList.add("hidden");

function toast(message, type = "") {
  const el = $("#toast");
  el.textContent = message;
  el.className = `toast ${type}`;
  show(el);
  clearTimeout(toast._t);
  toast._t = setTimeout(() => hide(el), 3000);
}

// ─── HTTP wrapper ────────────────────────────────────────────────────
async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

  let payload;
  if (form) {
    payload = new URLSearchParams(form).toString();
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { method, headers, body: payload });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

// ─── Auth flow ───────────────────────────────────────────────────────
function setSession(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("lib_token", token);
  localStorage.setItem("lib_user", JSON.stringify(user));
  renderAuthState();
  loadBooks();
  loadHistory();
}

function clearSession() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("lib_token");
  localStorage.removeItem("lib_user");
  renderAuthState();
}

function renderAuthState() {
  const info = $("#userInfo");
  const logoutBtn = $("#logoutBtn");
  const authPanel = $("#authPanel");
  const appPanel = $("#appPanel");
  const adminCard = $("#adminCard");

  if (state.user) {
    info.textContent = `${state.user.username} (${state.user.role})`;
    show(logoutBtn);
    hide(authPanel);
    show(appPanel);
    if (state.user.role === "admin") show(adminCard);
    else hide(adminCard);
  } else {
    info.textContent = "Not signed in";
    info.classList.add("muted");
    hide(logoutBtn);
    show(authPanel);
    hide(appPanel);
  }
}

// ─── Tabs ────────────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach((t) => {
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    if (t.dataset.tab === "login") {
      show($("#loginForm"));
      hide($("#registerForm"));
    } else {
      show($("#registerForm"));
      hide($("#loginForm"));
    }
  });
});

// ─── Login ───────────────────────────────────────────────────────────
$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    const res = await api("/auth/login", {
      method: "POST",
      form: { username: fd.get("username"), password: fd.get("password") },
    });
    setSession(res.access_token, res.user);
    toast("Welcome back!", "success");
  } catch (err) {
    toast(err.message, "error");
  }
});

// ─── Register ────────────────────────────────────────────────────────
$("#registerForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  try {
    await api("/auth/register", { method: "POST", body });
    // Auto-login after register
    const res = await api("/auth/login", {
      method: "POST",
      form: { username: body.username, password: body.password },
    });
    setSession(res.access_token, res.user);
    toast("Account created — welcome!", "success");
  } catch (err) {
    toast(err.message, "error");
  }
});

// ─── Logout ──────────────────────────────────────────────────────────
$("#logoutBtn").addEventListener("click", () => {
  clearSession();
  toast("Logged out");
});

// ─── Books ───────────────────────────────────────────────────────────
async function loadBooks(query = "") {
  try {
    const q = query ? `?q=${encodeURIComponent(query)}` : "";
    const data = await api(`/books${q}`);
    renderBooks(data.items || []);
  } catch (err) {
    toast(err.message, "error");
  }
}

function renderBooks(items) {
  const container = $("#bookList");
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = `<p class="muted small">No books in the catalog yet.</p>`;
    return;
  }

  for (const book of items) {
    const div = document.createElement("div");
    div.className = "book-item";
    const availability = book.available_copies > 0
      ? `<span class="availability">${book.available_copies}/${book.total_copies} available</span>`
      : `<span class="availability zero">Unavailable</span>`;
    div.innerHTML = `
      <div>
        <div class="book-title">${escapeHtml(book.title)}</div>
        <div class="book-meta">by ${escapeHtml(book.author)} ${book.category ? "· " + escapeHtml(book.category) : ""}</div>
        <div class="book-meta small">${book.isbn ? "ISBN " + escapeHtml(book.isbn) : ""}</div>
        <div style="margin-top:.4rem">${availability}</div>
      </div>
      <div class="book-actions"></div>
    `;
    const actions = div.querySelector(".book-actions");
    if (state.user) {
      const borrow = document.createElement("button");
      borrow.className = "btn btn-primary btn-sm";
      borrow.textContent = "Borrow";
      borrow.disabled = book.available_copies === 0;
      borrow.addEventListener("click", () => borrowBook(book.id));
      actions.appendChild(borrow);
    }
    if (state.user && state.user.role === "admin") {
      const del = document.createElement("button");
      del.className = "btn btn-danger btn-sm";
      del.textContent = "Delete";
      del.addEventListener("click", () => deleteBook(book.id));
      actions.appendChild(del);
    }
    container.appendChild(div);
  }
}

async function borrowBook(id) {
  try {
    await api("/borrow", { method: "POST", body: { book_id: id } });
    toast("Book borrowed", "success");
    loadBooks($("#search").value);
    loadHistory();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function deleteBook(id) {
  if (!confirm("Delete this book?")) return;
  try {
    await api(`/books/${id}`, { method: "DELETE" });
    toast("Deleted");
    loadBooks($("#search").value);
  } catch (err) {
    toast(err.message, "error");
  }
}

// Add book (admin)
$("#addBookForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  body.total_copies = Number(body.total_copies || 1);
  // Strip empty optional fields
  for (const k of ["isbn", "category", "description"]) if (!body[k]) delete body[k];
  try {
    await api("/books", { method: "POST", body });
    toast("Book added", "success");
    e.target.reset();
    loadBooks();
  } catch (err) {
    toast(err.message, "error");
  }
});

// ─── Search debounce ─────────────────────────────────────────────────
$("#search").addEventListener("input", (e) => {
  clearTimeout($("#search")._t);
  $("#search")._t = setTimeout(() => loadBooks(e.target.value), 250);
});

// ─── History ─────────────────────────────────────────────────────────
async function loadHistory() {
  if (!state.token) return;
  try {
    const data = await api("/borrow/me");
    renderHistory(data.items || []);
  } catch (err) {
    toast(err.message, "error");
  }
}

function renderHistory(items) {
  const container = $("#historyList");
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = `<p class="muted small">You haven't borrowed any books yet.</p>`;
    return;
  }
  for (const r of items) {
    const div = document.createElement("div");
    div.className = "history-item";
    const due = new Date(r.due_at).toLocaleDateString();
    div.innerHTML = `
      <div>
        <div><strong>${escapeHtml(r.book_title || "")}</strong></div>
        <div class="muted small">Due ${due} · <span class="status-pill ${r.status}">${r.status}</span></div>
      </div>
    `;
    if (r.status === "borrowed") {
      const ret = document.createElement("button");
      ret.className = "btn btn-success btn-sm";
      ret.textContent = "Return";
      ret.addEventListener("click", async () => {
        try {
          await api(`/borrow/${r.id}/return`, { method: "POST" });
          toast("Returned", "success");
          loadHistory();
          loadBooks($("#search").value);
        } catch (err) {
          toast(err.message, "error");
        }
      });
      div.appendChild(ret);
    }
    container.appendChild(div);
  }
}

// ─── Utilities ───────────────────────────────────────────────────────
function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// ─── Boot ────────────────────────────────────────────────────────────
renderAuthState();
loadBooks();
if (state.token) loadHistory();
