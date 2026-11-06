"use strict";
/* PDF Stüdyo arayüzü. Sunucu: /api/* (X-Token başlığıyla). */

const TOKEN = new URLSearchParams(location.search).get("t") || "";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const DPR = Math.min(window.devicePixelRatio || 1, 2);

/* ------------------------------------------------------------------ simgeler */
const ICONS = {
  home: '<path d="m15 18-6-6 6-6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
  redo: '<path d="m15 14 5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h3"/>',
  more: '<circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>',
  upload: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
  file: '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5"/>',
  word: '<path d="M6 3h8l4 4v14H6z"/><path d="m9 11 1.5 6 1.5-4 1.5 4 1.5-6"/>',
  excel: '<path d="M6 3h8l4 4v14H6z"/><path d="m9.5 11 5 6m0-6-5 6"/>',
  ppt: '<path d="M6 3h8l4 4v14H6z"/><path d="M10 17v-6h2.5a1.8 1.8 0 0 1 0 3.6H10"/>',
  scan: '<path d="M4 8V5a1 1 0 0 1 1-1h3"/><path d="M16 4h3a1 1 0 0 1 1 1v3"/><path d="M20 16v3a1 1 0 0 1-1 1h-3"/><path d="M8 20H5a1 1 0 0 1-1-1v-3"/><path d="M8 10h8M8 14h5"/>',
  summary: '<path d="M5 6h14M5 10h14M5 14h9M5 18h6"/>',
  merge: '<rect x="3" y="4" width="8" height="11" rx="1"/><rect x="13" y="9" width="8" height="11" rx="1"/>',
  split: '<rect x="4" y="3" width="16" height="7" rx="1"/><rect x="4" y="14" width="16" height="7" rx="1"/>',
  compress: '<path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/>',
  sign: '<path d="M3 17c3-4 5-9 7-9s-1 9 2 9 3-4 5-4 2 3 4 3"/><path d="M3 21h18"/>',
  edit: '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/>',
  cmd: '<path d="m4 17 6-6-6-6"/><path d="M12 19h8"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
  text: '<path d="M5 6V4h14v2"/><path d="M12 4v16"/><path d="M9 20h6"/>',
  hash: '<path d="M5 9h14M5 15h14M10 4 8 20M16 4l-2 16"/>',
  header: '<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M8 7h8M8 17h8"/>',
  water: '<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z"/>',
  pages: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="9" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  rotate: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  crop: '<path d="M6 2v14a2 2 0 0 0 2 2h14"/><path d="M18 22V8a2 2 0 0 0-2-2H2"/>',
  resize: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  extract: '<path d="M14 3h7v7"/><path d="M21 3 10 14"/><path d="M19 14v6H4V5h6"/>',
  highlight: '<path d="m9 11-6 6v3h9l3-3"/><path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/>',
  note: '<path d="M5 4h14v12l-4 4H5z"/><path d="M15 20v-4h4"/>',
  draw: '<path d="M3 17c4-6 6 2 9-3s5-4 9-1"/>',
  shape: '<rect x="3" y="3" width="10" height="10" rx="1"/><circle cx="16" cy="16" r="5"/>',
  stamp: '<path d="M5 21h14"/><path d="M6 17h12v-3a2 2 0 0 0-2-2h-2V8a2 2 0 1 0-4 0v4H8a2 2 0 0 0-2 2z"/>',
  field: '<rect x="3" y="7" width="18" height="10" rx="2"/><path d="M7 12h1"/>',
  comment: '<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  lang: '<path d="M4 5h8M8 3v2c0 4-2 8-5 10"/><path d="M6 10c1 2 3 4 6 5"/><path d="m13 21 4-9 4 9M14.5 18h5"/>',
  table: '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10h18M3 15h18M9 4v16"/>',
  hand: '<path d="M4 20c3 0 4-3 6-3s2 3 5 3 4-6 5-10"/><path d="M14 4l6 6"/>',
  web: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  camera: '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
  wand: '<path d="m15 4 5 5L9 20H4v-5z"/><path d="M13 6l5 5"/>',
  form: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h4"/>',
  fill: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="m8 12 2.5 2.5L16 9"/>',
  collect: '<path d="M4 4h16v6H4zM4 14h16v6H4z"/><path d="M8 7h1M8 17h1"/>',
  redact: '<rect x="3" y="8" width="18" height="8" rx="1" fill="currentColor"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  unlock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 7.5-2"/>',
  clean: '<path d="M3 21h18"/><path d="m7 17 9-9 3 3-9 9H7z"/><path d="m14 6 2-2 4 4-2 2"/>',
  cert: '<circle cx="12" cy="9" r="5"/><path d="m9 13-2 8 5-3 5 3-2-8"/>',
  verify: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
  compare: '<rect x="3" y="4" width="7" height="16" rx="1"/><rect x="14" y="4" width="7" height="16" rx="1"/><path d="M10 9h4M10 15h4"/>',
  access: '<circle cx="12" cy="4.5" r="1.8"/><path d="M5 8h14M12 8v6M9 21l3-7 3 7"/>',
  batch: '<path d="M4 6h16M4 12h16M4 18h10"/><path d="m17 16 2 2 3-4"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8M8 13h5"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  pres: '<rect x="3" y="4" width="18" height="12" rx="1"/><path d="M12 16v4M8 20h8"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
  save: '<path d="M5 3h11l3 3v15H5z"/><path d="M8 3v5h7M8 21v-7h8v7"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  up: '<path d="m18 15-6-6-6 6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  zin: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M8 11h6M11 8v6"/>',
  zout: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M8 11h6"/>',
  fit: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  send: '<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/>',
  key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l3 3"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
  reset: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
};
function icon(name, size = 18, extra = "") {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${ICONS[name] || ""}</svg>`;
}
const SPARK = (s = 12) => `<svg class="spark" width="${s}" height="${s}" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l2.2 6.3L20.5 10.5l-6.3 2.2L12 19l-2.2-6.3L3.5 10.5l6.3-2.2z"/></svg>`;

function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "html") e.innerHTML = v;
    else if (k === "class") e.className = v;
    else if (k === "style" && typeof v === "object") Object.assign(e.style, v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k != null && k !== false) e.append(k.nodeType ? k : document.createTextNode(String(k)));
  return e;
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const trNorm = (s) => String(s || "").toLocaleLowerCase("tr").replace(/[çğıöşüâî]/g, (c) => ({ ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u", â: "a", î: "i" }[c]));

/* ------------------------------------------------------------------ sunucu */
async function http(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { "X-Token": TOKEN, ...(opts.headers || {}) } });
  let data = {};
  try { data = await res.json(); } catch { data = { error: "Sunucu yanıtı okunamadı." }; }
  if (res.status >= 500 && !data.error) data.error = "Sunucu hatası.";
  return data;
}
const post = (path, body) => http(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

/* İşlem çalıştırır: hızlı işler hemen döner, uzun işlerde ilerleme kartı gösterilir. */
async function run(op, args = {}, opt = {}) {
  const data = await post("/api/run", { op, args });
  if (data.error) return fail(data.error, op, args, opt);
  let result = data.result;
  if (data.job) {
    result = await follow(data.job, opt);
    if (result && result.__error) return fail(result.__error, op, args, opt);
    if (result === undefined) return null;
  }
  if (!opt.raw) await handleResult(result || {}, opt);
  return result;
}

function follow(jobId, opt) {
  return new Promise((resolve) => {
    const card = opt.quiet ? null : jobCard(opt.label || "Çalışıyor", () => post(`/api/job/${jobId}/cancel`));
    const t0 = Date.now();
    const tick = async () => {
      const j = await http(`/api/job/${jobId}`);
      if (j.status === "running") {
        if (card && Date.now() - t0 > 250) card.update(j.progress, j.message);
        if (opt.onProgress) opt.onProgress(j);
        setTimeout(tick, 400);
        return;
      }
      if (card) card.close();
      if (j.status === "done") resolve(j.result);
      else resolve({ __error: j.error || "İşlem tamamlanamadı." });
    };
    setTimeout(tick, 150);
  });
}

async function fail(err, op, args, opt) {
  if (err === "API_ANAHTARI_YOK") { await openSettings(true); return null; }
  if (err === "PAROLA_GEREKLI") {
    const v = await dialog({ title: "Bu PDF parolalı", desc: "Açmak için belgenin parolasını gir.", fields: [{ id: "pw", label: "Parola", type: "password" }], ok: "Aç" });
    if (!v) return null;
    return run(op, { ...args, password: v.pw }, opt);
  }
  if (err === "KAYIT_YOLU_GEREKLI") return run("save", { as: true });
  if (err === "İptal edildi." || err === "İşlem iptal edildi.") return null;
  toast(err, { error: true });
  return null;
}

async function handleResult(r, opt) {
  if (r.cancelled) return;
  if (r.opened) { S.selection = null; S.pendingRedact = []; S.marks = {}; S.chat = []; S.panel = { kind: "tools" }; }
  if (r.changed) await refresh();
  if (opt.silent) return;
  if (r.saved || r.message) {
    const acts = [];
    if (r.open_file) acts.push(["Aç", () => post("/api/open_external", { path: r.open_file })]);
    if (r.saved) acts.push(["Klasörde göster", () => post("/api/open_external", { path: r.saved, folder: true })]);
    toast(r.message || "Kaydedildi: " + r.saved.split(/[\\/]/).pop(), { acts, long: !!r.saved });
  }
}

/* ------------------------------------------------------------------ bildirimler */
function toast(text, { error = false, acts = [], long = false } = {}) {
  const t = el("div", { class: "toast" + (error ? " err" : ""), role: error ? "alert" : "status" }, el("div", {}, text));
  if (acts.length) t.append(el("div", { class: "acts" }, acts.map(([l, f]) => el("button", { onclick: () => { f(); t.remove(); } }, l))));
  $("#toasts").append(t);
  setTimeout(() => t.remove(), error ? 9000 : long ? 9000 : 4500);
}

function jobCard(label, onCancel) {
  const bar = el("div", { class: "bar ind" }, el("i"));
  const msg = el("span", {}, label);
  const card = el("div", { class: "toast job" }, el("b", {}, label), bar,
    el("div", { class: "row2" }, msg, el("button", { class: "btn small ghost", onclick: () => { onCancel(); msg.textContent = "İptal ediliyor…"; } }, "İptal")));
  $("#toasts").append(card);
  return {
    update(p, m) {
      if (p > 0.01) { bar.classList.remove("ind"); bar.firstChild.style.width = Math.round(p * 100) + "%"; }
      if (m) msg.textContent = m;
    },
    close() { card.remove(); },
  };
}

/* ------------------------------------------------------------------ pencereler */
function dialog({ title, desc, fields = [], ok = "Tamam", okClass = "primary", cancel = "Vazgeç", wide = false, body = null, extra = [] }) {
  return new Promise((resolve) => {
    const inputs = {};
    const form = el("form", { class: "m-body", onsubmit: (e) => { e.preventDefault(); done(true); } });
    for (const f of fields) {
      const id = "f_" + f.id;
      let input;
      if (f.type === "textarea") input = el("textarea", { class: "input", id, rows: f.rows || 4, placeholder: f.placeholder || "" }, f.value || "");
      else if (f.type === "select") input = el("select", { class: "input", id }, (f.options || []).map((o) => el("option", { value: o[0], selected: o[0] === f.value }, o[1])));
      else if (f.type === "checkbox") input = el("input", { type: "checkbox", id, checked: !!f.value });
      else if (f.type === "checks") {
        input = el("div", { style: { display: "flex", flexDirection: "column", gap: "6px" } },
          f.options.map((o) => el("label", { class: "check" }, el("input", { type: "checkbox", value: o[0], checked: (f.value || []).includes(o[0]) }), o[1])));
      } else input = el("input", { class: "input", id, type: f.type || "text", value: f.value ?? "", placeholder: f.placeholder || "", min: f.min, max: f.max, step: f.step, autocomplete: "off" });
      inputs[f.id] = { f, input };
      if (f.type === "checkbox") form.append(el("label", { class: "check" }, input, f.label));
      else form.append(el("div", { class: "f" }, el("label", { for: id }, f.label), input, f.hint ? el("small", {}, f.hint) : null));
    }
    if (body) form.append(body);
    const read = () => {
      const v = {};
      for (const [k, { f, input }] of Object.entries(inputs)) {
        if (f.type === "checkbox") v[k] = input.checked;
        else if (f.type === "checks") v[k] = $$("input:checked", input).map((x) => x.value);
        else if (f.type === "number") v[k] = input.value === "" ? null : Number(input.value);
        else v[k] = input.value;
      }
      return v;
    };
    const scrim = el("div", { class: "scrim", onmousedown: (e) => { if (e.target === scrim) done(false); } });
    const modal = el("div", { class: "modal" + (wide ? " wide" : ""), role: "dialog", "aria-modal": "true", "aria-label": title },
      el("header", {}, el("h2", {}, title), desc ? el("p", { html: desc }) : null), form,
      el("footer", {}, extra.map(([l, f]) => el("button", { type: "button", class: "btn", onclick: () => f(read(), done) }, l)),
        cancel ? el("button", { type: "button", class: "btn", onclick: () => done(false) }, cancel) : null,
        ok ? el("button", { type: "button", class: "btn " + okClass, onclick: () => done(true) }, ok) : null));
    scrim.append(modal);
    const key = (e) => { if (e.key === "Escape") { e.stopPropagation(); done(false); } };
    document.addEventListener("keydown", key, true);
    function done(okd) {
      document.removeEventListener("keydown", key, true);
      const v = okd ? read() : null;
      scrim.remove();
      resolve(v);
    }
    document.body.append(scrim);
    const first = form.querySelector("input:not([type=checkbox]),textarea,select");
    setTimeout(() => (first || modal.querySelector(".btn.primary"))?.focus(), 30);
  });
}

const confirmBox = (title, desc, ok = "Devam et", okClass = "primary") => dialog({ title, desc, ok, okClass }).then((v) => !!v);

function showText(title, text, { md = false, name = null } = {}) {
  const content = md ? el("div", { class: "msg-ai", html: mdToHtml(text) }) : el("pre", { class: "result" }, text);
  return dialog({
    title, wide: true, body: content, ok: "Kapat", cancel: null,
    extra: [["Kopyala", () => { navigator.clipboard.writeText(text); toast("Kopyalandı."); }],
            ["Metin olarak kaydet", () => run("save_text", { text, name })]],
  });
}

function mdToHtml(src) {
  const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\W)\*(?!\s)(.+?)\*(?=\W|$)/g, "$1<i>$2</i>").replace(/`(.+?)`/g, "<code>$1</code>");
  const out = [];
  let list = null;
  const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const raw of String(src || "").split("\n")) {
    const line = raw.trimEnd();
    let m;
    if ((m = line.match(/^#{1,6}\s+(.*)/))) { close(); out.push(`<h4>${inline(m[1])}</h4>`); }
    else if ((m = line.match(/^\s*[-*•]\s+(.*)/))) { if (list !== "ul") { close(); out.push("<ul>"); list = "ul"; } out.push(`<li>${inline(m[1])}</li>`); }
    else if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) { if (list !== "ol") { close(); out.push("<ol>"); list = "ol"; } out.push(`<li>${inline(m[1])}</li>`); }
    else if (!line.trim()) close();
    else { close(); out.push(`<p>${inline(line)}</p>`); }
  }
  close();
  return out.join("");
}

/* ------------------------------------------------------------------ durum */
const S = {
  info: { open: false }, tab: "edit", panel: { kind: "tools" }, mode: "select", zoom: "fit", scale: 1,
  words: {}, wordsVersion: -1, selection: null, pendingRedact: [], marks: {}, chat: [], assistTab: "doc",
  find: { hits: [], i: -1, q: "" }, curPage: 0, thumbSel: new Set(), ink: {}, sig: null,
  opts: { color: "#FACC15", markup: null, shape: "rect", shapeColor: "#DC2626", width: 2, stamp: "ONAYLANDI", stampColor: "#15803D", stampDate: true, textSize: 12, textColor: "#111111", fieldKind: "text" },
  dismissed: new Set(), workspace: [], keyHint: null,
};

/* ------------------------------------------------------------------ araçlar */
const GROUPS = { edit: "Düzenle", pages: "Sayfalar", mark: "İşaretle", convert: "Dönüştür", forms: "Formlar", protect: "Koru", assistant: "Asistan", create: "Oluştur" };
const TAB_ORDER = ["edit", "pages", "mark", "convert", "forms", "protect"];
const TOOLS = [];
const tool = (id, group, name, desc, ic, run_, o = {}) => TOOLS.push({ id, group, name, desc, icon: ic, run: run_, ai: !!o.ai, doc: o.doc !== false, kw: o.kw || "" });
const pagesField = (value = "") => ({ id: "pages", label: "Sayfalar", value, placeholder: "Tümü (örn. 1-3, 5, 8-)", hint: "Boş bırakırsan bütün sayfalar." });

// Düzenle
tool("edit_text", "edit", "Metni düzenle", "Bir satıra tıkla, yerinde değiştir", "edit", () => setMode("edittext"), { kw: "yazı değiştir düzelt" });
tool("command_edit", "edit", "Komutla düzenle", "“Tüm 2025’leri 2026 yap” gibi yaz, önizle, onayla", "cmd", commandEdit, { ai: true, kw: "bul değiştir" });
tool("rewrite", "edit", "Yeniden yaz", "Seçili metni resmî, sade, kısa ya da uzun yap", "wand", () => S.selection ? rewriteSelection() : setMode("select", { hint: "Önce yeniden yazılacak metni sürükleyerek seç, sonra çıkan çubuktan “Yeniden yaz”a bas." }), { ai: true });
tool("add_image", "edit", "Görsel ekle", "Resim ya da logo yerleştir", "image", () => setMode("image"), { kw: "resim logo" });
tool("edit_images", "edit", "Görseli değiştir ya da sil", "Sayfadaki bir resme tıkla", "image", () => setMode("imgedit"), { kw: "resim" });
tool("textbox", "edit", "Metin kutusu ekle", "Sayfaya yeni yazı ekle", "text", () => setMode("textbox"), { kw: "yazı ekle" });
tool("page_numbers", "edit", "Sayfa numarası", "Numara konumu ve biçimini seç", "hash", pageNumbers);
tool("header_footer", "edit", "Üst ve alt bilgi", "Her sayfaya başlık ya da alt yazı", "header", headerFooter);
tool("bates", "edit", "Bates numarası", "Hukuki belgeler için sıra numarası", "hash", bates);
tool("watermark", "edit", "Filigran", "“GİZLİ”, “TASLAK” ya da logo", "water", watermark);
// Sayfalar
tool("organize", "pages", "Sayfaları düzenle", "Sırala, döndür, sil, çıkar, ekle", "pages", () => showPanel({ kind: "organize" }), { kw: "sırala döndür sil" });
tool("merge", "pages", "Birleştir", "Başka PDF’leri bu belgeye ekle", "merge", () => run("merge", {}, { label: "Birleştiriliyor" }), { doc: false });
tool("split", "pages", "Böl", "Aralığa, sayfa sayısına, boyuta göre", "split", split);
tool("compress", "pages", "Sıkıştır", "Dosyayı küçült; kaliteyi sen seç", "compress", compress, { kw: "küçült boyut" });
tool("crop", "pages", "Kırp", "Kenar boşluklarını kırp", "crop", crop);
tool("resize", "pages", "Sayfa boyutu", "A4, A3, A5, Letter yap", "resize", resize);
tool("rotate", "pages", "Döndür", "Seçili sayfaları döndür", "rotate", rotatePages);
tool("extract", "pages", "Sayfaları ayrı kaydet", "Seçili sayfalardan yeni PDF", "extract", extractPages, { kw: "çıkar ayır" });
tool("delete_pages", "pages", "Sayfa sil", "Seçili sayfaları kaldır", "trash", deletePages);
tool("insert_file", "pages", "Dosyadan sayfa ekle", "Başka PDF ya da resimden", "plus", () => run("insert_file", { after: S.curPage }, { label: "Ekleniyor" }));
// İşaretle
tool("highlight", "mark", "Vurgula ve çiz", "Vurgu, altı çizili, üstü çizili", "highlight", () => setMode("markup"));
tool("note", "mark", "Yapışkan not", "Bir yere tıkla, notunu yaz", "note", () => setMode("note"), { kw: "yorum" });
tool("draw", "mark", "Serbest çizim", "Kalemle çiz", "draw", () => setMode("ink"), { kw: "kalem" });
tool("shapes", "mark", "Şekil", "Kutu, daire, çizgi, ok", "shape", () => setMode("shape"));
tool("stamp", "mark", "Damga", "“Onaylandı”, “Taslak” ya da kendi damgan", "stamp", () => setMode("stamp"), { kw: "mühür" });
tool("sign", "mark", "İmzanı ekle", "Çiz, yaz ya da fotoğrafından al", "sign", () => setMode("signature"), { kw: "imzala" });
tool("sig_field", "mark", "İmza alanı ekle", "Başkasının imzalayacağı yer", "field", () => setMode("sigfield"));
tool("comments", "mark", "Yorumlar ve işaretler", "Tümünü listele, git, sil", "comment", () => showPanel({ kind: "annots" }));
tool("comments_summary", "mark", "Yorumları özetle", "Tüm yorumları yapılacaklar listesine çevir", "list", async () => { const r = await run("ai_comments_summary", {}, { label: "Yorumlar özetleniyor", raw: true }); if (r) showText("Yorumların özeti", r.text, { md: true }); }, { ai: true });
// Dönüştür
tool("to_word", "convert", "Word’e çevir", "Başlık, paragraf ve tablolarla düzenlenebilir .docx", "word", () => convertDialog("ai_to_word", "Word’e çevir"), { ai: true, kw: "docx" });
tool("to_excel", "convert", "Excel’e çevir", "Tablolar sütunlarına ayrılmış .xlsx", "excel", () => convertDialog("ai_to_excel", "Excel’e çevir"), { ai: true, kw: "xlsx tablo" });
tool("to_pptx", "convert", "PowerPoint’e çevir", "Bölümler slayt olur", "ppt", () => convertDialog("ai_to_pptx", "PowerPoint’e çevir"), { ai: true, kw: "pptx slayt" });
tool("searchable", "convert", "Aranabilir PDF yap", "Taranmış sayfalara metin katmanı (metin tanıma)", "scan", () => run("ai_searchable", {}, { label: "Metin tanınıyor" }), { ai: true, kw: "ocr metin tanıma tarama" });
tool("tables", "convert", "Tablo tanıma", "Taranmış tabloları Excel’e aktar", "table", () => convertDialog("ai_to_excel", "Tabloları Excel’e aktar"), { ai: true, kw: "ocr" });
tool("handwriting", "convert", "El yazısını oku", "El yazısı ve taranmış sayfaları metne çevir", "hand", transcribe, { ai: true, kw: "ocr" });
tool("translate", "convert", "Çevir", "Başka dile, düzeni koruyarak", "lang", translate, { ai: true, kw: "tercüme ingilizce" });
tool("to_images", "convert", "Resim olarak kaydet", "PNG ya da JPG", "image", toImages, { kw: "png jpg" });
tool("to_text", "convert", "Metin olarak kaydet", "Tüm metni .txt olarak al", "text", toText, { kw: "txt" });
// Formlar
tool("detect_fields", "forms", "Doldurulabilir yap", "Boşlukları bulur, alanlara çevirir", "wand", detectFields, { ai: true, kw: "form hazırla" });
tool("fill", "forms", "Formu doldur", "Alanlara yaz, işaretle", "fill", () => showPanel({ kind: "fields" }));
tool("autofill", "forms", "Otomatik doldur", "Bilgilerinden ya da başka belgeden", "user", autofill, { ai: true });
tool("add_field", "forms", "Alan ekle", "Elle yazı, onay kutusu, liste alanı", "field", () => setMode("field"));
tool("create_form", "forms", "Yeni form oluştur", "Anlat, form hazır olsun", "form", createForm, { ai: true, doc: false });
tool("collect", "forms", "Yanıtları Excel’de topla", "Doldurulmuş formlardan tek tablo", "collect", () => run("collect_responses", {}, { label: "Yanıtlar toplanıyor" }), { doc: false });
// Koru
tool("ai_redact", "protect", "Yapay zekâ ile karart", "TC no, IBAN, telefon bulunur; sen onaylarsın", "redact", aiRedact, { ai: true, kw: "gizle sansür kvkk" });
tool("redact", "protect", "Elle karart", "Alanları seç, kalıcı olarak kapat", "redact", () => setMode("redact"), { kw: "sansür" });
tool("protect", "protect", "Parola ve izinler", "Açılış parolası, yazdırma ve kopyalama kısıtı", "lock", protect, { kw: "şifre" });
tool("unlock", "protect", "Parolayı kaldır", "Parolasız bir kopya kaydet", "unlock", () => run("unlock"), { kw: "şifre" });
tool("sanitize", "protect", "Gizli veriyi temizle", "Meta veri, gizli katman, ekler", "clean", sanitize);
tool("digisign", "protect", "Dijital imza", "Sertifikayla imzala", "cert", () => showPanel({ kind: "digisign" }), { kw: "e-imza sertifika" });
tool("verify", "protect", "İmzaları doğrula", "Belge imzadan sonra değişmiş mi", "verify", () => showPanel({ kind: "verify" }));
tool("compare", "protect", "Belge karşılaştır", "Farkları işaretle, neyin değiştiğini özetle", "compare", compare, { kw: "fark sürüm" });
tool("access", "protect", "Erişilebilirlik", "Denetim, görsel açıklamaları, otomatik düzeltme", "access", () => showPanel({ kind: "access" }));
tool("batch", "protect", "Toplu işlem", "Bir klasördeki tüm PDF’lere aynı işlem", "batch", batch, { doc: false });
// Asistan
tool("summary", "assistant", "Özetle", "Belgenin kısa özeti ve ana noktalar", "summary", () => askAssistant("__summary"), { ai: true });
tool("chat", "assistant", "Belgeyle sohbet", "Sor, cevabı sayfasıyla gelsin", "chat", () => openAssistant("doc"), { ai: true, kw: "soru sor" });
tool("workspace", "assistant", "Çoklu belge alanı", "Birden çok PDF’e birlikte soru sor", "folder", () => openAssistant("ws"), { ai: true });
tool("presentation", "assistant", "Sunuma çevir", "Belgeden anlatımı kurulmuş bir sunum", "pres", () => convertDialog("ai_to_pptx", "Sunuma çevir", "story"), { ai: true });
tool("report", "assistant", "Grafik ve rapor", "Belgedeki sayılardan grafikler", "chart", report, { ai: true });
tool("extract_info", "assistant", "Bilgi çıkar", "Fatura, sözleşme alanlarını tabloya al (toplu)", "table", extractInfo, { ai: true, doc: false, kw: "fatura excel" });
// Oluştur
tool("from_files", "create", "Dosyalardan PDF", "Word, Excel, PowerPoint ya da resimden", "file", () => run("from_files", {}, { label: "PDF oluşturuluyor" }), { doc: false, kw: "word excel resim dönüştür" });
tool("from_web", "create", "Web sayfasından PDF", "Bir adresi PDF olarak kaydet", "web", fromWeb, { doc: false });
tool("from_text", "create", "Metinden PDF", "Anlat; dilekçe, teklif, mektup hazırlansın", "wand", fromText, { ai: true, doc: false });
tool("fix_photos", "create", "Fotoğraftan tara", "Telefon fotoğrafını düzleştirip PDF yap", "camera", fixPhotos, { doc: false, kw: "tarama" });

const toolById = (id) => TOOLS.find((t) => t.id === id);

async function useTool(t) {
  closePalette();
  if (t.doc && !S.info.open) {
    const r = await run("open", {}, { silent: true });
    if (!r || !S.info.open) return;
  }
  if (S.info.open && t.group !== "create" && t.group !== "assistant" && TAB_ORDER.includes(t.group)) S.tab = t.group;
  await t.run();
  renderTop();
}

/* ------------------------------------------------------------------ araç pencereleri */
async function pageNumbers() {
  const v = await dialog({ title: "Sayfa numarası", fields: [
    { id: "position", label: "Konum", type: "select", value: "bottom-center", options: [["bottom-center", "Alt orta"], ["bottom-right", "Alt sağ"], ["bottom-left", "Alt sol"], ["top-center", "Üst orta"], ["top-right", "Üst sağ"], ["top-left", "Üst sol"]] },
    { id: "format", label: "Biçim", type: "select", value: "{n} / {total}", options: [["{n}", "1"], ["{n} / {total}", "1 / 12"], ["Sayfa {n}", "Sayfa 1"], ["Sayfa {n} / {total}", "Sayfa 1 / 12"], ["- {n} -", "- 1 -"]] },
    { id: "start", label: "Başlangıç numarası", type: "number", value: 1, min: 0 }, pagesField(),
    { id: "size", label: "Yazı boyutu", type: "number", value: 9, min: 6, max: 20 }], ok: "Ekle" });
  if (v) run("page_numbers", v);
}
async function headerFooter() {
  const v = await dialog({ title: "Üst ve alt bilgi", desc: "{n} sayfa numarası, {total} toplam sayfa, {tarih} bugünün tarihi olur.", fields: [
    { id: "header", label: "Üst bilgi", placeholder: "örn. Gizli — {tarih}" }, { id: "footer", label: "Alt bilgi", placeholder: "örn. Şirket adı · Sayfa {n}/{total}" },
    { id: "align", label: "Hizalama", type: "select", value: "center", options: [["left", "Sol"], ["center", "Orta"], ["right", "Sağ"]] },
    { id: "size", label: "Yazı boyutu", type: "number", value: 9, min: 6, max: 20 }], ok: "Ekle" });
  if (v && (v.header || v.footer)) run("header_footer", v);
}
async function bates() {
  const v = await dialog({ title: "Bates numarası", desc: "Her sayfanın sağ altına sıra numarası eklenir.", fields: [
    { id: "prefix", label: "Ön ek", value: "DAVA-" }, { id: "start", label: "Başlangıç", type: "number", value: 1 }, { id: "digits", label: "Basamak", type: "number", value: 6, min: 3, max: 10 }], ok: "Ekle" });
  if (v) run("bates", v);
}
async function watermark() {
  const v = await dialog({ title: "Filigran", fields: [
    { id: "text", label: "Yazı", value: "GİZLİ" }, { id: "opacity", label: "Saydamlık (0.05–0.6)", type: "number", value: 0.15, step: 0.05, min: 0.05, max: 0.6 },
    { id: "angle", label: "Açı", type: "number", value: 45, min: -90, max: 90 },
    { id: "color", label: "Renk", type: "select", value: "#B91C1C", options: [["#B91C1C", "Kırmızı"], ["#1E3A8A", "Lacivert"], ["#374151", "Gri"], ["#15803D", "Yeşil"]] }, pagesField()], ok: "Ekle" });
  if (v) run("watermark", v);
}
async function split() {
  const v = await dialog({ title: "Böl", fields: [
    { id: "mode", label: "Nasıl bölünsün?", type: "select", value: "every", options: [["every", "Her N sayfada bir"], ["ranges", "Belirli aralıklara göre"], ["size", "Dosya boyutuna göre (MB)"], ["bookmarks", "Yer imlerine (bölümlere) göre"]] },
    { id: "value", label: "Değer", value: "1", hint: "Her N sayfa: 1, 2…  Aralıklar: 1-3; 4-10; 11-  Boyut: 5 (MB)" }], ok: "Böl ve klasör seç" });
  if (v) run("split", v, { label: "Bölünüyor" });
}
async function compress() {
  const v = await dialog({ title: "Sıkıştır", desc: `Şu anki boyut: <b>${fmtSize(S.info.size)}</b>`, fields: [
    { id: "level", label: "Seviye", type: "select", value: "medium", options: [["low", "Az (en iyi kalite)"], ["medium", "Orta (önerilen)"], ["high", "Çok (e-posta, WhatsApp için)"]] }], ok: "Sıkıştır" });
  if (v) run("compress", v, { label: "Sıkıştırılıyor" });
}
async function crop() {
  const v = await dialog({ title: "Kırp", desc: "Kenarlardan kesilecek pay (milimetre).", fields: [
    { id: "top", label: "Üst", type: "number", value: 10 }, { id: "bottom", label: "Alt", type: "number", value: 10 },
    { id: "left", label: "Sol", type: "number", value: 10 }, { id: "right", label: "Sağ", type: "number", value: 10 }, pagesField()], ok: "Kırp" });
  if (v) run("crop", v);
}
async function resize() {
  const v = await dialog({ title: "Sayfa boyutu", fields: [{ id: "size", label: "Boyut", type: "select", value: "A4", options: [["A4", "A4"], ["A3", "A3"], ["A5", "A5"], ["Letter", "Letter"], ["Legal", "Legal"]] }], ok: "Uygula" });
  if (v) run("resize", v, { label: "Boyutlandırılıyor" });
}
const selPages = () => S.thumbSel.size ? [...S.thumbSel].sort((a, b) => a - b).map((p) => p + 1).join(",") : String(S.curPage + 1);
async function rotatePages() {
  const v = await dialog({ title: "Döndür", fields: [pagesField(selPages()), { id: "angle", label: "Yön", type: "select", value: "90", options: [["90", "Sağa 90°"], ["-90", "Sola 90°"], ["180", "180°"]] }], ok: "Döndür" });
  if (v) run("rotate", { pages: v.pages, angle: Number(v.angle) });
}
async function extractPages() {
  const v = await dialog({ title: "Sayfaları ayrı kaydet", fields: [pagesField(selPages())], ok: "Kaydet" });
  if (v) run("extract_pages", v);
}
async function deletePages() {
  const v = await dialog({ title: "Sayfa sil", fields: [pagesField(selPages())], ok: "Sil", okClass: "danger" });
  if (v) { S.thumbSel.clear(); run("delete_pages", v); }
}
async function convertDialog(op, title, mode) {
  const fields = [pagesField()];
  if (op === "ai_to_pptx") fields.push({ id: "mode", label: "Tarz", type: "select", value: mode || "pages", options: [["pages", "Belgenin bölümlerini slayt yap"], ["story", "Anlatımı yeniden kur (sunum)"]] });
  const v = await dialog({ title, desc: `${SPARK()} Belge Claude’a gönderilir; uzun belgeler birkaç dakika sürebilir.`, fields, ok: "Başla" });
  if (v) run(op, v, { label: title });
}
async function transcribe() {
  const v = await dialog({ title: "El yazısını ve taranmış metni oku", fields: [pagesField(S.info.scanned?.length ? S.info.scanned.map((p) => p + 1).join(",") : "")], ok: "Oku" });
  if (!v) return;
  const r = await run("ai_transcribe", v, { label: "Metin okunuyor", raw: true });
  if (r) showText("Okunan metin", r.text, { name: stemName() + ".txt" });
}
async function toText() {
  const r = S.info.scanned?.length ? await run("ai_to_text", {}, { label: "Metin çıkarılıyor", raw: true }) : await run("to_text_local", {}, { raw: true });
  if (r) showText("Belgenin metni", r.text, { name: stemName() + ".txt" });
}
const LANGS = [["English", "İngilizce"], ["German", "Almanca"], ["French", "Fransızca"], ["Spanish", "İspanyolca"], ["Arabic", "Arapça"], ["Russian", "Rusça"], ["Italian", "İtalyanca"], ["Dutch", "Felemenkçe"], ["Turkish", "Türkçe"]];
async function translate() {
  const v = await dialog({ title: "Çevir", desc: `${SPARK()} Belge Claude ile çevrilir.`, fields: [
    { id: "lang", label: "Hedef dil", type: "select", value: "English", options: LANGS },
    { id: "output", label: "Çıktı", type: "select", value: "pdf", options: [["pdf", "Aynı düzende PDF"], ["docx", "Düzenlenebilir Word"]] }, pagesField()], ok: "Çevir" });
  if (v) run("ai_translate", v, { label: "Çevriliyor" });
}
async function toImages() {
  const v = await dialog({ title: "Resim olarak kaydet", fields: [
    { id: "format", label: "Biçim", type: "select", value: "png", options: [["png", "PNG"], ["jpg", "JPG"]] },
    { id: "dpi", label: "Çözünürlük (DPI)", type: "select", value: "150", options: [["96", "96 (ekran)"], ["150", "150 (önerilen)"], ["300", "300 (baskı)"]] }, pagesField()], ok: "Klasör seç ve kaydet" });
  if (v) run("to_images", { ...v, dpi: Number(v.dpi) }, { label: "Resimler kaydediliyor" });
}
async function detectFields() {
  const v = await dialog({ title: "Doldurulabilir yap", desc: `${SPARK()} Claude sayfadaki boşlukları, kutuları ve imza yerlerini bulup doldurulabilir alana çevirir.`, fields: [pagesField()], ok: "Başla" });
  if (!v) return;
  const r = await run("ai_detect_fields", v, { label: "Alanlar bulunuyor" });
  if (r) showPanel({ kind: "fields" });
}
async function autofill() {
  const v = await dialog({ title: "Otomatik doldur", desc: `${SPARK()} Claude form alanlarını bilgilerinle eşleştirir; bilmediği alanı boş bırakır.`, fields: [
    { id: "source", label: "Bilgiler nereden alınsın?", type: "select", value: "profile", options: [["profile", "Ayarlar’daki “Bilgilerim”"], ["file", "Başka bir belgeden (kimlik, eski form…)"]] }], ok: "Doldur" });
  if (!v) return;
  const r = await run("ai_autofill", v, { label: "Form dolduruluyor" });
  if (r) showPanel({ kind: "fields" });
}
async function createForm() {
  const v = await dialog({ title: "Yeni form oluştur", desc: `${SPARK()} Nasıl bir form istediğini anlat.`, fields: [{ id: "description", label: "Form", type: "textarea", placeholder: "örn. Personel izin talep formu: ad soyad, birim, izin türü (yıllık/mazeret/rapor), başlangıç ve bitiş tarihi, açıklama, yönetici onayı ve imza" }], ok: "Oluştur" });
  if (v && await guardDirty()) run("ai_create_form", v, { label: "Form tasarlanıyor" });
}
async function aiRedact() {
  const v = await dialog({ title: "Yapay zekâ ile karart", desc: `${SPARK()} Claude seçtiğin türdeki bilgileri bulur; hepsini kontrol edip onayladıktan sonra kalıcı olarak karartılır.`, fields: [
    { id: "types", label: "Neler aransın?", type: "checks", value: ["tc", "iban", "phone", "email", "address", "card"], options: [["tc", "TC kimlik numarası"], ["iban", "IBAN ve hesap numarası"], ["phone", "Telefon"], ["email", "E-posta"], ["address", "Adres"], ["name", "Kişi adları"], ["card", "Kart numarası"], ["birth", "Doğum tarihi"], ["plate", "Araç plakası"], ["health", "Sağlık bilgisi"], ["money", "Tutarlar, maaş"]] },
    { id: "custom", label: "Başka bir şey (isteğe bağlı)", placeholder: "örn. müşteri numaraları" }], ok: "Ara" });
  if (!v) return;
  const r = await run("ai_find_sensitive", v, { label: "Hassas bilgiler aranıyor", raw: true });
  if (r) { S.redactFound = r.items.map((it) => ({ ...it, on: it.found > 0 })); showPanel({ kind: "redact_review", scanned: r.scanned }); }
}
async function protect() {
  const v = await dialog({ title: "Parola ve izinler", desc: "Korumalı bir kopya kaydedilir; açık belge değişmez.", fields: [
    { id: "user_pw", label: "Açılış parolası", type: "password", hint: "Boş bırakırsan herkes açabilir ama izinler geçerli olur." },
    { id: "owner_pw", label: "İzin parolası (isteğe bağlı)", type: "password", hint: "İzinleri değiştirmek için gereken parola." },
    { id: "allow", label: "İzin verilenler", type: "checks", value: ["print", "copy"], options: [["print", "Yazdırma"], ["copy", "Metin kopyalama"], ["edit", "Düzenleme"], ["annotate", "Yorum ve form doldurma"]] }], ok: "Kaydet" });
  if (v) run("protect", v);
}
async function sanitize() {
  if (await confirmBox("Gizli veriyi temizle", "Meta veri (yazar, program), gizli metin, ekli dosyalar, betikler ve küçük resimler silinir. Görünen içerik değişmez.", "Temizle"))
    run("sanitize");
}
async function compare() {
  const r = await run("compare", {}, { label: "Karşılaştırılıyor", raw: true });
  if (!r || r.cancelled) return;
  S.compare = r;
  S.marks = {};
  for (const [p, rects] of Object.entries(r.marks || {})) S.marks[p] = rects.map((rc) => ({ rect: rc, cls: "mark-diff" }));
  drawMarks();
  showPanel({ kind: "compare" });
}
async function batch() {
  const v = await dialog({ title: "Toplu işlem", desc: "Bir klasördeki bütün PDF’lere aynı işlem uygulanır; sonuçlar “PDF Stüdyo çıktısı” klasörüne yazılır.", fields: [
    { id: "action", label: "İşlem", type: "select", value: "compress", options: [["compress", "Sıkıştır"], ["searchable", "✦ Aranabilir PDF yap (metin tanıma)"], ["to_word", "✦ Word’e çevir"], ["to_text", "✦ Metin olarak kaydet"], ["watermark", "Filigran ekle"], ["page_numbers", "Sayfa numarası ekle"], ["protect", "Parola koy"], ["sanitize", "Gizli veriyi temizle"], ["images", "Resim olarak kaydet"]] },
    { id: "text", label: "Filigran yazısı", value: "GİZLİ" }, { id: "password", label: "Parola (Parola koy için)", type: "password" }], ok: "Klasör seç ve başla" });
  if (v) run("batch", v, { label: "Toplu işlem" });
}
async function report() {
  const v = await dialog({ title: "Grafik ve rapor", desc: `${SPARK()} Claude belgedeki sayılardan grafikler ve öne çıkan rakamlar hazırlar.`, fields: [{ id: "request", label: "Özellikle görmek istediğin (isteğe bağlı)", placeholder: "örn. aylık giderleri karşılaştır" }], ok: "Hazırla" });
  if (!v) return;
  const r = await run("ai_report", v, { label: "Rapor hazırlanıyor", raw: true });
  if (!r) return;
  const frame = el("iframe", { class: "report", sandbox: "", title: "Rapor" });
  frame.srcdoc = r.html;
  dialog({ title: r.title, wide: true, body: frame, ok: "Kapat", cancel: null,
    extra: [["PDF olarak kaydet", () => run("report_to_pdf", {})], ["PDF olarak aç", async (_, done) => { done(false); if (await guardDirty()) run("report_to_pdf", { open: true }); }]] });
}
async function extractInfo() {
  const v = await dialog({ title: "Bilgi çıkar", desc: `${SPARK()} Claude belgeden alanları okur. Alan adı vermezsen belge türüne göre kendisi seçer.`, fields: [
    { id: "fields", label: "Alanlar (isteğe bağlı, virgülle)", placeholder: "örn. Fatura no, Tarih, Satıcı, KDV, Toplam" },
    { id: "batch", label: "Birden çok belgeden al ve tek Excel tablosuna yaz", type: "checkbox", value: !S.info.open }], ok: "Başla" });
  if (!v) return;
  if (!v.batch && !S.info.open) { const o = await run("open", {}, { silent: true }); if (!o || !S.info.open) return; }
  const r = await run("ai_extract", v, { label: "Bilgiler çıkarılıyor", raw: !v.batch });
  if (r && r.fields) { S.extracted = r.fields; showPanel({ kind: "extracted" }); }
}
async function fromWeb() {
  const v = await dialog({ title: "Web sayfasından PDF", fields: [{ id: "url", label: "Adres", placeholder: "https://…" }], ok: "Oluştur" });
  if (v && v.url && await guardDirty()) run("from_web", v, { label: "Sayfa indiriliyor" });
}
async function fromText() {
  const v = await dialog({ title: "Metinden PDF", desc: `${SPARK()} Ne hazırlanacağını anlat; Claude yazar, PDF olarak açılır.`, fields: [{ id: "description", label: "Belge", type: "textarea", rows: 5, placeholder: "örn. Ev sahibime kira artışına itiraz eden kısa ve resmî bir dilekçe. Adım Yusuf, adres Bursa…" }], ok: "Hazırla" });
  if (v && v.description && await guardDirty()) run("ai_from_text", v, { label: "Belge yazılıyor" });
}
async function fixPhotos() {
  const v = await dialog({ title: "Fotoğraftan tara", desc: "Telefonla çektiğin belge fotoğraflarını seç: kenarlar bulunur, sayfa düzleştirilir, okunurluk artırılır.", fields: [{ id: "bw", label: "Siyah beyaz (metin belgeleri için)", type: "checkbox" }], ok: "Fotoğrafları seç" });
  if (v && await guardDirty()) run("fix_photos", v, { label: "Fotoğraflar düzeltiliyor" });
}
async function commandEdit() {
  const v = await dialog({ title: "Komutla düzenle", desc: `${SPARK()} Ne değişsin, yaz. Claude değişiklikleri hazırlar; önce sen görürsün.`, fields: [{ id: "instruction", label: "Komut", type: "textarea", placeholder: "örn. Tüm 2025 tarihlerini 2026 yap. Kiracı adını Mehmet Öztürk olarak değiştir." }], ok: "Hazırla" });
  if (!v || !v.instruction) return;
  const r = await run("ai_command", v, { label: "Değişiklikler hazırlanıyor", raw: true });
  if (r) { S.changes = r.changes.map((c) => ({ ...c, on: c.found > 0 })); showPanel({ kind: "changes", note: r.note }); }
}

async function guardDirty() {
  if (!S.info.open || !S.info.dirty) return true;
  return confirmBox("Kaydedilmemiş değişiklikler var", `“${esc(S.info.name)}” kaydedilmedi. Devam edersen değişiklikler kaybolur.`, "Kaydetmeden devam et", "danger");
}

/* ------------------------------------------------------------------ üst çubuk ve ana ekran */
function renderTop() {
  const o = S.info.open;
  $("#homeBtn").hidden = !o;
  $("#tabs").hidden = !o;
  $("#undoBtn").hidden = !o;
  $("#redoBtn").hidden = !o;
  $("#saveBtn").hidden = !o;
  $("#assistBtn").hidden = !o;
  $("#docTitle").textContent = o ? S.info.name : "PDF Stüdyo";
  $("#docSub").textContent = o ? `${S.info.count} sayfa · ${fmtSize(S.info.size)} · ${S.info.dirty ? "kaydedilmedi" : "kaydedildi"}` : "";
  document.title = o ? `${S.info.dirty ? "• " : ""}${S.info.name} — PDF Stüdyo` : "PDF Stüdyo";
  $("#undoBtn").disabled = !S.info.can_undo;
  $("#redoBtn").disabled = !S.info.can_redo;
  $("#assistBtn").classList.toggle("on", S.panel.kind === "assistant");
  const tabs = $("#tabs");
  tabs.replaceChildren(...TAB_ORDER.map((g) => el("button", { class: "tab" + (S.tab === g && S.panel.kind !== "assistant" ? " on" : ""), onclick: () => { S.tab = g; setMode("select", { quiet: true }); showPanel({ kind: "tools" }); } }, GROUPS[g])));
}
const fmtSize = (n) => !n ? "" : n < 1048576 ? Math.round(n / 1024) + " KB" : (n / 1048576).toFixed(1) + " MB";
const stemName = () => (S.info.name || "belge").replace(/\.[^.]+$/, "");

function tileFor(t) {
  return el("button", { class: "tile", onclick: () => useTool(t) },
    el("span", { html: icon(t.icon, 22), style: { color: "var(--accent)" } }),
    el("b", {}, t.name),
    t.ai ? el("small", { class: "ai", html: SPARK() + "Claude" }) : el("small", {}, "Bilgisayarında"));
}

async function renderHome() {
  $("#quickTiles").replaceChildren(...["to_word", "searchable", "summary", "merge", "compress", "sign"].map((id) => tileFor(toolById(id))));
  $("#createTiles").replaceChildren(...["from_files", "from_text", "create_form", "fix_photos", "from_web", "batch"].map((id) => tileFor(toolById(id))));
  const r = await http("/api/recent");
  const box = $("#recent");
  const items = r.recent || [];
  if (!items.length) { box.replaceChildren(el("div", { class: "empty-note" }, "Açtığın belgeler burada görünecek.")); return; }
  box.replaceChildren(...items.map((it) => el("button", { onclick: () => openPath(it.path) },
    el("div", { class: "ph" }),
    el("div", { class: "t" }, el("b", {}, it.name), el("small", {}, `${it.pages} sayfa · ${it.path}`)),
    el("span", { class: "w" }, when(it.when)))));
}
function when(ts) {
  const d = new Date(ts * 1000), now = new Date();
  const days = Math.floor((now - d) / 86400000);
  if (d.toDateString() === now.toDateString()) return "Bugün";
  if (days < 2) return "Dün";
  return d.toLocaleDateString("tr-TR", { day: "numeric", month: "long" });
}
async function openPath(path) {
  if (!(await guardDirty())) return;
  await run("open", { path }, { silent: true, label: "Açılıyor" });
}

/* ------------------------------------------------------------------ yenileme */
async function refresh() {
  const info = await http("/api/info");
  const prevName = S.info.name, prevVersion = S.info.version;
  S.info = info;
  renderTop();
  if (!info.open) {
    $("#home").hidden = false;
    $("#editor").hidden = true;
    renderHome();
    return;
  }
  $("#home").hidden = true;
  $("#editor").hidden = false;
  if (prevName !== info.name) { S.curPage = 0; S.thumbSel.clear(); S.find = { hits: [], i: -1, q: "" }; }
  if (prevVersion !== info.version) { S.words = {}; S.selection = null; hideMinibar(); }
  renderThumbs();
  renderPages();
  renderBanner();
  renderPanel();
}

/* ------------------------------------------------------------------ küçük resimler */
let dragFrom = null;
function renderThumbs() {
  const box = $("#thumbs");
  const v = S.info.version;
  box.replaceChildren(...S.info.pages.map((p, i) => {
    const img = el("img", { alt: "", loading: "lazy", src: `/api/page/${i}.jpg?w=176&v=${v}&t=${TOKEN}`, style: { aspectRatio: `${p.w} / ${p.h}` } });
    const b = el("button", {
      class: "thumb" + (i === S.curPage ? " on" : "") + (S.thumbSel.has(i) ? " sel" : ""), draggable: "true", "aria-label": `Sayfa ${i + 1}`,
      onclick: (e) => {
        if (e.ctrlKey || e.shiftKey) { S.thumbSel.has(i) ? S.thumbSel.delete(i) : S.thumbSel.add(i); renderThumbs(); if (S.panel.kind === "organize") renderPanel(); return; }
        S.thumbSel.clear(); scrollToPage(i);
      },
      oncontextmenu: (e) => { e.preventDefault(); if (!S.thumbSel.has(i)) { S.thumbSel = new Set([i]); } renderThumbs(); S.tab = "pages"; showPanel({ kind: "organize" }); },
      ondragstart: (e) => { dragFrom = i; e.dataTransfer.effectAllowed = "move"; },
      ondragover: (e) => { if (dragFrom == null) return; e.preventDefault(); $$(".thumb", box).forEach((t) => t.classList.remove("drop-before")); b.classList.add("drop-before"); },
      ondragleave: () => b.classList.remove("drop-before"),
      ondrop: (e) => {
        e.preventDefault(); e.stopPropagation(); b.classList.remove("drop-before");
        if (dragFrom == null || dragFrom === i) { dragFrom = null; return; }
        const order = [...Array(S.info.count).keys()];
        const [m] = order.splice(dragFrom, 1);
        order.splice(dragFrom < i ? i - 1 : i, 0, m);
        dragFrom = null;
        run("reorder", { order });
      },
      ondragend: () => { dragFrom = null; $$(".thumb", box).forEach((t) => t.classList.remove("drop-before")); },
    }, img, el("span", {}, i + 1));
    return b;
  }));
}

/* ------------------------------------------------------------------ sayfalar */
let observer = null;
function computeScale() {
  const avail = Math.max(200, $("#pages").clientWidth - 56);
  const maxW = Math.max(...S.info.pages.map((p) => p.w));
  const fit = Math.min(avail / maxW, 2.2);
  S.fitScale = fit;
  S.scale = S.zoom === "fit" ? fit : S.zoom;
  $("#zoomLabel").textContent = Math.round(S.scale / (96 / 72) * 100) + "%";
}
function renderPages() {
  computeScale();
  const box = $("#pages");
  const keep = box.scrollTop / Math.max(1, box.scrollHeight);
  if (observer) observer.disconnect();
  observer = new IntersectionObserver((entries) => {
    for (const en of entries) if (en.isIntersecting) loadPageImage(en.target);
  }, { root: box, rootMargin: "800px 0px" });
  const pages = S.info.pages.map((p, i) => {
    const w = Math.round(p.w * S.scale), hgt = Math.round(p.h * S.scale);
    const ov = el("div", { class: "ov" });
    const d = el("div", { class: "page", "data-p": i, style: { width: w + "px", height: hgt + "px" } }, el("img", { alt: `Sayfa ${i + 1}` }), ov, el("div", { class: "pno" }, i + 1));
    attachOverlay(ov, i);
    observer.observe(d);
    return d;
  });
  box.replaceChildren(...pages);
  if (keep) box.scrollTop = keep * box.scrollHeight;
  applyModeClass();
  drawMarks();
  drawSelection();
  drawInk();
}
function loadPageImage(d) {
  const i = Number(d.dataset.p);
  const w = Math.min(3000, Math.round(parseFloat(d.style.width) * DPR));
  const src = `/api/page/${i}.png?w=${w}&v=${S.info.version}&t=${TOKEN}`;
  const img = d.querySelector("img");
  if (img.getAttribute("src") !== src) img.src = src;
  ensureWords(i);   // seçim için kelimeleri önceden al
}
const pageEl = (i) => $(`.page[data-p="${i}"]`);
function scrollToPage(i, y = null) {
  const d = pageEl(i);
  if (!d) return;
  const box = $("#pages");
  box.scrollTop = d.offsetTop - 18 + (y != null ? Math.max(0, y * S.scale - 120) : 0);
  S.curPage = i;
  updateThumbOn();
}
function updateThumbOn() {
  $$(".thumb").forEach((t, k) => t.classList.toggle("on", k === S.curPage));
  const on = $$(".thumb")[S.curPage];
  if (on) on.scrollIntoView({ block: "nearest" });
}
function setZoom(z) {
  const box = $("#pages");
  const rel = box.scrollTop / Math.max(1, box.scrollHeight);
  S.zoom = z === "fit" ? "fit" : Math.max(0.4, Math.min(4, z));
  renderPages();
  box.scrollTop = rel * box.scrollHeight;
}

/* ------------------------------------------------------------------ uyarı şeridi */
function renderBanner() {
  const box = $("#banner");
  box.replaceChildren();
  const key = (k) => `${S.info.name}:${k}`;
  let msg = null, acts = [];
  if (S.info.scanned?.length && !S.dismissed.has(key("scan"))) {
    msg = `Bu belgenin ${S.info.scanned.length === S.info.count ? "tüm sayfaları" : S.info.scanned.length + " sayfası"} taranmış görünüyor. Metni seçebilmek ve içinde arama yapabilmek için metin tanıma yapılsın mı?`;
    acts = [[SPARK() + " Metin tanıma yap", "primary", () => run("ai_searchable", {}, { label: "Metin tanınıyor" })], ["Şimdi değil", "ghost", () => { S.dismissed.add(key("scan")); renderBanner(); }]];
  } else if (S.info.has_fields && !S.dismissed.has(key("form"))) {
    msg = "Bu belgede doldurulabilir form alanları var.";
    acts = [["Formu doldur", "primary", () => { S.tab = "forms"; showPanel({ kind: "fields" }); }], ["Kapat", "ghost", () => { S.dismissed.add(key("form")); renderBanner(); }]];
  }
  if (!msg) return;
  box.append(el("div", { class: "banner", role: "status" }, el("span", { html: icon("info", 18) }), el("span", {}, msg),
    ...acts.map(([l, c, f]) => el("button", { class: "btn small " + c, html: l, onclick: f }))));
}

/* ------------------------------------------------------------------ çizim modları */
const MODE_CLASS = { select: "select", markup: "select", edittext: "pick", imgedit: "pick", note: "point", ink: "cross", shape: "cross", stamp: "cross", signature: "cross", image: "cross", textbox: "cross", field: "cross", sigfield: "cross", redact: "cross", digisign: "cross" };
function setMode(mode, opt = {}) {
  S.mode = mode;
  if (mode !== "select" && mode !== "markup") { S.selection = null; hideMinibar(); drawSelection(); }
  applyModeClass();
  if (mode === "imgedit") loadImageBoxes();
  else clearImageBoxes();
  if (!opt.quiet) showPanel(mode === "select" ? (opt.hint ? { kind: "hint", text: opt.hint } : { kind: "tools" }) : { kind: "mode" });
}
function applyModeClass() {
  $$(".page .ov").forEach((o) => { o.className = "ov " + (MODE_CLASS[S.mode] || "select"); });
}
function pt(ov, e) {
  const r = ov.getBoundingClientRect();
  return [(e.clientX - r.left) / S.scale, (e.clientY - r.top) / S.scale];
}

function attachOverlay(ov, page) {
  let start = null, rectEl = null, inkPath = null;
  ov.addEventListener("mousedown", async (e) => {
    if (e.button !== 0) return;
    S.curPage = page; updateThumbOn();
    const p = pt(ov, e);
    const m = S.mode;
    if (m === "select" || m === "markup") { startSelect(page, p, e); return; }
    if (m === "note") { placeNote(page, p); return; }
    if (m === "edittext") { await ensureWords(page); editLineAt(page, p); return; }
    if (m === "imgedit") return;
    if (m === "ink") {
      inkPath = [p];
      (S.ink[page] ||= []).push(inkPath);
      const move = (ev) => { inkPath.push(pt(ov, ev)); drawInk(page); };
      const up = () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); renderPanel(); };
      window.addEventListener("mousemove", move); window.addEventListener("mouseup", up);
      return;
    }
    start = p;
    rectEl = el("div", { class: "drag-rect" });
    ov.append(rectEl);
    const move = (ev) => {
      const q = pt(ov, ev);
      const [x0, y0, x1, y1] = [Math.min(start[0], q[0]), Math.min(start[1], q[1]), Math.max(start[0], q[0]), Math.max(start[1], q[1])];
      Object.assign(rectEl.style, { left: x0 * S.scale + "px", top: y0 * S.scale + "px", width: (x1 - x0) * S.scale + "px", height: (y1 - y0) * S.scale + "px" });
    };
    const up = (ev) => {
      window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up);
      const q = pt(ov, ev);
      rectEl.remove();
      finishDrag(page, start, q);
    };
    window.addEventListener("mousemove", move); window.addEventListener("mouseup", up);
  });
  ov.addEventListener("dblclick", async (e) => {
    if (S.mode !== "select" && S.mode !== "markup") return;
    await ensureWords(page);
    const i = wordAt(page, pt(ov, e), true);
    if (i >= 0) { S.selection = { page, a: i, b: i }; drawSelection(); afterSelect(); }
  });
}

