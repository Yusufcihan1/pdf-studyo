"""Claude işlerinin sahte yanıtlarla testi: istek hazırlama ve yanıtı belgeye/dosyaya işleme yolu doğrulanır."""
import json
import os
import sys
import tempfile
import traceback
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "app"))
sys.path.insert(0, HERE)

import pymupdf  # noqa: E402

import core  # noqa: E402
import ops_ai  # noqa: E402
import ops_local  # noqa: E402
from core import SESSION, Job  # noqa: E402
from test_local import sample_pdf, QUEUE, fake  # noqa: E402

for mod in (ops_ai,):
    for name in ("ask_open_many", "ask_save"):
        setattr(mod, name, fake)

TMP = tempfile.mkdtemp(prefix="pdfstudyo_ai_")
SENT = []


def fake_call(content=None, system="", schema=None, effort="medium", max_tokens=48000, job=None, messages=None,
              progress=(0, 1), label=""):
    SENT.append({"label": label, "schema": bool(schema), "content": content or messages})
    # istek içeriği JSON'a çevrilebilir olmalı (API'ye gidecek gövde)
    json.dumps(content or messages, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o))
    props = set((schema or {}).get("properties", {}))
    if props == {"pages"}:
        pages = [int(b["text"].split()[-1].rstrip(":")) for b in content if b.get("type") == "text" and b["text"].startswith("Image for page")]
        return {"pages": [{"page": p, "lines": [{"text": "Tanınan satır ğüş", "box": [100, 100, 600, 130]},
                                                {"text": "İkinci satır 2026", "box": [100, 150, 500, 175]}]} for p in pages]}
    if props == {"blocks"}:
        return {"blocks": [
            {"type": "heading", "level": 1, "text": "Kira Sözleşmesi", "items": [], "rows": [], "align": "left"},
            {"type": "paragraph", "level": 0, "text": "Bu **önemli** bir paragraf.", "items": [], "rows": [], "align": "justify"},
            {"type": "bullet_list", "level": 0, "text": "", "items": ["bir", "iki"], "rows": [], "align": "left"},
            {"type": "table", "level": 0, "text": "", "items": [], "rows": [["Ad", "Tutar"], ["Kira", "1.250,50"]], "align": "left"},
            {"type": "image", "level": 0, "text": "p1_1", "items": [], "rows": [], "align": "left"}]}
    if props == {"tables"}:
        return {"tables": [{"title": "Ödemeler", "page": 1, "header": ["Ay", "Tutar"], "rows": [["Ocak", "1.250,50"], ["Şubat", "₺2.000"]]}]}
    if "slides" in props:
        return {"title": "Sunum", "subtitle": "Alt başlık", "slides": [
            {"layout": l, "title": f"{l} slaytı", "bullets": ["%42 — artış", "madde iki"], "right": ["sağ"], "notes": "not", "image": "p1_1"}
            for l in ("section", "bullets", "two_column", "quote", "numbers")]}
    if props == {"text"}:
        return {"text": "Yeniden yazılmış metin."}
    if props == {"items"} and "Translate each item" in json.dumps(content, ensure_ascii=False):
        items = json.loads(content[0]["text"].split("\n", 1)[1])
        return {"items": [{"id": i["id"], "text": "EN " + i["text"][:40]} for i in items]}
    if props == {"items"} and "alt text" in json.dumps(content):
        return {"items": [{"id": 0, "alt": "Turuncu daire"}]}
    if props == {"items"}:
        return {"items": [{"text": "12345678901", "page": 1, "type": "TC kimlik"}, {"text": "yok-boyle", "page": 1, "type": "x"}]}
    if props == {"changes", "note"}:
        return {"changes": [{"page": 1, "find": "on iki aylık", "replace": "yirmi dört aylık", "reason": "süre"}], "note": ""}
    if "values" in props and "doc_type" in props:
        return {"doc_type": "Sözleşme", "values": [{"name": "Kiracı", "value": "Ahmet Yılmaz"}, {"name": "Tutar", "value": "1.250,50"}]}
    if props == {"values"} and "Form fields" in json.dumps(content, ensure_ascii=False):
        ids = [f["id"] for f in json.loads(content[-1]["text"].split("(JSON): ", 1)[1].split("\n\n")[0])]
        return {"values": [{"id": ids[0], "value": "Ayşe Kaya"}]}
    if props == {"fields"}:
        return {"fields": [{"label": "Ad Soyad", "type": "text", "box": [150, 200, 600, 230], "options": []},
                           {"label": "Onay", "type": "checkbox", "box": [100, 300, 120, 320], "options": []}]}
    if "sections" in props:
        return {"title": "İzin Formu", "intro": "Lütfen doldurun.", "sections": [
            {"title": "Kişi", "fields": [{"label": "Ad Soyad", "type": "text", "options": []},
                                         {"label": "Birim", "type": "choice", "options": ["A", "B"]},
                                         {"label": "Açıklama", "type": "multiline", "options": []},
                                         {"label": "Onaylıyorum", "type": "checkbox", "options": []},
                                         {"label": "İmza", "type": "signature", "options": []}]}]}
    if props == {"title", "html"}:
        return {"title": "Dilekçe", "html": "<html><body><h1>Dilekçe</h1><p>Sayın [Ad Soyad], ğüşıöç</p></body></html>"}
    if "charts" in props:
        return {"title": "Rapor", "summary": "Özet", "key_numbers": [{"label": "Toplam", "value": "₺3.250"}],
                "charts": [{"title": "Aylık", "type": t, "labels": ["Oca", "Şub", "Mar"], "series": [{"name": "Tutar", "values": [1, 3, 2]}],
                            "unit": "₺", "page": 1, "insight": "Artış var."} for t in ("bar", "line", "pie")]}
    if schema is None:
        cites = [NS(type="page_location", document_index=0, start_page_number=2, cited_text="Kira bedeli her yıl")]
        return NS(content=[NS(type="text", text="Cevap: TÜFE ortalaması.", citations=cites,
                              model_dump=lambda exclude_none=True: {"type": "text", "text": "Cevap"})])
    raise AssertionError(f"beklenmeyen şema: {props}")


