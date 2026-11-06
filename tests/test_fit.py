"""'Her CV tek sayfaya sığsın': Claude'un sayfa işlemleri (sahte cevapla) ve sığdırma sonucu."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "app"))

import pymupdf  # noqa: E402

import ops_ai  # noqa: E402
from core import SESSION, Job  # noqa: E402
from ops_local import FONT_REGULAR  # noqa: E402

OUT = os.path.join(os.environ.get("TEMP", "."), "fit_test")
os.makedirs(OUT, exist_ok=True)


def make_cvs(path):
    doc = pymupdf.open()
    people = [("Ayşe Yılmaz", 70), ("Mehmet Demir", 30), ("Zeynep Kaya", 85)]
    for name, lines in people:
        page = doc.new_page()
        page.insert_font(fontname="AR", fontfile=FONT_REGULAR)
        page.draw_rect(pymupdf.Rect(0, 0, 595, 70), color=None, fill=(0.06, 0.12, 0.10))
        page.insert_text((40, 45), name, fontname="AR", fontsize=24, color=(1, 1, 1))
        y = 100
        for i in range(lines):
            if y > 800:
                page = doc.new_page()
                page.insert_font(fontname="AR", fontfile=FONT_REGULAR)
                y = 50
            page.insert_text((40, y), f"{name} · deneyim satırı {i + 1}: proje, görev ve sonuç açıklaması",
                             fontname="AR", fontsize=11)
            y += 16
    doc.save(path)
    return doc.page_count


def fake_call(content=None, system="", schema=None, effort="medium", max_tokens=48000, job=None, messages=None,
              progress=(0.1, 0.9), label=""):
    text = content[0]["text"]
    assert "fit_one_page" in text and "Her CV tek sayfaya" in text
    return {"changes": [], "page_actions": [
        {"action": "fit_one_page", "pages": [1, 2], "angle": 0, "reason": "Ayşe Yılmaz'ın CV'si"},
        {"action": "fit_one_page", "pages": [4, 5], "angle": 0, "reason": "Zeynep Kaya'nın CV'si"}], "note": ""}


ops_ai.call = fake_call
src = os.path.join(OUT, "cvler.pdf")
n = make_cvs(src)
print("önce:", n, "sayfa")
SESSION.open_path(src)
r = ops_ai.op_ai_command(SESSION, {"instruction": "Her CV tek sayfaya sığsın"}, Job("t"))
print("öneriler:", [c["label"] for c in r["changes"]])
r2 = ops_ai.op_apply_changes(SESSION, {"changes": r["changes"]}, Job("t"))
print(r2["message"], "→", SESSION.doc.page_count, "sayfa")
assert SESSION.doc.page_count == 3
for i, page in enumerate(SESSION.doc):
    txt = page.get_text()
    print(f"  s.{i + 1}: {txt.splitlines()[0]} … {len(txt.splitlines())} satır")
    page.get_pixmap(dpi=60).save(os.path.join(OUT, f"sonuc_{i + 1}.png"))
assert "deneyim satırı 70" in SESSION.doc[0].get_text().replace("\xa0", " ")
assert "deneyim satırı 85" in SESSION.doc[2].get_text().replace("\xa0", " ")
SESSION.undo()
print("geri al:", SESSION.doc.page_count, "sayfa")
print("TAMAM", OUT)