const DEFAULT_SIZE = { stamp: [170, 46], signature: [160, 60], textbox: [220, 40], field: [180, 20], sigfield: [190, 52], image: [200, 150], redact: [120, 16], digisign: [200, 70], shape: [120, 80] };
async function finishDrag(page, a, b) {
  const m = S.mode;
  let [x0, y0, x1, y1] = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
  const small = (x1 - x0) < 6 && (y1 - y0) < 6;
  if (small && m !== "shape") {
    const [w, h] = DEFAULT_SIZE[m] || [120, 40];
    if (m === "field" && S.opts.fieldKind === "checkbox") { x1 = x0 + 14; y1 = y0 + 14; }
    else { x1 = x0 + w; y1 = y0 + h; }
  }
  if (small && m === "shape") return;
  const rect = [x0, y0, x1, y1];
  if (m === "shape") {
    const r = (S.opts.shape === "line" || S.opts.shape === "arrow") ? [a[0], a[1], b[0], b[1]] : rect;
    return run("shape", { page, kind: S.opts.shape, rect: r, color: S.opts.shapeColor, width: S.opts.width }, { silent: true });
  }
  if (m === "textbox") {
    const v = await dialog({ title: "Metin kutusu", fields: [{ id: "text", label: "Yazı", type: "textarea", rows: 3 }], ok: "Ekle" });
    if (v && v.text) run("textbox", { page, rect, text: v.text, size: S.opts.textSize, color: S.opts.textColor }, { silent: true });
    return;
  }
  if (m === "stamp") return run("stamp", { page, rect, text: S.opts.stamp, color: S.opts.stampColor, date: S.opts.stampDate }, { silent: true });
  if (m === "signature") {
    if (!S.sig) { toast("Önce sağdaki panelden bir imza seç ya da yeni imza oluştur."); return; }
    return run("place_signature", { page, rect, path: S.sig }, { silent: true });
  }
  if (m === "image") return run("add_image", { page, rect }, { silent: true });
  if (m === "sigfield") return run("signature_field", { page, rect }, { silent: true });
  if (m === "field") {
    const kind = S.opts.fieldKind;
    const fields = [{ id: "label", label: "Alanın adı", placeholder: "örn. Ad Soyad" }];
    if (kind === "choice") fields.push({ id: "options", label: "Seçenekler (virgülle)", placeholder: "Evet, Hayır" });
    const v = await dialog({ title: "Alan ekle", fields, ok: "Ekle" });
    if (!v) return;
    return run("add_field", { page, rect, kind, name: slug(v.label || "alan"), label: v.label, options: v.options ? v.options.split(",").map((s) => s.trim()).filter(Boolean) : null }, { silent: true });
  }
  if (m === "redact") { S.pendingRedact.push({ page, rect }); drawMarks(); renderPanel(); return; }
  if (m === "digisign") {
    const v = await dialog({ title: "Dijital imza", desc: "İmzadan sonra belgede yapılan her değişiklik imzayı geçersiz kılar.", fields: [
      { id: "password", label: "Sertifika parolası", type: "password" }, { id: "reason", label: "Neden (isteğe bağlı)", placeholder: "örn. Onaylıyorum" }, { id: "location", label: "Yer (isteğe bağlı)", placeholder: "örn. Bursa" }], ok: "İmzala" });
    if (v) { const r = await run("digital_sign", { ...v, page, rect }, { label: "İmzalanıyor" }); if (r && r.opened) setMode("select"); }
  }
}
const slug = (t) => trNorm(t).replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 40) || "alan";

