# PDF Stüdyo — özellik listesi (çalışma adı)

Acrobat Pro'nun özelliklerinin Claude API ile işlenen hâli. 6 Kasım 2026'da kullanıcıyla tek tek seçildi.

## Kararlar

- **Tür:** Windows masaüstü uygulaması (kurulum exe'si). Solda sayfa küçük resimleri, ortada görüntüleyici, sağda araçlar ve asistan.
- **Model:** Claude Sonnet 5.5 (`claude-sonnet-5-5`), her işte.
- **API anahtarı:** Kullanıcının kendi anahtarı; ilk açılışta uygulamaya girilir, Windows Kimlik Bilgisi Yöneticisi'nde saklanır. Uygulamanın içinde anahtar yok.
- **Dağıtım:** Uygulamalarım sitesinde (herkese açık) kurulum dosyası olarak yayınlanacak.
- **İlke:** Claude yalnız anlama gerektiren işlerde kullanılır. Birleştirme, sıkıştırma, parola gibi işler yerelde ve ücretsiz yapılır. Belge API'ye gitmeden önce kullanıcı bunu görür.

Yerel = Claude'suz, bilgisayarda. Claude = API'ye gider.

## Dönüştürme

| Özellik | Nasıl |
|---|---|
| PDF → Word | Claude yapıyı çıkarır (başlık, paragraf, liste, tablo); .docx yerelde yazılır |
| PDF → Excel | Claude tabloları çıkarır; .xlsx yerelde yazılır |
| PDF → PowerPoint | Claude bölümleri slaytlara böler; .pptx yerelde yazılır |
| PDF → Resim / Metin | Resim yerelde; metin taranmışsa Claude |
| Word/Excel/PPT → PDF | Yerelde (Word ya da LibreOffice) |
| Resimler → PDF | Yerelde; isteğe bağlı metin tanıma Claude |
| Web sayfası → PDF | Yerelde (Edge, ekran olmadan) |
| Metinden PDF oluştur | Claude metni ve biçimi yazar, PDF yerelde üretilir |

## Metin tanıma (OCR)

| Özellik | Nasıl |
|---|---|
| Aranabilir PDF (görünmez metin katmanı) | Claude metni ve konumunu okur; katman yerelde eklenir |
| Tablo tanıma | Claude |
| El yazısı tanıma | Claude |
| Fotoğraf düzeltme (kenar bulma, düzleştirme, kontrast) | Yerelde, sonra Claude ile metin tanıma |

## Sayfa araçları (hepsi yerelde)

Birleştir ve böl · sayfaları düzenle (sırala, döndür, sil, çıkar, ekle) · sıkıştır · kırp ve boyutlandır

## İçerik düzenleme

| Özellik | Nasıl |
|---|---|
| Metin düzenleme (tıkla, değiştir) | Yerelde |
| Komutla düzenleme ("2025'leri 2026 yap") | Claude değişiklikleri önerir, kullanıcı onaylar, yerelde uygulanır |
| Yeniden yaz (ton, uzunluk) | Claude |
| Görsel ekle / değiştir | Yerelde |

## Yapay zekâ asistanı

Özet · belgeyle sohbet (sayfa atıflı cevap) · çeviri (düzeni koruyarak) · çoklu belge alanı (birden çok PDF'e birlikte soru) — hepsi Claude

## Üretim

Sunuma çevir · grafik ve rapor · bilgi çıkarma (fatura/sözleşme alanlarını Excel'e, toplu) — hepsi Claude

## İşaretleme

Vurgula ve not · çizim ve şekil · damga (yerelde) · yorumları özetle (Claude)

## Formlar

| Özellik | Nasıl |
|---|---|
| Form alanı algılama (düz/taranmış PDF → doldurulabilir) | Claude alanları bulur, yerelde eklenir |
| Formu doldur (elle ya da başka belgeden/kayıtlı bilgiden otomatik) | Yerelde / Claude |
| Sıfırdan form oluştur (anlatımdan) | Claude |
| Form verisini Excel'de topla | Yerelde |

## İmza

İmzanı ekle (çizim, yazı, fotoğraftan) · dijital (sertifikalı) imza ve doğrulama · imza alanı ekle — hepsi yerelde.
*İmza iste ve takip et* seçilmedi (sunucu gerektirir).

## Güvenlik

Parola ve izinler · gizli veri temizleme · filigran (yerelde) · yapay zekâ ile karartma (Claude bulur, kullanıcı onaylar, yerelde kalıcı silinir)

## Pro araçları

Belge karşılaştır (yerelde fark + Claude ile anlamsal özet) · sayfa no, üst-alt bilgi, Bates · toplu işlem (klasöre aynı işlem) · erişilebilirlik (etiketleme, okuma sırası, Claude ile alt metin, denetim)

## Seçilmeyenler

Sesli özet (podcast) · imza iste ve takip et
