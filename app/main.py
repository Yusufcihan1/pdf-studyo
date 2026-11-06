"""PDF Stüdyo giriş noktası: yerel sunucuyu başlatır, arayüzü Edge uygulama penceresinde açar."""
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import core
from core import APP_NAME, APP_VERSION, DATA_DIR, JOBS, SESSION, UserError, load_settings, resource, save_settings, start_job
from ops_ai import AI_OPS
from ops_local import LOCAL_OPS, find_edge
from ops_sign import SIGN_OPS

OPS = {**LOCAL_OPS, **AI_OPS, **SIGN_OPS}
# Hızlı ve pencere açmayan işler istekte hemen yanıtlanır; gerisi arka plan işi olur.
SYNC = {"words", "page_text", "undo", "redo", "annots", "fields", "page_images", "signatures", "delete_signature",
        "ai_key_status", "cert_status", "access_check", "to_text_local", "search", "signature_png"}

TOKEN = secrets.token_urlsafe(24)
STATIC = resource("static")
LAST_PING = [time.time()]
BYE = [0.0]


class Handler(BaseHTTPRequestHandler):
    server_version = "PDFStudyo"

    def log_message(self, *args):
        pass

    # --- yanıt yardımcıları
    def _send(self, code, body, ctype="application/json; charset=utf-8", cache=False):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=3600" if cache else "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self, query):
        return secrets.compare_digest(self.headers.get("X-Token", "") or query.get("t", [""])[0], TOKEN)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    # --- GET
    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        path = url.path
        if not path.startswith("/api/"):
            return self._static(path)
        if not self._authorized(q):
            return self._send(403, {"error": "yetkisiz"})
        try:
            if path == "/api/info":
                return self._send(200, {**SESSION.info(), "app": APP_NAME, "version_app": APP_VERSION})
            if path.startswith("/api/page/"):
                n = int(path.rsplit("/", 1)[1].split(".")[0])
                w = max(60, min(3000, int(q.get("w", ["900"])[0])))
                data = SESSION.render(n, w)
                return self._send(200, data, "image/png" if w > 240 else "image/jpeg", cache=True)
            if path.startswith("/api/job/"):
                job = JOBS.get(path.rsplit("/", 1)[1])
                return self._send(200, job.as_dict() if job else {"status": "error", "error": "İş bulunamadı."})
            if path == "/api/recent":
                items = [r for r in load_settings().get("recent", []) if os.path.exists(r.get("path", ""))]
                return self._send(200, {"recent": items})
            if path == "/api/settings":
                st = load_settings()
                return self._send(200, {"profile": st.get("profile", "")})
            if path == "/api/ping":
                LAST_PING[0] = time.time()
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "yok"})
        except UserError as e:
            return self._send(200, {"error": str(e)})
        except Exception as e:
            core.log_error(path, e)
            return self._send(500, {"error": core.friendly_error(e)})

    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        full = os.path.normpath(os.path.join(STATIC, unquote(path).lstrip("/")))
        if not full.startswith(os.path.normpath(STATIC)) or not os.path.isfile(full):
            return self._send(404, "bulunamadı", "text/plain; charset=utf-8")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    # --- POST
    def do_POST(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if not self._authorized(q):
            return self._send(403, {"error": "yetkisiz"})
        path = url.path
        try:
            if path == "/api/run":
                req = json.loads(self._body() or b"{}")
                op, args = req.get("op"), req.get("args") or {}
                fn = OPS.get(op)
                if not fn:
                    return self._send(200, {"error": f"Bilinmeyen işlem: {op}"})
                if op in SYNC:
                    return self._send(200, {"result": fn(SESSION, args, core.Job(op))})
                job = start_job(op, fn, args)
                return self._send(200, {"job": job.id})
            if path.startswith("/api/job/") and path.endswith("/cancel"):
                job = JOBS.get(path.split("/")[3])
                if job:
                    job.cancelled = True
                return self._send(200, {"ok": True})
            if path == "/api/upload":
                name = unquote(q.get("name", ["belge.pdf"])[0])
                data = self._body()
                password = self.headers.get("X-Password") or None
                if name.lower().endswith(".pdf"):
                    SESSION.load_bytes(data, name=name, password=password)
                else:
                    import tempfile
                    tmp = os.path.join(tempfile.mkdtemp(prefix="pdfstudyo_"), os.path.basename(name))
                    with open(tmp, "wb") as f:
                        f.write(data)
                    job = start_job("from_files", OPS["from_files"], {"paths": [tmp]})
                    return self._send(200, {"job": job.id})
                return self._send(200, {"result": {"changed": True, "opened": True}})
            if path == "/api/settings":
                req = json.loads(self._body() or b"{}")
                st = load_settings()
                if "profile" in req:
                    st["profile"] = req["profile"]
                save_settings(st)
                return self._send(200, {"ok": True})
            if path == "/api/open_external":
                req = json.loads(self._body() or b"{}")
                target = req.get("path")
                if target and os.path.exists(target):
                    if req.get("folder"):
                        core.open_in_explorer(target)
                    else:
                        os.startfile(target)
                return self._send(200, {"ok": True})
            if path == "/api/bye":
                BYE[0] = time.time()
                return self._send(200, {"ok": True})
            if path == "/api/close_doc":
                with SESSION.lock:
                    if SESSION.doc:
                        SESSION.doc.close()
                    SESSION.__init__()
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "yok"})
        except UserError as e:
            return self._send(200, {"error": str(e)})
        except Exception as e:
            core.log_error(path, e)
            return self._send(500, {"error": core.friendly_error(e)})