async function placeNote(page, p) {
  const v = await dialog({ title: "Yapışkan not", fields: [{ id: "text", label: "Not", type: "textarea", rows: 4 }], ok: "Ekle" });
  if (v && v.text) run("note", { page, x: p[0], y: p[1], text: v.text, color: "#F59E0B" }, { silent: true });
}

function drawInk(only) {
  for (const d of $$(".page")) {
    const i = Number(d.dataset.p);
    if (only != null && only !== i) continue;
    d.querySelector("svg.ink")?.remove();
    const paths = S.ink[i];
    if (!paths?.length) continue;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "ink");
    for (const path of paths) {
      const pl = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      pl.setAttribute("points", path.map(([x, y]) => `${x * S.scale},${y * S.scale}`).join(" "));
      pl.setAttribute("fill", "none");
      pl.setAttribute("stroke", S.opts.shapeColor);
      pl.setAttribute("stroke-width", S.opts.width * S.scale);
      pl.setAttribute("stroke-linecap", "round");
      pl.setAttribute("stroke-linejoin", "round");
      svg.append(pl);
    }
    d.querySelector(".ov").append(svg);
  }
}
async function applyInk() {
  const pages = Object.keys(S.ink).filter((k) => S.ink[k].length);
  for (const p of pages) await run("ink", { page: Number(p), paths: S.ink[p], color: S.opts.shapeColor, width: S.opts.width }, { silent: true });
  S.ink = {};
  drawInk();
  renderPanel();
}

