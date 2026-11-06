"""Claude ile yapılan işler: metin tanıma, dönüştürme, asistan, çeviri, formlar, karartma, karşılaştırma, rapor."""
import base64
import html as html_lib
import io
import json
import os
import re
import time

import keyring
import pymupdf

from core import (SESSION, UserError, fix_fonts, to_bytes, ask_open_many, ask_save, ensure_font, fit_text, load_settings, save_settings,
                  stem, FONT_REGULAR, page_text_lines)
from ops_local import (R, add_widget, apply_redactions, html_to_pdf, list_fields, replace_phrase, set_field_values,
                       _as_pdf)

MODEL = "claude-sonnet-5-5"
KEYRING_SERVICE = "PDF Stüdyo"
KEYRING_USER = "anthropic_api_key"
PRICE_IN, PRICE_OUT = 2.0, 10.0      # $ / 1M token (Claude Sonnet 5.5)
USAGE = {"input": 0, "output": 0, "calls": 0}

TR = "Respond in Turkish unless the task says otherwise."


# ---------------------------------------------------------------- istemci ve çağrı

def get_key():
    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    except Exception:
        return None


def client():
    key = get_key()
    if not key:
        raise UserError("API_ANAHTARI_YOK")
    import anthropic   # ağır kütüphane: ilk Claude işinde (ya da açılışta arka planda) yüklenir
    return anthropic.Anthropic(api_key=key, max_retries=3, timeout=900)


def op_ai_key_status(s, a, job):
    k = get_key()
    return {"set": bool(k), "hint": (k[:10] + "…" + k[-4:]) if k else "", "usage": usage_summary()}


def op_ai_key_set(s, a, job):
    key = (a.get("key") or "").strip()
    if not key:
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
        except Exception:
            pass
        return {"set": False}
    if not key.startswith("sk-ant-"):
        raise UserError("Bu bir Claude API anahtarına benzemiyor (sk-ant- ile başlamalı).")
    import anthropic
    test = anthropic.Anthropic(api_key=key, max_retries=1, timeout=60)
    job.update(0.3, "Anahtar deneniyor…")
    test.models.retrieve(MODEL)       # ücretsiz bir çağrı: anahtar ve model erişimi doğrulanır
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key)
    return {"set": True, "hint": key[:10] + "…" + key[-4:], "message": "Anahtar doğrulandı ve Windows Kimlik Bilgisi Yöneticisi'ne kaydedildi."}


def usage_summary():
    cost = USAGE["input"] / 1e6 * PRICE_IN + USAGE["output"] / 1e6 * PRICE_OUT
    return {"calls": USAGE["calls"], "input": USAGE["input"], "output": USAGE["output"], "cost": round(cost, 4)}


def call(content=None, system="", schema=None, effort="medium", max_tokens=48000, job=None, messages=None,
         progress=(0.1, 0.9), label="Claude çalışıyor"):
    """Claude'a tek istek. schema verilirse JSON döner, yoksa mesajın kendisini."""
    cl = client()
    output_config = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system,
                  messages=messages or [{"role": "user", "content": content}],
                  output_config=output_config, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    lo, hi = progress

    def consume(stream):
        written = 0
        for event in stream:
            if event.type == "content_block_delta" and getattr(event.delta, "type", "") == "text_delta":
                written += len(event.delta.text)
                if job:
                    job.update(lo + (hi - lo) * min(0.95, written / 6000), f"{label}… ({written} karakter)")
            elif job:
                job.update(None, None)    # iptal edildiyse burada durur
        return stream.get_final_message()

    import anthropic
    try:
        with cl.beta.messages.stream(**kwargs) as stream:
            msg = consume(stream)
    except anthropic.BadRequestError as e:
        # Yedek model özelliği bu hesapta ya da modelde kabul edilmezse aynı isteği onsuz bir kez dene.
        if "fallback" not in str(e).lower() and "beta" not in str(e).lower():
            raise
        kwargs.pop("betas")
        kwargs.pop("fallbacks")
        with cl.messages.stream(**kwargs) as stream:
            msg = consume(stream)
    USAGE["calls"] += 1
    USAGE["input"] += (msg.usage.input_tokens or 0) + (getattr(msg.usage, "cache_read_input_tokens", 0) or 0) \
        + (getattr(msg.usage, "cache_creation_input_tokens", 0) or 0)
    USAGE["output"] += msg.usage.output_tokens or 0
    if msg.stop_reason == "refusal":
        raise UserError("Claude bu isteği güvenlik nedeniyle yanıtlamadı.")
    if msg.stop_reason == "max_tokens":
        raise UserError("Çıktı çok uzun oldu ve yarıda kesildi. Daha az sayfa seçip tekrar dene.")
    if schema:
        text = "".join(b.text for b in msg.content if b.type == "text")
        try:
            return json.loads(text)
        except ValueError:
            raise UserError("Claude'un yanıtı okunamadı. Tekrar dene.")
    return msg


def text_of(msg):
    return "".join(b.text for b in msg.content if b.type == "text").strip()


# ---------------------------------------------------------------- belgeyi Claude'a verme

def subset_pdf(doc, pages):
    out = pymupdf.open()
    for p in pages:
        out.insert_pdf(doc, from_page=p, to_page=p)
    data = out.tobytes(garbage=3, deflate=True)
    if len(data) > 28 * 1024 * 1024:
        out.rewrite_images(dpi_threshold=120, dpi_target=100, quality=60)
        data = out.tobytes(garbage=4, deflate=True)
    if len(data) > 31 * 1024 * 1024:
        raise UserError("Seçilen sayfalar Claude'a göndermek için çok büyük. Daha az sayfa seç ya da önce sıkıştır.")
    return data


def pdf_block(doc, pages, title=None, citations=False, cache=False):
    block = {"type": "document",
             "source": {"type": "base64", "media_type": "application/pdf",
                        "data": base64.standard_b64encode(subset_pdf(doc, pages)).decode()}}
    if title:
        block["title"] = title
    if citations:
        block["citations"] = {"enabled": True}
    if cache:
        block["cache_control"] = {"type": "ephemeral"}
    return block


def image_block(doc, pno, longest=1600):
    page = doc[pno]
    zoom = longest / max(page.rect.width, page.rect.height)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.standard_b64encode(pix.tobytes("jpeg", jpg_quality=85)).decode()}}


def chunks(pages, n):
    return [pages[i:i + n] for i in range(0, len(pages), n)]


def _pages(s, a, doc):
    from core import parse_pages
    return parse_pages(a.get("pages"), doc.page_count)


def norm_rect(page, box):
    """0-1000 ölçekli kutuyu (görünen sayfa) PDF koordinatına çevirir."""
    w, h = page.rect.width, page.rect.height
    r = pymupdf.Rect(box[0] * w / 1000, box[1] * h / 1000, box[2] * w / 1000, box[3] * h / 1000).normalize()
    if page.rotation:
        r = (r * page.derotation_matrix).normalize()
    return r


def S(props, required=None):
    """Katı JSON şeması kısaltması."""
    return {"type": "object", "properties": props, "required": required or list(props), "additionalProperties": False}


STR = {"type": "string"}
INT = {"type": "integer"}
NUM = {"type": "number"}
BOX = {"type": "array", "items": INT, "description": "[x0, y0, x1, y1] on a 0-1000 scale of the page image"}


def arr(item):
    return {"type": "array", "items": item}


# ---------------------------------------------------------------- metin tanıma

OCR_SCHEMA = S({"pages": arr(S({"page": INT, "lines": arr(S({"text": STR, "box": BOX}))}))})


