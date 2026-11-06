"""Arayüz denemesi için gerçekçi örnek PDF'ler üretir (Edge ile HTML'den)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "app"))
from ops_local import html_to_pdf  # noqa: E402

CSS = """<style>@page{margin:20mm} body{font-family:Georgia,serif;font-size:11.5pt;line-height:1.55;color:#222}
h1{text-align:center;font-size:18pt;letter-spacing:.06em} h2{font-size:12.5pt;margin-top:18px}
table{border-collapse:collapse;width:100%;margin:10px 0} td,th{border:1px solid #999;padding:5px 8px;font-size:10.5pt}
th{background:#eee} .sig{display:flex;justify-content:space-between;margin-top:60px}</style>"""

madde = "".join(f"<h2>Madde {i} · {t}</h2><p>{b}</p>" for i, (t, b) in enumerate([
    ("Taraflar", "Bu sözleşme, Bursa ili Nilüfer ilçesinde bulunan konutun kiraya verilmesine ilişkin olarak kiraya veren Ayşe Demir ile kiracı Ahmet Yılmaz (TC 12345678901) arasında 1 Ocak 2025 tarihinde imzalanmıştır."),
    ("Kira bedeli", "Aylık kira bedeli 18.500 TL olup her ayın beşinci gününe kadar kiraya verenin TR12 0006 4000 0011 2345 6789 01 numaralı hesabına ödenir."),
    ("Artış", "Kira bedeli her yıl, bir önceki yılın on iki aylık tüketici fiyat endeksi ortalaması oranında artırılır. Artış, kira yılının başladığı ayda uygulanır."),
    ("Depozito", "Kiracı, sözleşme tarihinde iki aylık kira bedeli tutarında depozito öder; depozito tahliye sırasında hasar tespitinden sonra iade edilir."),
    ("Kullanım", "Kiralanan yalnız konut olarak kullanılır; kiraya verenin yazılı izni olmadan başkasına devredilemez. Kiracının telefonu 0532 111 22 33'tür."),
    ("Süre", "Sözleşme 1 Ocak 2025'te başlar ve 31 Aralık 2025'te sona erer. Taraflardan biri süre bitiminden on beş gün önce bildirimde bulunmazsa sözleşme bir yıl uzar."),
], 1))
tablo = """<h2>Ek 1 · Ödeme planı</h2><table><tr><th>Ay</th><th>Tutar</th><th>Son ödeme</th></tr>""" + "".join(
    f"<tr><td>{m}</td><td>18.500,00 TL</td><td>5 {m} 2025</td></tr>" for m in ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran"]) + "</table>"
html = f"<html><head><meta charset='utf-8'>{CSS}</head><body><h1>KİRA SÖZLEŞMESİ</h1>{madde}{tablo}<div style='page-break-before:always'></div>" \
       f"<h2>Ek 2 · Demirbaş listesi</h2><table><tr><th>Eşya</th><th>Adet</th><th>Durum</th></tr>" + "".join(
    f"<tr><td>{e}</td><td>{n}</td><td>{d}</td></tr>" for e, n, d in [("Buzdolabı", 1, "Çalışır"), ("Klima", 2, "Bakımlı"), ("Gardırop", 3, "İyi"), ("Perde", 6, "Yeni")]) + \
       "</table><div class='sig'><div>Kiraya veren<br><br>__________________</div><div>Kiracı<br><br>__________________</div></div></body></html>"
out = os.path.join(HERE, "ornek_sozlesme.pdf")
with open(out, "wb") as f:
    f.write(html_to_pdf(html))
print(out)