ops_ai.call = fake_call


def run(op, args=None, ok=lambda r: True, answers=()):
    QUEUE[:] = list(answers)
    fn = {**ops_ai.AI_OPS, **ops_local.LOCAL_OPS}[op]
    try:
        r = fn(SESSION, args or {}, Job(op))
        good = ok(r)
        print(("OK  " if good else "BAD ") + op, "" if good else str(r)[:300])
        return r
    except Exception as e:
        print("ERR " + op, type(e).__name__, e)
        traceback.print_exc(limit=4)


def main():
    src = os.path.join(TMP, "ornek.pdf")
    sample_pdf(src, 3)
    # taranmış örnek: sayfaları resme çevir
    scan = pymupdf.open()
    for p in pymupdf.open(src):
        pix = p.get_pixmap(dpi=80)
        np_ = scan.new_page(width=p.rect.width, height=p.rect.height)
        np_.insert_image(np_.rect, stream=pix.tobytes("png"))
    scan_path = os.path.join(TMP, "taranmis.pdf")
    scan.save(scan_path)

    run("open", {"path": scan_path}, lambda r: SESSION.scanned_pages() == [0, 1, 2])
    run("ai_searchable", {}, lambda r: "Tanınan satır ğüş" in SESSION.doc[0].get_text().replace("\xa0", " ") and not SESSION.scanned_pages())
    run("open", {"path": scan_path})
    run("ai_transcribe", {"pages": "1"}, lambda r: "Tanınan" in r["text"])
    run("ai_to_text", {}, lambda r: r["text"].count("Tanınan") == 3)
    run("open", {"path": src})
    run("ai_to_word", {}, lambda r: os.path.getsize(r["saved"]) > 5000, [os.path.join(TMP, "a.docx")])
    run("ai_to_excel", {}, lambda r: os.path.exists(r["saved"]), [os.path.join(TMP, "a.xlsx")])
    from openpyxl import load_workbook
    ws = load_workbook(os.path.join(TMP, "a.xlsx")).active
    print("   excel sayılar:", [c.value for c in ws["B"]])
    run("ai_to_pptx", {"mode": "story"}, lambda r: os.path.exists(r["saved"]), [os.path.join(TMP, "a.pptx")])
    run("ai_summary", {}, lambda r: "TÜFE" in r["text"])
    run("ai_chat", {"question": "Artış nasıl?"}, lambda r: r["segments"][0]["cites"][0]["page"] == 1)
    run("ai_chat", {"question": "Peki depozito?"}, lambda r: len(SESSION.chat) == 4)
    run("ai_rewrite", {"text": "deneme", "style": "resmi"}, lambda r: r["text"])
    r = run("ai_command", {"instruction": "süreyi yirmi dört ay yap"}, lambda r: r["changes"][0]["found"] >= 1)
    run("apply_changes", {"changes": r["changes"]}, lambda r: "yirmi dört aylık" in SESSION.doc[0].get_text().replace("\xa0", " "))
    found = run("ai_find_sensitive", {}, lambda r: r["items"][0]["found"] == 1 and r["items"][1]["found"] == 0)
    run("redact", {"items": [{"page": i["page"], "rect": rc} for i in found["items"] for rc in i["rects"]]},
        lambda r: "12345678901" not in SESSION.doc[0].get_text().replace("\xa0", " "))
    run("ai_translate", {"lang": "English"}, lambda r: "EN " in SESSION.doc[0].get_text().replace("\xa0", " "))
    run("open", {"path": src})
    run("ai_translate", {"lang": "English", "output": "docx"}, lambda r: os.path.exists(r["saved"]), [os.path.join(TMP, "en.docx")])
    run("compare", {"path": scan_path})
    run("ai_compare_summary", {}, lambda r: r["text"])
    run("markup", {"page": 0, "kind": "highlight", "rects": [[72, 100, 300, 115]], "comment": "kontrol"})
    run("ai_comments_summary", {}, lambda r: r["text"])
    run("ai_extract", {}, lambda r: r["fields"][0]["name"] == "Belge türü")
    run("ai_extract", {"batch": True}, lambda r: os.path.exists(r["saved"]), [[src, scan_path], os.path.join(TMP, "bilgi.xlsx")])
    run("ai_report", {}, lambda r: "<svg" in r["html"])
    with open(os.path.join(TMP, "rapor.html"), "w", encoding="utf-8") as f:
        f.write(SESSION.last_report)
    run("report_to_pdf", {"open": True}, lambda r: SESSION.doc.page_count >= 1)
    run("open", {"path": src})
    run("ai_detect_fields", {"pages": "1"}, lambda r: len(ops_local.list_fields(SESSION.doc)) == 2)
    st = core.load_settings()
    st["profile"] = "Ad: Ayşe Kaya"
    core.save_settings(st)
    run("ai_autofill", {}, lambda r: any(f["value"] == "Ayşe Kaya" for f in ops_local.list_fields(SESSION.doc)))
    run("ai_create_form", {"description": "izin formu"}, lambda r: len(ops_local.list_fields(SESSION.doc)) == 5)
    form_path = os.path.join(TMP, "form.pdf")
    SESSION.save(form_path)
    run("ai_from_text", {"description": "dilekçe"}, lambda r: "Dilekçe" in SESSION.doc[0].get_text().replace("\xa0", " "))
    run("open", {"path": src})
    run("ai_alt_text", {}, lambda r: r["items"])
    os.makedirs(os.path.join(TMP, "toplu"), exist_ok=True)
    sample_pdf(os.path.join(TMP, "toplu", "x.pdf"), 1)
    run("batch", {"folder": os.path.join(TMP, "toplu"), "action": "to_word"}, lambda r: "1/1" in r["message"])
    print("calls:", len(SESSION.history), "TMP", TMP)


if __name__ == "__main__":
    main()