def ocr_pages(doc, pages, job, lo=0.0, hi=1.0):
    """Sayfa görüntülerinden satır satır metin ve konum."""
    result = {}
    groups = chunks(pages, 2)
    for gi, group in enumerate(groups):
        span = (lo + (hi - lo) * gi / len(groups), lo + (hi - lo) * (gi + 1) / len(groups))
        content = []
        for p in group:
            content.append({"type": "text", "text": f"Image for page {p + 1}:"})
            content.append(image_block(doc, p))
        content.append({"type": "text", "text":
                        "Transcribe every line of text on these page images, including handwriting, stamps, table cells "
                        "and small print, exactly as written (keep the original language and Turkish characters). "
                        "One entry per visual line, in reading order. For each line give its bounding box on a 0-1000 "
                        "scale of that page image (x from left, y from top). Use the page numbers given above."})
        data = call(content, system="You are a precise OCR engine.", schema=OCR_SCHEMA, effort="medium", job=job,
                    progress=span, label=f"Metin tanınıyor (sayfa {group[0] + 1}-{group[-1] + 1})")
        for pg in data["pages"]:
            if pg["page"] - 1 in group:
                result[pg["page"] - 1] = pg["lines"]
    return result


def add_text_layer(doc, ocr):
    """Görünmez metin katmanı: görüntü aynı kalır, metin seçilip aranabilir olur."""
    font = pymupdf.Font(fontfile=FONT_REGULAR)
    for pno, lines in ocr.items():
        page = doc[pno]
        name = ensure_font(page)
        for line in lines:
            text = line["text"].strip()
            if not text or len(line["box"]) != 4:
                continue
            r = norm_rect(page, line["box"])
            if r.is_empty or r.height < 2:
                continue
            size = max(3, r.height * 0.82)
            width = font.text_length(text, size) or 1
            sx = r.width / width
            origin = pymupdf.Point(r.x0, r.y1 - r.height * 0.2)
            page.insert_text(origin, text, fontsize=size, fontname=name, render_mode=3,
                             morph=(origin, pymupdf.Matrix(sx, 1)), rotate=page.rotation)


def op_ai_searchable(s, a, job):
    doc = s.require()
    pages = s.scanned_pages() if not a.get("pages") else _pages(s, a, doc)
    if not pages:
        raise UserError("Taranmış sayfa yok: bu belgenin metni zaten seçilebilir.")
    ocr = ocr_pages(doc, pages, job, 0.02, 0.92)
    job.update(0.95, "Metin katmanı ekleniyor…")
    add_text_layer(doc, ocr)
    s.commit()
    n = sum(len(v) for v in ocr.values())
    return {"changed": True, "message": f"{len(pages)} sayfaya {n} satır metin eklendi. Artık metni seçebilir ve arayabilirsin."}


def op_ai_transcribe(s, a, job):
    """El yazısı / taranmış sayfaları düz metne çevirir."""
    doc = s.require()
    pages = _pages(s, a, doc)
    ocr = ocr_pages(doc, pages, job, 0.02, 0.98)
    parts = []
    for p in pages:
        parts.append(f"--- Sayfa {p + 1} ---\n" + "\n".join(l["text"] for l in ocr.get(p, [])))
    return {"text": "\n\n".join(parts)}


def op_ai_to_text(s, a, job):
    doc = s.require()
    scanned = set(s.scanned_pages())
    ocr = ocr_pages(doc, sorted(scanned), job, 0.02, 0.95) if scanned else {}
    parts = []
    for p in doc:
        body = "\n".join(l["text"] for l in ocr.get(p.number, [])) if p.number in scanned else p.get_text("text").strip()
        parts.append(f"--- Sayfa {p.number + 1} ---\n{body}")
    return {"text": "\n\n".join(parts)}


# ---------------------------------------------------------------- Word

DOC_SCHEMA = S({"blocks": arr(S({
    "type": {"type": "string", "enum": ["heading", "paragraph", "bullet_list", "numbered_list", "table", "image", "page_break"]},
    "level": INT, "text": STR, "items": arr(STR), "rows": arr(arr(STR)), "align": {"type": "string", "enum": ["left", "center", "right", "justify"]},
}))})

WORD_PROMPT = """Convert these PDF pages into a structured document so it can be rebuilt as an editable Word file.
Rules:
- Keep ALL text, in the original order and language. Do not summarize, translate, or correct anything{extra}.
- heading: use level 1-3 for real headings only. paragraph: join lines of the same paragraph into one text (remove hyphenation at line ends). Use **double asterisks** around bold words.
- bullet_list / numbered_list: put each item in items.
- table: rows is a list of rows, each a list of cell strings; first row is the header if there is one. Use empty strings for empty or merged cells.
- image: where a picture, logo or chart appears, set text to its reference from the list below (e.g. "p3_1"). Omit decorative lines.
- Skip repeating page headers/footers and page numbers. Add page_break between pages only if the next page starts a new section.
- Unused fields: level 0, text "", items [], rows [], align "left".
Images on these pages: {images}"""


def page_images(doc, pages, min_size=40):
    refs, listing = {}, []
    for p in pages:
        for i, info in enumerate(doc[p].get_image_info(xrefs=True), 1):
            r = pymupdf.Rect(info["bbox"])
            if not info.get("xref") or r.width < min_size or r.height < min_size:
                continue
            ref = f"p{p + 1}_{i}"
            refs[ref] = (p, info["xref"], r)
            listing.append(f"{ref} (page {p + 1}, {int(r.width)}x{int(r.height)} pt at y={int(r.y0)})")
    return refs, ", ".join(listing) or "none"


def structure_doc(doc, pages, job, extra="", lo=0.0, hi=1.0, translate_to=None):
    blocks, refs_all = [], {}
    groups = chunks(pages, 10)
    for gi, group in enumerate(groups):
        refs, listing = page_images(doc, group)
        refs_all.update(refs)
        prompt = WORD_PROMPT.format(images=listing, extra=extra)
        if translate_to:
            prompt = prompt.replace("Do not summarize, translate, or correct anything",
                                    f"Translate all text into {translate_to}; do not summarize")
        span = (lo + (hi - lo) * gi / len(groups), lo + (hi - lo) * (gi + 1) / len(groups))
        data = call([pdf_block(doc, group), {"type": "text", "text": prompt}], schema=DOC_SCHEMA, effort="medium",
                    job=job, progress=span, label=f"Sayfa {group[0] + 1}-{group[-1] + 1} okunuyor")
        blocks.extend(data["blocks"])
    return blocks, refs_all


def _add_runs(par, text):
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            run = par.add_run(part)
            run.bold = i % 2 == 1


def build_docx(doc, blocks, refs, path, title=None):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, Inches
    d = Document()
    st = d.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(11)
    if title:
        d.core_properties.title = title
    align = {"center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT,
             "justify": WD_ALIGN_PARAGRAPH.JUSTIFY}
    for b in blocks:
        t = b["type"]
        if t == "heading":
            h = d.add_heading(level=max(1, min(3, b.get("level") or 1)))
            _add_runs(h, b["text"].replace("**", ""))
        elif t == "paragraph":
            par = d.add_paragraph()
            _add_runs(par, b["text"])
            if b.get("align") in align:
                par.alignment = align[b["align"]]
        elif t in ("bullet_list", "numbered_list"):
            style = "List Bullet" if t == "bullet_list" else "List Number"
            for it in b.get("items") or [b.get("text", "")]:
                _add_runs(d.add_paragraph(style=style), it)
        elif t == "table" and b.get("rows"):
            rows = b["rows"]
            ncol = max(len(r) for r in rows)
            table = d.add_table(rows=len(rows), cols=ncol)
            table.style = "Table Grid"
            for i, r in enumerate(rows):
                for j in range(ncol):
                    cell = table.cell(i, j)
                    cell.text = ""
                    _add_runs(cell.paragraphs[0], r[j] if j < len(r) else "")
                    if i == 0:
                        for run in cell.paragraphs[0].runs:
                            run.bold = True
            d.add_paragraph()
        elif t == "image" and b.get("text") in refs:
            p, xref, r = refs[b["text"]]
            try:
                pix = pymupdf.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                width = min(6.3, max(0.6, r.width / 72))
                d.add_picture(io.BytesIO(pix.tobytes("png")), width=Inches(width))
            except Exception:
                pass
        elif t == "page_break":
            d.add_page_break()
    d.save(path)


