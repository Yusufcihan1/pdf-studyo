"""PDF Stüdyo çekirdeği: ayarlar, açık belge oturumu (geri al geçmişiyle), arka plan işleri, dosya pencereleri."""
import io
import json
import os
import queue
import re
import sys
import threading
import time
import traceback
import uuid

import pymupdf

APP_NAME = "PDF Stüdyo"
APP_VERSION = "1.0.0"
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
SETTINGS_PATH = os.path.join(DATA_DIR, "ayarlar.json")
SIGN_DIR = os.path.join(DATA_DIR, "imzalar")
os.makedirs(SIGN_DIR, exist_ok=True)

FONT_DIR = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Fonts")
FONT_REGULAR = os.path.join(FONT_DIR, "arial.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "arialbd.ttf")
EMBED_FONT = "PSArial"   # belgeye gömülen Türkçe karakterli yazı tipinin adı

# Gömülen yazı tipinin karakter tablosunda aynı glifi paylaşan karakterlerden yanlışı seçiliyor (boşluk → \xa0,
# tire → yumuşak tire). Metin kopyalanıp aranabilsin diye bunları düzeltiyoruz.
_TOUNICODE_FIX = {"00a0": "0020", "00ad": "002d", "2010": "002d", "2011": "002d", "fd3e": "0028", "fd3f": "0029"}
_SECTION = re.compile(rb"(\d+)\s+begin(bfchar|bfrange)(.*?)end\2", re.S)
_PAIR = re.compile(rb"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>")
_RANGE = re.compile(rb"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>")


def _fixed_cmap(data):
    """ToUnicode CMap'ini okuyup yanlış eşlemeleri düzeltilmiş hâliyle baştan yazar; değişiklik yoksa None."""
    first = _SECTION.search(data)
    end = data.find(b"endcmap")
    if not first or end < 0:
        return None
    mapping = {}
    for m in _SECTION.finditer(data):
        body = m.group(3)
        if m.group(2) == b"bfchar":
            for g, u in _PAIR.findall(body):
                mapping[int(g, 16)] = u.decode().lower()
        else:
            for s, e, d in _RANGE.findall(body):
                s, e, d0 = int(s, 16), int(e, 16), int(d, 16)
                width = len(d)
                for i in range(e - s + 1):
                    mapping[s + i] = f"{d0 + i:0{width}x}"
    if not any(u in _TOUNICODE_FIX for u in mapping.values()):
        return None
    items = sorted((g, _TOUNICODE_FIX.get(u, u)) for g, u in mapping.items())
    blocks = []
    for i in range(0, len(items), 100):
        chunk = items[i:i + 100]
        lines = "\n".join(f"<{g:04x}> <{u}>" for g, u in chunk)
        blocks.append(f"{len(chunk)} beginbfchar\n{lines}\nendbfchar")
    return data[:first.start()] + "\n".join(blocks).encode() + b"\n" + data[end:]


def fix_fonts(doc):
    """Bizim gömdüğümüz Arial'ın ToUnicode tablosunu düzeltir (belgenin kendi yazı tiplerine dokunmaz)."""
    for xref in range(1, doc.xref_length()):
        try:
            if "Arial" not in doc.xref_get_key(xref, "BaseFont")[1]:
                continue
            tu = doc.xref_get_key(xref, "ToUnicode")
            if tu[0] != "xref":
                continue
            txref = int(tu[1].split()[0])
            new = _fixed_cmap(doc.xref_stream(txref) or b"")
            if new:
                doc.update_stream(txref, new)
        except Exception:
            continue


def to_bytes(doc):
    fix_fonts(doc)
    return doc.tobytes(garbage=3, deflate=True)


def resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


class UserError(Exception):
    """Kullanıcıya olduğu gibi gösterilecek hata."""


# ---------------------------------------------------------------- ayarlar

DEFAULTS = {"profile": "", "recent": [], "signatures": [], "cert_path": ""}


def load_settings():
    data = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, encoding="utf-8-sig") as f:
            data.update(json.load(f))
    except (OSError, ValueError):
        pass
    return data


def save_settings(data):
    tmp = SETTINGS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SETTINGS_PATH)


