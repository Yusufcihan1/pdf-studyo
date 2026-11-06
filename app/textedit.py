"""Belgedeki metni biçimini koruyarak değiştirme: yazı tipi ailesi, kalın/italik, boyut, renk ve satır içi boşluklar.
Tek satırlık değişiklik satırı yerinde yeniden yazar; çok satırlı ya da sığmayan değişiklik paragrafı yeniden dizer."""
import difflib
import os
import re

import pymupdf

from core import FONT_DIR, FONT_REGULAR

# PDF'teki yazı tipi adı → Windows'taki (normal, kalın, italik, kalın italik) dosyaları
FAMILIES = [
    (("timesnewroman", "times", "liberationserif", "tinos"), ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf")),
    (("calibri", "carlito"), ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf")),
    (("cambria", "caladea"), ("cambria.ttc", "cambriab.ttf", "cambriai.ttf", "cambriaz.ttf")),
    (("segoeui",), ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf")),
    (("verdana", "dejavusans"), ("verdana.ttf", "verdanab.ttf", "verdanai.ttf", "verdanaz.ttf")),
    (("tahoma",), ("tahoma.ttf", "tahomabd.ttf", "tahoma.ttf", "tahomabd.ttf")),
    (("georgia",), ("georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf")),
    (("trebuchet",), ("trebuc.ttf", "trebucbd.ttf", "trebucit.ttf", "trebucbi.ttf")),
    (("garamond",), ("GARA.TTF", "GARABD.TTF", "GARAIT.TTF", "GARABD.TTF")),
    (("bookman",), ("BOOKOS.TTF", "BOOKOSB.TTF", "BOOKOSI.TTF", "BOOKOSBI.TTF")),
    (("couriernew", "courier", "liberationmono", "cousine"), ("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf")),
    (("arialnarrow",), ("ARIALN.TTF", "ARIALNB.TTF", "ARIALNI.TTF", "ARIALNBI.TTF")),
]
ARIAL = ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf")
_FONTS = {}


def _norm(t):
    # Bazı PDF'ler tireyi U+2010/2011, boşluğu sabit boşluk olarak verir; Claude düz karakterle yazar.
    return re.sub(r"[‐‑­]", "-", re.sub(r"[\xa0  ]", " ", t or ""))


def font_file(span):
    """Bir metin parçasına en yakın sistem yazı tipi dosyası."""
    name = re.sub(r"[^a-z]", "", span["font"].split("+")[-1].lower())
    flags = span.get("flags", 0)
    bold = bool(flags & 16) or any(k in name for k in ("bold", "black", "heavy", "semibold", "demi"))
    italic = bool(flags & 2) or "italic" in name or "oblique" in name
    files = ARIAL
    for keys, fam in FAMILIES:
        if any(k in name for k in keys):
            files = fam
            break
    path = os.path.join(FONT_DIR, files[bold + 2 * italic])
    if not os.path.exists(path):
        path = os.path.join(FONT_DIR, ARIAL[bold + 2 * italic])
    return path if os.path.exists(path) else FONT_REGULAR


def _font(path):
    if path not in _FONTS:
        try:
            _FONTS[path] = pymupdf.Font(fontfile=path)
        except Exception:
            _FONTS[path] = pymupdf.Font(fontfile=FONT_REGULAR)
    return _FONTS[path]


def _use_font(page, path):
    """Yazı tipini sayfaya gömer ve sayfadaki adını döndürür."""
    name = "PS" + re.sub(r"[^A-Za-z0-9]", "", os.path.basename(path).rsplit(".", 1)[0])[:12]
    try:
        page.insert_font(fontname=name, fontfile=path)
    except Exception:
        name = "PSarial"
        page.insert_font(fontname=name, fontfile=FONT_REGULAR)
    return name


def _style(span):
    c = span["color"]
    return (font_file(span), span["size"], ((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255))


def line_chars(line):
    """Satırın metni ve her karakterin biçimi; ayrıca her parçanın başladığı karakter ve x konumu."""
    text, styles, anchors = "", [], []
    prev = None
    for sp in line["spans"]:
        t = _norm(sp["text"])
        if not t:
            continue
        st = _style(sp)
        # Ayrı parçalar arasındaki görünür boşluk metinde boşluk karakteri olarak görünsün ("Telefon:" + "0555…").
        if prev and text and not text[-1].isspace() and not t[0].isspace() \
                and sp["origin"][0] - prev["bbox"][2] > sp["size"] * 0.15:
            text += " "
            styles.append(styles[-1])
        anchors.append((len(text), sp["origin"][0]))
        text += t
        styles += [st] * len(t)
        prev = sp
    return text, styles, anchors


def map_styles(old, styles, new):
    """Eski metnin karakter biçimlerini yeni metne taşır: korunan karakterler kendi biçimini, yeni yazılanlar
    yerine geçtikleri ilk karakterin (yoksa bir öncekinin) biçimini alır. Ayrıca yeni metindeki her karakterin
    eski metindeki karşılığını (yoksa None) döndürür."""
    out, src = [], []
    default = styles[0] if styles else (FONT_REGULAR, 11, (0, 0, 0))
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if op == "equal":
            out += styles[i1:i2]
            src += list(range(i1, i2))
        elif j2 > j1:
            st = styles[i1] if i1 < len(styles) else (styles[i1 - 1] if i1 else default)
            out += [st] * (j2 - j1)
            src += [None] * (j2 - j1)
    return out, src


def _runs(text, styles, scale=1.0):
    runs = []
    for ch, st in zip(text, styles):
        if runs and runs[-1][1] == st:
            runs[-1][0] += ch
        else:
            runs.append([ch, st])
    return [(t, st, _font(st[0]).text_length(t, st[1] * scale)) for t, st in runs]


def _right_limit(page, bbox):
    """Satırın sağa ne kadar uzayabileceği: aynı hizadaki bir sonraki yazıya ya da sayfa kenarına kadar."""
    limit = page.rect.width - 30
    for w in page.get_text("words"):
        wr = pymupdf.Rect(w[:4])
        if wr.x0 > bbox.x1 + 1 and wr.y1 > bbox.y0 + 1 and wr.y0 < bbox.y1 - 1:
            limit = min(limit, wr.x0 - 3)
    return max(limit, bbox.x1)


def _centered(page, bbox):
    w = page.rect.width
    mid = (bbox.x0 + bbox.x1) / 2
    return abs(mid - w / 2) < w * 0.03 and bbox.x0 > w * 0.15


def _erase(page, rects):
    for r in rects:
        r = pymupdf.Rect(r)
        page.add_redact_annot((r * page.derotation_matrix if page.rotation else r).normalize(), fill=False)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)


def _draw(page, x, baseline, text, styles, scale, anchors=None, src=None):
    """Satırı biçimli parçalar hâlinde yazar. anchors/src verilirse eski parçaların başladığı x konumları korunur
    (sekmeyle ayrılmış sütunlar kaymasın diye)."""
    anchor_x = dict(anchors or [])
    names = {}
    seg, seg_st = "", None
    for i, (ch, st) in enumerate(zip(text, styles)):
        j = src[i] if src else None
        if seg and (st != seg_st or j in anchor_x):
            x = _put(page, names, x, baseline, seg, seg_st, scale)
            seg = ""
        if j in anchor_x and anchor_x[j] > x + 0.5:
            x = anchor_x[j]
        seg += ch
        seg_st = st
    if seg:
        x = _put(page, names, x, baseline, seg, seg_st, scale)
    return x


def _put(page, names, x, baseline, text, st, scale):
    path, size, color = st
    if path not in names:
        names[path] = _use_font(page, path)
    origin = pymupdf.Point(x, baseline)
    if page.rotation:
        origin = origin * page.derotation_matrix
    page.insert_text(origin, text, fontsize=size * scale, fontname=names[path], color=color, rotate=page.rotation)
    return x + _font(path).text_length(text, size * scale)


def _width(text, styles, scale, x0, anchors=None, src=None):
    """_draw'ın yazacağı satırın bittiği x."""
    anchor_x = dict(anchors or [])
    x = x0
    for i, (ch, st) in enumerate(zip(text, styles)):
        j = src[i] if src else None
        if j in anchor_x and anchor_x[j] > x + 0.5:
            x = anchor_x[j]
        x += _font(st[0]).text_length(ch, st[1] * scale)
    return x


def rewrite_line(page, line, new_text):
    """Bir satırı biçimini koruyarak yeniden yazar; sağa sığmazsa gerektiği kadar küçültür.
    Kullanılan küçültme oranını döndürür."""
    old, styles, anchors = line_chars(line)
    new_styles, src = map_styles(old, styles, new_text)
    bbox = pymupdf.Rect(line["bbox"])
    first = next((sp for sp in line["spans"] if sp["text"].strip()), line["spans"][0])
    x0, baseline = first["origin"]
    centered = _centered(page, bbox)
    limit = page.rect.width - 30 if centered else _right_limit(page, bbox)
    scale = 1.0
    for _ in range(4):
        end = _width(new_text, new_styles, scale, x0, anchors, src)
        if centered:
            room = (limit - 30)
            if end - x0 <= room:
                break
            scale *= room / (end - x0)
        else:
            if end <= limit:
                break
            scale *= (limit - x0) / (end - x0)
    if centered:
        width = _width(new_text, new_styles, scale, 0)
        x0 = (page.rect.width - width) / 2
        anchors = None
    _erase(page, [bbox])
    _draw(page, x0, baseline, new_text, new_styles, scale, anchors, src)
    return scale


# ---------------------------------------------------------------- bulma

def page_lines(page):
    """Sayfanın görünen satırları. PDF'te aynı satır çoğu zaman ayrı parçalar hâlinde durur ("Telefon:" kalın,
    numara normal): aynı taban çizgisindeki yakın parçalar tek satırda birleştirilir. Uzak sütunlar ayrı kalır."""
    rows = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            spans = [sp for sp in ln["spans"] if sp["text"]]
            if not "".join(sp["text"] for sp in spans).strip():
                continue
            box = pymupdf.Rect(ln["bbox"])
            base = spans[0]["origin"][1]
            size = max(sp["size"] for sp in spans)
            for row in rows:
                if abs(row["base"] - base) < 1.5 and (box.x0 - row["box"].x1 < 2.5 * size and row["box"].x0 - box.x1 < 2.5 * size):
                    row["spans"] = sorted(row["spans"] + spans, key=lambda sp: sp["origin"][0])
                    row["box"] |= box
                    break
            else:
                rows.append({"base": base, "box": box, "spans": spans})
    return [{"bbox": tuple(r["box"]), "spans": r["spans"]} for r in rows]


def _squash(t):
    return re.sub(r"\s+", " ", _norm(t)).strip()


def find_matches(page, find, lines=None):
    """Aranan ifadenin sayfadaki yerleri; satır sonlarını aşabilir. Her eşleşme [(satır, baş, son), …]."""
    lines = lines if lines is not None else page_lines(page)
    target = _squash(find)
    if not target:
        return []
    chars, where = [], []
    for li, ln in enumerate(lines):
        text = line_chars(ln)[0]
        for ci, ch in enumerate(text):
            if ch.isspace():
                if chars and chars[-1] != " ":
                    chars.append(" ")
                    where.append((li, ci))
            else:
                chars.append(ch)
                where.append((li, ci))
        if chars and chars[-1] != " ":
            chars.append(" ")
            where.append((li, len(text)))
    joined = "".join(chars)
    out, start = [], 0
    while True:
        i = joined.find(target, start)
        if i < 0:
            break
        segs = {}
        for k in range(i, i + len(target)):
            li, ci = where[k]
            a, b = segs.get(li, (ci, ci + 1))
            segs[li] = (min(a, ci), max(b, ci + 1))
        out.append(sorted((li, a, b) for li, (a, b) in segs.items()))
        start = i + len(target)
    return out


# ---------------------------------------------------------------- değiştirme

def _below_limit(page, lines, block):
    """Yeniden dizilen paragrafın aşağıya ne kadar uzayabileceği: altındaki ilk içerik ya da sayfa kenarı."""
    limit = page.rect.height - 28
    own = {id(ln) for ln in block}
    box = pymupdf.Rect(block[0]["bbox"])
    for ln in block[1:]:
        box |= pymupdf.Rect(ln["bbox"])
    for ln in lines:
        r = pymupdf.Rect(ln["bbox"])
        if id(ln) not in own and r.y0 >= box.y1 - 1 and r.x1 > box.x0 and r.x0 < box.x1:
            limit = min(limit, r.y0 - 1)
    for img in page.get_image_info():
        r = pymupdf.Rect(img["bbox"])
        if r.y0 >= box.y1 - 1 and r.x1 > box.x0 and r.x0 < box.x1 and r.get_area() < page.rect.get_area() * 0.6:
            limit = min(limit, r.y0 - 1)
    return max(limit, box.y1)


def _wrap(text, styles, width, scale):
    """Biçimli metni verilen genişliğe sözcük sözcük dizer; '\n' yeni satır demektir."""
    out = []
    for para_text, para_styles in _split(text, styles, "\n"):
        words = list(_split(para_text, para_styles, " "))
        cur_t, cur_s = "", []
        for wt, ws in words:
            cand_t = (cur_t + " " + wt) if cur_t else wt
            cand_s = (cur_s + [ws[0] if ws else cur_s[-1]] + ws) if cur_t else ws
            if cur_t and _width(cand_t, cand_s, scale, 0) > width:
                out.append((cur_t, cur_s))
                cur_t, cur_s = wt, ws
            else:
                cur_t, cur_s = cand_t, cand_s
        out.append((cur_t, cur_s))
    return out


def _split(text, styles, sep):
    start = 0
    for i, ch in enumerate(text):
        if ch == sep:
            yield text[start:i], styles[start:i]
            start = i + 1
    yield text[start:], styles[start:]


def reflow(page, lines, block, new_text, styles):
    """Satırları siler, yeni metni aynı alana biçimiyle yeniden dizer; sığmazsa küçültür.
    Yazdıysa küçültme oranını, yer yoksa None döndürür."""
    box = pymupdf.Rect(block[0]["bbox"])
    for ln in block[1:]:
        box |= pymupdf.Rect(ln["bbox"])
    bottom = _below_limit(page, lines, block)
    first = next((sp for sp in block[0]["spans"] if sp["text"].strip()), block[0]["spans"][0])
    x0, base0 = first["origin"]
    size0 = first["size"]
    if len(block) > 1:
        lead = (block[-1]["spans"][0]["origin"][1] - base0) / (len(block) - 1)
    else:
        lead = size0 * 1.25
    lead = max(lead, size0 * 1.05)
    centered = len(block) == 1 and _centered(page, box)
    right = max(box.x1, page.rect.width - 30 if centered else _right_limit(page, box))
    left = min(x0, box.x0)
    width = right - left
    scale = 1.0
    while scale >= 0.6:
        rows = _wrap(new_text, styles, width, scale)
        end = base0 + lead * scale * (len(rows) - 1) + size0 * scale * 0.3
        if end <= bottom + 1:
            break
        scale -= 0.04
    else:
        return None
    _erase(page, [ln["bbox"] for ln in block])
    y = base0
    for i, (t, st) in enumerate(rows):
        if t:
            x = left if i else x0
            if centered:
                x = (page.rect.width - _width(t, st, scale, 0)) / 2
            _draw(page, x, y, t, st, scale)
        y += lead * scale
    return scale


def replace_text(page, find, replace):
    """Sayfada `find`ın geçtiği her yeri `replace` ile değiştirir. (değişen yer sayısı, uyarılar) döndürür."""
    lines = page_lines(page)
    matches = find_matches(page, find, lines)
    if not matches:
        return 0, []
    single, multi = {}, []
    for m in matches:
        if len(m) == 1 and "\n" not in replace:
            li, a, b = m[0]
            single.setdefault(li, []).append((a, b))
        else:
            multi.append(m)
    done, warns = 0, []
    used = set()
    for li, spans in single.items():
        ln = lines[li]
        old, styles, _ = line_chars(ln)
        new = old
        for a, b in sorted(spans, reverse=True):
            new = new[:a] + replace + new[b:]
        new_styles, _ = map_styles(old, styles, new)
        box = pymupdf.Rect(ln["bbox"])
        # Çok uzayıp sağa sığmayan satır, küçültülmek yerine alta doğru paragraf olarak dizilir.
        if not _centered(page, box) and len(new) > len(old) * 1.15                 and _width(new, new_styles, 1.0, ln["spans"][0]["origin"][0]) > _right_limit(page, box) + 0.5:
            multi.append(("whole", li, new))
            continue
        scale = rewrite_line(page, ln, new)
        used.add(li)
        done += len(spans)
        if scale < 0.85:
            warns.append(f"«{replace[:30]}» sığması için yazı %{round(scale * 100)} boyuta küçüldü")
    for m in multi:
        if isinstance(m, tuple):
            _, li, new = m
            idx = [li]
            old, old_styles, _ = line_chars(lines[li])
        else:
            idx = list(range(m[0][0], m[-1][0] + 1))
            if used & set(idx):
                continue
            old, old_styles = "", []
            for k in idx:
                t, st, _ = line_chars(lines[k])
                if old:
                    old += " "
                    old_styles.append(old_styles[-1])
                old += t
                old_styles += st
            first_old = line_chars(lines[idx[0]])[0]
            last_old = line_chars(lines[idx[-1]])[0]
            new = first_old[:m[0][1]] + replace + last_old[m[-1][2]:]
            # aradaki satırlar tümüyle eşleşmenin içinde; baştaki ve sondaki taşan kısımlar korunur
        new_styles, _ = map_styles(old, old_styles, new)
        block = [lines[k] for k in idx]
        scale = reflow(page, lines, block, new, new_styles)
        if scale is None:
            warns.append(f"«{replace[:30]}» için yer yok, değiştirilmedi")
            continue
        used.update(idx)
        done += 1
        if scale < 0.85:
            warns.append(f"«{replace[:30]}» sığması için yazı %{round(scale * 100)} boyuta küçüldü")
    return done, warns