def op_ai_to_word(s, a, job, translate_to=None):
    doc = s.require()
    pages = _pages(s, a, doc)
    suffix = f" ({translate_to})" if translate_to else ""
    path = a.get("out") or ask_save("Word olarak kaydet", f"{stem(s.name)}{suffix}.docx", ".docx", [("Word", "*.docx")])
    if not path:
        return {"cancelled": True}
    blocks, refs = structure_doc(doc, pages, job, lo=0.02, hi=0.95, translate_to=translate_to)
    job.update(0.97, "Word dosyası yazılıyor…")
    build_docx(doc, blocks, refs, path, title=stem(s.name))
    return {"saved": path, "message": f"{len(pages)} sayfa Word'e çevrildi.", "open_file": path}


# ---------------------------------------------------------------- Excel

TABLE_SCHEMA = S({"tables": arr(S({"title": STR, "page": INT, "header": arr(STR), "rows": arr(arr(STR))}))})


def _num(v):
    s_ = str(v).strip().replace(" ", " ")
    m = re.fullmatch(r"(-?)(?:₺|TL|\$|€)?\s*([\d.]+(?:,\d+)?|[\d,]+(?:\.\d+)?)\s*(?:₺|TL|\$|€|%)?", s_)
    if not m or not re.search(r"\d", s_):
        return v
    num = m.group(2)
    if "," in num and "." in num:
        num = num.replace(".", "").replace(",", ".") if num.rfind(",") > num.rfind(".") else num.replace(",", "")
    elif "," in num:
        num = num.replace(",", ".") if len(num.split(",")[-1]) != 3 else num.replace(",", "")
    elif num.count(".") > 1 or (num.count(".") == 1 and len(num.split(".")[-1]) == 3 and len(num) > 4):
        num = num.replace(".", "")
    try:
        f = float(m.group(1) + num)
        return int(f) if f.is_integer() and "." not in num else f
    except ValueError:
        return v


def op_ai_to_excel(s, a, job):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    doc = s.require()
    pages = _pages(s, a, doc)
    path = a.get("out") or ask_save("Excel olarak kaydet", f"{stem(s.name)}.xlsx", ".xlsx", [("Excel", "*.xlsx")])
    if not path:
        return {"cancelled": True}
    tables = []
    groups = chunks(pages, 8)
    for gi, group in enumerate(groups):
        data = call([pdf_block(doc, group), {"type": "text", "text":
                     "Find every table on these pages (including tables in scanned images) and extract them completely. "
                     "Keep cell text exactly as written; numbers as they appear. A table continuing across pages is one "
                     "table. If there is no table but there is clearly tabular data (lists of items with amounts), extract "
                     "that. title: a short Turkish name for the table. page: the page number where it starts."}],
                    schema=TABLE_SCHEMA, effort="medium", job=job,
                    progress=(0.02 + 0.9 * gi / len(groups), 0.02 + 0.9 * (gi + 1) / len(groups)), label="Tablolar okunuyor")
        tables.extend(data["tables"])
    if not tables:
        raise UserError("Bu sayfalarda tablo bulunamadı.")
    wb = Workbook()
    wb.remove(wb.active)
    used = set()
    for i, t in enumerate(tables, 1):
        name = re.sub(r"[\[\]:*?/\\]", "", t["title"] or f"Tablo {i}")[:28] or f"Tablo {i}"
        while name in used:
            name = name[:25] + f" {i}"
        used.add(name)
        ws = wb.create_sheet(name)
        if t["header"]:
            ws.append(t["header"])
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="4F46E5")
            ws.freeze_panes = "A2"
        for r in t["rows"]:
            ws.append([_num(v) for v in r])
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(48, max(8, max(len(str(c.value or "")) for c in col) + 2))
    wb.save(path)
    return {"saved": path, "message": f"{len(tables)} tablo Excel'e aktarıldı.", "open_file": path}


# ---------------------------------------------------------------- PowerPoint

SLIDE_SCHEMA = S({"title": STR, "subtitle": STR, "slides": arr(S({
    "layout": {"type": "string", "enum": ["section", "bullets", "two_column", "quote", "numbers"]},
    "title": STR, "bullets": arr(STR), "right": arr(STR), "notes": STR, "image": STR}))})


def op_ai_to_pptx(s, a, job):
    doc = s.require()
    pages = _pages(s, a, doc)
    story = a.get("mode") == "story"
    path = a.get("out") or ask_save("Sunum olarak kaydet", f"{stem(s.name)}.pptx", ".pptx", [("PowerPoint", "*.pptx")])
    if not path:
        return {"cancelled": True}
    refs, listing = page_images(doc, pages, 80)
    if story:
        prompt = ("Design a clear, persuasive presentation from this document (8-15 slides). Restructure the content into "
                  "a narrative: opening, key points, evidence and numbers, conclusion. Each slide has one idea, a short "
                  "title and at most 5 concise bullets (max ~12 words each). Use 'numbers' layout for key figures "
                  "(bullets like '42% — what it means'), 'two_column' for comparisons (bullets=left, right=right column), "
                  "'quote' for one strong statement, 'section' for section dividers. Put talking points in notes. ")
    else:
        prompt = ("Convert this document into slides that follow its own structure: one slide per section or page, "
                  "title from the heading, the content as concise bullets (keep the original wording where possible). ")
    prompt += f"Write in the document's language. image: optionally one image reference from this list or \"\": {listing}"
    data = call([pdf_block(doc, pages[:100]), {"type": "text", "text": prompt}], schema=SLIDE_SCHEMA,
                effort="high" if story else "medium", job=job, progress=(0.05, 0.9), label="Sunum hazırlanıyor")
    job.update(0.93, "PowerPoint dosyası yazılıyor…")
    build_pptx(doc, data, refs, path)
    return {"saved": path, "message": f"{len(data['slides']) + 1} slaytlık sunum hazırlandı.", "open_file": path}


def build_pptx(doc, data, refs, path):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Emu, Pt
    from pptx.enum.shapes import MSO_SHAPE

    ACC = RGBColor(0x4F, 0x46, 0xE5)
    INK = RGBColor(0x16, 0x18, 0x1D)
    MUTED = RGBColor(0x5B, 0x62, 0x70)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    W, H = prs.slide_width, prs.slide_height
    blank = prs.slide_layouts[6]

    def text(slide, x, y, w, h, value, size, color=INK, bold=False, lines=None):
        tb = slide.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame
        tf.word_wrap = True
        items = lines if lines is not None else [value]
        for i, line in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = ("•  " + line) if lines is not None else line
            p.font.size = Pt(size)
            p.font.bold = bold
            p.font.color.rgb = color
            p.font.name = "Segoe UI"
            p.space_after = Pt(10)
        return tb

    def bar(slide):
        r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Emu(180000), H)
        r.fill.solid()
        r.fill.fore_color.rgb = ACC
        r.line.fill.background()

    m = Emu(700000)
    s0 = prs.slides.add_slide(blank)
    bar(s0)
    text(s0, m, Emu(2300000), W - 2 * m, Emu(1200000), data["title"], 40, bold=True)
    text(s0, m, Emu(3500000), W - 2 * m, Emu(800000), data.get("subtitle", ""), 20, MUTED)
    for sl in data["slides"]:
        slide = prs.slides.add_slide(blank)
        bar(slide)
        lay = sl["layout"]
        if lay == "section":
            text(slide, m, Emu(2600000), W - 2 * m, Emu(1200000), sl["title"], 36, ACC, True)
        elif lay == "quote":
            text(slide, m, Emu(2000000), W - 2 * m, Emu(2400000), "“" + (sl["bullets"][0] if sl["bullets"] else sl["title"]) + "”", 30, INK, True)
            text(slide, m, Emu(4600000), W - 2 * m, Emu(600000), sl["title"], 16, MUTED)
        else:
            text(slide, m, Emu(500000), W - 2 * m, Emu(900000), sl["title"], 30, INK, True)
            img = refs.get(sl.get("image") or "")
            body_w = W - 2 * m
            if img and lay != "two_column":
                body_w = int((W - 2 * m) * 0.55)
                try:
                    p, xref, r = img
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.n - pix.alpha >= 4:
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    pic = slide.shapes.add_picture(io.BytesIO(pix.tobytes("png")), m + body_w + Emu(300000), Emu(1600000),
                                                   width=int((W - 2 * m) * 0.4))
                    if pic.height > H - Emu(2000000):
                        ratio = (H - Emu(2000000)) / pic.height
                        pic.height = int(pic.height * ratio)
                        pic.width = int(pic.width * ratio)
                except Exception:
                    body_w = W - 2 * m
            if lay == "two_column":
                half = int((W - 2 * m) / 2) - Emu(150000)
                text(slide, m, Emu(1600000), half, H - Emu(2200000), "", 18, lines=sl["bullets"])
                text(slide, m + half + Emu(300000), Emu(1600000), half, H - Emu(2200000), "", 18, lines=sl["right"])
            elif lay == "numbers":
                n = max(1, len(sl["bullets"]))
                cw = int((W - 2 * m) / min(n, 4))
                for i, b in enumerate(sl["bullets"][:4]):
                    big, _, rest = b.partition("—")
                    text(slide, m + i * cw, Emu(2000000), cw - Emu(200000), Emu(1000000), big.strip(), 40, ACC, True)
                    text(slide, m + i * cw, Emu(3100000), cw - Emu(200000), Emu(1500000), rest.strip(), 16, MUTED)
            else:
                text(slide, m, Emu(1600000), body_w, H - Emu(2200000), "", 20, lines=sl["bullets"])
        if sl.get("notes"):
            slide.notes_slide.notes_text_frame.text = sl["notes"]
    prs.save(path)