def add_recent(path, pages):
    s = load_settings()
    items = [r for r in s.get("recent", []) if r.get("path") != path]
    items.insert(0, {"path": path, "name": os.path.basename(path), "pages": pages, "when": time.time()})
    s["recent"] = items[:12]
    save_settings(s)


# ---------------------------------------------------------------- belge oturumu

class Session:
    """Açık belge. Her değişiklik bir sürüm olarak saklanır; geri al/yinele bunlar arasında gezer."""

    MAX_HISTORY = 30

    def __init__(self):
        self.lock = threading.RLock()
        self.doc = None
        self.path = None
        self.name = None
        self.history = []      # bayt anlık görüntüleri
        self.index = -1
        self.saved_index = -1
        self.version = 0
        self.render_cache = {}
        self.password = None

    # --- açma / kaydetme
    def load_bytes(self, data, path=None, name=None, password=None):
        doc = pymupdf.open(stream=data, filetype="pdf")
        if doc.needs_pass:
            if not password or not doc.authenticate(password):
                doc.close()
                raise UserError("PAROLA_GEREKLI")
        with self.lock:
            if self.doc:
                self.doc.close()
            self.doc = doc
            self.path = path
            self.name = name or (os.path.basename(path) if path else "Adsız.pdf")
            self.password = password
            self.history = [doc.tobytes(garbage=1, deflate=True)]
            self.index = 0
            self.saved_index = 0 if path else -1
            self._bump()

    def open_path(self, path, password=None):
        if not os.path.exists(path):
            raise UserError(f"Dosya bulunamadı: {path}")
        with open(path, "rb") as f:
            data = f.read()
        self.load_bytes(data, path=path, password=password)
        add_recent(path, self.doc.page_count)

    def require(self):
        if not self.doc:
            raise UserError("Önce bir belge aç.")
        return self.doc

    def commit(self):
        """Belgedeki değişikliği yeni sürüm olarak kaydet."""
        with self.lock:
            fix_fonts(self.doc)
            data = self.doc.tobytes(garbage=1, deflate=True)
            del self.history[self.index + 1:]
            self.history.append(data)
            if len(self.history) > self.MAX_HISTORY:
                drop = len(self.history) - self.MAX_HISTORY
                self.history = self.history[drop:]
                self.saved_index -= drop
            self.index = len(self.history) - 1
            self._reload(data)

    def replace_with(self, data, name=None):
        """Belgeyi tümden yeni baytlarla değiştir (geri alınabilir)."""
        with self.lock:
            del self.history[self.index + 1:]
            self.history.append(data)
            self.index = len(self.history) - 1
            if name:
                self.name = name
            self._reload(data)

    def _reload(self, data):
        old = self.doc
        self.doc = pymupdf.open(stream=data, filetype="pdf")
        if old:
            old.close()
        self._bump()

    def _bump(self):
        self.version += 1
        self.render_cache.clear()

    def undo(self):
        with self.lock:
            if self.index <= 0:
                return False
            self.index -= 1
            self._reload(self.history[self.index])
            return True

    def redo(self):
        with self.lock:
            if self.index >= len(self.history) - 1:
                return False
            self.index += 1
            self._reload(self.history[self.index])
            return True

    def save(self, path=None, encryption=None):
        doc = self.require()
        target = path or self.path
        if not target:
            raise UserError("KAYIT_YOLU_GEREKLI")
        if not encryption and target == self.path and self.index == self.saved_index and os.path.exists(target):
            return target   # değişiklik yok: yeniden yazmak dijital imzayı bozar
        tmp = target + ".pdfstudyo.tmp"
        kwargs = {"garbage": 3, "deflate": True}
        if encryption:
            kwargs.update(encryption)
        with self.lock:
            fix_fonts(doc)
            doc.save(tmp, **kwargs)
        os.replace(tmp, target)
        if not encryption:
            self.path = target
            self.name = os.path.basename(target)
            self.saved_index = self.index
            add_recent(target, doc.page_count)
        return target

    # --- bilgi
    def info(self):
        if not self.doc:
            return {"open": False}
        d = self.doc
        pages = [{"w": p.rect.width, "h": p.rect.height} for p in d]
        scanned = self.scanned_pages()
        has_fields = any(True for p in d for _ in p.widgets())
        return {
            "open": True, "name": self.name, "path": self.path, "pages": pages, "count": d.page_count,
            "version": self.version, "dirty": self.index != self.saved_index,
            "can_undo": self.index > 0, "can_redo": self.index < len(self.history) - 1,
            "scanned": scanned, "has_fields": has_fields, "size": len(self.history[self.index]),
            "metadata": {k: v for k, v in (d.metadata or {}).items() if v},
        }

    def scanned_pages(self):
        """Metni olmayan ama görseli olan sayfalar: taranmış kabul edilir."""
        out = []
        for p in self.doc:
            if len(p.get_text("text").strip()) < 20 and p.get_images():
                out.append(p.number)
        return out

    def render(self, pno, width):
        key = (self.version, pno, width)
        with self.lock:
            if key in self.render_cache:
                return self.render_cache[key]
            page = self.require()[pno]
            zoom = max(0.05, width / page.rect.width)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False, annots=True)
            data = pix.tobytes("jpeg", jpg_quality=88) if width <= 240 else pix.tobytes("png")
            if len(self.render_cache) > 120:
                self.render_cache.clear()
            self.render_cache[key] = data
            return data


