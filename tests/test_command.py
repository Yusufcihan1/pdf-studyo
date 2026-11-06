"""Komutla düzenle: biçimi koruyan satır değişikliği, paragraf yeniden yazma, satır ekleme ve yeni sayfa işlemleri
(Claude'un cevabı sahte)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "app"))

import pymupdf  # noqa: E402

import ops_ai  # noqa: E402
from core import FONT_DIR, SESSION, Job  # noqa: E402

OUT = os.path.join(os.environ.get("TEMP", "."), "command_test")
os.makedirs(OUT, exist_ok=True)
CAL, CALB = os.path.join(FONT_DIR, "calibri.ttf"), os.path.join(FONT_DIR, "calibrib.ttf")
PARA = ["Yazılım geliştirme alanında beş yıllık deneyime sahibim ve ekip",
        "çalışmasına yatkınım. Yeni teknolojileri öğrenmeyi seviyorum ve",
        "işimi zamanında teslim ederim."]


def make(path):
    doc = pymupdf.open()
    for name in ("Zeynep Kaya", "Ali Demir", "Can Öz"):
        page = doc.new_page()
        page.insert_font(fontname="CA", fontfile=CAL)
        page.insert_font(fontname="CB", fontfile=CALB)
        w = pymupdf.get_text_length(name, fontsize=22)
        page.insert_text(((595 - w) / 2, 60), name, fontname="CB", fontsize=22)
        page.insert_text((50, 100), "Telefon:", fontname="CB", fontsize=11)
        page.insert_text((100, 100), "0555 111 22 33", fontname="CA", fontsize=11)
        page.insert_text((50, 116), "E-posta:", fontname="CB", fontsize=11)
        page.insert_text((100, 116), "ad@ornek.com", fontname="CA", fontsize=11)
        page.insert_text((50, 150), "Özet", fontname="CB", fontsize=13)
        for i, line in enumerate(PARA):
            page.insert_text((50, 170 + i * 14), line, fontname="CA", fontsize=11)
        page.insert_text((50, 300), "Deneyim", fontname="CB", fontsize=13)
        page.insert_text((50, 320), "Kıdemli Geliştirici", fontname="CA", fontsize=11)
        page.insert_text((400, 320), "2021 - 2025", fontname="CA", fontsize=11)
    doc.save(path)


def spans(page, contains):
    out = []
    from textedit import page_lines, line_chars
    for ln in page_lines(page):
        if contains in line_chars(ln)[0]:
            out.append([(sp["text"], sp["font"], round(sp["size"], 1), round(sp["origin"][0])) for sp in ln["spans"]])
    return out


ANSWER = {"changes": [
    {"page": 1, "find": "0555 111 22 33", "replace": "0532 999 88 77", "all_pages": False, "reason": "telefon"},
    {"page": 1, "find": " ".join(PARA), "replace": "Beş yıllık deneyimli bir yazılım geliştiriciyim; ekip çalışmasına "
     "yatkın, öğrenmeye açık ve teslim tarihlerine sadık biriyim. Ölçeklenebilir web uygulamaları geliştirdim.",
     "all_pages": False, "reason": "özet resmîleşti"},
    {"page": 1, "find": "E-posta: ad@ornek.com", "replace": "E-posta: ad@ornek.com\nLinkedIn: linkedin.com/in/zeynep",
     "all_pages": False, "reason": "satır eklendi"},
    {"page": 1, "find": "2025", "replace": "2026", "all_pages": True, "reason": "yıl"},
    {"page": 1, "find": "Zeynep Kaya", "replace": "Zeynep Kaya Yıldırım", "all_pages": False, "reason": "soyadı"}],
    "page_actions": [
        {"action": "reorder", "pages": [2, 3, 1], "angle": 0, "text": "", "position": "", "reason": "isme göre"},
        {"action": "page_numbers", "pages": [], "angle": 0, "text": "Sayfa {n} / {total}", "position": "bottom-right",
         "reason": "numara"},
        {"action": "watermark", "pages": [], "angle": 0, "text": "TASLAK", "position": "", "reason": "filigran"},
        {"action": "highlight", "pages": [], "angle": 0, "text": "Kıdemli Geliştirici", "position": "", "reason": "vurgu"},
        {"action": "redact", "pages": [2], "angle": 0, "text": "0555 111 22 33", "position": "", "reason": "karart"},
        {"action": "insert_blank", "pages": [0], "angle": 0, "text": "", "position": "", "reason": "kapak"},
    ], "note": ""}


def fake_call(content=None, **kw):
    assert "reorder" in content[-1]["text"]
    return ANSWER


ops_ai.call = fake_call
src = os.path.join(OUT, "cv.pdf")
make(src)
SESSION.open_path(src)
r = ops_ai.op_ai_command(SESSION, {"instruction": "test"}, Job("t"))
for c in r["changes"]:
    print(" ", c.get("label") or f"{c['find'][:30]} → {c['replace'][:30]}", "· bulundu:", c["found"])
assert all(c["found"] for c in r["changes"]), "bulunamayan öneri var"
before_p1 = SESSION.doc[0]
r2 = ops_ai.op_apply_changes(SESSION, {"changes": r["changes"]}, Job("t"))
print(r2["message"])
doc = SESSION.doc
print("sayfa sayısı:", doc.page_count)
assert doc.page_count == 4 and set(doc[0].get_text().split()) <= {"Sayfa", "1", "/", "4", "TASLAK"}  # başta boş sayfa
names = [doc[i].get_text().split("\n")[0] for i in range(1, 4)]
print("sıra:", names)
assert names[0].startswith("Ali") and names[1].startswith("Can") and "Zeynep Kaya Yıldırım" in doc[3].get_text().replace("\xa0", " ")
zp = doc[3]
tel = spans(zp, "0532")[0]
print("telefon satırı:", tel)
assert "Bold" in tel[0][1] or "calibrib" in tel[0][1].lower(), "Telefon: etiketi kalın kalmalı"
assert any(abs(s_[3] - 100) <= 1 for s_ in tel if "0532" in s_[0]), "numara eski sütununda kalmalı"
name = spans(zp, "Yıldırım")[0]
print("isim:", name)
x0 = name[0][3]
w = zp.get_text("dict")
assert "calibrib" in name[0][1].lower() or "bold" in name[0][1].lower()
print("özet:", [l[0][0][:50] for l in spans(zp, "") if l and 160 < 0] or "")
from textedit import _norm  # noqa: E402
txt = _norm(zp.get_text())
assert "Ölçeklenebilir web" in txt and "beş yıllık deneyime" not in txt
assert "LinkedIn: linkedin.com/in/zeynep" in txt and "ad@ornek.com" in txt
assert "2021 - 2026" in txt and "2021 - 2026" in _norm(doc[1].get_text())
assert "0555 111 22 33" not in _norm(doc[1].get_text())                 # özgün 2. sayfa (Ali) karartıldı
assert "Sayfa 4 / 4" in zp.get_text()
assert any(a.type[1] == "Highlight" for a in zp.annots())
for i, page in enumerate(doc):
    page.get_pixmap(dpi=70).save(os.path.join(OUT, f"sonuc_{i + 1}.png"))
SESSION.undo()
assert SESSION.doc.page_count == 3 and "0555 111 22 33" in _norm(SESSION.doc[0].get_text())
print("geri al: tek adımda döndü")
print("TAMAM", OUT)