# ---------------------------------------------------------------- özet, sohbet, çalışma alanı

def doc_pages_limit(doc):
    return list(range(min(doc.page_count, 500)))


def op_ai_summary(s, a, job):
    doc = s.require()
    length = a.get("length", "orta")
    guide = {"kısa": "3-5 bullet points", "orta": "a short paragraph followed by the key points as bullets",
             "uzun": "a section-by-section summary with headings"}[length]
    msg = call([pdf_block(doc, doc_pages_limit(doc)), {"type": "text", "text":
                f"Summarize this document as {guide}. Mention important dates, amounts, parties, obligations and "
                f"deadlines if present. Use Markdown. {TR}"}], effort="medium", job=job, label="Özetleniyor")
    return {"text": text_of(msg)}


def _citation_segments(msg, titles):
    segs = []
    for b in msg.content:
        if b.type != "text":
            continue
        cites = []
        for c in (getattr(b, "citations", None) or []):
            if getattr(c, "type", "") == "page_location":
                cites.append({"doc": c.document_index, "title": titles[c.document_index] if c.document_index < len(titles) else "",
                              "page": c.start_page_number - 1, "quote": (c.cited_text or "")[:300]})
        segs.append({"text": b.text, "cites": cites})
    return segs


def op_ai_chat(s, a, job):
    doc = s.require()
    question = (a.get("question") or "").strip()
    if not question:
        raise UserError("Bir soru yaz.")
    ws = [p for p in (getattr(s, "workspace", None) or []) if os.path.exists(p)] if a.get("workspace") else []
    key = ("ws", tuple(ws)) if ws else ("doc", s.version)
    if getattr(s, "chat_key", None) != key or a.get("reset"):
        s.chat = []
        s.chat_key = key
    if not s.chat:
        blocks = []
        titles = []
        if ws:
            for p in ws:
                d = pymupdf.open(p)
                blocks.append(pdf_block(d, list(range(min(d.page_count, 300))), title=os.path.basename(p), citations=True))
                titles.append(os.path.basename(p))
        else:
            blocks.append(pdf_block(doc, doc_pages_limit(doc), title=s.name, citations=True))
            titles.append(s.name)
        blocks[-1]["cache_control"] = {"type": "ephemeral"}
        s.chat_titles = titles
        first = blocks + [{"type": "text", "text": question}]
        s.chat.append({"role": "user", "content": first})
    else:
        s.chat.append({"role": "user", "content": question})
    system = ("You answer questions about the user's documents. Base answers only on the documents and cite them. "
              "If the answer is not in the documents, say so plainly. Be concise. "
              "You cannot change the document from this chat. If the user asks for an edit (change text, make each "
              "CV/item fit on one page, delete or rotate pages), say that 'Komutla düzenle' (Düzenle sekmesi) does it, "
              "and give the exact command to paste there. Never claim you changed the document. " + TR)
    try:
        msg = call(system=system, messages=s.chat, effort="medium", job=job, label="Cevap yazılıyor")
    except Exception:
        s.chat.pop()
        raise
    s.chat.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in msg.content]})
    return {"segments": _citation_segments(msg, s.chat_titles), "titles": s.chat_titles}


def op_workspace(s, a, job):
    cur = list(getattr(s, "workspace", None) or [])
    if a.get("clear"):
        cur = []
    elif a.get("remove"):
        cur = [p for p in cur if p != a["remove"]]
    elif a.get("add"):
        paths = ask_open_many("Çalışma alanına PDF ekle")
        cur += [p for p in paths if p not in cur]
    if s.path and s.path not in cur and a.get("include_current", True) and cur:
        cur.insert(0, s.path)
    s.workspace = cur
    return {"workspace": [{"path": p, "name": os.path.basename(p)} for p in cur]}


# ---------------------------------------------------------------- yeniden yazma ve komutla düzenleme

STYLES = {"resmi": "more formal and professional", "sade": "simpler and easier to understand",
          "kisa": "shorter (about half the length) without losing meaning", "uzun": "more detailed and complete",
          "duzelt": "correct spelling, grammar and punctuation only; change nothing else",
          "akici": "more fluent and natural"}


def op_ai_rewrite(s, a, job):
    text = (a.get("text") or "").strip()
    if not text:
        raise UserError("Önce metin seç.")
    goal = STYLES.get(a.get("style"), a.get("custom") or "clearer")
    data = call([{"type": "text", "text": f"Rewrite the text below to be {goal}. Keep the same language and meaning. "
                  f"Return only the rewritten text.\n\n<text>\n{text}\n</text>"}],
                schema=S({"text": STR}), effort="low", job=job, label="Yeniden yazılıyor")
    return {"text": data["text"]}


def op_ai_translate_text(s, a, job):
    text = (a.get("text") or "").strip()
    data = call([{"type": "text", "text": f"Translate into {a.get('lang') or 'English'}. Return only the translation.\n\n{text}"}],
                schema=S({"text": STR}), effort="low", job=job, label="Çevriliyor")
    return {"text": data["text"]}


CHANGE_SCHEMA = S({
    "changes": arr(S({"page": INT, "find": STR, "replace": STR, "reason": STR})),
    "page_actions": arr(S({"action": {"type": "string", "enum": ["fit_one_page", "delete", "rotate"]},
                           "pages": arr(INT), "angle": INT, "reason": STR})),
    "note": STR})
ACTION_TR = {"fit_one_page": "Tek sayfaya sığdır", "delete": "Sil", "rotate": "Döndür"}