/* ------------------------------------------------------------------ metin seçimi */
async function ensureWords(page) {
  if (S.wordsVersion !== S.info.version) { S.words = {}; S.wordsP = {}; S.wordsVersion = S.info.version; }
  if (S.words[page]) return S.words[page];
  S.wordsP ||= {};
  if (!S.wordsP[page]) {
    const v = S.info.version;
    S.wordsP[page] = run("words", { page }, { raw: true }).then((r) => { if (S.info.version === v) S.words[page] = r ? r.words : []; return S.words[page] || []; });
  }
  return S.wordsP[page];
}
function wordAt(page, [x, y], exact = false) {
  const ws = S.words[page] || [];
  let best = -1, bd = Infinity;
  ws.forEach((w, i) => {
    const dx = x < w[0] ? w[0] - x : x > w[2] ? x - w[2] : 0;
    const dy = y < w[1] ? w[1] - y : y > w[3] ? y - w[3] : 0;
    const d = dy * 4 + dx;
    if (d < bd) { bd = d; best = i; }
  });
  if (exact && bd > 2) return -1;
  return bd < 40 ? best : -1;
}
function startSelect(page, p, e) {
  hideMinibar();
  const ov = pageEl(page).querySelector(".ov");
  const startX = e.clientX, startY = e.clientY;
  let last = p, moved = false;
  const ready = ensureWords(page);   // çoğu zaman önceden yüklenmiştir
  const apply = () => {
    if (!S.words[page]) return false;
    const a = wordAt(page, p);
    if (a < 0) { S.selection = null; drawSelection(); return false; }
    const b = wordAt(page, last);
    S.selection = { page, a, b: b >= 0 ? b : a };
    drawSelection();
    return true;
  };
  const move = (ev) => {
    if (Math.abs(ev.clientX - startX) + Math.abs(ev.clientY - startY) > 3) moved = true;
    last = pt(ov, ev);
    if (moved) apply();
  };
  const up = async (ev) => {
    window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up);
    last = pt(ov, ev);
    await ready;
    if (!moved) { S.selection = null; drawSelection(); return; }
    if (apply()) afterSelect();
  };
  window.addEventListener("mousemove", move); window.addEventListener("mouseup", up);
}
function selWords() {
  const s = S.selection;
  if (!s) return [];
  const [a, b] = s.a <= s.b ? [s.a, s.b] : [s.b, s.a];
  return (S.words[s.page] || []).slice(a, b + 1);
}
function selText() {
  const ws = selWords();
  let out = "", prev = null;
  for (const w of ws) {
    if (prev) out += (prev[5] !== w[5] || prev[6] !== w[6]) ? "\n" : " ";
    out += w[4];
    prev = w;
  }
  return out.replace(/\n(?=\S)/g, (m, i) => m);
}
function drawSelection() {
  $$(".hl").forEach((h) => h.remove());
  const ws = selWords();
  if (!ws.length) return;
  const ov = pageEl(S.selection.page)?.querySelector(".ov");
  if (!ov) return;
  for (const w of ws) ov.append(el("div", { class: "hl", style: { left: w[0] * S.scale + "px", top: w[1] * S.scale + "px", width: (w[2] - w[0]) * S.scale + "px", height: (w[3] - w[1]) * S.scale + "px" } }));
}
async function afterSelect() {
  if (S.mode === "markup" && S.opts.markup) {
    await run("markup", { page: S.selection.page, kind: S.opts.markup, rects: selWords().map((w) => w.slice(0, 4)), color: S.opts.color }, { silent: true });
    S.selection = null; drawSelection();
    return;
  }
  showMinibar();
}
function showMinibar() {
  const hl = $$(".hl");
  if (!hl.length) return;
  const last = hl[0].getBoundingClientRect();
  const bar = $("#minibar");
  const b = (label, f, ai = false) => el("button", { onmousedown: (e) => e.preventDefault(), onclick: () => { hideMinibar(); f(); }, html: (ai ? SPARK(11) : "") + label });
  bar.replaceChildren(
    b("Vurgula", () => markSel("highlight")), b("Altını çiz", () => markSel("underline")), b("Üstünü çiz", () => markSel("strike")),
    b("Düzenle", editSelection), b("Yeniden yaz", rewriteSelection, true), b("Çevir", translateSelection, true), b("Sor", askSelection, true),
    b("Kopyala", () => { navigator.clipboard.writeText(selText()); toast("Kopyalandı."); }), b("Karart", redactSelection));
  bar.hidden = false;
  const w = bar.offsetWidth;
  bar.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, last.left)) + "px";
  bar.style.top = Math.max(64, last.top - 46) + "px";
}
function hideMinibar() { $("#minibar").hidden = true; }
async function markSel(kind) {
  const s = S.selection;
  const color = kind === "highlight" ? "#FACC15" : kind === "underline" ? "#2563EB" : "#DC2626";
  await run("markup", { page: s.page, kind, rects: selWords().map((w) => w.slice(0, 4)), color }, { silent: true });
  S.selection = null; drawSelection();
}
async function editSelection() {
  const s = S.selection;
  const text = selText();
  const v = await dialog({ title: "Metni düzenle", desc: "Yeni metin aynı yere, benzer boyda yazılır.", fields: [{ id: "text", label: "Metin", type: "textarea", value: text, rows: Math.min(8, 2 + text.split("\n").length) }], ok: "Değiştir" });
  if (v && v.text !== text) { await run("replace_text", { page: s.page, rects: selWords().map((w) => w.slice(0, 4)), text: v.text }, { silent: true }); }
}
async function editLineAt(page, p) {
  const i = wordAt(page, p, true);
  if (i < 0) { toast("Burada metin yok. Bir satırın üstüne tıkla."); return; }
  const ws = S.words[page];
  const w = ws[i];
  let a = i, b = i;
  while (a > 0 && ws[a - 1][5] === w[5] && ws[a - 1][6] === w[6]) a--;
  while (b < ws.length - 1 && ws[b + 1][5] === w[5] && ws[b + 1][6] === w[6]) b++;
  S.selection = { page, a, b };
  drawSelection();
  await editSelection();
  S.selection = null; drawSelection();
}
async function rewriteSelection() {
  const s = S.selection;
  if (!s) return;
  const text = selText();
  const v = await dialog({ title: "Yeniden yaz", desc: `${SPARK()} Seçtiğin metin Claude ile yeniden yazılır; önce sonucu görürsün.`, fields: [
    { id: "style", label: "Nasıl?", type: "select", value: "resmi", options: [["resmi", "Daha resmî"], ["sade", "Daha sade"], ["kisa", "Daha kısa"], ["uzun", "Daha ayrıntılı"], ["akici", "Daha akıcı"], ["duzelt", "Yalnız yazım hatalarını düzelt"], ["custom", "Kendi isteğim…"]] },
    { id: "custom", label: "Kendi isteğin (seçtiysen)", placeholder: "örn. daha nazik bir dille" }], ok: "Yeniden yaz" });
  if (!v) return;
  const r = await run("ai_rewrite", { text, style: v.style === "custom" ? null : v.style, custom: v.custom }, { label: "Yeniden yazılıyor", raw: true });
  if (!r) return;
  const out = await dialog({ title: "Yeni metin", fields: [{ id: "text", label: "İstersen düzelt", type: "textarea", value: r.text, rows: 6 }], ok: "Belgede değiştir", extra: [["Kopyala", (val) => { navigator.clipboard.writeText(val.text); toast("Kopyalandı."); }]] });
  if (out) await run("replace_text", { page: s.page, rects: selWords().map((w) => w.slice(0, 4)), text: out.text }, { silent: true });
}
async function translateSelection() {
  const text = selText();
  const v = await dialog({ title: "Seçili metni çevir", fields: [{ id: "lang", label: "Dil", type: "select", value: "English", options: LANGS }], ok: "Çevir" });
  if (!v) return;
  const r = await run("ai_translate_text", { text, lang: v.lang }, { label: "Çevriliyor", raw: true });
  if (r) showText("Çeviri", r.text);
}
function askSelection() {
  const text = selText();
  openAssistant("doc", `“${text.slice(0, 400)}” ifadesini açıklar mısın?`);
}
async function redactSelection() {
  const s = S.selection;
  if (await confirmBox("Seçili metni karart", "Metin kalıcı olarak silinir ve siyah kutuyla kapatılır.", "Karart", "danger")) {
    await run("redact", { items: selWords().map((w) => ({ page: s.page, rect: w.slice(0, 4) })) });
    S.selection = null; drawSelection();
  }
}