def _edge_windows(profile):
    """Bu profili kullanan Edge ana süreçleri ve açtıkları uygulama adresleri."""
    import psutil
    out = []
    key = f"--user-data-dir={profile}".lower()
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            if (p.info["name"] or "").lower() != "msedge.exe":
                continue
            cmd = p.info["cmdline"] or []
            if any(c.lower() == key for c in cmd):
                app = next((c[6:] for c in cmd if c.startswith("--app=")), None)
                if app:
                    out.append((p, app))
        except (psutil.Error, OSError):
            continue
    return out


def _alive(url):
    import urllib.request
    q = parse_qs(urlparse(url).query)
    try:
        req = urllib.request.Request(url.split("?")[0].rstrip("/") + "/api/ping", headers={"X-Token": q.get("t", [""])[0]})
        with urllib.request.urlopen(req, timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def pick_profile():
    """Kapanmadan kalmış (sunucusu ölü) pencereleri kapatır; başka bir açık PDF Stüdyo varsa ayrı profil seçer."""
    import psutil
    for n in range(1, 6):
        profile = os.path.join(DATA_DIR, "pencere" if n == 1 else f"pencere{n}")
        busy = False
        for proc, app in _edge_windows(profile):
            if _alive(app):
                busy = True
                continue
            try:
                for ch in proc.children(recursive=True):
                    ch.kill()
                proc.kill()
            except psutil.Error:
                pass
        if not busy:
            return profile
    return os.path.join(DATA_DIR, f"pencere_{os.getpid()}")


def launch_window(url):
    profile = pick_profile()
    # Uygulama penceresinin kendi Edge profili: Microsoft hesabıyla otomatik oturum açma ve eşitleme kapalı.
    args = [find_edge(), f"--app={url}", f"--user-data-dir={profile}", "--no-first-run",
            "--no-default-browser-check", "--disable-sync", "--disable-background-networking",
            "--disable-features=Translate,msEdgeSidebarV2,msHubApps,msImplicitSignin,msEdgeSyncConsent,"
            "msEdgeSignInFRE,msShowSignInFlyout,msEdgeAutoSignIn,msSignInPromo,SigninInterception",
            "--window-size=1440,920", "--lang=tr"]
    return subprocess.Popen(args)


def main():
    start_path = next((a for a in sys.argv[1:] if os.path.isfile(a)), None)
    if start_path:
        try:
            if start_path.lower().endswith(".pdf"):
                SESSION.open_path(start_path)
            else:
                start_job("from_files", OPS["from_files"], {"paths": [start_path]})
        except UserError:
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/?t={TOKEN}"
    # Claude kütüphanesi ağır: pencere açılırken arka planda yüklensin, ilk Claude işi beklemesin.
    threading.Thread(target=lambda: __import__("anthropic"), daemon=True).start()
    if "--no-window" in sys.argv:
        print(url, flush=True)
        while True:
            time.sleep(3600)
    proc = launch_window(url)
    # Pencere kapanınca çık. Sayfa kapanırken "bye" gönderir; yenilemede hemen yeniden yoklama gelir.
    # Edge süreci başka bir sürece devredebildiği için yoklama zamanına da bakılır (küçültülmüş pencere
    # zamanlayıcıları dakikada bire indirilebilir, bu yüzden eşik geniş).
    while True:
        time.sleep(1)
        now = time.time()
        if BYE[0] and now - BYE[0] > 4 and LAST_PING[0] < BYE[0]:
            break
        if proc.poll() is not None and now - LAST_PING[0] > 150:
            break
    server.shutdown()


if __name__ == "__main__":
    main()
