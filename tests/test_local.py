"""Yerel işlemlerin duman testi: örnek PDF üretir, her işlemi çalıştırır, sonucu kontrol eder."""
import os
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "app"))

import pymupdf  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import core  # noqa: E402
import ops_local  # noqa: E402
import ops_sign  # noqa: E402
from core import SESSION, Job  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudyo_test_")
QUEUE = []   # dosya pencerelerinin vereceği cevaplar


def fake(*a, **k):
    return QUEUE.pop(0) if QUEUE else None


for mod in (core, ops_local, ops_sign):
    for name in ("ask_open", "ask_open_many", "ask_save", "ask_folder"):
        if hasattr(mod, name):
            setattr(mod, name, fake)


def sample_pdf(path, pages=4):
    doc = pymupdf.open()
    img = Image.new("RGB", (600, 400), (79, 70, 229))
    ImageDraw.Draw(img).ellipse((150, 50, 450, 350), fill=(245, 158, 11))
    img_path = os.path.join(TMP, "resim.png")
    img.save(img_path)
    for i in range(pages):
        page = doc.new_page()
        page.insert_font(fontname="ar", fontfile=core.FONT_REGULAR)
        page.insert_text((72, 80), f"KİRA SÖZLEŞMESİ — Sayfa {i + 1}", fontsize=18, fontname="ar")
        page.insert_textbox(pymupdf.Rect(72, 100, 520, 300),
                            "Madde 4 · Artış. Kira bedeli her yıl, bir önceki yılın on iki aylık tüketici fiyat "
                            "endeksi ortalaması oranında artırılır. Kiracı Ahmet Yılmaz, TC 12345678901, "
                            "IBAN TR12 0006 4000 0011 2345 6789 01, telefon 0532 111 22 33.", fontsize=11, fontname="ar")
        page.insert_image(pymupdf.Rect(72, 320, 372, 520), filename=img_path)
    doc.save(path)
    return img_path


def run(op, args=None, ok=lambda r: True, answers=()):
    QUEUE[:] = list(answers)
    fn = {**ops_local.LOCAL_OPS, **ops_sign.SIGN_OPS}[op]
    try:
        r = fn(SESSION, args or {}, Job(op))
        good = ok(r)
        print(("OK  " if good else "BAD ") + op, "" if good else r)
        return r
    except Exception as e:
        print("ERR " + op, type(e).__name__, e)
        traceback.print_exc(limit=3)
        return None