def op_ai_command(s, a, job):
    doc = s.require()
    instruction = (a.get("instruction") or "").strip()
    if not instruction:
        raise UserError("Ne yapılacağını yaz.")
    text = page_text_lines(doc, max_chars=600000)
    data = call([{"type": "text", "text":
                  f"The document has {doc.page_count} pages. Document text by page:\n{text}\n\n"
                  f"User instruction: {instruction}\n\n"
                  "Turn the instruction into edits of two kinds:\n"
                  "1) 'changes': exact text replacements. Each: page number, 'find' = text copied EXACTLY as it appears "
                  "on that page within one line (short and unique enough to locate), 'replace' = new text.\n"
                  "2) 'page_actions': layout operations on 1-based page numbers.\n"
                  "   - fit_one_page: the listed consecutive pages are ONE item that overflowed (e.g. one CV, letter or "
                  "form spread over 2+ pages); they are merged onto a single page, scaled down if needed. Work out where "
                  "each item starts (a new name/title/header) and make one action per item that spans 2+ pages. "
                  "Use this when the user wants things to fit on one page each.\n"
                  "   - delete: remove the listed pages.\n"
                  "   - rotate: rotate the listed pages by 'angle' (90, 180, 270).\n"
                  "   'angle' is 0 for non-rotate actions.\n"
                  "Only do what the instruction asks; leave a list empty when not needed. reason: one short Turkish "
                  "phrase. note: a short Turkish note if part of the request cannot be done with these tools, else \"\"."}],
                schema=CHANGE_SCHEMA, effort="high", job=job, label="Değişiklikler hazırlanıyor")
    changes = []
    for c in data["changes"]:
        p = c["page"] - 1
        if 0 <= p < doc.page_count:
            hits = doc[p].search_for(c["find"])
            changes.append({**c, "kind": "text", "page": p, "found": len(hits)})
    for act in data.get("page_actions", []):
        pages = sorted({p - 1 for p in act["pages"] if 1 <= p <= doc.page_count})
        if not pages or (act["action"] == "fit_one_page" and len(pages) < 2):
            continue
        if act["action"] == "fit_one_page":
            pages = list(range(pages[0], pages[-1] + 1))     # yalnız ardışık sayfalar birleşir
        label = ACTION_TR[act["action"]] + (f" ({act['angle']}°)" if act["action"] == "rotate" else "")
        rng = f"s. {pages[0] + 1}" + (f"–{pages[-1] + 1}" if len(pages) > 1 else "")
        changes.append({"kind": "page", "action": act["action"], "pages": pages, "angle": act.get("angle", 0),
                        "reason": act["reason"], "label": f"{label}: {rng}", "page": pages[0], "found": 1})
    return {"changes": changes, "note": data["note"]}


def op_apply_changes(s, a, job):
    from ops_local import fit_groups
    doc = s.require()
    applied, layout = 0, 0
    items = a.get("changes", [])
    for c in items:
        if c.get("kind", "text") != "text":
            continue
        page = doc[int(c["page"])]
        for r in page.search_for(c["find"]):
            replace_phrase(page, r, c["find"], c["replace"])
            applied += 1
    groups, drop = [], set()
    for c in items:
        if c.get("kind") != "page":
            continue
        pages = [int(p) for p in c["pages"] if 0 <= int(p) < doc.page_count]
        if c["action"] == "rotate":
            for p in pages:
                doc[p].set_rotation((doc[p].rotation + int(c.get("angle") or 90)) % 360)
        elif c["action"] == "delete":
            drop |= set(pages)
        elif c["action"] == "fit_one_page" and len(pages) > 1:
            groups.append(pages)
        layout += 1
    if not applied and not layout:
        raise UserError("Değiştirilecek metin belgede bulunamadı.")
    if len(drop) >= doc.page_count:
        raise UserError("Bütün sayfalar silinemez.")
    if groups or drop:
        fix_fonts(doc)
        out = fit_groups(doc, groups, drop)
        s.replace_with(out.tobytes(garbage=3, deflate=True))
    else:
        s.commit()
    parts = []
    if applied:
        parts.append(f"{applied} yerde metin değişti")
    if groups:
        parts.append(f"{len(groups)} parça tek sayfaya sığdırıldı")
    if drop:
        parts.append(f"{len(drop)} sayfa silindi")
    return {"changed": True, "message": ", ".join(parts).capitalize() + "." if parts else "Uygulandı."}


# ---------------------------------------------------------------- çeviri (düzeni koruyarak)

def op_ai_translate(s, a, job):
    doc = s.require()
    lang = a.get("lang") or "English"
    if a.get("output") == "docx":
        return op_ai_to_word(s, a, job, translate_to=lang)
    pages = _pages(s, a, doc)
    scanned = set(s.scanned_pages())
    out = pymupdf.open(stream=doc.tobytes(), filetype="pdf")
    skipped = [p + 1 for p in pages if p in scanned]
    work = [p for p in pages if p not in scanned]
    groups = chunks(work, 4)
    for gi, group in enumerate(groups):
        items = []
        for p in group:
            for bi, b in enumerate(out[p].get_text("dict")["blocks"]):
                if b["type"] != 0:
                    continue
                t = " ".join("".join(sp["text"] for sp in ln["spans"]) for ln in b["lines"]).strip()
                if t:
                    items.append({"id": f"{p}:{bi}", "text": t})
        if not items:
            continue
        data = call([{"type": "text", "text":
                      f"Translate each item into {lang}. Keep numbers, names, codes and formatting markers. Keep the "
                      f"translation about as long as the original (it must fit the same box). Return every id.\n"
                      + json.dumps(items, ensure_ascii=False)}],
                    schema=S({"items": arr(S({"id": STR, "text": STR}))}), effort="medium", job=job,
                    progress=(0.03 + 0.85 * gi / len(groups), 0.03 + 0.85 * (gi + 1) / len(groups)), label="Çevriliyor")
        tr = {i["id"]: i["text"] for i in data["items"]}
        for p in group:
            page = out[p]
            blocks = [(bi, b) for bi, b in enumerate(page.get_text("dict")["blocks"]) if b["type"] == 0]
            styled = []
            for bi, b in blocks:
                key = f"{p}:{bi}"
                if key not in tr:
                    continue
                spans = [sp for ln in b["lines"] for sp in ln["spans"] if sp["text"].strip()]
                size = max((sp["size"] for sp in spans), default=10)
                c = spans[0]["color"] if spans else 0
                color = ((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255)
                r = pymupdf.Rect(b["bbox"])
                if page.rotation:
                    r = (r * page.derotation_matrix).normalize()
                page.add_redact_annot(r, fill=False)
                styled.append((r, tr[key], size, color))
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
            for r, t, size, color in styled:
                fit_text(page, pymupdf.Rect(r.x0, r.y0, r.x1 + 2, r.y1 + size * 0.5), t, fontsize=size, color=color, max_size=size)
    job.update(0.95, "Çevrilmiş belge açılıyor…")
    s.replace_with(to_bytes(out), name=f"{stem(s.name)} ({lang}).pdf")
    s.path = None
    msg = f"Belge {lang} diline çevrildi; yeni dosya olarak kaydet."
    if skipped:
        msg += f" Taranmış sayfalar ({', '.join(map(str, skipped[:10]))}) çevrilmedi: önce Aranabilir PDF yap ya da Word çıktısını seç."
    return {"changed": True, "message": msg}


# ---------------------------------------------------------------- karartma

PII_TYPES = {"tc": "Turkish national ID numbers (TC kimlik no, 11 digits)", "iban": "IBAN and bank account numbers",
             "phone": "phone numbers", "email": "e-mail addresses", "address": "postal addresses",
             "name": "names of people", "card": "credit card numbers", "birth": "dates of birth",
             "plate": "vehicle plates", "health": "health information", "money": "amounts of money/salaries"}


def op_ai_find_sensitive(s, a, job):
    doc = s.require()
    types = a.get("types") or ["tc", "iban", "phone", "email", "address", "card"]
    wanted = "; ".join(PII_TYPES[t] for t in types if t in PII_TYPES)
    if a.get("custom"):
        wanted += "; " + a["custom"]
    text = page_text_lines(doc, max_chars=600000)
    content = [{"type": "text", "text": f"Document text by page:\n{text}"}]
    scanned = s.scanned_pages()
    if scanned:
        content.insert(0, pdf_block(doc, scanned[:50]))
        content.insert(1, {"type": "text", "text": "The attached PDF contains scanned pages " + ", ".join(str(p + 1) for p in scanned[:50]) + " (no text layer)."})
    content.append({"type": "text", "text":
                    f"Find every occurrence of: {wanted}. For each, copy the text EXACTLY as it appears on the page "
                    "(so it can be searched), give its page number and type (one Turkish word or two)."})
    data = call(content, schema=S({"items": arr(S({"text": STR, "page": INT, "type": STR}))}), effort="medium",
                job=job, label="Hassas bilgiler aranıyor")
    items = []
    seen = set()
    for it in data["items"]:
        p = it["page"] - 1
        if not (0 <= p < doc.page_count) or (it["text"], p) in seen:
            continue
        seen.add((it["text"], p))
        hits = doc[p].search_for(it["text"])
        items.append({"text": it["text"], "page": p, "type": it["type"], "found": len(hits),
                      "rects": [[r.x0, r.y0, r.x1, r.y1] for r in hits]})
    return {"items": items, "scanned": [p + 1 for p in scanned]}


# ---------------------------------------------------------------- karşılaştırma özeti, yorum özeti

def op_ai_compare_summary(s, a, job):
    changes = a.get("changes") or getattr(s, "compare", {}).get("changes", [])
    if not changes:
        raise UserError("Önce iki belgeyi karşılaştır.")
    listing = "\n".join(f"- s.{c['page'] + 1} {c['kind']}: «{c['old']}» → «{c['new']}»" for c in changes[:600])
    msg = call([{"type": "text", "text": f"These are word-level differences between an old and a new version of a "
                 f"document:\n{listing}\n\nExplain what changed in meaning, most important first (obligations, amounts, "
                 f"dates, deadlines, parties). Ignore pure formatting or typo fixes but mention that they exist. "
                 f"Use short Markdown bullets with page numbers. {TR}"}], effort="high", job=job, label="Farklar yorumlanıyor")
    return {"text": text_of(msg)}


def op_ai_comments_summary(s, a, job):
    from ops_local import op_annots
    annots = op_annots(s, {}, job)["annots"]
    rows = [a_ for a_ in annots if a_["text"] or a_["quoted"]]
    if not rows:
        raise UserError("Belgede yorum ya da vurgu yok.")
    listing = "\n".join(f"- s.{r['page'] + 1} [{r['type']}] {r['author']}: {r['text']} {('«' + r['quoted'] + '»') if r['quoted'] else ''}" for r in rows)
    msg = call([{"type": "text", "text": f"Comments and highlights in a document:\n{listing}\n\nGroup them into a "
                 f"to-do list (what needs to be done, with page numbers), then list open questions. Markdown. {TR}"}],
               effort="medium", job=job, label="Yorumlar özetleniyor")
    return {"text": text_of(msg)}


# ---------------------------------------------------------------- bilgi çıkarma

def op_ai_extract(s, a, job):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    fields = [f.strip() for f in (a.get("fields") or "").split(",") if f.strip()]
    paths = a.get("paths") or []
    if a.get("batch") and not paths:
        paths = ask_open_many("Bilgi çıkarılacak belgeleri seç")
        if not paths:
            return {"cancelled": True}
    docs = [(os.path.basename(p), _as_pdf(p)) for p in paths] if paths else [(s.name, s.require())]
    if fields:
        schema = S({"values": arr(S({"name": STR, "value": STR}))})
        ask = "Extract these fields: " + ", ".join(fields) + ". Use exactly these names. value: as written in the document, \"\" if missing."
    else:
        schema = S({"doc_type": STR, "values": arr(S({"name": STR, "value": STR}))})
        ask = ("Identify the document type (Turkish, e.g. Fatura, Sözleşme, Dekont) and extract its key fields "
               "(e.g. for an invoice: seller, buyer, invoice no, date, due date, subtotal, VAT, total; for a contract: "
               "parties, start/end dates, amounts, notice periods). Field names in Turkish.")
    rows = []
    for i, (name, d) in enumerate(docs):
        data = call([pdf_block(d, list(range(min(d.page_count, 100)))), {"type": "text", "text": ask}],
                    schema=schema, effort="medium", job=job,
                    progress=(0.05 + 0.85 * i / len(docs), 0.05 + 0.85 * (i + 1) / len(docs)), label=f"Okunuyor: {name}")
        row = {"Dosya": name}
        if data.get("doc_type"):
            row["Belge türü"] = data["doc_type"]
        for v in data["values"]:
            row[v["name"]] = v["value"]
        rows.append(row)
    if len(rows) == 1 and not a.get("save"):
        return {"fields": [{"name": k, "value": v} for k, v in rows[0].items() if k != "Dosya"]}
    out = a.get("out") or ask_save("Bilgileri Excel'e kaydet", "Çıkarılan bilgiler.xlsx", ".xlsx", [("Excel", "*.xlsx")])
    if not out:
        return {"cancelled": True}
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    wb = Workbook()
    ws = wb.active
    ws.title = "Bilgiler"
    ws.append(cols)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="4F46E5")
    for r in rows:
        ws.append([_num(r.get(c, "")) if c not in ("Dosya", "Belge türü") else r.get(c, "") for c in cols])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(45, max(10, max(len(str(c.value or "")) for c in col) + 2))
    wb.save(out)
    return {"saved": out, "message": f"{len(rows)} belgeden bilgi çıkarıldı.", "open_file": out}