/* ------------------------------------------------------------------ işaret katmanları */
function drawMarks() {
  $$(".mark-red,.mark-diff,.mark-field,.hit").forEach((m) => m.remove());
  const add = (page, rect, cls) => {
    const ov = pageEl(page)?.querySelector(".ov");
    if (ov) ov.append(el("div", { class: cls, style: { left: rect[0] * S.scale + "px", top: rect[1] * S.scale + "px", width: (rect[2] - rect[0]) * S.scale + "px", height: (rect[3] - rect[1]) * S.scale + "px" } }));
  };
  for (const [p, list] of Object.entries(S.marks)) for (const m of list) add(Number(p), m.rect, m.cls);
  for (const r of S.pendingRedact) add(r.page, r.rect, "mark-red");
  if (S.panel.kind === "redact_review") for (const it of S.redactFound || []) if (it.on) for (const rc of it.rects) add(it.page, rc, "mark-red");
  S.find.hits.forEach((h, k) => add(h.page, h.rect, "hit" + (k === S.find.i ? " cur" : "")));
}
function flashRects(page, rects) {
  const ov = pageEl(page)?.querySelector(".ov");
  if (!ov) return;
  for (const r of rects) ov.append(el("div", { class: "flash", style: { left: r[0] * S.scale - 2 + "px", top: r[1] * S.scale - 2 + "px", width: (r[2] - r[0]) * S.scale + 4 + "px", height: (r[3] - r[1]) * S.scale + 4 + "px" } }));
  setTimeout(() => $$(".flash", ov).forEach((f) => f.remove()), 2600);
}
async function loadImageBoxes() {
  clearImageBoxes();
  for (const d of $$(".page")) {
    const page = Number(d.dataset.p);
    const r = await run("page_images", { page }, { raw: true });
    for (const im of r?.images || []) {
      const box = el("button", { class: "mark-img", "aria-label": "Görsel", style: { left: im.rect[0] * S.scale + "px", top: im.rect[1] * S.scale + "px", width: (im.rect[2] - im.rect[0]) * S.scale + "px", height: (im.rect[3] - im.rect[1]) * S.scale + "px" },
        onclick: async () => {
          const v = await dialog({ title: "Görsel", desc: "Bu görsel ne yapılsın?", ok: "Başka resimle değiştir", extra: [["Sil", async (_, done) => { done(false); await run("replace_image", { page, xref: im.xref, delete: true }, { silent: true }); }]] });
          if (v) await run("replace_image", { page, xref: im.xref }, { silent: true });
        } });
      d.querySelector(".ov").append(box);
    }
  }
}
function clearImageBoxes() { $$(".mark-img").forEach((b) => b.remove()); }

/* ------------------------------------------------------------------ belgede arama */
function openFind() {
  if (!S.info.open) return;
  $("#findbar").hidden = false;
  $("#findInput").focus();
  $("#findInput").select();
}
let findTimer = null;
async function doFind() {
  const q = $("#findInput").value.trim();
  S.find.q = q;
  if (!q) { S.find = { hits: [], i: -1, q }; $("#findCount").textContent = ""; drawMarks(); return; }
  const r = await run("search", { query: q }, { raw: true });
  S.find.hits = r?.hits || [];
  S.find.i = S.find.hits.length ? 0 : -1;
  showFindHit();
}
function showFindHit() {
  $("#findCount").textContent = S.find.hits.length ? `${S.find.i + 1} / ${S.find.hits.length}` : "Yok";
  drawMarks();
  const h = S.find.hits[S.find.i];
  if (h) scrollToPage(h.page, h.rect[1]);
}
function stepFind(d) {
  if (!S.find.hits.length) return;
  S.find.i = (S.find.i + d + S.find.hits.length) % S.find.hits.length;
  showFindHit();
}
function closeFind() { $("#findbar").hidden = true; S.find = { hits: [], i: -1, q: "" }; drawMarks(); }

/* ------------------------------------------------------------------ sağ panel */
function showPanel(p) {
  S.panel = p;
  if (p.kind !== "redact_review" && p.kind !== "compare") { /* işaretler kalır */ }
  renderPanel();
  renderTop();
  drawMarks();
}
function head(title, desc, closeTo = "tools") {
  return el("div", { class: "p-head" }, el("div", { class: "grow" }, el("h2", {}, title), desc ? el("p", { html: desc }) : null),
    closeTo ? el("button", { class: "icon-btn", "aria-label": "Kapat", html: icon("close", 16), onclick: () => { if (S.mode !== "select") setMode("select", { quiet: true }); showPanel({ kind: closeTo }); } }) : null);
}
function toolButton(t) {
  return el("button", { class: "tool" + (t.ai ? " ai" : ""), onclick: () => useTool(t) },
    el("span", { class: "chip", html: t.ai ? SPARK(15) : icon(t.icon, 16) }),
    el("span", { class: "txt" }, el("b", {}, t.name), el("small", {}, t.desc)));
}
function seg(options, value, onpick) {
  return el("div", { class: "seg" }, options.map(([v, l]) => el("button", { class: v === value ? "on" : "", onclick: () => onpick(v) }, l)));
}
function swatches(colors, value, onpick) {
  return el("div", { class: "swatches" }, colors.map((c) => el("button", { class: "sw" + (c === value ? " on" : ""), style: { background: c }, "aria-label": c, onclick: () => onpick(c) })));
}

const MODE_INFO = {
  markup: ["Vurgula ve çiz", "Metni sürükleyerek seç; bırakınca uygulanır."],
  note: ["Yapışkan not", "Notun duracağı yere tıkla."],
  ink: ["Serbest çizim", "Sayfanın üstünde basılı tutarak çiz, bitince “Uygula”ya bas."],
  shape: ["Şekil", "Sayfada sürükleyerek çiz."],
  stamp: ["Damga", "Damganın yerine tıkla ya da sürükleyerek boyutunu ver."],
  signature: ["İmzanı ekle", "Bir imza seç, sonra sayfada yerine tıkla ya da sürükle."],
  image: ["Görsel ekle", "Görselin duracağı alanı sürükle; ardından resmi seç."],
  imgedit: ["Görseli değiştir ya da sil", "Kesik çizgili bir görsele tıkla."],
  textbox: ["Metin kutusu", "Yazının duracağı alanı sürükle."],
  edittext: ["Metni düzenle", "Değiştirmek istediğin satıra tıkla. Birkaç kelimeyi değiştirmek için metni seçip mini çubuktan “Düzenle”ye de basabilirsin."],
  field: ["Alan ekle", "Alan türünü seç, sayfada alanın yerini sürükle."],
  sigfield: ["İmza alanı ekle", "İmza yerini sayfada sürükle."],
  redact: ["Elle karart", "Karartılacak alanları sürükleyerek işaretle, sonra “Karart”a bas."],
  digisign: ["Dijital imza", "İmzanın görüneceği alanı sürükle."],
};

async function renderPanel() {
  const P = $("#panel");
  P.classList.toggle("wide", S.panel.kind === "assistant");
  const k = S.panel.kind;
  if (k === "assistant") return renderAssistant(P);
  if (k === "tools") {
    const list = TOOLS.filter((t) => t.group === S.tab);
    P.replaceChildren(head(GROUPS[S.tab], { edit: "Metin, görsel ve sayfa bilgileri", pages: "Bu işler bilgisayarında, ücretsiz", mark: "Yorum, çizim, damga ve imza", convert: "Bu belgeyi başka biçime çevir", forms: "Doldur, oluştur, topla", protect: "Gizlilik, imza ve denetim" }[S.tab], null),
      el("div", { class: "p-body" }, list.map(toolButton),
        el("div", { class: "legend" }, el("div", { html: `<b>${SPARK(11)}Claude</b> işaretliler belgeyi Claude’a gönderir; diğerleri bilgisayarında çalışır.` }),
          el("button", { class: "linkbtn", style: { textAlign: "left" }, onclick: openPalette }, "Aradığın burada yok mu? Ctrl K ile tüm araçlar"))));
    return;
  }
  if (k === "hint") { P.replaceChildren(head("İpucu", null), el("div", { class: "p-body" }, el("p", { class: "hint" }, S.panel.text))); return; }
  if (k === "mode") return renderModePanel(P);
  if (k === "organize") return renderOrganize(P);
  if (k === "annots") return renderAnnots(P);
  if (k === "fields") return renderFields(P);
  if (k === "changes") return renderChanges(P);
  if (k === "redact_review") return renderRedactReview(P);
  if (k === "compare") return renderCompare(P);
  if (k === "access") return renderAccess(P);
  if (k === "digisign") return renderDigisign(P);
  if (k === "verify") return renderVerify(P);
  if (k === "extracted") return renderExtracted(P);
}