SESSION = Session()


# ---------------------------------------------------------------- arka plan işleri

class Job:
    def __init__(self, op):
        self.id = uuid.uuid4().hex[:12]
        self.op = op
        self.status = "running"     # running | done | error | cancelled
        self.progress = 0.0
        self.message = ""
        self.result = None
        self.error = None
        self.cancelled = False
        self.created = time.time()

    def update(self, progress=None, message=None):
        if self.cancelled:
            raise UserError("İşlem iptal edildi.")
        if progress is not None:
            self.progress = max(0.0, min(1.0, progress))
        if message is not None:
            self.message = message

    def as_dict(self):
        return {"id": self.id, "op": self.op, "status": self.status, "progress": self.progress,
                "message": self.message, "result": self.result, "error": self.error}


JOBS = {}


def start_job(op, fn, args):
    job = Job(op)
    JOBS[job.id] = job

    def run():
        try:
            job.result = fn(SESSION, args, job)
            job.status = "done"
            job.progress = 1.0
        except UserError as e:
            job.status = "error"
            job.error = str(e)
        except Exception as e:  # beklenmeyen hata: ayrıntıyı günlüğe, kısa mesajı arayüze
            log_error(op, e)
            job.status = "error"
            job.error = friendly_error(e)
    threading.Thread(target=run, daemon=True).start()
    # eski işleri temizle
    for k in [k for k, j in JOBS.items() if time.time() - j.created > 3600 and j.status != "running"]:
        JOBS.pop(k, None)
    return job


def friendly_error(e):
    if "anthropic" not in sys.modules:
        return f"Beklenmeyen hata: {type(e).__name__}: {str(e)[:300]}"
    try:
        import anthropic
        if isinstance(e, anthropic.AuthenticationError):
            return "Claude API anahtarı geçersiz. Ayarlar'dan anahtarını kontrol et."
        if isinstance(e, anthropic.PermissionDeniedError):
            return "API anahtarının bu işleme izni yok."
        if isinstance(e, anthropic.RateLimitError):
            return "Claude şu an çok yoğun ya da kullanım sınırına ulaşıldı. Biraz sonra tekrar dene."
        if isinstance(e, anthropic.BadRequestError):
            msg = getattr(e, "message", str(e))
            if "credit" in msg.lower() or "balance" in msg.lower():
                return "API hesabında kredi kalmamış. console.anthropic.com'dan bakiye ekle."
            return f"Claude isteği kabul etmedi: {msg[:300]}"
        if isinstance(e, anthropic.APIConnectionError):
            return "Claude'a bağlanılamadı. İnternet bağlantını kontrol et."
        if isinstance(e, anthropic.APIStatusError):
            return f"Claude sunucu hatası ({e.status_code}). Biraz sonra tekrar dene."
    except ImportError:
        pass
    return f"Beklenmeyen hata: {type(e).__name__}: {str(e)[:300]}"


def log_error(op, e):
    try:
        with open(os.path.join(DATA_DIR, "hata.log"), "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {op}\n{traceback.format_exc()}")
    except OSError:
        pass