# ---------------------------------------------------------------- grafik ve rapor

REPORT_SCHEMA = S({"title": STR, "summary": STR, "key_numbers": arr(S({"label": STR, "value": STR})),
                   "charts": arr(S({"title": STR, "type": {"type": "string", "enum": ["bar", "line", "pie"]},
                                    "labels": arr(STR), "series": arr(S({"name": STR, "values": arr(NUM)})),
                                    "unit": STR, "page": INT, "insight": STR}))})

PALETTE = ["#4F46E5", "#F59E0B", "#0EA5A4", "#E11D48", "#64748B", "#7C3AED"]


def _svg_chart(c):
    w, h, pad_l, pad_b, pad_t = 640, 300, 56, 56, 16
    labels, series = c["labels"], c["series"] or []
    esc = html_lib.escape
    if c["type"] == "pie" and series:
        vals = [max(0, v) for v in series[0]["values"]]
        total = sum(vals) or 1
        import math
        cx, cy, r = 150, 150, 120
        ang = -math.pi / 2
        parts, legend = [], []
        for i, v in enumerate(vals):
            a2 = ang + 2 * math.pi * v / total
            x1, y1 = cx + r * math.cos(ang), cy + r * math.sin(ang)
            x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
            large = 1 if a2 - ang > math.pi else 0
            col = PALETTE[i % len(PALETTE)]
            parts.append(f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f} Z" fill="{col}" stroke="#fff" stroke-width="2"/>')
            lab = labels[i] if i < len(labels) else ""
            legend.append(f'<rect x="300" y="{40 + i * 26}" width="12" height="12" rx="2" fill="{col}"/>'
                          f'<text x="320" y="{51 + i * 26}" font-size="13" fill="#16181D">{esc(lab)} — {v:g}{esc(c["unit"])} (%{v * 100 / total:.0f})</text>')
            ang = a2
        return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(c["title"])}">{"".join(parts)}{"".join(legend)}</svg>'
    allv = [v for sr in series for v in sr["values"]] or [0]
    vmax = max(allv + [0]) or 1
    vmin = min(allv + [0])
    span = (vmax - vmin) or 1
    n = max(1, len(labels))
    pw, ph = w - pad_l - 16, h - pad_b - pad_t
    y = lambda v: pad_t + ph - (v - vmin) / span * ph
    out = []
    for k in range(5):
        v = vmin + span * k / 4
        yy = y(v)
        out.append(f'<line x1="{pad_l}" x2="{w - 16}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#E5E7EB"/>'
                   f'<text x="{pad_l - 8}" y="{yy + 4:.1f}" font-size="11" text-anchor="end" fill="#5B6270">{v:,.0f}</text>')
    step = pw / n
    for i, lab in enumerate(labels):
        out.append(f'<text x="{pad_l + step * (i + 0.5):.1f}" y="{h - pad_b + 18}" font-size="11" text-anchor="middle" fill="#5B6270">{esc(lab[:14])}</text>')
    if c["type"] == "bar":
        bw = step * 0.7 / max(1, len(series))
        for si, sr in enumerate(series):
            col = PALETTE[si % len(PALETTE)]
            for i, v in enumerate(sr["values"][:n]):
                x = pad_l + step * i + step * 0.15 + bw * si
                y0, y1 = sorted((y(0), y(v)))
                out.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bw - 2:.1f}" height="{max(1, y1 - y0):.1f}" rx="2" fill="{col}"/>')
    else:
        for si, sr in enumerate(series):
            col = PALETTE[si % len(PALETTE)]
            pts = " ".join(f"{pad_l + step * (i + 0.5):.1f},{y(v):.1f}" for i, v in enumerate(sr["values"][:n]))
            out.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5"/>')
    legend = "".join(f'<rect x="{pad_l + i * 150}" y="{h - 18}" width="10" height="10" rx="2" fill="{PALETTE[i % len(PALETTE)]}"/>'
                     f'<text x="{pad_l + i * 150 + 16}" y="{h - 9}" font-size="12" fill="#16181D">{esc(sr["name"][:18])}</text>'
                     for i, sr in enumerate(series)) if len(series) > 1 else ""
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(c["title"])}">{"".join(out)}{legend}</svg>'