async function renderModePanel(P) {
  const m = S.mode;
  const [title, desc] = MODE_INFO[m] || ["Araç", ""];
  const body = el("div", { class: "p-body" }, el("p", { class: "hint" }, desc));
  const foot = el("div", { class: "p-foot" });
  const o = S.opts;
  const rerender = () => renderPanel();
  if (m === "markup") {
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Tür"),
      seg([["highlight", "Vurgula"], ["underline", "Altını çiz"], ["strike", "Üstünü çiz"], ["squiggly", "Dalgalı"]], o.markup || "highlight", (v) => { o.markup = v; rerender(); })));
    if (!o.markup) o.markup = "highlight";
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Renk"), swatches(["#FACC15", "#4ADE80", "#60A5FA", "#F472B6", "#EF4444"], o.color, (c) => { o.color = c; rerender(); })));
  }
  if (m === "ink" || m === "shape") {
    if (m === "shape") body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Şekil"), seg([["rect", "Kutu"], ["ellipse", "Daire"], ["line", "Çizgi"], ["arrow", "Ok"]], o.shape, (v) => { o.shape = v; rerender(); })));
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Renk"), swatches(["#DC2626", "#2563EB", "#16A34A", "#111111", "#F59E0B"], o.shapeColor, (c) => { o.shapeColor = c; drawInk(); rerender(); })));
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Kalınlık"), seg([[1, "İnce"], [2, "Orta"], [4, "Kalın"]], o.width, (v) => { o.width = v; drawInk(); rerender(); })));
    if (m === "ink") {
      const n = Object.values(S.ink).reduce((a, b) => a + b.length, 0);
      foot.append(el("button", { class: "btn primary", disabled: !n, onclick: applyInk }, "Uygula"), el("button", { class: "btn", disabled: !n, onclick: () => { S.ink = {}; drawInk(); rerender(); } }, "Temizle"));
    }
  }
  if (m === "stamp") {
    const presets = ["ONAYLANDI", "REDDEDİLDİ", "TASLAK", "GİZLİ", "ÖDENDİ", "ASLI GİBİDİR", "İNCELENDİ"];
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Damga"), el("div", { class: "row" }, presets.map((p) => el("button", { class: "btn small" + (o.stamp === p ? " ai on" : ""), onclick: () => { o.stamp = p; rerender(); } }, p)))));
    const inp = el("input", { class: "input", value: presets.includes(o.stamp) ? "" : o.stamp, placeholder: "Kendi damgan", oninput: (e) => { o.stamp = e.target.value || "ONAYLANDI"; } });
    body.append(el("div", { class: "opt" }, inp));
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Renk"), swatches(["#15803D", "#B91C1C", "#1D4ED8", "#374151"], o.stampColor, (c) => { o.stampColor = c; rerender(); })));
    body.append(el("label", { class: "check", style: { padding: "4px 6px" } }, el("input", { type: "checkbox", checked: o.stampDate, onchange: (e) => { o.stampDate = e.target.checked; } }), "Altına bugünün tarihini yaz"));
  }
  if (m === "textbox") {
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Boyut"), seg([[9, "Küçük"], [12, "Normal"], [16, "Büyük"], [22, "Başlık"]], o.textSize, (v) => { o.textSize = v; rerender(); })));
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Renk"), swatches(["#111111", "#1D4ED8", "#B91C1C", "#15803D"], o.textColor, (c) => { o.textColor = c; rerender(); })));
  }
  if (m === "signature") {
    const r = await run("signatures", {}, { raw: true });
    const sigs = r?.signatures || [];
    if (!S.sig && sigs.length) S.sig = sigs[0].path;
    const grid = el("div", { class: "sig-grid" }, sigs.map((s) => el("div", { class: "sig" + (S.sig === s.path ? " on" : ""), role: "button", tabindex: "0", onclick: () => { S.sig = s.path; rerender(); } },
      el("img", { alt: "İmza", src: "data:," }),
      el("button", { class: "x", "aria-label": "İmzayı sil", onclick: async (e) => { e.stopPropagation(); await run("delete_signature", { path: s.path }, { raw: true }); if (S.sig === s.path) S.sig = null; rerender(); } }, "×"))));
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "İmzaların"), sigs.length ? grid : el("p", { class: "hint" }, "Henüz kayıtlı imzan yok.")));
    foot.append(el("button", { class: "btn primary", onclick: newSignature }, "Yeni imza"));
    // imza resimlerini yükle
    sigs.forEach((s, k) => loadSigImage(s.path, grid.children[k]?.querySelector("img")));
  }
  if (m === "field") {
    body.append(el("div", { class: "opt" }, el("span", { class: "lbl" }, "Alan türü"),
      seg([["text", "Yazı"], ["multiline", "Uzun yazı"], ["date", "Tarih"], ["checkbox", "Onay kutusu"], ["choice", "Liste"]], o.fieldKind, (v) => { o.fieldKind = v; rerender(); })));
  }
  if (m === "redact") {
    body.append(el("p", { class: "hint" }, `${S.pendingRedact.length} alan işaretlendi. Karartılan metin belgeden tamamen silinir, geri getirilemez.`));
    foot.append(el("button", { class: "btn danger", disabled: !S.pendingRedact.length, onclick: async () => { const items = S.pendingRedact; S.pendingRedact = []; await run("redact", { items }); setMode("select"); } }, "Karart"),
      el("button", { class: "btn", disabled: !S.pendingRedact.length, onclick: () => { S.pendingRedact = []; drawMarks(); rerender(); } }, "Temizle"));
  }
  foot.append(el("button", { class: "btn ghost", onclick: () => setMode("select") }, "Bitti"));
  $("#panel").replaceChildren(head(title, null), body, foot);
}
async function loadSigImage(path, img) {
  if (!img) return;
  // imzalar yerel dosya: küçük bir PNG olarak sunucudan okunur
  const r = await post("/api/run", { op: "signature_png", args: { path } });
  if (r.result?.png) img.src = r.result.png;
}

async function newSignature() {
  const pad = el("canvas", { class: "sigpad", width: 900, height: 270 });
  const typed = el("div", { class: "typed-sig", contenteditable: "true" }, "");
  let mode = "draw";
  const tabs = seg([["draw", "Çiz"], ["type", "Yaz"], ["photo", "Fotoğraftan"]], "draw", (v) => { mode = v; tabs.querySelectorAll("button").forEach((b, i) => b.classList.toggle("on", ["draw", "type", "photo"][i] === v)); pad.hidden = v !== "draw"; typed.hidden = v !== "type"; photoNote.hidden = v !== "photo"; });
  const photoNote = el("p", { class: "hint", hidden: true }, "Beyaz kağıda attığın imzanın fotoğrafını seç; kağıt saydam yapılır.");
  typed.hidden = true;
  const ctx = pad.getContext("2d");
  ctx.lineWidth = 5; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.strokeStyle = "#14204F";
  let drawing = false;
  const pos = (e) => { const r = pad.getBoundingClientRect(); return [(e.clientX - r.left) * pad.width / r.width, (e.clientY - r.top) * pad.height / r.height]; };
  pad.addEventListener("pointerdown", (e) => { drawing = true; pad.setPointerCapture(e.pointerId); ctx.beginPath(); ctx.moveTo(...pos(e)); });
  pad.addEventListener("pointermove", (e) => { if (drawing) { ctx.lineTo(...pos(e)); ctx.stroke(); } });
  pad.addEventListener("pointerup", () => { drawing = false; });
  const body = el("div", { style: { display: "flex", flexDirection: "column", gap: "10px" } }, tabs, pad, typed, photoNote);
  const v = await dialog({ title: "Yeni imza", body, ok: "Kaydet", extra: [["Temizle", () => { ctx.clearRect(0, 0, pad.width, pad.height); typed.textContent = ""; }]] });
  if (!v) return;
  let png = null;
  if (mode === "draw") png = pad.toDataURL("image/png");
  if (mode === "type") {
    const t = typed.textContent.trim();
    if (!t) return;
    const c = el("canvas", { width: 1000, height: 260 });
    const g = c.getContext("2d");
    g.font = "120px 'Segoe Script', 'Lucida Handwriting', cursive";
    g.fillStyle = "#14204F";
    g.textBaseline = "middle";
    g.fillText(t, 20, 135);
    png = c.toDataURL("image/png");
  }
  const r = await run("save_signature", { png, kind: mode }, { raw: true });
  if (r?.path) { S.sig = r.path; renderPanel(); toast("İmza kaydedildi. Şimdi sayfada yerine tıkla."); }
}

function renderOrganize(P) {
  const sel = [...S.thumbSel].sort((a, b) => a - b);
  const label = sel.length ? `${sel.length} sayfa seçili (${sel.map((p) => p + 1).join(", ")})` : `Sayfa ${S.curPage + 1}`;
  const pages = sel.length ? sel.map((p) => p + 1).join(",") : String(S.curPage + 1);
  P.replaceChildren(head("Sayfaları düzenle", "Soldaki küçük resimleri sürükleyerek sırala. Ctrl ile birden çok sayfa seç."),
    el("div", { class: "p-body" }, el("p", { class: "hint" }, label),
      el("div", { class: "row", style: { padding: "6px" } },
        el("button", { class: "btn", html: icon("rotate", 16) + " Sağa döndür", onclick: () => run("rotate", { pages, angle: 90 }) }),
        el("button", { class: "btn", html: icon("rotate", 16, 'style="transform:scaleX(-1)"') + " Sola döndür", onclick: () => run("rotate", { pages, angle: -90 }) })),
      el("div", { class: "row", style: { padding: "6px" } },
        el("button", { class: "btn", html: icon("extract", 16) + " Ayrı kaydet", onclick: () => run("extract_pages", { pages }) }),
        el("button", { class: "btn", html: icon("trash", 16) + " Sil", onclick: async () => { if (await confirmBox("Sayfaları sil", label + " silinsin mi?", "Sil", "danger")) { S.thumbSel.clear(); run("delete_pages", { pages }); } } })),
      el("div", { class: "row", style: { padding: "6px" } },
        el("button", { class: "btn", html: icon("plus", 16) + " Sonrasına boş sayfa", onclick: () => run("insert_blank", { after: sel.length ? sel[sel.length - 1] : S.curPage }) }),
        el("button", { class: "btn", html: icon("file", 16) + " Dosyadan ekle", onclick: () => run("insert_file", { after: sel.length ? sel[sel.length - 1] : S.curPage }, { label: "Ekleniyor" }) }))));
}

async function renderAnnots(P) {
  const r = await run("annots", {}, { raw: true });
  const list = r?.annots || [];
  P.replaceChildren(head("Yorumlar ve işaretler", `${list.length} işaret`),
    el("div", { class: "p-body" }, list.length ? list.map((a) => el("div", { class: "list-item" },
      el("div", { class: "grow", role: "button", tabindex: "0", style: { cursor: "pointer" }, onclick: () => { scrollToPage(a.page, a.rect[1]); flashRects(a.page, [a.rect]); } },
        el("b", {}, `${a.type} · s. ${a.page + 1}`), a.text ? el("small", {}, a.text) : null, a.quoted ? el("small", {}, "“" + a.quoted + "”") : null),
      el("button", { class: "icon-btn", "aria-label": "Sil", html: icon("trash", 16), onclick: async () => { await run("delete_annot", { page: a.page, xref: a.xref }, { silent: true }); renderPanel(); } })))
      : el("p", { class: "hint" }, "Bu belgede yorum ya da işaret yok.")),
    el("div", { class: "p-foot" }, el("button", { class: "btn ai", disabled: !list.length, html: SPARK() + " Yorumları özetle", onclick: () => toolById("comments_summary").run() })));
}

async function renderFields(P) {
  const r = await run("fields", {}, { raw: true });
  const fields = (r?.fields || []).filter((f) => f.type !== "Signature");
  S.marks = {};
  for (const f of r?.fields || []) (S.marks[f.page] ||= []).push({ rect: f.rect, cls: "mark-field" });
  drawMarks();
  const inputs = {};
  const rows = fields.map((f) => {
    let input;
    if (f.on !== null) input = el("input", { type: "checkbox", checked: f.value && f.value !== "Off" });
    else if (f.options?.length) input = el("select", { class: "input" }, f.options.map((o) => el("option", { value: o, selected: o === f.value }, o)));
    else input = el(f.label.length > 0 && /açıklama|adres|not/i.test(f.label) ? "textarea" : "input", { class: "input", value: f.value || "", rows: 2 }, /textarea/.test(f.label) ? f.value : null);
    if (input.tagName === "TEXTAREA") input.value = f.value || "";
    inputs[f.xref] = input;
    return el("div", { class: "field-row" },
      el("div", { class: "top" }, el("span", { title: f.name }, f.label || f.name), el("small", {}, "s. " + (f.page + 1)),
        el("button", { class: "icon-btn", style: { width: "28px", height: "28px" }, "aria-label": "Alanı göster", html: icon("search", 14), onclick: () => { scrollToPage(f.page, f.rect[1]); flashRects(f.page, [f.rect]); } }),
        el("button", { class: "icon-btn", style: { width: "28px", height: "28px" }, "aria-label": "Alanı sil", html: icon("trash", 14), onclick: async () => { await run("delete_field", { xref: f.xref }, { silent: true }); renderPanel(); } })),
      input);
  });
  const save = async () => {
    const values = {};
    for (const f of fields) { const i = inputs[f.xref]; values[String(f.xref)] = i.type === "checkbox" ? i.checked : i.value; }
    await run("set_fields", { values });
  };
  P.replaceChildren(head("Formu doldur", fields.length ? `${fields.length} alan` : null),
    el("div", { class: "p-body" }, fields.length ? rows : el("p", { class: "hint" }, "Bu belgede doldurulabilir alan yok. “Doldurulabilir yap” ile Claude alanları bulabilir ya da “Alan ekle” ile elle ekleyebilirsin.")),
    el("div", { class: "p-foot" },
      fields.length ? el("button", { class: "btn primary", onclick: save }, "Alanları kaydet") : null,
      el("button", { class: "btn ai", html: SPARK() + (fields.length ? " Otomatik doldur" : " Doldurulabilir yap"), onclick: () => (fields.length ? autofill() : detectFields()) }),
      el("button", { class: "btn", onclick: () => setMode("field") }, "Alan ekle")));
}

function renderChanges(P) {
  const list = S.changes || [];
  P.replaceChildren(head("Önerilen değişiklikler", `${list.filter((c) => c.on).length}/${list.length} seçili` + (S.panel.note ? " · " + esc(S.panel.note) : "")),
    el("div", { class: "p-body" }, list.length ? list.map((c) => el("label", { class: "list-item" },
      el("input", { type: "checkbox", checked: c.on, disabled: !c.found, onchange: (e) => { c.on = e.target.checked; } }),
      el("div", { class: "grow" }, el("div", { html: `<del>${esc(c.find)}</del> → <ins>${esc(c.replace)}</ins>` }),
        el("small", {}, `s. ${c.page + 1} · ${c.reason}${c.found ? "" : " · belgede bulunamadı"}`)),
      el("button", { class: "icon-btn", "aria-label": "Göster", html: icon("search", 14), onclick: async (e) => { e.preventDefault(); scrollToPage(c.page); const r = await run("search", { query: c.find }, { raw: true }); flashRects(c.page, (r?.hits || []).filter((h) => h.page === c.page).map((h) => h.rect)); } })))
      : el("p", { class: "hint" }, "Değişiklik önerilmedi.")),
    el("div", { class: "p-foot" }, el("button", { class: "btn primary", disabled: !list.some((c) => c.on), onclick: async () => { await run("apply_changes", { changes: list.filter((c) => c.on) }); showPanel({ kind: "tools" }); } }, "Seçilenleri uygula"),
      el("button", { class: "btn", onclick: () => showPanel({ kind: "tools" }) }, "Vazgeç")));
}