def main():
    src = os.path.join(TMP, "ornek.pdf")
    img_path = sample_pdf(src)
    other = os.path.join(TMP, "ornek2.pdf")
    sample_pdf(other, 2)

    run("open", {"path": src}, lambda r: r["opened"] and SESSION.doc.page_count == 4)
    w = run("words", {"page": 0}, lambda r: len(r["words"]) > 10)
    words = w["words"]
    rects = [x[:4] for x in words if x[4] in ("Kira", "bedeli")]
    run("markup", {"page": 0, "kind": "highlight", "rects": rects}, lambda r: r["changed"])
    run("markup", {"page": 0, "kind": "underline", "rects": rects, "color": "#2563EB"})
    run("note", {"page": 0, "x": 500, "y": 90, "text": "Bunu kontrol et"})
    run("textbox", {"page": 0, "rect": [300, 560, 520, 600], "text": "Türkçe kutu: ğüşıöç İ", "size": 12})
    run("ink", {"page": 0, "paths": [[[100, 600], [150, 640], [200, 610]]]})
    for kind in ("rect", "ellipse", "line", "arrow"):
        run("shape", {"page": 1, "kind": kind, "rect": [100, 600, 200, 680]})
    run("stamp", {"page": 1, "rect": [380, 40, 540, 80], "text": "ONAYLANDI", "date": True})
    run("annots", {}, lambda r: len(r["annots"]) >= 5)
    ann = SESSION.info()
    a0 = run("annots")["annots"][0]
    run("delete_annot", {"page": a0["page"], "xref": a0["xref"]})
    run("replace_text", {"page": 0, "rects": [x[:4] for x in words if x[4] in ("Ahmet", "Yılmaz,")], "text": "Mehmet Öztürk,"},
        lambda r: "Mehmet" in SESSION.doc[0].get_text().replace("\xa0", " "))
    run("undo", {}, lambda r: r["changed"])
    run("redo", {}, lambda r: r["changed"])
    imgs = run("page_images", {"page": 0}, lambda r: len(r["images"]) == 1)
    run("add_image", {"page": 1, "rect": [400, 600, 500, 700], "path": img_path})
    run("page_numbers", {"position": "bottom-center"}, lambda r: "1 / 4" in SESSION.doc[0].get_text().replace("\xa0", " "))
    run("header_footer", {"header": "Gizli belge {tarih}", "footer": "Sayfa {n}/{total}"})
    run("bates", {"prefix": "DAVA-", "start": 1, "digits": 5}, lambda r: "DAVA-00001" in SESSION.doc[0].get_text().replace("\xa0", " "))
    run("watermark", {"text": "TASLAK", "opacity": 0.2})
    run("rotate", {"pages": "2", "angle": 90}, lambda r: SESSION.doc[1].rotation == 90)
    run("markup", {"page": 1, "kind": "highlight", "rects": [[100, 100, 200, 120]]})
    run("insert_blank", {"after": 0}, lambda r: SESSION.doc.page_count == 5)
    run("delete_pages", {"pages": "2"}, lambda r: SESSION.doc.page_count == 4)
    run("reorder", {"order": [3, 2, 1, 0]})
    run("insert_file", {"after": 3, "paths": [other]}, lambda r: SESSION.doc.page_count == 6)
    run("merge", {"paths": [other]}, lambda r: SESSION.doc.page_count == 8)
    run("extract_pages", {"pages": "1-2"}, lambda r: os.path.exists(r["saved"]), [os.path.join(TMP, "parca.pdf")])
    os.makedirs(os.path.join(TMP, "bol"), exist_ok=True)
    run("split", {"mode": "every", "value": 3}, lambda r: len(os.listdir(os.path.join(TMP, "bol"))) == 3, [os.path.join(TMP, "bol")])
    run("compress", {"level": "high"})
    run("crop", {"top": 10, "bottom": 10, "left": 5, "right": 5, "pages": "1"})
    run("resize", {"size": "A4"})
    run("fields", {}, lambda r: r["fields"] == [])
    run("add_field", {"page": 0, "rect": [72, 700, 300, 720], "kind": "text", "name": "ad_soyad", "label": "Ad Soyad"})
    run("add_field", {"page": 0, "rect": [320, 700, 334, 714], "kind": "checkbox", "name": "onay"})
    run("add_field", {"page": 0, "rect": [72, 730, 300, 750], "kind": "choice", "name": "sehir", "options": ["Bursa", "İstanbul"]})
    f = run("fields", {}, lambda r: len(r["fields"]) == 3)["fields"]
    run("set_fields", {"values": {str(f[0]["xref"]): "Ayşe Kaya", str(f[1]["xref"]): True, str(f[2]["xref"]): "İstanbul"}},
        lambda r: "3 alan" in r["message"])
    filled = os.path.join(TMP, "dolu.pdf")
    run("save", {"as": True}, lambda r: os.path.exists(filled), [filled])
    run("collect_responses", {"paths": [filled, filled]}, lambda r: os.path.exists(r["saved"]), [os.path.join(TMP, "yanit.xlsx")])
    sig = run("save_signature", {"png": "data:image/png;base64," + _png_b64()}, lambda r: os.path.exists(r["path"]))
    run("place_signature", {"page": 0, "rect": [350, 650, 500, 700], "path": sig["path"]})
    run("signature_field", {"page": 0, "rect": [72, 760, 250, 800]})
    run("access_check", {}, lambda r: len(r["items"]) >= 5)
    run("access_fix", {"title": "Kira", "lang": "tr-TR", "toc": True})
    run("compare", {"path": other}, lambda r: len(r["changes"]) > 0)
    run("sanitize", {}, lambda r: r["changed"])
    run("redact", {"items": [{"text": "12345678901"}]}, lambda r: "12345678901" not in "".join(p.get_text() for p in SESSION.doc))
    run("protect", {"user_pw": "1234", "allow": ["print"]}, lambda r: pymupdf.open(r["saved"]).needs_pass,
        [os.path.join(TMP, "korumali.pdf")])
    run("open", {"path": os.path.join(TMP, "korumali.pdf"), "password": "1234"}, lambda r: r["opened"])
    run("unlock", {}, lambda r: not pymupdf.open(r["saved"]).needs_pass, [os.path.join(TMP, "acik.pdf")])
    os.makedirs(os.path.join(TMP, "resimler"), exist_ok=True)
    run("to_images", {"format": "jpg", "dpi": 72}, lambda r: len(os.listdir(r["saved"])) == SESSION.doc.page_count,
        [os.path.join(TMP, "resimler")])
    run("from_files", {"paths": [img_path, img_path]}, lambda r: SESSION.doc.page_count == 2)
    run("fix_photos", {"paths": [img_path]}, lambda r: SESSION.doc.page_count == 1)
    docx = os.path.join(TMP, "deneme.docx")
    _make_docx(docx)
    run("from_files", {"paths": [docx]}, lambda r: "Merhaba" in SESSION.doc[0].get_text().replace("\xa0", " "))
    run("from_web", {"url": "https://example.com"}, lambda r: SESSION.doc.page_count >= 1)
    # dijital imza
    run("open", {"path": filled})
    run("cert_create", {"name": "Test Kişi", "password": "abcd"}, lambda r: os.path.exists(r["cert"]["path"]))
    run("digital_sign", {"password": "abcd", "page": 0, "reason": "Onay"}, lambda r: os.path.exists(r["saved"]),
        [os.path.join(TMP, "imzali.pdf")])
    run("verify_signatures", {}, lambda r: r["signatures"] and r["signatures"][0]["intact"])
    os.makedirs(os.path.join(TMP, "toplu"), exist_ok=True)
    for name in ("a.pdf", "b.pdf"):
        sample_pdf(os.path.join(TMP, "toplu", name), 2)
    run("batch", {"folder": os.path.join(TMP, "toplu"), "action": "compress"}, lambda r: "2/2" in r["message"])
    run("batch", {"folder": os.path.join(TMP, "toplu"), "action": "watermark", "text": "GİZLİ"}, lambda r: "2/2" in r["message"])
    print("info:", {k: v for k, v in SESSION.info().items() if k not in ("pages", "metadata")})
    print("TMP", TMP)


def _png_b64():
    import base64
    import io
    img = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    ImageDraw.Draw(img).line((10, 80, 100, 20, 200, 70, 290, 30), fill=(20, 30, 80, 255), width=4)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _make_docx(path):
    from docx import Document
    d = Document()
    d.add_heading("Merhaba dünya", 1)
    d.add_paragraph("Bu bir Word belgesidir: ğüşıöç.")
    d.save(path)


if __name__ == "__main__":
    main()