def report_html(data):
    esc = html_lib.escape
    nums = "".join(f'<div class="kpi"><div class="v">{esc(k["value"])}</div><div class="l">{esc(k["label"])}</div></div>'
                   for k in data["key_numbers"])
    charts = "".join(f'<section class="chart"><h2>{esc(c["title"])}</h2>{_svg_chart(c)}'
                     f'<p>{esc(c["insight"])} <span class="src">Kaynak: sayfa {c["page"]}</span></p></section>'
                     for c in data["charts"])
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>{esc(data['title'])}</title><style>
body{{font-family:'Segoe UI',sans-serif;color:#16181D;margin:0;padding:40px;background:#fff}}
h1{{font-size:26px;margin:0 0 8px}} .sum{{color:#3F4552;line-height:1.6;max-width:760px}}
.kpis{{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}} .kpi{{border:1px solid #E2E5EA;border-radius:12px;padding:14px 18px;min-width:140px}}
.kpi .v{{font-size:24px;font-weight:700;color:#4F46E5}} .kpi .l{{font-size:12px;color:#5B6270;margin-top:4px}}
.chart{{break-inside:avoid;margin:28px 0}} .chart h2{{font-size:16px;margin:0 0 8px}} svg{{width:100%;max-width:680px;height:auto}}
.chart p{{color:#3F4552;font-size:13px}} .src{{color:#5B6270}} @page{{margin:16mm}}
</style></head><body><h1>{esc(data['title'])}</h1><p class="sum">{esc(data['summary'])}</p>
<div class="kpis">{nums}</div>{charts}<p class="src" style="font-size:11px;margin-top:40px">PDF Stüdyo · Claude ile hazırlandı · {time.strftime('%d.%m.%Y')}</p></body></html>"""


def op_ai_report(s, a, job):
    doc = s.require()
    req = (a.get("request") or "").strip()
    data = call([pdf_block(doc, doc_pages_limit(doc)), {"type": "text", "text":
                 "Build a visual report from the numbers in this document. Extract the most meaningful datasets "
                 "(1-4 charts) using ONLY numbers that appear in the document; choose bar for comparisons, line for "
                 "trends over time, pie for parts of a whole. key_numbers: 2-6 headline figures with units. "
                 "insight: one sentence per chart. page: where the data comes from. Turkish text. "
                 + (f"The user asks: {req}" if req else "")}],
                schema=REPORT_SCHEMA, effort="high", job=job, label="Rapor hazırlanıyor")
    if not data["charts"] and not data["key_numbers"]:
        raise UserError("Belgede grafiğe dökülecek sayısal veri bulunamadı.")
    s.last_report = report_html(data)
    return {"html": s.last_report, "title": data["title"]}


def op_report_to_pdf(s, a, job):
    html = getattr(s, "last_report", None)
    if not html:
        raise UserError("Önce rapor oluştur.")
    data = html_to_pdf(html)
    if a.get("open"):
        s.load_bytes(data, name="Rapor.pdf")
        return {"changed": True, "opened": True}
    path = ask_save("Raporu kaydet", f"{stem(s.name)} - rapor.pdf")
    if not path:
        return {"cancelled": True}
    with open(path, "wb") as f:
        f.write(data)
    return {"saved": path, "open_file": path}


# ---------------------------------------------------------------- formlar

FIELD_SCHEMA = S({"fields": arr(S({"label": STR, "type": {"type": "string", "enum": ["text", "multiline", "date", "checkbox", "choice", "signature"]},
                                   "box": BOX, "options": arr(STR)}))})


def _slug(t):
    t = t.lower().translate(str.maketrans("çğıöşü", "cgiosu"))
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:40] or "alan"


def op_ai_detect_fields(s, a, job):
    doc = s.require()
    pages = _pages(s, a, doc)
    names = {w.field_name for p in doc for w in p.widgets()}
    added = 0
    for i, p in enumerate(pages):
        data = call([image_block(doc, p, 1800), {"type": "text", "text":
                     "This is a form page. Find every place where someone is expected to write, tick or sign: blank "
                     "lines, boxes, table cells to fill, checkboxes, date blanks, signature lines. For each give the "
                     "label it belongs to (Turkish, as printed), its type, and the bounding box of the EMPTY area to "
                     "fill (not the label) on a 0-1000 scale. options only for choice fields, else []."}],
                    schema=FIELD_SCHEMA, effort="medium", job=job,
                    progress=(0.03 + 0.9 * i / len(pages), 0.03 + 0.9 * (i + 1) / len(pages)), label=f"Sayfa {p + 1} inceleniyor")
        page = doc[p]
        existing = [w.rect for w in page.widgets()]
        for f in data["fields"]:
            r = norm_rect(page, f["box"])
            if r.width < 6 or r.height < 5 or any(r.intersects(e) and (r & e).get_area() > 0.5 * r.get_area() for e in existing):
                continue
            if f["type"] == "checkbox":
                side = min(max(r.height, 9), 14)
                r = pymupdf.Rect(r.x0, r.y0, r.x0 + side, r.y0 + side)
            elif r.height < 12:
                r.y0 = r.y1 - 14
            base = _slug(f["label"])
            name, k = base, 2
            while name in names:
                name, k = f"{base}_{k}", k + 1
            names.add(name)
            add_widget(page, r, f["type"], name, f["label"], f["options"])
            existing.append(r)
            added += 1
    s.commit()
    return {"changed": True, "message": f"{added} doldurulabilir alan eklendi. Kontrol et; yanlış olanı Formlar panelinden sil."}


def op_ai_autofill(s, a, job):
    doc = s.require()
    fields = [f for f in list_fields(doc) if f["type"] != "Signature"]
    if not fields:
        raise UserError("Bu belgede doldurulabilir alan yok. Önce 'Doldurulabilir yap'.")
    listing = json.dumps([{"id": str(f["xref"]), "label": f["label"] or f["name"], "type": f["type"], "options": f["options"]}
                          for f in fields], ensure_ascii=False)
    content = []
    if a.get("source") == "file":
        path = a.get("path") or (ask_open_many("Bilgilerin alınacağı belgeyi seç") or [None])[0]
        if not path:
            return {"cancelled": True}
        src = _as_pdf(path)
        content.append(pdf_block(src, list(range(min(src.page_count, 100)))))
        content.append({"type": "text", "text": "Use the attached document as the source of information."})
    else:
        profile = (load_settings().get("profile") or "").strip()
        if not profile:
            raise UserError("Önce Ayarlar'da 'Bilgilerim' alanını doldur (ad, adres, telefon…).")
        content.append({"type": "text", "text": f"Information about the person filling the form:\n{profile}"})
    content.append({"type": "text", "text": f"Form fields (JSON): {listing}\n\nFill every field you can from the "
                    "information. Checkbox: \"true\" or \"false\". Choice: one of the options. Dates as GG.AA.YYYY. "
                    "Leave out fields you cannot fill — never invent."})
    data = call(content, schema=S({"values": arr(S({"id": STR, "value": STR}))}), effort="medium", job=job,
                label="Form dolduruluyor")
    values = {v["id"]: v["value"] for v in data["values"] if v["value"] != ""}
    n = set_field_values(doc, values)
    s.commit()
    return {"changed": True, "message": f"{n}/{len(fields)} alan dolduruldu. Gönderiyorsan önce kontrol et."}


FORM_SCHEMA = S({"title": STR, "intro": STR, "sections": arr(S({"title": STR, "fields": arr(S({
    "label": STR, "type": {"type": "string", "enum": ["text", "multiline", "date", "checkbox", "choice", "signature"]},
    "options": arr(STR)}))}))})


def op_ai_create_form(s, a, job):
    desc = (a.get("description") or "").strip()
    if not desc:
        raise UserError("Nasıl bir form istediğini yaz.")
    data = call([{"type": "text", "text": f"Design a fillable form: {desc}\nGroup fields into sections. Labels in "
                  "the user's language. Use checkbox for yes/no items, choice (with options) for picking one of a few, "
                  "multiline for long answers, signature for signing lines (usually at the end). intro: one or two "
                  "sentences of instructions."}],
                schema=FORM_SCHEMA, effort="medium", job=job, label="Form tasarlanıyor")
    job.update(0.9, "PDF form oluşturuluyor…")
    out = build_form_pdf(data)
    s.load_bytes(out, name=f"{data['title'][:60]}.pdf")
    return {"changed": True, "opened": True, "message": "Form hazır. Alanlar doldurulabilir; kaydetmeyi unutma."}


def build_form_pdf(data):
    doc = pymupdf.open()
    a4 = pymupdf.paper_rect("a4")
    M = 54
    page = doc.new_page(width=a4.width, height=a4.height)
    font = ensure_font(page)
    y = M
    names = set()

    def newpage():
        nonlocal page, y
        page = doc.new_page(width=a4.width, height=a4.height)
        ensure_font(page)
        y = M

    def need(h):
        if y + h > a4.height - M:
            newpage()

    page.insert_textbox(pymupdf.Rect(M, y, a4.width - M, y + 40), data["title"], fontsize=18, fontname=font, color=(0.09, 0.09, 0.11))
    y += 34
    if data["intro"]:
        h = 14 * (1 + len(data["intro"]) // 95)
        page.insert_textbox(pymupdf.Rect(M, y, a4.width - M, y + h + 6), data["intro"], fontsize=10, fontname=font, color=(0.33, 0.35, 0.4))
        y += h + 12
    for sec in data["sections"]:
        need(60)
        page.draw_rect(pymupdf.Rect(M, y, a4.width - M, y + 22), color=None, fill=(0.93, 0.94, 1.0))
        page.insert_text((M + 8, y + 15), sec["title"], fontsize=11.5, fontname=font, color=(0.19, 0.18, 0.64))
        y += 32
        for f in sec["fields"]:
            kind = f["type"]
            h = 48 if kind == "multiline" else (40 if kind == "signature" else 20)
            need(h + 12)
            base = _slug(f["label"])
            name, k = base, 2
            while name in names:
                name, k = f"{base}_{k}", k + 1
            names.add(name)
            if kind == "checkbox":
                add_widget(page, pymupdf.Rect(M, y + 3, M + 13, y + 16), "checkbox", name, f["label"])
                page.insert_text((M + 20, y + 14), f["label"], fontsize=10, fontname=font)
                y += 24
                continue
            label_w = 170
            page.insert_textbox(pymupdf.Rect(M, y + 3, M + label_w - 8, y + h), f["label"], fontsize=10, fontname=font)
            r = pymupdf.Rect(M + label_w, y, a4.width - M, y + h)
            add_widget(page, r, kind, name, f["label"], f["options"])
            y += h + 10
        y += 6
    return to_bytes(doc)


# ---------------------------------------------------------------- metinden PDF

def op_ai_from_text(s, a, job):
    desc = (a.get("description") or "").strip()
    if not desc:
        raise UserError("Ne hazırlanacağını yaz.")
    data = call([{"type": "text", "text": f"Write this document: {desc}\n\nReturn a complete, print-ready HTML document "
                  "(A4, @page margin 18mm, clean professional typography with font-family 'Segoe UI' or Georgia, no "
                  "external resources, no scripts). Use real content, not lorem ipsum; where specific facts are unknown "
                  "use clear placeholders like [Ad Soyad]. Write in the user's language."}],
                schema=S({"title": STR, "html": STR}), effort="high", job=job, label="Belge yazılıyor")
    job.update(0.9, "PDF oluşturuluyor…")
    pdf = html_to_pdf(data["html"])
    s.load_bytes(pdf, name=f"{data['title'][:60] or 'Yeni belge'}.pdf")
    return {"changed": True, "opened": True, "message": "Belge hazır. Metinleri tıklayıp düzenleyebilirsin; kaydetmeyi unutma."}


# ---------------------------------------------------------------- erişilebilirlik: görsel açıklamaları

def op_ai_alt_text(s, a, job):
    doc = s.require()
    imgs = []
    for p in doc:
        for i, info in enumerate(p.get_image_info(xrefs=True)):
            r = pymupdf.Rect(info["bbox"])
            if r.width > 40 and r.height > 40:
                imgs.append((p.number, i, r))
    if not imgs:
        raise UserError("Belgede görsel yok.")
    imgs = imgs[:40]
    results = []
    for gi, group in enumerate(chunks(imgs, 8)):
        content = []
        for k, (pno, i, r) in enumerate(group):
            zoom = min(3, 800 / max(r.width, r.height))
            pix = doc[pno].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=r, alpha=False)
            content.append({"type": "text", "text": f"Image id {gi * 8 + k} (page {pno + 1}):"})
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                        "data": base64.standard_b64encode(pix.tobytes("jpeg")).decode()}})
        content.append({"type": "text", "text": "Write concise alt text (max 25 words, Turkish) for each image, for "
                        "screen-reader users. For charts state the main takeaway. For decorative images write \"dekoratif\"."})
        data = call(content, schema=S({"items": arr(S({"id": INT, "alt": STR}))}), effort="low", job=job,
                    label="Görseller açıklanıyor")
        for it in data["items"]:
            if 0 <= it["id"] < len(imgs):
                results.append({"page": imgs[it["id"]][0], "alt": it["alt"]})
    # Etiketsiz PDF'te görsele bağlanamaz: açıklamaları görselin üstüne görünmez bir not olarak ekleriz.
    for (pno, i, r), res in zip(imgs, results):
        page = doc[pno]
        annot = page.add_text_annot(pymupdf.Point(r.x0, r.y0), f"Görsel açıklaması: {res['alt']}", icon="Note")
        annot.set_flags(pymupdf.PDF_ANNOT_IS_HIDDEN | pymupdf.PDF_ANNOT_IS_NO_VIEW)
        annot.set_info(title="Erişilebilirlik")
        annot.update()
    s.commit()
    return {"changed": True, "items": results,
            "message": f"{len(results)} görsel açıklandı; açıklamalar belgeye görünmez not olarak eklendi."}


# ---------------------------------------------------------------- toplu işlem için Claude işleri

def _batch_searchable(doc, outbase, job):
    scanned = [p.number for p in doc if len(p.get_text("text").strip()) < 20 and p.get_images()]
    if scanned:
        add_text_layer(doc, ocr_pages(doc, scanned, job))
    fix_fonts(doc)
    doc.save(outbase + ".pdf", garbage=3, deflate=True)


def _batch_word(doc, outbase, job):
    blocks, refs = structure_doc(doc, list(range(doc.page_count)), job)
    build_docx(doc, blocks, refs, outbase + ".docx")


def _batch_text(doc, outbase, job):
    scanned = [p.number for p in doc if len(p.get_text("text").strip()) < 20 and p.get_images()]
    ocr = ocr_pages(doc, scanned, job) if scanned else {}
    with open(outbase + ".txt", "w", encoding="utf-8") as f:
        for p in doc:
            body = "\n".join(l["text"] for l in ocr.get(p.number, [])) if p.number in ocr else p.get_text("text")
            f.write(f"--- Sayfa {p.number + 1} ---\n{body}\n\n")


BATCH_AI = {"searchable": _batch_searchable, "to_word": _batch_word, "to_text": _batch_text}

AI_OPS = {k[3:]: v for k, v in globals().items() if k.startswith("op_") and callable(v)}
