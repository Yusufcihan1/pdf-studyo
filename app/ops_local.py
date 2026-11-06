"""Bilgisayarda çalışan işlemler (Claude'suz): sayfalar, düzenleme, işaretleme, formlar, güvenlik, dönüştürme."""
import difflib
import io
import os
import re
import shutil
import subprocess
import tempfile
import time

import pymupdf
from PIL import Image

from core import (SESSION, UserError, fix_fonts, to_bytes, ask_folder, ask_open, ask_open_many, ask_save, bytes_size, ensure_font,
                  fit_text, hex_to_rgb, load_settings, parse_pages, save_settings, SIGN_DIR, stem, FONT_REGULAR,
                  EMBED_FONT)

CREATE_NO_WINDOW = 0x08000000
IMAGE_TYPES = [("Resimler", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.heic")]
OFFICE_TYPES = [("Office belgeleri", "*.docx *.doc *.xlsx *.xls *.pptx *.ppt *.rtf *.odt *.txt")]


# ---------------------------------------------------------------- yardımcılar

def R(page, box):
    """Arayüzden gelen (görünen sayfa) dikdörtgeni PDF'in döndürülmemiş koordinatına çevirir."""
    r = pymupdf.Rect(box)
    if page.rotation:
        r = r * page.derotation_matrix
    return r.normalize()


def P(page, x, y):
    p = pymupdf.Point(x, y)
    return p * page.derotation_matrix if page.rotation else p


def _page(doc, n):
    n = int(n)
    if not 0 <= n < doc.page_count:
        raise UserError("Sayfa bulunamadı.")
    return doc[n]


def _save_target(title, default, ext=".pdf", types=None):
    path = ask_save(title, default, ext, types or [("PDF", "*.pdf")])
    if not path:
        raise UserError("İptal edildi.")
    return path


# ---------------------------------------------------------------- belge

def op_open(s, a, job):
    path = a.get("path") or ask_open("Dosya aç", [("Desteklenen dosyalar", "*.pdf *.docx *.doc *.xlsx *.xls *.pptx *.ppt *.rtf *.odt *.txt *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp"), ("PDF", "*.pdf")])
    if not path:
        return {"cancelled": True}
    ext = os.path.splitext(path)[1].lower()
    if ext != ".pdf":
        return op_from_files(s, {"paths": [path]}, job)
    s.open_path(path, a.get("password"))
    return {"changed": True, "opened": True}


def op_save(s, a, job):
    s.require()
    if not s.path or a.get("as"):
        path = _save_target("Farklı kaydet", s.name or "belge.pdf")
        s.save(path)
    else:
        path = s.save()
    return {"changed": True, "message": "Kaydedildi.", "saved": path}


def op_undo(s, a, job):
    return {"changed": s.undo()}


def op_redo(s, a, job):
    return {"changed": s.redo()}


def op_words(s, a, job):
    page = _page(s.require(), a["page"])
    words = page.get_text("words", sort=True)
    return {"words": [[round(w[0], 2), round(w[1], 2), round(w[2], 2), round(w[3], 2), w[4], w[5], w[6]]
                      for w in words]}


def op_search(s, a, job):
    doc = s.require()
    q = (a.get("query") or "").strip()
    if not q:
        return {"hits": []}
    hits = []
    for page in doc:
        for r in page.search_for(q):
            hits.append({"page": page.number, "rect": [r.x0, r.y0, r.x1, r.y1]})
            if len(hits) >= 500:
                return {"hits": hits}
    return {"hits": hits}


def op_save_text(s, a, job):
    path = _save_target("Metni kaydet", a.get("name") or f"{stem(s.name)}.txt", ".txt", [("Metin", "*.txt")])
    with open(path, "w", encoding="utf-8") as f:
        f.write(a.get("text", ""))
    return {"saved": path, "open_file": path}


def op_fields_to_xlsx(s, a, job):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    path = _save_target("Excel'e kaydet", f"{stem(s.name)} - bilgiler.xlsx", ".xlsx", [("Excel", "*.xlsx")])
    wb = Workbook()
    ws = wb.active
    ws.append(["Alan", "Değer"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for f in a.get("fields", []):
        ws.append([f.get("name"), f.get("value")])
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 60
    wb.save(path)
    return {"saved": path, "open_file": path}


def op_page_text(s, a, job):
    doc = s.require()
    return {"text": doc[int(a["page"])].get_text("text")}


# ---------------------------------------------------------------- sayfalar

def op_rotate(s, a, job):
    doc = s.require()
    for p in parse_pages(a.get("pages"), doc.page_count):
        doc[p].set_rotation((doc[p].rotation + int(a.get("angle", 90))) % 360)
    s.commit()
    return {"changed": True}


def op_delete_pages(s, a, job):
    doc = s.require()
    pages = parse_pages(a.get("pages"), doc.page_count)
    if len(pages) >= doc.page_count:
        raise UserError("Bütün sayfalar silinemez; en az bir sayfa kalmalı.")
    doc.delete_pages(sorted(set(pages)))
    s.commit()
    return {"changed": True, "message": f"{len(set(pages))} sayfa silindi."}


def op_move_page(s, a, job):
    doc = s.require()
    src, dst = int(a["from"]), int(a["to"])
    if src == dst:
        return {"changed": False}
    doc.move_page(src, dst if dst > src else dst)
    s.commit()
    return {"changed": True}


def op_reorder(s, a, job):
    doc = s.require()
    order = [int(x) for x in a["order"]]
    if sorted(order) != list(range(doc.page_count)):
        raise UserError("Sayfa sırası geçersiz.")
    doc.select(order)
    s.commit()
    return {"changed": True}


def op_extract_pages(s, a, job):
    doc = s.require()
    pages = parse_pages(a.get("pages"), doc.page_count)
    path = _save_target("Seçili sayfaları kaydet", f"{stem(s.name)} (sayfalar).pdf")
    out = pymupdf.open()
    for p in pages:
        out.insert_pdf(doc, from_page=p, to_page=p)
    out.save(path, garbage=3, deflate=True)
    return {"saved": path, "message": f"{len(pages)} sayfa ayrı dosyaya kaydedildi."}


def op_insert_blank(s, a, job):
    doc = s.require()
    after = int(a.get("after", doc.page_count - 1))
    ref = doc[max(0, min(after, doc.page_count - 1))].rect
    doc.new_page(after + 1, width=ref.width, height=ref.height)
    s.commit()
    return {"changed": True}


def op_insert_file(s, a, job):
    doc = s.require()
    paths = a.get("paths") or ask_open_many("Eklenecek dosyaları seç", [("PDF ve resimler", "*.pdf *.png *.jpg *.jpeg")])
    if not paths:
        return {"cancelled": True}
    at = int(a.get("after", doc.page_count - 1)) + 1
    added = 0
    for i, path in enumerate(paths):
        job.update(i / len(paths), f"Ekleniyor: {os.path.basename(path)}")
        src = _as_pdf(path)
        doc.insert_pdf(src, start_at=at + added)
        added += src.page_count
    s.commit()
    return {"changed": True, "message": f"{added} sayfa eklendi."}


def _as_pdf(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return pymupdf.open(path)
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"):
        img = pymupdf.open(path)
        data = img.convert_to_pdf()
        return pymupdf.open("pdf", data)
    raise UserError(f"Bu dosya türü eklenemez: {os.path.basename(path)}")


def op_merge(s, a, job):
    paths = a.get("paths") or ask_open_many("Birleştirilecek PDF'leri seç (sırasıyla)")
    if not paths:
        return {"cancelled": True}
    if s.doc:
        doc = s.doc
        for i, p in enumerate(paths):
            job.update(i / len(paths), f"Ekleniyor: {os.path.basename(p)}")
            doc.insert_pdf(_as_pdf(p))
        s.commit()
        return {"changed": True, "message": f"{len(paths)} dosya belgenin sonuna eklendi."}
    out = pymupdf.open()
    for p in paths:
        out.insert_pdf(_as_pdf(p))
    s.load_bytes(out.tobytes(garbage=3, deflate=True), name="Birleştirilmiş.pdf")
    return {"changed": True, "opened": True, "message": f"{len(paths)} dosya birleştirildi."}


def op_split(s, a, job):
    doc = s.require()
    mode = a.get("mode", "every")
    folder = ask_folder("Parçaların kaydedileceği klasörü seç")
    if not folder:
        return {"cancelled": True}
    groups = []
    if mode == "every":
        n = max(1, int(a.get("value") or 1))
        groups = [list(range(i, min(i + n, doc.page_count))) for i in range(0, doc.page_count, n)]
    elif mode == "ranges":
        for part in str(a.get("value", "")).split(";"):
            if part.strip():
                groups.append(parse_pages(part, doc.page_count))
    elif mode == "size":
        limit = float(a.get("value") or 5) * 1024 * 1024
        cur = []
        for p in range(doc.page_count):
            trial = pymupdf.open()
            trial.insert_pdf(doc, from_page=(cur[0] if cur else p), to_page=p)
            if cur and len(trial.tobytes(garbage=3, deflate=True)) > limit:
                groups.append(cur)
                cur = [p]
            else:
                cur.append(p)
        if cur:
            groups.append(cur)
    elif mode == "bookmarks":
        toc = [t for t in doc.get_toc() if t[0] == 1]
        starts = [t[2] - 1 for t in toc] or [0]
        starts = sorted(set([0] + starts))
        for i, st in enumerate(starts):
            end = (starts[i + 1] if i + 1 < len(starts) else doc.page_count)
            groups.append(list(range(st, end)))
    if not groups:
        raise UserError("Bölünecek sayfa bulunamadı.")
    base = stem(s.name)
    for i, g in enumerate(groups, 1):
        job.update(i / len(groups), f"Parça {i}/{len(groups)}")
        out = pymupdf.open()
        for p in g:
            out.insert_pdf(doc, from_page=p, to_page=p)
        out.save(os.path.join(folder, f"{base} - {i:02d}.pdf"), garbage=3, deflate=True)
    return {"saved": folder, "message": f"Belge {len(groups)} parçaya bölündü."}


def op_compress(s, a, job):
    doc = s.require()
    level = a.get("level", "medium")
    before = len(s.history[s.index])
    settings = {"low": (200, 150, 80), "medium": (150, 110, 65), "high": (100, 72, 45)}[level]
    job.update(0.2, "Resimler küçültülüyor…")
    doc.rewrite_images(dpi_threshold=settings[0], dpi_target=settings[1], quality=settings[2])
    job.update(0.7, "Gereksiz veriler temizleniyor…")
    data = doc.tobytes(garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, use_objstms=1)
    if len(data) >= before:
        return {"changed": False, "message": "Belge zaten sıkıştırılmış; daha fazla küçülmedi."}
    s.replace_with(data)
    after = len(data)
    return {"changed": True, "message": f"{bytes_size(before)} → {bytes_size(after)} (%{100 - after * 100 // before} küçüldü). Kaydetmeyi unutma."}


def op_crop(s, a, job):
    doc = s.require()
    mm = 72 / 25.4
    t, r, b, l = (float(a.get(k) or 0) * mm for k in ("top", "right", "bottom", "left"))
    for p in parse_pages(a.get("pages"), doc.page_count):
        page = doc[p]
        mb = page.mediabox
        box = pymupdf.Rect(mb.x0 + l, mb.y0 + t, mb.x1 - r, mb.y1 - b)
        if box.width < 20 or box.height < 20:
            raise UserError("Kırpma payı sayfadan büyük.")
        page.set_cropbox(box)
    s.commit()
    return {"changed": True}


PAPER = {"A4": pymupdf.paper_rect("a4"), "A3": pymupdf.paper_rect("a3"), "A5": pymupdf.paper_rect("a5"),
         "Letter": pymupdf.paper_rect("letter"), "Legal": pymupdf.paper_rect("legal")}


def op_resize(s, a, job):
    doc = s.require()
    target = PAPER.get(a.get("size", "A4"))
    out = pymupdf.open()
    for page in doc:
        r = target
        if page.rect.width > page.rect.height:
            r = pymupdf.Rect(0, 0, target.height, target.width)
        np_ = out.new_page(width=r.width, height=r.height)
        np_.show_pdf_page(np_.rect, doc, page.number, keep_proportion=True)
    s.replace_with(out.tobytes(garbage=3, deflate=True))
    return {"changed": True, "message": f"Sayfalar {a.get('size', 'A4')} boyutuna getirildi."}


def content_box(page):
    """Sayfada yazı ve görsellerin kapladığı alan (tam sayfa arka plan çizimleri sayılmaz)."""
    area = page.rect
    box = pymupdf.Rect()
    for b in page.get_text("blocks"):
        r = pymupdf.Rect(b[:4]) & area
        if not r.is_empty and b[4].strip():
            box |= r
    for img in page.get_image_info():
        r = pymupdf.Rect(img["bbox"]) & area
        if not r.is_empty and r.get_area() < area.get_area() * 0.8:
            box |= r
    for d in page.get_drawings():
        r = pymupdf.Rect(d["rect"]) & area
        if not r.is_empty and r.get_area() < area.get_area() * 0.5 and r.height < area.height * 0.8:
            box |= r
    return box if not box.is_empty else pymupdf.Rect()


def fit_groups(doc, groups, drop=()):
    """Her sayfa grubunu tek sayfaya sığdırır: içerikler alt alta dizilir ve gerekirse orantılı küçültülür.
    groups: 0 tabanlı sayfa numarası listeleri; listede olmayan sayfalar olduğu gibi kalır. drop: silinecekler."""
    first_of = {g[0]: g for g in groups if g}
    skip = {p for g in groups for p in g[1:]} | set(drop)
    out = pymupdf.open()
    for pno in range(doc.page_count):
        if pno in skip:
            continue
        g = first_of.get(pno)
        if not g or len(g) == 1:
            out.insert_pdf(doc, from_page=pno, to_page=pno)
            continue
        base = doc[g[0]].rect
        clips = []
        for i, p in enumerate(g):
            page = doc[p]
            cb = content_box(page)
            if cb.is_empty:
                continue
            # İlk sayfa üstten, son sayfa alttan doğal boşluğunu korur; aradakiler yalnız içerik kadar.
            clip = pymupdf.Rect(page.rect.x0, page.rect.y0 if i == 0 else max(page.rect.y0, cb.y0 - 6),
                                page.rect.x1, cb.y1 + 6 if i < len(g) - 1 else min(page.rect.y1, cb.y1 + 6))
            clips.append((p, clip))
        top_margin = max(18.0, min(36.0, content_box(doc[g[0]]).y0 if not content_box(doc[g[0]]).is_empty else 36.0))
        bottom_margin = top_margin
        avail_h = base.height - bottom_margin
        total_h = sum(c.height for _, c in clips)
        scale = min(1.0, avail_h / total_h) if total_h else 1.0
        new = out.new_page(width=base.width, height=base.height)
        width = base.width * scale
        x0 = (base.width - width) / 2
        y = 0.0
        for p, clip in clips:
            h = clip.height * scale
            new.show_pdf_page(pymupdf.Rect(x0, y, x0 + width, y + h), doc, p, clip=clip, keep_proportion=False)
            y += h
    return out


def parse_groups(text, n):
    """'1-2, 3, 4-5' → [[0,1],[2],[3,4]]"""
    groups = []
    for part in re.split(r"[;,]", text or ""):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a_, b_ = part.split("-", 1)
            g = list(range(int(a_) - 1, int(b_)))
        else:
            g = [int(part) - 1]
        if not g or min(g) < 0 or max(g) >= n:
            raise UserError(f"Geçersiz sayfa aralığı: {part}")
        groups.append(g)
    return groups


def op_fit_one_page(s, a, job):
    doc = s.require()
    groups = a.get("groups")
    if isinstance(groups, str) or groups is None:
        groups = parse_groups(groups or f"1-{doc.page_count}", doc.page_count)
    out = fit_groups(doc, groups)
    s.replace_with(out.tobytes(garbage=3, deflate=True))
    return {"changed": True, "message": f"{sum(1 for g in groups if len(g) > 1)} grup tek sayfaya sığdırıldı."}


# ---------------------------------------------------------------- metin ve görsel düzenleme

def _style_at(page, rect):
    """Bir alandaki yazının boyutu ve rengi (yeni yazıyı benzer yazmak için)."""
    size, color = 11, (0, 0, 0)
    best = 0
    for block in page.get_text("dict", clip=rect)["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                area = pymupdf.Rect(span["bbox"]).intersect(rect).get_area()
                if area > best and span["text"].strip():
                    best = area
                    size = span["size"]
                    c = span["color"]
                    color = ((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255)
    return size, color


def replace_in_rect(page, rect, new_text, size=None, color=None):
    """Alandaki metni siler ve yerine yeni metni aynı boyda yazar."""
    st_size, st_color = _style_at(page, rect)
    size = size or st_size
    color = color or st_color
    page.add_redact_annot(rect, fill=False)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    box = pymupdf.Rect(rect.x0, rect.y0 - size * 0.15, max(rect.x1, rect.x0 + 30), rect.y1 + size * 0.6)
    fit_text(page, box, new_text, fontsize=size, color=color, max_size=size)


def _norm(t):
    return re.sub(r"[\xa0  ]", " ", t or "")


def line_at(page, rect):
    """Görünen sayfa koordinatındaki bir alanın içinde bulunduğu metin satırı (dict biçiminde)."""
    best, area = None, 0
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            ov = (pymupdf.Rect(ln["bbox"]) & rect).get_area()
            if ov > area:
                best, area = ln, ov
    return best


def line_text(line):
    return _norm("".join(sp["text"] for sp in line["spans"]))


def rewrite_line(page, line, new_text):
    """Bir satırı silip değiştirilmiş hâliyle aynı yerden, aynı boyda yeniden yazar (gerekirse biraz küçültür)."""
    spans = [sp for sp in line["spans"] if sp["text"].strip()] or line["spans"]
    size = spans[0]["size"]
    c = spans[0]["color"]
    color = ((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255)
    lr = pymupdf.Rect(line["bbox"])
    # sağa ne kadar uzayabilir: aynı hizadaki bir sonraki yazıya ya da sayfa kenarına kadar
    limit = page.rect.width - 30
    for w in page.get_text("words"):
        wr = pymupdf.Rect(w[:4])
        if wr.x0 > lr.x1 + 1 and wr.y1 > lr.y0 + 1 and wr.y0 < lr.y1 - 1:
            limit = min(limit, wr.x0 - 3)
    font = pymupdf.Font(fontfile=FONT_REGULAR)
    width = font.text_length(new_text, size)
    room = max(lr.width, limit - lr.x0)
    if width > room:
        size = size * room / width
    origin = pymupdf.Point(spans[0]["origin"])
    red = lr * page.derotation_matrix if page.rotation else lr
    page.add_redact_annot(red.normalize(), fill=False)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    if page.rotation:
        origin = origin * page.derotation_matrix
    page.insert_text(origin, new_text, fontsize=size, fontname=ensure_font(page), color=color, rotate=page.rotation)


def replace_phrase(page, hit, find, replace):
    """Bulunan ifadeyi satırı yeniden yazarak değiştirir; satır bulunamazsa kutuya yazar."""
    line = line_at(page, hit)
    if line:
        text = line_text(line)
        f = _norm(find)
        if f in text:
            rewrite_line(page, line, text.replace(f, replace, 1))
            return
    replace_in_rect(page, hit * page.derotation_matrix if page.rotation else hit, replace)


def op_replace_text(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    shown = [pymupdf.Rect(r) for r in a["rects"]]
    rects = [R(page, r) for r in a["rects"]]
    lines = _group_lines(rects)
    new_lines = a["text"].split("\n")
    if len(lines) == 1 and len(new_lines) == 1:
        sel = " ".join(_norm(w[4]) for w in page.get_text("words", sort=True)
                       if any(pymupdf.Rect(w[:4]).intersects(r) for r in shown))
        whole = shown[0]
        for r in shown[1:]:
            whole |= r
        line = line_at(page, whole)
        if line and sel and sel in line_text(line):
            rewrite_line(page, line, line_text(line).replace(sel, a["text"], 1))
            s.commit()
            return {"changed": True}
    if len(lines) == len(new_lines):
        for r, t in zip(lines, new_lines):
            replace_in_rect(page, r, t)
    else:
        whole = lines[0]
        for r in lines[1:]:
            whole |= r
        replace_in_rect(page, whole, a["text"])
    s.commit()
    return {"changed": True}


def _group_lines(rects):
    """Kelime kutularını satır kutularına birleştirir."""
    lines = []
    for r in sorted(rects, key=lambda r: (round(r.y0), r.x0)):
        for i, l in enumerate(lines):
            if abs(l.y0 - r.y0) < r.height * 0.5:
                lines[i] = l | r
                break
        else:
            lines.append(pymupdf.Rect(r))
    return lines


def op_add_image(s, a, job):
    doc = s.require()
    path = a.get("path") or ask_open("Eklenecek resmi seç", IMAGE_TYPES)
    if not path:
        return {"cancelled": True}
    page = _page(doc, a["page"])
    page.insert_image(R(page, a["rect"]), filename=path, keep_proportion=True)
    s.commit()
    return {"changed": True}


def op_page_images(s, a, job):
    page = _page(s.require(), a["page"])
    out = []
    for info in page.get_image_info(xrefs=True):
        if info.get("xref"):
            r = pymupdf.Rect(info["bbox"])
            if page.rotation:
                r = r * page.rotation_matrix
            out.append({"xref": info["xref"], "rect": [r.x0, r.y0, r.x1, r.y1]})
    return {"images": out}


def op_replace_image(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    if a.get("delete"):
        page.delete_image(int(a["xref"]))
    else:
        path = ask_open("Yeni resmi seç", IMAGE_TYPES)
        if not path:
            return {"cancelled": True}
        page.replace_image(int(a["xref"]), filename=path)
    s.commit()
    return {"changed": True}


POSITIONS = {"bottom-center": ("bottom", 1), "bottom-right": ("bottom", 2), "bottom-left": ("bottom", 0),
             "top-center": ("top", 1), "top-right": ("top", 2), "top-left": ("top", 0)}


def _stamp_text(page, text, where, align, size=9, color=(0.25, 0.25, 0.25)):
    r = page.rect
    m = 28
    box = pymupdf.Rect(m, r.height - m - size * 1.6, r.width - m, r.height - m + 2) if where == "bottom" \
        else pymupdf.Rect(m, m - 6, r.width - m, m + size * 1.6)
    if page.rotation:
        box = box * page.derotation_matrix
    font = ensure_font(page)
    page.insert_textbox(box, text, fontsize=size, fontname=font, color=color, align=align,
                        rotate=page.rotation)


def op_page_numbers(s, a, job):
    doc = s.require()
    where, align = POSITIONS.get(a.get("position", "bottom-center"))
    fmt = a.get("format", "{n} / {total}")
    start = int(a.get("start") or 1)
    pages = parse_pages(a.get("pages"), doc.page_count)
    for i, p in enumerate(pages):
        _stamp_text(doc[p], fmt.replace("{n}", str(start + i)).replace("{total}", str(len(pages) + start - 1)),
                    where, align, float(a.get("size") or 9))
    s.commit()
    return {"changed": True}


def op_header_footer(s, a, job):
    doc = s.require()
    date = time.strftime("%d.%m.%Y")
    for i, page in enumerate(doc):
        for key, where in (("header", "top"), ("footer", "bottom")):
            text = (a.get(key) or "").strip()
            if text:
                text = text.replace("{n}", str(i + 1)).replace("{total}", str(doc.page_count)).replace("{tarih}", date)
                _stamp_text(page, text, where, {"left": 0, "center": 1, "right": 2}[a.get("align", "center")],
                            float(a.get("size") or 9))
    s.commit()
    return {"changed": True}


def op_bates(s, a, job):
    doc = s.require()
    prefix = a.get("prefix", "")
    n = int(a.get("start") or 1)
    digits = int(a.get("digits") or 6)
    count = doc.page_count
    for i, page in enumerate(doc):
        _stamp_text(page, f"{prefix}{n + i:0{digits}d}", "bottom", 2, 9, (0, 0, 0))
    s.commit()
    return {"changed": True, "message": f"Bates numaraları: {prefix}{n:0{digits}d} – {prefix}{n + count - 1:0{digits}d}"}


def op_watermark(s, a, job):
    doc = s.require()
    text = (a.get("text") or "GİZLİ").strip()
    opacity = float(a.get("opacity") or 0.15)
    color = hex_to_rgb(a.get("color") or "#B91C1C")
    image = a.get("image")
    for p in parse_pages(a.get("pages"), doc.page_count):
        page = doc[p]
        r = page.rect
        if image:
            w = r.width * 0.5
            box = pymupdf.Rect((r.width - w) / 2, (r.height - w) / 2, (r.width + w) / 2, (r.height + w) / 2)
            page.insert_image(R(page, box), filename=image, keep_proportion=True, overlay=True)
            continue
        size = min(r.width, r.height) / max(4, len(text)) * 1.5
        font = pymupdf.Font(fontfile=FONT_REGULAR)
        tw = pymupdf.TextWriter(page.rect, opacity=opacity, color=color)
        width = font.text_length(text, size)
        start = pymupdf.Point((r.width - width) / 2, (r.height + size * 0.35) / 2)
        tw.append(start, text, font=font, fontsize=size)
        center = pymupdf.Point(r.width / 2, r.height / 2)
        mat = pymupdf.Matrix(-float(a.get("angle") or 45))
        morph = (center, mat)
        if page.rotation:
            tw.write_text(page, morph=morph, overlay=True)
        else:
            tw.write_text(page, morph=morph, overlay=True)
    s.commit()
    return {"changed": True}


# ---------------------------------------------------------------- işaretleme

def op_markup(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    kind = a.get("kind", "highlight")
    rects = [R(page, r) for r in a["rects"]]
    fn = {"highlight": page.add_highlight_annot, "underline": page.add_underline_annot,
          "strike": page.add_strikeout_annot, "squiggly": page.add_squiggly_annot}[kind]
    annot = fn(rects)
    if a.get("color"):
        annot.set_colors(stroke=hex_to_rgb(a["color"]))
    if a.get("comment"):
        annot.set_info(content=a["comment"])
    annot.update()
    s.commit()
    return {"changed": True}


def op_note(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    annot = page.add_text_annot(P(page, a["x"], a["y"]), a.get("text", ""), icon="Comment")
    annot.set_colors(stroke=hex_to_rgb(a.get("color") or "#F59E0B"))
    annot.set_info(title=a.get("author") or "PDF Stüdyo")
    annot.update()
    s.commit()
    return {"changed": True}


def op_textbox(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    rect = R(page, a["rect"])
    annot = page.add_freetext_annot(rect, a.get("text", ""), fontsize=float(a.get("size") or 12),
                                    fontname="Helv", text_color=hex_to_rgb(a.get("color") or "#111111"),
                                    rotate=page.rotation)
    annot.update()
    if a.get("flatten", True):
        # Türkçe karakterler için kalıcı yazı olarak gömülür; kutu not olarak da dursun istenirse flatten=False
        page.delete_annot(annot)
        fit_text(page, rect, a.get("text", ""), fontsize=float(a.get("size") or 12),
                 color=hex_to_rgb(a.get("color") or "#111111"), max_size=float(a.get("size") or 12))
    s.commit()
    return {"changed": True}


def op_ink(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    paths = [[tuple(P(page, x, y)) for x, y in path] for path in a["paths"] if len(path) > 1]
    if not paths:
        return {"changed": False}
    annot = page.add_ink_annot(paths)
    annot.set_colors(stroke=hex_to_rgb(a.get("color") or "#DC2626"))
    annot.set_border(width=float(a.get("width") or 2))
    annot.update()
    s.commit()
    return {"changed": True}


def op_shape(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    kind = a.get("kind", "rect")
    color = hex_to_rgb(a.get("color") or "#DC2626")
    x0, y0, x1, y1 = a["rect"]
    if kind in ("line", "arrow"):
        annot = page.add_line_annot(P(page, x0, y0), P(page, x1, y1))
        if kind == "arrow":
            annot.set_line_ends(pymupdf.PDF_ANNOT_LE_NONE, pymupdf.PDF_ANNOT_LE_CLOSED_ARROW)
            annot.set_colors(stroke=color, fill=color)
        else:
            annot.set_colors(stroke=color)
    else:
        rect = R(page, [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)])
        annot = page.add_rect_annot(rect) if kind == "rect" else page.add_circle_annot(rect)
        annot.set_colors(stroke=color)
    annot.set_border(width=float(a.get("width") or 2))
    annot.update()
    s.commit()
    return {"changed": True}


def op_stamp(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    rect = R(page, a["rect"])
    text = a.get("text") or "ONAYLANDI"
    color = hex_to_rgb(a.get("color") or "#15803D")
    size = max(8, min(rect.height * 0.5, rect.width / max(4, len(text)) * 1.6))
    page.draw_rect(rect, color=color, width=2.2, radius=0.12)
    font = ensure_font(page)
    inner = pymupdf.Rect(rect.x0 + 4, rect.y0 + (rect.height - size * 1.25) / 2, rect.x1 - 4, rect.y1)
    page.insert_textbox(inner, text, fontsize=size, fontname=font, color=color, align=1, rotate=page.rotation)
    if a.get("date"):
        page.insert_textbox(pymupdf.Rect(rect.x0, rect.y1 + 1, rect.x1, rect.y1 + 14), time.strftime("%d.%m.%Y"),
                            fontsize=8, fontname=font, color=color, align=1)
    s.commit()
    return {"changed": True}


def op_annots(s, a, job):
    doc = s.require()
    out = []
    for page in doc:
        for an in page.annots():
            info = an.info
            text = info.get("content", "")
            if an.type[0] in (pymupdf.PDF_ANNOT_HIGHLIGHT, pymupdf.PDF_ANNOT_UNDERLINE, pymupdf.PDF_ANNOT_STRIKE_OUT):
                quoted = page.get_textbox(an.rect).strip()
            else:
                quoted = ""
            r = an.rect * page.rotation_matrix if page.rotation else an.rect
            out.append({"page": page.number, "xref": an.xref, "type": an.type[1], "text": text, "quoted": quoted[:300],
                        "author": info.get("title", ""), "rect": [r.x0, r.y0, r.x1, r.y1]})
    return {"annots": out}


def op_delete_annot(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    for an in page.annots():
        if an.xref == int(a["xref"]):
            page.delete_annot(an)
            s.commit()
            return {"changed": True}
    raise UserError("İşaret bulunamadı.")


# ---------------------------------------------------------------- imza (görsel)

def op_signatures(s, a, job):
    st = load_settings()
    sigs = [x for x in st.get("signatures", []) if os.path.exists(x.get("path", ""))]
    return {"signatures": sigs}


def op_save_signature(s, a, job):
    import base64
    data = a.get("png")
    st = load_settings()
    path = os.path.join(SIGN_DIR, f"imza_{int(time.time() * 1000)}.png")
    if data:
        raw = base64.b64decode(data.split(",", 1)[-1])
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
    else:
        src = ask_open("İmzanın fotoğrafını seç", IMAGE_TYPES)
        if not src:
            return {"cancelled": True}
        img = _remove_background(Image.open(src))
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.save(path)
    st.setdefault("signatures", []).insert(0, {"path": path, "kind": a.get("kind", "draw")})
    st["signatures"] = st["signatures"][:8]
    save_settings(st)
    return {"signatures": st["signatures"], "path": path}


def _remove_background(img):
    """İmza fotoğrafında kağıdı saydam yapar, mürekkebi koyulaştırır."""
    gray = img.convert("L")
    gray = gray.point(lambda v: v)
    w, h = gray.size
    scale = 1600 / max(w, h)
    if scale < 1:
        gray = gray.resize((int(w * scale), int(h * scale)))
    hist = gray.histogram()
    total = sum(hist)
    acc, thr = 0, 160
    for i, c in enumerate(hist):   # en koyu %8'lik dilimin üstünü kağıt say
        acc += c
        if acc > total * 0.08:
            thr = min(200, i + 60)
            break
    alpha = gray.point(lambda v: 0 if v > thr else min(255, int((thr - v) * 255 / max(1, thr - 30))))
    ink = Image.new("RGBA", gray.size, (20, 30, 80, 0))
    ink.putalpha(alpha)
    return ink


def op_signature_png(s, a, job):
    import base64
    path = a.get("path") or ""
    if not os.path.abspath(path).startswith(os.path.abspath(SIGN_DIR)) or not os.path.exists(path):
        return {"png": None}
    with open(path, "rb") as f:
        return {"png": "data:image/png;base64," + base64.b64encode(f.read()).decode()}


def op_delete_signature(s, a, job):
    st = load_settings()
    st["signatures"] = [x for x in st.get("signatures", []) if x.get("path") != a.get("path")]
    save_settings(st)
    try:
        os.remove(a.get("path"))
    except OSError:
        pass
    return {"signatures": st["signatures"]}


def op_place_signature(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    page.insert_image(R(page, a["rect"]), filename=a["path"], keep_proportion=True)
    s.commit()
    return {"changed": True}


def op_signature_field(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    w = pymupdf.Widget()
    w.field_type = pymupdf.PDF_WIDGET_TYPE_SIGNATURE
    w.field_name = a.get("name") or f"imza_{int(time.time())}"
    w.rect = R(page, a["rect"])
    w.border_color = (0.3, 0.3, 0.6)
    w.border_width = 1
    page.add_widget(w)
    if a.get("label", True):
        font = ensure_font(page)
        r = w.rect
        page.insert_textbox(pymupdf.Rect(r.x0, r.y1 + 2, r.x1, r.y1 + 14), a.get("caption") or "İmza",
                            fontsize=7.5, fontname=font, color=(0.35, 0.35, 0.45))
    s.commit()
    return {"changed": True}


# ---------------------------------------------------------------- formlar

def _widget_dict(page, w):
    r = w.rect * page.rotation_matrix if page.rotation else w.rect
    return {"page": page.number, "name": w.field_name, "label": w.field_label or "", "type": w.field_type_string,
            "value": w.field_value if w.field_value is not None else "", "options": w.choice_values or [],
            "on": w.on_state() if w.field_type in (pymupdf.PDF_WIDGET_TYPE_CHECKBOX, pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON) else None,
            "rect": [r.x0, r.y0, r.x1, r.y1], "xref": w.xref}


def list_fields(doc):
    out = []
    for page in doc:
        for w in page.widgets():
            out.append(_widget_dict(page, w))
    return out


def op_fields(s, a, job):
    return {"fields": list_fields(s.require())}


def set_field_values(doc, values):
    count = 0
    for page in doc:
        for w in page.widgets():
            key = f"{w.xref}"
            if key not in values and w.field_name not in values:
                continue
            v = values.get(key, values.get(w.field_name))
            if w.field_type in (pymupdf.PDF_WIDGET_TYPE_CHECKBOX, pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON):
                w.field_value = w.on_state() if v in (True, "true", "1", "evet", "Evet", "on", w.on_state()) else "Off"
            elif w.field_type == pymupdf.PDF_WIDGET_TYPE_SIGNATURE:
                continue
            else:
                w.field_value = "" if v is None else str(v)
            w.update()
            count += 1
    return count


def op_set_fields(s, a, job):
    doc = s.require()
    n = set_field_values(doc, a.get("values", {}))
    s.commit()
    return {"changed": True, "message": f"{n} alan güncellendi."}


WIDGET_TYPES = {"text": pymupdf.PDF_WIDGET_TYPE_TEXT, "checkbox": pymupdf.PDF_WIDGET_TYPE_CHECKBOX,
                "choice": pymupdf.PDF_WIDGET_TYPE_COMBOBOX, "date": pymupdf.PDF_WIDGET_TYPE_TEXT,
                "multiline": pymupdf.PDF_WIDGET_TYPE_TEXT, "signature": pymupdf.PDF_WIDGET_TYPE_SIGNATURE,
                "radio": pymupdf.PDF_WIDGET_TYPE_CHECKBOX}


def add_widget(page, rect, kind, name, label="", options=None):
    w = pymupdf.Widget()
    w.field_type = WIDGET_TYPES.get(kind, pymupdf.PDF_WIDGET_TYPE_TEXT)
    w.field_name = name
    w.field_label = label or name
    w.rect = rect
    w.border_color = (0.55, 0.6, 0.75)
    w.border_width = 0.6
    w.fill_color = (0.94, 0.95, 1.0)
    w.text_font = "Helv"
    w.text_fontsize = 0
    if kind == "choice" and options:
        w.choice_values = options
        w.field_value = options[0]
    if kind == "multiline":
        w.field_flags |= pymupdf.PDF_TX_FIELD_IS_MULTILINE
    if kind == "date":
        w.field_label = (label or name) + " (GG.AA.YYYY)"
    page.add_widget(w)
    return w


def op_add_field(s, a, job):
    doc = s.require()
    page = _page(doc, a["page"])
    names = {w.field_name for p in doc for w in p.widgets()}
    base = (a.get("name") or "alan").strip() or "alan"
    name, i = base, 2
    while name in names:
        name, i = f"{base}_{i}", i + 1
    add_widget(page, R(page, a["rect"]), a.get("kind", "text"), name, a.get("label", ""), a.get("options"))
    s.commit()
    return {"changed": True}


def op_delete_field(s, a, job):
    doc = s.require()
    for page in doc:
        for w in page.widgets():
            if w.xref == int(a["xref"]):
                page.delete_widget(w)
                s.commit()
                return {"changed": True}
    raise UserError("Alan bulunamadı.")


def op_collect_responses(s, a, job):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    paths = a.get("paths") or ask_open_many("Doldurulmuş formları seç")
    if not paths:
        return {"cancelled": True}
    rows, columns = [], []
    for i, p in enumerate(paths):
        job.update(i / len(paths), os.path.basename(p))
        d = pymupdf.open(p)
        row = {"Dosya": os.path.basename(p)}
        for f in list_fields(d):
            if f["type"] == "Signature":
                continue
            key = f["label"] or f["name"]
            if key not in columns:
                columns.append(key)
            v = f["value"]
            if f["on"] is not None:
                v = "Evet" if v and v != "Off" else "Hayır"
            row[key] = v
        rows.append(row)
    if not columns:
        raise UserError("Seçilen dosyalarda doldurulabilir alan yok.")
    out = _save_target("Yanıtları Excel olarak kaydet", "Form yanıtları.xlsx", ".xlsx", [("Excel", "*.xlsx")])
    wb = Workbook()
    ws = wb.active
    ws.title = "Yanıtlar"
    header = ["Dosya"] + columns
    ws.append(header)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="4F46E5")
    for r in rows:
        ws.append([r.get(h, "") for h in header])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(50, max(10, max(len(str(c.value or "")) for c in col) + 2))
    ws.freeze_panes = "A2"
    wb.save(out)
    return {"saved": out, "message": f"{len(rows)} formun yanıtı tek tabloda toplandı."}


# ---------------------------------------------------------------- güvenlik

PERMS = {"print": pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_PRINT_HQ, "copy": pymupdf.PDF_PERM_COPY,
         "edit": pymupdf.PDF_PERM_MODIFY | pymupdf.PDF_PERM_ASSEMBLE, "annotate": pymupdf.PDF_PERM_ANNOTATE | pymupdf.PDF_PERM_FORM}


def op_protect(s, a, job):
    s.require()
    user_pw = a.get("user_pw") or ""
    owner_pw = a.get("owner_pw") or user_pw or os.urandom(12).hex()
    perms = pymupdf.PDF_PERM_ACCESSIBILITY
    for key in a.get("allow", ["print", "copy", "edit", "annotate"]):
        perms |= PERMS.get(key, 0)
    if not user_pw and len(a.get("allow", [])) == 4:
        raise UserError("Bir açılış parolası gir ya da en az bir izni kapat.")
    path = _save_target("Korumalı kopyayı kaydet", f"{stem(s.name)} (korumalı).pdf")
    s.save(path, encryption={"encryption": pymupdf.PDF_ENCRYPT_AES_256, "user_pw": user_pw, "owner_pw": owner_pw,
                             "permissions": perms})
    return {"saved": path, "message": "Parola korumalı kopya kaydedildi."}


def op_unlock(s, a, job):
    s.require()
    path = _save_target("Parolasız kopyayı kaydet", f"{stem(s.name)} (parolasız).pdf")
    s.save(path)
    return {"saved": path, "message": "Parolasız kopya kaydedildi."}


def op_sanitize(s, a, job):
    doc = s.require()
    doc.scrub(attached_files=True, clean_pages=True, embedded_files=True, hidden_text=True, javascript=True,
              metadata=True, redactions=True, redact_images=0, remove_links=bool(a.get("links")),
              reset_fields=False, reset_responses=True, thumbnails=True, xml_metadata=True)
    doc.set_metadata({})
    s.commit()
    return {"changed": True, "message": "Meta veri, gizli metin, ekler, betikler ve küçük resimler temizlendi. Kaydetmeyi unutma."}


def apply_redactions(doc, items):
    """items: [{page, rect}] ya da [{text, page?}] → kalıcı karartma."""
    count = 0
    for it in items:
        pages = [int(it["page"])] if it.get("page") is not None else range(doc.page_count)
        for pno in pages:
            page = doc[pno]
            if it.get("rect"):
                page.add_redact_annot(R(page, it["rect"]), fill=(0, 0, 0))
                count += 1
            elif it.get("text"):
                for q in page.search_for(it["text"], quads=False):
                    page.add_redact_annot(q, fill=(0, 0, 0))
                    count += 1
    for page in doc:
        if page.first_annot and any(an.type[0] == pymupdf.PDF_ANNOT_REDACT for an in page.annots()):
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
    return count


def op_redact(s, a, job):
    doc = s.require()
    n = apply_redactions(doc, a.get("items", []))
    if not n:
        raise UserError("Karartılacak bir şey bulunamadı.")
    doc.scrub(metadata=False, redactions=True, hidden_text=True, attached_files=False, embedded_files=False,
              javascript=False, xml_metadata=False, thumbnails=True, reset_fields=False, reset_responses=False,
              clean_pages=True, remove_links=False, redact_images=0)
    s.commit()
    return {"changed": True, "message": f"{n} alan kalıcı olarak karartıldı. Kaydedince geri getirilemez."}


# ---------------------------------------------------------------- dönüştürme (yerel)

def op_to_images(s, a, job):
    doc = s.require()
    fmt = a.get("format", "png")
    dpi = int(a.get("dpi") or 150)
    pages = parse_pages(a.get("pages"), doc.page_count)
    folder = ask_folder("Resimlerin kaydedileceği klasör")
    if not folder:
        return {"cancelled": True}
    base = stem(s.name)
    for i, p in enumerate(pages):
        job.update(i / len(pages), f"Sayfa {p + 1}")
        pix = doc[p].get_pixmap(dpi=dpi, alpha=False)
        out = os.path.join(folder, f"{base} - s{p + 1:03d}.{fmt}")
        if fmt == "png":
            pix.save(out)
        else:
            pix.pil_save(out, quality=90)
    return {"saved": folder, "message": f"{len(pages)} sayfa resim olarak kaydedildi."}


def op_from_files(s, a, job):
    """Resim, Office ya da PDF dosyalarından tek PDF oluşturup açar."""
    paths = a.get("paths") or ask_open_many("Dosyaları seç", [("Desteklenen dosyalar",
                                                               "*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.docx *.doc *.xlsx *.xls *.pptx *.ppt *.rtf *.odt *.txt")])
    if not paths:
        return {"cancelled": True}
    out = pymupdf.open()
    for i, p in enumerate(paths):
        job.update(i / len(paths), f"Dönüştürülüyor: {os.path.basename(p)}")
        ext = os.path.splitext(p)[1].lower()
        if ext in (".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".rtf", ".odt", ".txt"):
            pdf = office_to_pdf(p)
            out.insert_pdf(pymupdf.open(pdf))
            os.remove(pdf)
        else:
            out.insert_pdf(_as_pdf(p))
    name = (stem(os.path.basename(paths[0])) + ".pdf") if len(paths) == 1 else "Birleştirilmiş.pdf"
    s.load_bytes(out.tobytes(garbage=3, deflate=True), name=name)
    return {"changed": True, "opened": True, "message": f"{len(paths)} dosya PDF'e çevrildi. Kaydetmeyi unutma."}


def office_to_pdf(path):
    """Word/Excel/PowerPoint'in kendisiyle PDF'e çevirir (bilgisayarda Office kurulu olmalı)."""
    import pythoncom
    import win32com.client
    ext = os.path.splitext(path)[1].lower()
    out = os.path.join(tempfile.gettempdir(), f"pdfstudyo_{int(time.time() * 1000)}.pdf")
    src = os.path.abspath(path)
    pythoncom.CoInitialize()
    try:
        if ext in (".docx", ".doc", ".rtf", ".odt", ".txt"):
            app = win32com.client.DispatchEx("Word.Application")
            app.Visible = False
            app.DisplayAlerts = 0
            try:
                d = app.Documents.Open(src, ReadOnly=True, AddToRecentFiles=False)
                d.ExportAsFixedFormat(out, 17)
                d.Close(False)
            finally:
                app.Quit()
        elif ext in (".xlsx", ".xls"):
            app = win32com.client.DispatchEx("Excel.Application")
            app.Visible = False
            app.DisplayAlerts = False
            try:
                wb = app.Workbooks.Open(src, ReadOnly=True)
                wb.ExportAsFixedFormat(0, out)
                wb.Close(False)
            finally:
                app.Quit()
        elif ext in (".pptx", ".ppt"):
            app = win32com.client.DispatchEx("PowerPoint.Application")
            try:
                pres = app.Presentations.Open(src, ReadOnly=True, WithWindow=False)
                pres.SaveAs(out, 32)
                pres.Close()
            finally:
                app.Quit()
        else:
            raise UserError("Bu dosya türü desteklenmiyor.")
    except UserError:
        raise
    except Exception as e:
        raise UserError(f"Office ile dönüştürülemedi ({os.path.basename(path)}). Office kurulu ve lisanslı olmalı. Ayrıntı: {e}")
    finally:
        pythoncom.CoUninitialize()
    if not os.path.exists(out):
        raise UserError("Office dosyayı PDF'e çeviremedi.")
    return out


def find_edge():
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if base:
            p = os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")
            if os.path.exists(p):
                return p
    raise UserError("Microsoft Edge bulunamadı.")


def html_to_pdf(html=None, url=None):
    """Edge'i görünmez çalıştırıp sayfayı PDF olarak yazdırır."""
    tmpdir = tempfile.mkdtemp(prefix="pdfstudyo_")
    out = os.path.join(tmpdir, "cikti.pdf")
    if html is not None:
        src = os.path.join(tmpdir, "sayfa.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(html)
        url = "file:///" + src.replace("\\", "/")
    args = [find_edge(), "--headless=new", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
            f"--user-data-dir={os.path.join(tmpdir, 'profil')}", "--virtual-time-budget=8000",
            f"--print-to-pdf={out}", url]
    subprocess.run(args, capture_output=True, timeout=120, creationflags=CREATE_NO_WINDOW)
    if not os.path.exists(out) or os.path.getsize(out) < 500:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise UserError("Sayfa PDF'e çevrilemedi. Adresi ve internet bağlantısını kontrol et.")
    with open(out, "rb") as f:
        data = f.read()
    shutil.rmtree(tmpdir, ignore_errors=True)
    return data


def op_from_web(s, a, job):
    url = (a.get("url") or "").strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    job.update(0.2, "Sayfa açılıyor…")
    data = html_to_pdf(url=url)
    name = re.sub(r"[^\w\-. ]+", "_", re.sub(r"^https?://(www\.)?", "", url))[:60].strip("_") + ".pdf"
    s.load_bytes(data, name=name)
    return {"changed": True, "opened": True, "message": "Web sayfası PDF'e çevrildi. Kaydetmeyi unutma."}


def op_fix_photos(s, a, job):
    """Telefonla çekilmiş belge fotoğraflarını düzleştirip PDF yapar."""
    import cv2
    import numpy as np
    paths = a.get("paths") or ask_open_many("Belge fotoğraflarını seç", IMAGE_TYPES)
    if not paths:
        return {"cancelled": True}
    out = pymupdf.open()
    fixed = 0
    for i, p in enumerate(paths):
        job.update(i / len(paths), f"Düzeltiliyor: {os.path.basename(p)}")
        img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        warped, ok = _scan_document(img)
        fixed += ok
        if a.get("bw", False):
            gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
            warped = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
        else:
            lab = cv2.cvtColor(warped, cv2.COLOR_BGR2LAB)
            l, aa, b = cv2.split(lab)
            l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
            warped = cv2.cvtColor(cv2.merge((l, aa, b)), cv2.COLOR_LAB2BGR)
        ok2, buf = cv2.imencode(".jpg", warped, [cv2.IMWRITE_JPEG_QUALITY, 88])
        h, w = warped.shape[:2]
        a4 = pymupdf.paper_rect("a4")
        page = out.new_page(width=a4.width, height=a4.width * h / w)
        page.insert_image(page.rect, stream=buf.tobytes())
    if not out.page_count:
        raise UserError("Fotoğraflar okunamadı.")
    s.load_bytes(out.tobytes(garbage=3, deflate=True), name="Taranan belge.pdf")
    return {"changed": True, "opened": True,
            "message": f"{out.page_count} fotoğraf PDF yapıldı ({fixed} tanesinin kenarları bulunup düzleştirildi). Metin tanıma için Dönüştür → Aranabilir PDF."}


def _scan_document(img):
    import cv2
    import numpy as np
    h, w = img.shape[:2]
    scale = 1000 / max(h, w)
    small = cv2.resize(img, (int(w * scale), int(h * scale)))
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.dilate(cv2.Canny(gray, 50, 150), np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:6]:
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4 and cv2.contourArea(approx) > 0.2 * small.shape[0] * small.shape[1]:
            pts = approx.reshape(4, 2).astype("float32") / scale
            s_ = pts.sum(axis=1)
            d = np.diff(pts, axis=1).ravel()
            tl, br, tr, bl = pts[np.argmin(s_)], pts[np.argmax(s_)], pts[np.argmin(d)], pts[np.argmax(d)]
            wid = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
            hei = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
            m = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype="float32"),
                                            np.array([[0, 0], [wid - 1, 0], [wid - 1, hei - 1], [0, hei - 1]], dtype="float32"))
            return cv2.warpPerspective(img, m, (wid, hei)), 1
    return img, 0


def op_to_text_local(s, a, job):
    doc = s.require()
    text = "\n\n".join(f"--- Sayfa {p.number + 1} ---\n{p.get_text('text').strip()}" for p in doc)
    return {"text": text}


# ---------------------------------------------------------------- karşılaştırma

def op_compare(s, a, job):
    doc = s.require()
    other_path = a.get("path") or ask_open("Karşılaştırılacak diğer sürümü seç")
    if not other_path:
        return {"cancelled": True}
    other = pymupdf.open(other_path)
    old_words = [(w[4], p.number) for p in other for w in p.get_text("words", sort=True)]
    new_words = [(w[4], p.number, w[:4]) for p in doc for w in p.get_text("words", sort=True)]
    sm = difflib.SequenceMatcher(a=[w[0] for w in old_words], b=[w[0] for w in new_words], autojunk=False)
    changes = []
    marks = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        old = " ".join(w[0] for w in old_words[i1:i2])
        new = " ".join(w[0] for w in new_words[j1:j2])
        page = new_words[j1][1] if j1 < len(new_words) else (new_words[-1][1] if new_words else 0)
        kind = {"replace": "Değişti", "delete": "Silindi", "insert": "Eklendi"}[tag]
        changes.append({"kind": kind, "old": old[:400], "new": new[:400], "page": page})
        for w in new_words[j1:j2]:
            marks.setdefault(w[1], []).append(w[2])
    # farkları işaretli bir kopya: yalnız görüntüde, belgeyi değiştirmeden
    s.compare = {"other": other_path, "changes": changes}
    summary = f"{len(changes)} fark bulundu ({other.page_count} → {doc.page_count} sayfa)."
    return {"changes": changes[:500], "marks": {str(k): v for k, v in marks.items()}, "summary": summary,
            "other_name": os.path.basename(other_path)}


# ---------------------------------------------------------------- erişilebilirlik

def op_access_check(s, a, job):
    doc = s.require()
    cat = doc.pdf_catalog()
    items = []

    def add(ok, title, detail):
        items.append({"ok": ok, "title": title, "detail": detail})

    meta = doc.metadata or {}
    add(bool(meta.get("title")), "Belge başlığı", meta.get("title") or "Başlık yok; ekran okuyucular dosya adını okur.")
    lang = doc.xref_get_key(cat, "Lang")
    add(lang[0] != "null", "Belge dili", lang[1].strip("()") if lang[0] != "null" else "Dil belirtilmemiş.")
    marked = doc.xref_get_key(cat, "MarkInfo")
    add(marked[0] != "null", "Etiketli PDF", "Etiketli." if marked[0] != "null" else "Etiket yok: başlık, paragraf ve tablo yapısı ekran okuyucuya aktarılamaz.")
    scanned = s.scanned_pages()
    add(not scanned, "Metin olarak okunabilirlik",
        "Tüm sayfalarda metin var." if not scanned else f"{len(scanned)} sayfa taranmış (metin yok). Aranabilir PDF yap.")
    imgs = sum(len(p.get_images()) for p in doc)
    add(imgs == 0, "Görsel açıklamaları", "Görsel yok." if imgs == 0 else f"{imgs} görsel var; açıklama (alternatif metin) üretilebilir.")
    add(bool(doc.get_toc()), "Yer imleri", "Var." if doc.get_toc() else "Yer imi yok; uzun belgelerde gezinmeyi zorlaştırır.")
    fields = list_fields(doc)
    unnamed = [f for f in fields if not f["label"]]
    if fields:
        add(not unnamed, "Form alanı açıklamaları", "Tamam." if not unnamed else f"{len(unnamed)} alanın açıklaması yok.")
    return {"items": items}


def op_access_fix(s, a, job):
    doc = s.require()
    meta = doc.metadata or {}
    meta["title"] = a.get("title") or meta.get("title") or stem(s.name)
    doc.set_metadata(meta)
    cat = doc.pdf_catalog()
    doc.xref_set_key(cat, "Lang", f"({a.get('lang') or 'tr-TR'})")
    doc.xref_set_key(cat, "ViewerPreferences", "<</DisplayDocTitle true>>")
    if a.get("toc") and not doc.get_toc():
        toc = []
        for page in doc:
            for b in page.get_text("dict")["blocks"]:
                for line in b.get("lines", []):
                    spans = line["spans"]
                    if spans and spans[0]["size"] >= 15 and len("".join(x["text"] for x in spans).strip()) > 2:
                        toc.append([1, "".join(x["text"] for x in spans).strip()[:80], page.number + 1])
        if toc:
            doc.set_toc(toc[:200])
    for page in doc:
        for w in page.widgets():
            if not w.field_label:
                w.field_label = w.field_name
                w.update()
    s.commit()
    return {"changed": True, "message": "Başlık, dil, belge başlığını gösterme ve form açıklamaları eklendi."}


# ---------------------------------------------------------------- toplu işlem

def op_batch(s, a, job):
    from ops_ai import BATCH_AI
    folder = a.get("folder") or ask_folder("PDF'lerin olduğu klasörü seç")
    if not folder:
        return {"cancelled": True}
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".pdf"))
    if not files:
        raise UserError("Klasörde PDF yok.")
    outdir = os.path.join(folder, "PDF Stüdyo çıktısı")
    os.makedirs(outdir, exist_ok=True)
    action = a.get("action", "compress")
    done, failed = 0, []
    for i, name in enumerate(files):
        job.update(i / len(files), f"{i + 1}/{len(files)}: {name}")
        src = os.path.join(folder, name)
        try:
            doc = pymupdf.open(src)
            if action == "compress":
                doc.rewrite_images(dpi_threshold=150, dpi_target=110, quality=65)
                doc.save(os.path.join(outdir, name), garbage=4, deflate=True, use_objstms=1)
            elif action == "sanitize":
                doc.scrub()
                doc.set_metadata({})
                doc.save(os.path.join(outdir, name), garbage=3, deflate=True)
            elif action == "watermark":
                tmp = _Tmp(doc)
                op_watermark(tmp, {"text": a.get("text") or "GİZLİ"}, job)
                fix_fonts(tmp.doc)
                tmp.doc.save(os.path.join(outdir, name), garbage=3, deflate=True)
            elif action == "page_numbers":
                tmp = _Tmp(doc)
                op_page_numbers(tmp, {}, job)
                fix_fonts(tmp.doc)
                tmp.doc.save(os.path.join(outdir, name), garbage=3, deflate=True)
            elif action == "protect":
                pw = a.get("password") or ""
                if not pw:
                    raise UserError("Parola gerekli.")
                doc.save(os.path.join(outdir, name), encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=pw, owner_pw=pw,
                         garbage=3, deflate=True)
            elif action == "images":
                for p in doc:
                    p.get_pixmap(dpi=150).save(os.path.join(outdir, f"{stem(name)} - s{p.number + 1:03d}.png"))
            elif action in BATCH_AI:
                BATCH_AI[action](doc, os.path.join(outdir, stem(name)), job)
            else:
                raise UserError("Bilinmeyen işlem.")
            done += 1
        except UserError as e:
            if str(e) == "İşlem iptal edildi.":
                raise
            failed.append(f"{name}: {e}")
        except Exception as e:
            failed.append(f"{name}: {type(e).__name__}")
    msg = f"{done}/{len(files)} dosya işlendi."
    if failed:
        msg += " Sorun çıkanlar: " + "; ".join(failed[:5])
    return {"saved": outdir, "message": msg}


class _Tmp:
    """Toplu işlemde tek dosya için geçici oturum (commit belgeyi değiştirmeden bırakır)."""

    def __init__(self, doc):
        self.doc = doc
        self.name = "belge.pdf"

    def require(self):
        return self.doc

    def commit(self):
        pass


LOCAL_OPS = {k[3:]: v for k, v in globals().items() if k.startswith("op_") and callable(v)}