function renderRedactReview(P) {
  const list = S.redactFound || [];
  const update = () => { drawMarks(); renderRedactReview(P); };
  P.replaceChildren(head("Karartılacaklar", `${list.filter((i) => i.on).length} öğe seçili. Kırmızı kutular kalıcı olarak silinecek.`),
    el("div", { class: "p-body" },
      S.panel.scanned?.length ? el("p", { class: "hint" }, `Taranmış sayfalar (${S.panel.scanned.join(", ")}) için önce “Aranabilir PDF yap”; yoksa bu sayfalardaki bilgiler işaretlenemez.`) : null,
      list.length ? list.map((it) => el("label", { class: "list-item" },
        el("input", { type: "checkbox", checked: it.on, disabled: !it.found, onchange: (e) => { it.on = e.target.checked; update(); } }),
        el("div", { class: "grow" }, el("b", {}, it.text), el("small", {}, `${it.type} · s. ${it.page + 1}${it.found ? "" : " · konumu bulunamadı"}`)),
        el("button", { class: "icon-btn", "aria-label": "Göster", html: icon("search", 14), onclick: (e) => { e.preventDefault(); scrollToPage(it.page, it.rects[0]?.[1]); flashRects(it.page, it.rects); } })))
        : el("p", { class: "hint" }, "Hassas bilgi bulunamadı.")),
    el("div", { class: "p-foot" },
      el("button", { class: "btn danger", disabled: !list.some((i) => i.on), onclick: async () => {
        const items = list.filter((i) => i.on).flatMap((i) => i.rects.map((rc) => ({ page: i.page, rect: rc })));
        if (await confirmBox("Kalıcı olarak karart", `${items.length} alan silinip siyah kutuyla kapatılacak. Kaydettikten sonra geri getirilemez.`, "Karart", "danger")) { S.redactFound = []; await run("redact", { items }); showPanel({ kind: "tools" }); }
      } }, "Karart"),
      el("button", { class: "btn", onclick: () => { S.redactFound = []; showPanel({ kind: "tools" }); } }, "Vazgeç")));
}

function renderCompare(P) {
  const c = S.compare;
  if (!c) return showPanel({ kind: "tools" });
  P.replaceChildren(head("Karşılaştırma", `${esc(c.other_name)} ile · ${esc(c.summary)} Yeşil alanlar değişen yerler.`),
    el("div", { class: "p-body" }, c.changes.slice(0, 300).map((d) => el("div", { class: "list-item", role: "button", tabindex: "0", style: { cursor: "pointer" }, onclick: () => scrollToPage(d.page) },
      el("div", { class: "grow" }, el("small", {}, `${d.kind} · s. ${d.page + 1}`), el("div", { html: (d.old ? `<del>${esc(d.old.slice(0, 160))}</del> ` : "") + (d.new ? `<ins>${esc(d.new.slice(0, 160))}</ins>` : "") }))))),
    el("div", { class: "p-foot" }, el("button", { class: "btn ai", html: SPARK() + " Neyin değiştiğini özetle", onclick: async () => { const r = await run("ai_compare_summary", {}, { label: "Farklar yorumlanıyor", raw: true }); if (r) showText("Neler değişti?", r.text, { md: true }); } }),
      el("button", { class: "btn", onclick: () => { S.marks = {}; S.compare = null; drawMarks(); showPanel({ kind: "tools" }); } }, "Kapat")));
}

async function renderAccess(P) {
  const r = await run("access_check", {}, { raw: true });
  const items = r?.items || [];
  P.replaceChildren(head("Erişilebilirlik", "Ekran okuyucu kullananlar için belge denetimi"),
    el("div", { class: "p-body" }, items.map((it) => el("div", { class: "list-item" }, el("span", { class: "badge " + (it.ok ? "ok" : "bad") }, it.ok ? "Tamam" : "Eksik"),
      el("div", { class: "grow" }, el("b", {}, it.title), el("small", {}, it.detail))))),
    el("div", { class: "p-foot" },
      el("button", { class: "btn primary", onclick: async () => { const v = await dialog({ title: "Otomatik düzelt", fields: [{ id: "title", label: "Belge başlığı", value: stemName() }, { id: "lang", label: "Dil", type: "select", value: "tr-TR", options: [["tr-TR", "Türkçe"], ["en-US", "İngilizce"], ["de-DE", "Almanca"]] }, { id: "toc", label: "Büyük başlıklardan yer imi oluştur", type: "checkbox", value: true }], ok: "Düzelt" }); if (v) { await run("access_fix", v); renderPanel(); } } }, "Otomatik düzelt"),
      el("button", { class: "btn ai", html: SPARK() + " Görsel açıklamaları", onclick: async () => { const x = await run("ai_alt_text", {}, { label: "Görseller açıklanıyor", raw: true }); if (x) { await refresh(); showText("Görsel açıklamaları", x.items.map((i) => `s. ${i.page + 1}: ${i.alt}`).join("\n")); } } })));
}

async function renderDigisign(P) {
  const r = await run("cert_status", {}, { raw: true });
  const cert = r?.cert;
  P.replaceChildren(head("Dijital imza", "Belgenin sana ait olduğunu ve imzadan sonra değişmediğini kanıtlar."),
    el("div", { class: "p-body" },
      cert ? el("div", { class: "list-item" }, el("span", { class: "badge ok" }, "Hazır"), el("div", { class: "grow" }, el("b", {}, cert.name), el("small", {}, cert.path)))
        : el("p", { class: "hint" }, "Önce bir sertifika gerekiyor. Kendin oluşturabilir (kişisel kullanım için) ya da sahip olduğun .p12/.pfx dosyasını içe aktarabilirsin."),
      el("p", { class: "hint" }, "Not: Kendi oluşturduğun sertifika, nitelikli elektronik imza (e-imza kartı) yerine geçmez; belgenin değiştirilmediğini kanıtlamak için kullanılır."),
      S.info.dirty ? el("p", { class: "hint", style: { color: "var(--danger)" } }, "İmzalamadan önce belgeyi kaydet.") : null),
    el("div", { class: "p-foot" },
      cert ? el("button", { class: "btn primary", disabled: S.info.dirty, onclick: () => setMode("digisign") }, "İmza yerini seç") : null,
      el("button", { class: "btn", onclick: async () => { const v = await dialog({ title: "Sertifika oluştur", fields: [{ id: "name", label: "Ad Soyad" }, { id: "email", label: "E-posta (isteğe bağlı)" }, { id: "org", label: "Kurum (isteğe bağlı)" }, { id: "password", label: "Sertifika parolası", type: "password", hint: "İmzalarken bu parola istenir; unutma." }], ok: "Oluştur" }); if (v) { await run("cert_create", v); renderPanel(); } } }, cert ? "Yeni sertifika" : "Sertifika oluştur"),
      el("button", { class: "btn", onclick: async () => { await run("cert_import", {}); renderPanel(); } }, "İçe aktar")));
}

async function renderVerify(P) {
  P.replaceChildren(head("İmzaları doğrula", null), el("div", { class: "p-body" }, el("div", { class: "thinking" }, el("span", { class: "dots" }, el("i"), el("i"), el("i")), "Denetleniyor")));
  const r = await run("verify_signatures", {}, { raw: true, quiet: true });
  const sigs = r?.signatures || [];
  P.replaceChildren(head("İmzaları doğrula", sigs.length ? `${sigs.length} dijital imza` : null),
    el("div", { class: "p-body" }, sigs.length ? sigs.map((s) => el("div", { class: "list-item" },
      el("span", { class: "badge " + (s.intact ? "ok" : "bad") }, s.intact ? "Geçerli" : "Bozuk"),
      el("div", { class: "grow" }, el("b", {}, s.signer || s.field), el("small", {}, [s.when, s.intact ? "İmzadan sonra değiştirilmemiş." : "İmzadan sonra belge değiştirilmiş ya da imza bozuk.", s.trusted ? "Güvenilir kökten." : "Sertifika güvenilir bir kuruluşça verilmemiş (kişisel sertifika)."].filter(Boolean).join(" · ")))))
      : el("p", { class: "hint" }, "Bu belgede dijital imza yok.")));
}

function renderExtracted(P) {
  const f = S.extracted || [];
  P.replaceChildren(head("Çıkarılan bilgiler", null),
    el("div", { class: "p-body" }, el("table", { class: "md-table" }, el("tbody", {}, f.map((x) => el("tr", {}, el("td", {}, x.name), el("td", {}, x.value)))))),
    el("div", { class: "p-foot" }, el("button", { class: "btn primary", onclick: () => run("fields_to_xlsx", { fields: f }) }, "Excel’e kaydet"),
      el("button", { class: "btn", onclick: () => { navigator.clipboard.writeText(f.map((x) => `${x.name}: ${x.value}`).join("\n")); toast("Kopyalandı."); } }, "Kopyala")));
}