# ---------------------------------------------------------------- dosya pencereleri

_dialog_lock = threading.Lock()


def _dialog(kind, **kw):
    """Windows dosya penceresi. Tk her seferinde kendi iş parçacığında açılıp kapatılır."""
    result = queue.Queue()

    def run():
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            fn = {"open": filedialog.askopenfilename, "open_many": filedialog.askopenfilenames,
                  "save": filedialog.asksaveasfilename, "folder": filedialog.askdirectory}[kind]
            r = fn(parent=root, **kw)
            result.put(list(r) if kind == "open_many" else (r or None))
        finally:
            root.destroy()

    with _dialog_lock:
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join()
    r = result.get() if not result.empty() else None
    return r or None


PDF_TYPES = [("PDF", "*.pdf")]


def ask_open(title="Dosya seç", types=PDF_TYPES):
    return _dialog("open", title=title, filetypes=types + [("Tüm dosyalar", "*.*")])


def ask_open_many(title="Dosyaları seç", types=PDF_TYPES):
    return _dialog("open_many", title=title, filetypes=types + [("Tüm dosyalar", "*.*")]) or []


def ask_save(title="Kaydet", default_name="belge.pdf", ext=".pdf", types=PDF_TYPES):
    initial = os.path.dirname(SESSION.path) if SESSION.path else os.path.join(os.path.expanduser("~"), "Documents")
    return _dialog("save", title=title, initialfile=default_name, defaultextension=ext,
                   initialdir=initial, filetypes=types)


def ask_folder(title="Klasör seç"):
    return _dialog("folder", title=title)


def stem(name):
    return os.path.splitext(name or "belge")[0]


def open_in_explorer(path):
    try:
        if os.path.isdir(path):
            os.startfile(path)
        else:
            import subprocess
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    except OSError:
        pass


# ---------------------------------------------------------------- yardımcılar

def parse_pages(spec, count):
    """'1-3, 5, 8-' gibi ifadeyi 0 tabanlı sayfa listesine çevirir."""
    if spec in (None, "", "all", "tümü"):
        return list(range(count))
    if isinstance(spec, list):
        return [int(p) for p in spec if 0 <= int(p) < count]
    pages = []
    for part in str(spec).replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a = int(a) if a else 1
            b = int(b) if b else count
            pages.extend(range(a - 1, min(b, count)))
        else:
            pages.append(int(part) - 1)
    pages = [p for p in pages if 0 <= p < count]
    if not pages:
        raise UserError("Sayfa aralığı geçersiz. Örnek: 1-3, 5, 8-")
    return pages


def page_text_lines(doc, pages=None, max_chars=None):
    """Sayfa sayfa satır listesi: Claude'a konum bilgisiyle metin vermek için."""
    out = []
    total = 0
    for pno in pages if pages is not None else range(doc.page_count):
        txt = doc[pno].get_text("text")
        out.append(f"=== Sayfa {pno + 1} ===\n{txt.strip()}")
        total += len(txt)
        if max_chars and total > max_chars:
            break
    return "\n\n".join(out)


def ensure_font(page):
    """Türkçe karakterleri yazabilmek için sayfaya Arial'ı ekler."""
    try:
        page.insert_font(fontname=EMBED_FONT, fontfile=FONT_REGULAR)
    except Exception:
        pass
    return EMBED_FONT


def fit_text(page, rect, text, fontsize=11, color=(0, 0, 0), align=0, max_size=None):
    """Metni kutuya sığana kadar küçülterek yazar."""
    font = ensure_font(page)
    size = max_size or fontsize
    while size >= 4:
        rc = page.insert_textbox(rect, text, fontsize=size, fontname=font, color=color, align=align)
        if rc >= 0:
            return size
        size -= 0.5
    rect = pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y1 + 200)
    page.insert_textbox(rect, text, fontsize=4, fontname=font, color=color, align=align)
    return 4


def hex_to_rgb(h, default=(0, 0, 0)):
    try:
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except (AttributeError, ValueError, IndexError):
        return default


def bytes_size(n):
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def pdf_bytes_from_doc(doc):
    buf = io.BytesIO()
    doc.save(buf, garbage=3, deflate=True)
    return buf.getvalue()
