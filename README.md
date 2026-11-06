# PDF Stüdyo

Acrobat Pro'daki araçların Windows için sade bir karşılığı. Anlama gerektiren işler (metin tanıma, Word/Excel/PowerPoint'e
çevirme, özet, belgeyle sohbet, çeviri, form alanı bulma, karartma, karşılaştırma yorumu) **Claude API** ile; sayfa
düzenleme, işaretleme, imza, parola gibi işler bilgisayarda, ücretsiz yapılır.

İndir: [Uygulamalarım](https://yusufcihan1.github.io/uygulamalarim/)

## İlk açılış

Claude kullanan bir araca ilk bastığında uygulama API anahtarını ister. Anahtar almak için:
[console.anthropic.com](https://console.anthropic.com) → **API Keys** → **Create Key**. API kullanımı Claude
aboneliğinden ayrı ücretlendirilir (Billing'den bakiye eklenir). Anahtar Windows Kimlik Bilgisi Yöneticisi'nde saklanır.
Model: Claude Sonnet 5.5. Ayarlar'da bu oturumda harcanan token ve yaklaşık ücret görünür.

Claude araçları ✦ işaretlidir; bu araçlar belgeyi (ya da seçili sayfaları) Anthropic'e gönderir. Diğer araçlar
belgeyi bilgisayardan çıkarmaz.

## Araçlar (51)

- **Düzenle:** metni yerinde düzenle, ✦ komutla düzenle, ✦ yeniden yaz, görsel ekle/değiştir/sil, metin kutusu, sayfa
  numarası, üst-alt bilgi, Bates numarası, filigran
- **Sayfalar:** sürükle-bırak sıralama, döndür, sil, ayrı kaydet, boş sayfa, dosyadan sayfa ekle, birleştir, böl
  (aralık, sayfa sayısı, boyut, yer imi), sıkıştır, kırp, sayfa boyutu
- **İşaretle:** vurgula, altını/üstünü çiz, yapışkan not, serbest çizim, şekil ve ok, damga, imzanı ekle (çiz, yaz,
  fotoğraftan), imza alanı, yorum listesi, ✦ yorumları özetle
- **Dönüştür:** ✦ Word, ✦ Excel, ✦ PowerPoint, ✦ aranabilir PDF (metin tanıma), ✦ tablo tanıma, ✦ el yazısı, ✦ çeviri
  (düzeni koruyarak ya da Word), resim, metin; Office/resim/web sayfası → PDF, fotoğraftan tarama
- **Formlar:** ✦ doldurulabilir yap, doldur, ✦ otomatik doldur, alan ekle, ✦ anlatımdan form oluştur, yanıtları Excel'de
  topla
- **Koru:** ✦ yapay zekâ ile karartma (sen onaylarsın), elle karartma, parola ve izinler, parola kaldırma, gizli veri
  temizleme, dijital imza (kendi sertifikan ya da .p12/.pfx) ve doğrulama, belge karşılaştırma (+ ✦ anlamsal özet),
  erişilebilirlik denetimi (+ ✦ görsel açıklamaları), toplu işlem
- **Asistan:** ✦ özet, ✦ sayfa atıflı sohbet, ✦ çoklu belge çalışma alanı, ✦ sunum, ✦ grafik ve rapor, ✦ bilgi çıkarma
  (toplu, Excel'e)

Kısayollar: `Ctrl K` araç ara, `Ctrl F` belgede ara, `Ctrl S` kaydet, `Ctrl Z` / `Ctrl Y` geri al / yinele.

## Bilinen sınırlar

- Metin düzenleme satırı Arial ile yeniden yazar; özel yazı tipli belgelerde yazı tipi farkı görünebilir.
- Kendi oluşturulan sertifikayla atılan dijital imza nitelikli elektronik imza (e-imza kartı) yerine geçmez.
- Etiketsiz PDF'lerde görsel açıklamaları görsele bağlanamaz; belgeye gizli not olarak eklenir.
- Office'ten PDF'e çevirme için bilgisayarda Microsoft Office kurulu olmalı.

## Kaynaktan derleme

```powershell
python -m venv .venv
.venv\Scripts\pip install pymupdf anthropic keyring python-docx openpyxl python-pptx pywin32 pillow opencv-python-headless pyhanko psutil pyinstaller
.venv\Scripts\python app\main.py          # geliştirme
powershell -ExecutionPolicy Bypass -File build.ps1   # kurulum dosyası (Inno Setup gerekir)
```

Testler: `tests\test_local.py` (yerel işler), `tests\test_ai.py` (Claude işleri sahte yanıtlarla).

## Lisans

AGPL-3.0 (PyMuPDF'in lisansı gereği). Bkz. `LICENSE`.