/* ------------------------------------------------------------------ asistan */
function openAssistant(tab = "doc", prefill = "") {
  S.assistTab = tab;
  setMode("select", { quiet: true });
  showPanel({ kind: "assistant", prefill });
}
function toggleAssistant() {
  if (S.panel.kind === "assistant") showPanel({ kind: "tools" });
  else openAssistant(S.assistTab);
}
async function renderAssistant(P) {
  const chat = el("div", { class: "chat", "aria-live": "polite" });
  const ta = el("textarea", { rows: 2, placeholder: S.assistTab === "ws" ? "Belgelerin hepsine bir soru sor" : "Belgeye bir soru sor", "aria-label": "Soru" });
  ta.value = S.panel.prefill || "";
  S.panel.prefill = "";
  const send = () => { const q = ta.value.trim(); if (q) { ta.value = ""; askAssistant(q); } };
  ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
  ta.addEventListener("input", () => { ta.style.height = "auto"; ta.style.height = Math.min(140, ta.scrollHeight) + "px"; });
  const chips = el("div", { class: "chips" },
    [["Özetle", "__summary"], ["Önemli maddeler", "Bu belgedeki önemli maddeleri, yükümlülükleri ve tarihleri listele."], ["Tarih ve tutarları bul", "Belgedeki bütün tarihleri ve tutarları sayfalarıyla listele."], ["Riskleri göster", "Bu belgede benim için riskli ya da dikkat etmem gereken noktalar neler?"]]
      .map(([l, q]) => el("button", { class: "chip-btn", onclick: () => askAssistant(q) }, l)));
  let wsBox = null;
  if (S.assistTab === "ws") {
    const r = await run("workspace", {}, { raw: true });
    S.workspace = r?.workspace || [];
    wsBox = el("div", { style: { padding: "0 16px", display: "flex", flexDirection: "column", gap: "4px" } },
      S.workspace.map((w) => el("div", { class: "list-item" }, el("span", { html: icon("file", 16) }), el("div", { class: "grow" }, w.name),
        el("button", { class: "icon-btn", "aria-label": "Çıkar", html: icon("close", 14), onclick: async () => { await run("workspace", { remove: w.path }, { raw: true }); S.chat = []; renderPanel(); } }))),
      el("button", { class: "btn small", style: { alignSelf: "flex-start" }, html: icon("plus", 14) + " PDF ekle", onclick: async () => { await run("workspace", { add: true }, { raw: true }); S.chat = []; renderPanel(); } }));
  }
  for (const m of S.chat) chat.append(renderMsg(m));
  if (!S.chat.length) chat.append(el("p", { class: "hint", style: { padding: 0 } }, S.assistTab === "ws" ? "Birden çok PDF ekle; sorduğun soruyu hepsinde araştırır, hangi belgenin hangi sayfasından aldığını gösterir." : "Belge hakkında soru sor. Cevaplar belgedeki sayfalara bağlanır; rozete tıklayınca o yere gidersin."), chips);
  P.replaceChildren(
    el("div", { class: "p-head" }, el("div", { class: "grow" }, el("h2", { html: SPARK(14) + " Asistan" }), el("p", {}, "Claude Sonnet 5.5")),
      el("button", { class: "icon-btn", "aria-label": "Sohbeti sıfırla", title: "Yeni sohbet", html: icon("reset", 16), onclick: () => { S.chat = []; S.chatReset = true; renderPanel(); } }),
      el("button", { class: "icon-btn", "aria-label": "Kapat", html: icon("close", 16), onclick: () => showPanel({ kind: "tools" }) })),
    el("div", { style: { padding: "0 16px 8px" } }, seg([["doc", "Bu belge"], ["ws", "Çalışma alanı"]], S.assistTab, (v) => { S.assistTab = v; S.chat = []; S.chatReset = true; renderPanel(); })),
    wsBox, chat,
    el("div", { class: "composer" }, el("div", { class: "box" }, ta, el("button", { class: "btn primary", style: { width: "36px", padding: 0, justifyContent: "center" }, "aria-label": "Gönder", html: icon("send", 16), onclick: send })),
      el("small", {}, S.assistTab === "ws" ? "Eklenen belgeler cevap için Claude’a gönderilir." : `Bu belge (${S.info.count} sayfa) cevap için Claude’a gönderilir.`)));
  chat.scrollTop = chat.scrollHeight;
  if (S.panel.kind === "assistant" && document.activeElement !== ta) setTimeout(() => ta.focus(), 30);
}
function renderMsg(m) {
  if (m.role === "user") return el("div", { class: "msg-user" }, m.text);
  if (m.role === "thinking") return el("div", { class: "thinking" }, el("span", { class: "dots" }, el("i"), el("i"), el("i")), m.text || "Düşünüyor");
  const box = el("div", { class: "msg-ai" });
  if (m.segments) {
    const html = m.segments.map((s) => esc(s.text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>") + s.cites.map((c, k) => `<button class="cite" data-c="${esc(JSON.stringify(c))}">${m.ws ? esc(c.title.replace(/\.pdf$/i, "").slice(0, 18)) + " · " : ""}s. ${c.page + 1}</button>`).join("")).join("");
    box.innerHTML = mdToHtmlKeep(html);
    $$(".cite", box).forEach((b) => b.addEventListener("click", () => goCite(JSON.parse(b.dataset.c))));
  } else box.innerHTML = mdToHtml(m.text);
  const plain = m.segments ? m.segments.map((s) => s.text).join("") : m.text;
  box.append(el("div", { class: "msg-tools" },
    el("button", { class: "icon-btn", "aria-label": "Kopyala", title: "Kopyala", html: icon("copy", 15), onclick: () => { navigator.clipboard.writeText(plain); toast("Kopyalandı."); } }),
    el("button", { class: "icon-btn", "aria-label": "Metin olarak kaydet", title: "Metin olarak kaydet", html: icon("save", 15), onclick: () => run("save_text", { text: plain, name: stemName() + " - asistan.txt" }) })));
  return box;
}
/* Kaçışlı HTML'deki satır yapısını paragraflara ve listelere çevirir (alıntı düğmeleri korunur). */
function mdToHtmlKeep(html) {
  const lines = html.split("\n");
  const out = [];
  let list = null;
  const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const line of lines) {
    let m;
    if ((m = line.match(/^#{1,6}\s+(.*)/))) { close(); out.push(`<h4>${m[1]}</h4>`); }
    else if ((m = line.match(/^\s*[-*•]\s+(.*)/))) { if (list !== "ul") { close(); out.push("<ul>"); list = "ul"; } out.push(`<li>${m[1]}</li>`); }
    else if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) { if (list !== "ol") { close(); out.push("<ol>"); list = "ol"; } out.push(`<li>${m[1]}</li>`); }
    else if (!line.trim()) close();
    else { close(); out.push(`<p>${line}</p>`); }
  }
  close();
  return out.join("");
}
async function goCite(c) {
  if (S.assistTab === "ws" && c.title && c.title !== S.info.name) { toast(`Bu alıntı “${c.title}” belgesinin ${c.page + 1}. sayfasından: “${c.quote.slice(0, 160)}”`); return; }
  scrollToPage(c.page);
  const q = (c.quote || "").replace(/\s+/g, " ").trim();
  if (!q) return;
  for (const piece of [q.slice(0, 80), q.split(" ").slice(0, 6).join(" ")]) {
    const r = await run("search", { query: piece }, { raw: true });
    const hits = (r?.hits || []).filter((h) => h.page === c.page);
    if (hits.length) { scrollToPage(c.page, hits[0].rect[1]); flashRects(c.page, hits.map((h) => h.rect)); return; }
  }
}
async function askAssistant(q) {
  if (S.panel.kind !== "assistant") openAssistant(S.assistTab);
  const ws = S.assistTab === "ws";
  if (ws && !S.workspace.length) { toast("Önce çalışma alanına PDF ekle."); return; }
  if (q === "__summary") {
    S.chat.push({ role: "user", text: "Bu belgeyi özetle." }, { role: "thinking", text: "Özetleniyor" });
    renderPanel();
    const r = await run("ai_summary", {}, { raw: true, quiet: true });
    S.chat = S.chat.filter((m) => m.role !== "thinking");
    if (r) S.chat.push({ role: "ai", text: r.text });
    else S.chat.pop();
    return renderPanel();
  }
  S.chat.push({ role: "user", text: q }, { role: "thinking", text: "Belge okunuyor" });
  renderPanel();
  const reset = !!S.chatReset;
  S.chatReset = false;
  const r = await run("ai_chat", { question: q, workspace: ws, reset }, { raw: true, quiet: true });
  S.chat = S.chat.filter((m) => m.role !== "thinking");
  if (r) S.chat.push({ role: "ai", segments: r.segments, ws });
  else S.chat.pop();
  renderPanel();
}

/* ------------------------------------------------------------------ komut paleti */
let palIndex = 0;
function openPalette() {
  if ($("#palette")) return;
  const input = el("input", { placeholder: "Araç ara: “word”, “imza”, “karart”…", "aria-label": "Araç ara" });
  const list = el("div", { class: "pal-list", role: "listbox" });
  const scrim = el("div", { class: "scrim", id: "palette", onmousedown: (e) => { if (e.target === scrim) closePalette(); } },
    el("div", { class: "modal" }, el("div", { class: "pal-in", html: icon("search", 18) }, input), list,
      el("div", { class: "pal-foot" }, el("span", {}, "↑↓ seç"), el("span", {}, "Enter aç"), el("span", {}, "Esc kapat"), el("span", { html: SPARK(11) + " Claude kullanır" }))));
  $(".pal-in", scrim).append(input);
  let shown = [];
  const render = () => {
    const q = trNorm(input.value.trim());
    shown = TOOLS.filter((t) => !q || q.split(/\s+/).every((w) => trNorm(`${t.name} ${t.desc} ${GROUPS[t.group]} ${t.kw}`).includes(w)));
    palIndex = Math.min(palIndex, Math.max(0, shown.length - 1));
    list.replaceChildren();
    let g = null;
    shown.forEach((t, i) => {
      if (!q && t.group !== g) { g = t.group; list.append(el("div", { class: "pal-group" }, GROUPS[g])); }
      list.append(el("button", { class: "pal-item" + (i === palIndex ? " on" : ""), role: "option", onmouseenter: () => { palIndex = i; $$(".pal-item", list).forEach((b, k) => b.classList.toggle("on", k === i)); }, onclick: () => useTool(t) },
        el("span", { class: "chip", style: { color: t.ai ? "var(--accent-hover)" : "var(--muted)" }, html: t.ai ? SPARK(15) : icon(t.icon, 16) }),
        el("span", { class: "txt" }, el("b", {}, t.name), el("small", {}, t.desc)), q ? el("span", { class: "grp" }, GROUPS[t.group]) : null));
    });
    if (!shown.length) list.append(el("p", { class: "hint", style: { padding: "14px" } }, "Bulunamadı."));
  };
  input.addEventListener("input", () => { palIndex = 0; render(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { palIndex = Math.min(shown.length - 1, palIndex + 1); render(); $(".pal-item.on", list)?.scrollIntoView({ block: "nearest" }); e.preventDefault(); }
    else if (e.key === "ArrowUp") { palIndex = Math.max(0, palIndex - 1); render(); $(".pal-item.on", list)?.scrollIntoView({ block: "nearest" }); e.preventDefault(); }
    else if (e.key === "Enter" && shown[palIndex]) { e.preventDefault(); useTool(shown[palIndex]); }
    else if (e.key === "Escape") { e.preventDefault(); closePalette(); }
  });
  document.body.append(scrim);
  palIndex = 0;
  render();
  input.focus();
}
function closePalette() { $("#palette")?.remove(); }

/* ------------------------------------------------------------------ ayarlar */
async function openSettings(needKey = false) {
  const st = await run("ai_key_status", {}, { raw: true }) || {};
  const prof = await http("/api/settings");
  const u = st.usage || {};
  const body = el("div", { style: { display: "flex", flexDirection: "column", gap: "14px" } },
    el("div", { class: "f" }, el("label", { for: "key" }, "Claude API anahtarı"),
      el("input", { class: "input", id: "key", type: "password", placeholder: st.set ? `Kayıtlı: ${st.hint}` : "sk-ant-…", autocomplete: "off" }),
      el("small", { html: "Anahtar Windows Kimlik Bilgisi Yöneticisi’nde saklanır, hiçbir yere gönderilmez. Yoksa: <b>console.anthropic.com</b> → giriş yap → <b>API Keys</b> → <b>Create Key</b>. API kullanımı Claude aboneliğinden ayrı ücretlendirilir (Billing’den bakiye eklenir)." })),
    el("div", { class: "f" }, el("label", { for: "prof" }, "Bilgilerim"),
      el("textarea", { class: "input", id: "prof", rows: 5, placeholder: "Form doldururken kullanılır. Örn.\nAd Soyad: …\nTC Kimlik: …\nAdres: …\nTelefon: …\nE-posta: …" }, prof.profile || ""),
      el("small", {}, "Yalnızca “Otomatik doldur” kullandığında Claude’a gönderilir.")),
    el("div", { class: "hint", style: { padding: 0 } }, `Bu oturumda: ${u.calls || 0} Claude isteği · ${(u.input || 0).toLocaleString("tr-TR")} giriş + ${(u.output || 0).toLocaleString("tr-TR")} çıkış token · yaklaşık $${(u.cost || 0).toFixed(3)} (Sonnet 5.5 liste fiyatıyla)`),
    el("div", { class: "hint", style: { padding: 0 } }, `PDF Stüdyo ${S.info.version_app || ""} · Açık kaynak (AGPL): github.com/Yusufcihan1/pdf-studyo`));
  const v = await dialog({ title: needKey ? "Claude API anahtarı gerekli" : "Ayarlar", desc: needKey ? "Bu araç Claude kullanıyor. Kullanmak için kendi API anahtarını bir kez gir." : null, body, ok: "Kaydet",
    extra: st.set ? [["Anahtarı sil", async (_, done) => { done(false); await run("ai_key_set", { key: "" }, { raw: true }); toast("Anahtar silindi."); }]] : [] });
  if (!v) return false;
  await post("/api/settings", { profile: $("#prof")?.value ?? prof.profile });
  const key = body.querySelector("#key").value.trim();
  if (key) {
    const r = await run("ai_key_set", { key }, { label: "Anahtar deneniyor", raw: true });
    if (r?.set) toast(r.message);
    return !!r?.set;
  }
  toast("Kaydedildi.");
  return true;
}

/* ------------------------------------------------------------------ diğer menü */
async function moreMenu() {
  const items = [
    ["Aç…", "folder", async () => { if (await guardDirty()) run("open", {}, { silent: true, label: "Açılıyor" }); }],
    S.info.open ? ["Farklı kaydet…", "save", () => run("save", { as: true })] : null,
    S.info.open ? ["Belgede ara (Ctrl F)", "search", openFind] : null,
    S.info.open ? ["Belgeyi kapat", "close", async () => { if (await guardDirty()) { await post("/api/close_doc"); S.info = { open: false }; refresh(); } }] : null,
    ["Ayarlar ve API anahtarı", "key", () => openSettings()],
  ].filter(Boolean);
  const body = el("div", { style: { display: "flex", flexDirection: "column", gap: "2px" } });
  const p = dialog({ title: "Menü", body, ok: null, cancel: "Kapat" });
  for (const [l, ic, f] of items) body.append(el("button", { class: "tool", onclick: () => { document.querySelector(".scrim:last-child")?.querySelector("footer .btn")?.click(); f(); } }, el("span", { class: "chip", html: icon(ic, 16) }), el("span", { class: "txt" }, el("b", {}, l))));
  await p;
}

/* ------------------------------------------------------------------ dosya bırakma */
async function uploadFile(file) {
  if (!(await guardDirty())) return;
  const card = jobCard("Açılıyor: " + file.name, () => {});
  const buf = await file.arrayBuffer();
  const res = await fetch(`/api/upload?name=${encodeURIComponent(file.name)}`, { method: "POST", headers: { "X-Token": TOKEN }, body: buf });
  card.close();
  let data = {};
  try { data = await res.json(); } catch { /* */ }
  if (data.error === "PAROLA_GEREKLI") {
    const v = await dialog({ title: "Bu PDF parolalı", fields: [{ id: "pw", label: "Parola", type: "password" }], ok: "Aç" });
    if (!v) return;
    const r2 = await fetch(`/api/upload?name=${encodeURIComponent(file.name)}`, { method: "POST", headers: { "X-Token": TOKEN, "X-Password": v.pw }, body: buf });
    data = await r2.json();
  }
  if (data.error) return toast(data.error, { error: true });
  if (data.job) { const r = await follow(data.job, { label: "Dönüştürülüyor" }); if (r?.__error) toast(r.__error, { error: true }); }
  S.chat = []; S.panel = { kind: "tools" };
  await refresh();
}

/* ------------------------------------------------------------------ başlat */
function init() {
  $("#homeBtn").innerHTML = icon("home");
  $("#paletteBtn").innerHTML = icon("search");
  $("#undoBtn").innerHTML = icon("undo");
  $("#redoBtn").innerHTML = icon("redo");
  $("#moreBtn").innerHTML = icon("more");
  $("#assistBtn").innerHTML = SPARK(13) + " Asistan";
  $("#homeCmdIcon").outerHTML = icon("search", 20);
  $("#dropIcon").innerHTML = icon("upload", 26);
  $("#findPrev").innerHTML = icon("up", 16);
  $("#findNext").innerHTML = icon("down", 16);
  $("#findClose").innerHTML = icon("close", 16);
  $("#zoomOut").innerHTML = icon("zout", 17);
  $("#zoomIn").innerHTML = icon("zin", 17);
  $("#zoomFit").innerHTML = icon("fit", 17);

  $("#homeBtn").onclick = async () => { if (await guardDirty()) { await post("/api/close_doc"); S.info = { open: false }; S.chat = []; refresh(); } };
  $("#paletteBtn").onclick = openPalette;
  $("#homeCmd").onclick = openPalette;
  $("#allTools").onclick = openPalette;
  $("#openBtn").onclick = async () => { if (await guardDirty()) run("open", {}, { silent: true, label: "Açılıyor" }); };
  $("#undoBtn").onclick = () => run("undo", {}, { silent: true });
  $("#redoBtn").onclick = () => run("redo", {}, { silent: true });
  $("#saveBtn").onclick = () => run("save", {});
  $("#assistBtn").onclick = toggleAssistant;
  $("#moreBtn").onclick = moreMenu;
  $("#zoomIn").onclick = () => setZoom((S.scale || 1) * 1.2);
  $("#zoomOut").onclick = () => setZoom((S.scale || 1) / 1.2);
  $("#zoomFit").onclick = () => setZoom("fit");
  $("#findInput").addEventListener("input", () => { clearTimeout(findTimer); findTimer = setTimeout(doFind, 250); });
  $("#findInput").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); e.shiftKey ? stepFind(-1) : stepFind(1); } if (e.key === "Escape") closeFind(); });
  $("#findPrev").onclick = () => stepFind(-1);
  $("#findNext").onclick = () => stepFind(1);
  $("#findClose").onclick = closeFind;

  const pagesBox = $("#pages");
  pagesBox.addEventListener("scroll", () => {
    hideMinibar();
    const mid = pagesBox.scrollTop + pagesBox.clientHeight / 3;
    let cur = 0;
    for (const d of $$(".page")) { if (d.offsetTop <= mid) cur = Number(d.dataset.p); else break; }
    if (cur !== S.curPage) { S.curPage = cur; updateThumbOn(); }
  });
  pagesBox.addEventListener("wheel", (e) => { if (e.ctrlKey) { e.preventDefault(); setZoom((S.scale || 1) * (e.deltaY < 0 ? 1.1 : 1 / 1.1)); } }, { passive: false });
  let resizeT = null;
  window.addEventListener("resize", () => { clearTimeout(resizeT); resizeT = setTimeout(() => { if (S.info.open && S.zoom === "fit") renderPages(); }, 200); });

  document.addEventListener("keydown", (e) => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
    const k = e.key.toLowerCase();
    if (e.ctrlKey && k === "k") { e.preventDefault(); openPalette(); return; }
    if ($(".scrim")) return;
    if (e.ctrlKey && k === "s" && S.info.open) { e.preventDefault(); run("save", { as: e.shiftKey }); return; }
    if (e.ctrlKey && k === "o") { e.preventDefault(); $("#openBtn").click(); return; }
    if (e.ctrlKey && k === "f" && S.info.open) { e.preventDefault(); openFind(); return; }
    if (typing) return;
    if (e.ctrlKey && k === "z" && S.info.can_undo) { e.preventDefault(); run("undo", {}, { silent: true }); return; }
    if (e.ctrlKey && (k === "y" || (e.shiftKey && k === "z")) && S.info.can_redo) { e.preventDefault(); run("redo", {}, { silent: true }); return; }
    if (e.ctrlKey && k === "c" && S.selection) { navigator.clipboard.writeText(selText()); toast("Kopyalandı."); return; }
    if (e.key === "Escape") { if (S.selection) { S.selection = null; drawSelection(); hideMinibar(); } else if (S.mode !== "select") setMode("select"); else if (!$("#findbar").hidden) closeFind(); }
    if ((e.key === "+" || e.key === "=") && e.ctrlKey) { e.preventDefault(); setZoom((S.scale || 1) * 1.2); }
    if (e.key === "-" && e.ctrlKey) { e.preventDefault(); setZoom((S.scale || 1) / 1.2); }
    if (S.info.open && !e.ctrlKey && (e.key === "PageDown" || e.key === "PageUp")) { e.preventDefault(); scrollToPage(Math.max(0, Math.min(S.info.count - 1, S.curPage + (e.key === "PageDown" ? 1 : -1)))); }
  });
  document.addEventListener("mousedown", (e) => { if (!e.target.closest("#minibar") && !e.target.closest(".page")) hideMinibar(); });

  // dosya sürükle-bırak (pencerenin her yerine)
  let dragDepth = 0;
  window.addEventListener("dragenter", (e) => { if (e.dataTransfer?.types.includes("Files")) { dragDepth++; $("#dropall").hidden = false; $("#drop").classList.add("over"); } });
  window.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) { $("#dropall").hidden = true; $("#drop").classList.remove("over"); } });
  window.addEventListener("dragover", (e) => { if (e.dataTransfer?.types.includes("Files")) e.preventDefault(); });
  window.addEventListener("drop", (e) => {
    if (!e.dataTransfer?.files?.length) return;
    e.preventDefault();
    dragDepth = 0; $("#dropall").hidden = true; $("#drop").classList.remove("over");
    const files = [...e.dataTransfer.files];
    if (files.length > 1) toast("Birden çok dosyayı birleştirmek için Sayfalar → Birleştir’i kullan. İlk dosya açılıyor.");
    uploadFile(files[0]);
  });

  // pencere kapanınca sunucu kapansın
  setInterval(() => http("/api/ping"), 5000);
  http("/api/ping");
  window.addEventListener("pagehide", () => navigator.sendBeacon(`/api/bye?t=${TOKEN}`));
  window.addEventListener("beforeunload", (e) => { if (S.info.open && S.info.dirty) { e.preventDefault(); e.returnValue = ""; } });

  refresh();
}
init();
