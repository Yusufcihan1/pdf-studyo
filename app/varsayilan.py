"""Varsayılan PDF uygulaması: Windows 10/11 varsayılanı programla atamaya izin vermez (UserChoice karması korumalı).
Burada uygulama kullanıcı kayıt defterine (HKCU) "PDF açabilen uygulama" olarak kaydedilir ve Windows Ayarları'nın
kendi sayfası açılır; seçimi kullanıcı yapar."""
import os
import sys

APP_LABEL = "PDF Stüdyo"
PROG_ID = "PDFStudyo.pdf"
CAPS = r"Software\PDFStudyo\Capabilities"


def _exe():
    return sys.executable if getattr(sys, "frozen", False) else None


def current_progid():
    """Şu an .pdf dosyalarını açan uygulamanın ProgId'si (yoksa boş)."""
    import winreg
    base = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf"
    for sub in ("UserChoiceLatest", "UserChoice"):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + "\\" + sub) as k:
                return winreg.QueryValueEx(k, "ProgId")[0] or ""
        except OSError:
            continue
    return ""


def status():
    pid = current_progid()
    return {"is_default": pid == PROG_ID, "current": pid, "installed": bool(_exe())}


def register():
    """Kaydı (kurulumun yaptığının aynısı) bu exe'nin yoluyla yeniler; kurulum yeri değiştiyse de doğru çalışır."""
    import winreg
    exe = _exe()
    if not exe:
        return False
    cmd = f'"{exe}" "%1"'
    entries = [
        (rf"Software\Classes\{PROG_ID}", "", "PDF belgesi"),
        (rf"Software\Classes\{PROG_ID}\DefaultIcon", "", f"{exe},0"),
        (rf"Software\Classes\{PROG_ID}\shell\open\command", "", cmd),
        (r"Software\Classes\.pdf\OpenWithProgids", PROG_ID, ""),
        (CAPS, "ApplicationName", APP_LABEL),
        (CAPS, "ApplicationDescription", "PDF görüntüleme, düzenleme ve Claude ile belge işleri"),
        (CAPS + r"\FileAssociations", ".pdf", PROG_ID),
        (r"Software\RegisteredApplications", APP_LABEL, CAPS),
    ]
    for key, name, value in entries:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED
    except Exception:
        pass
    return True


def make_default():
    if status()["is_default"]:
        return {"message": "PDF Stüdyo zaten varsayılan PDF uygulaması.", **status()}
    registered = register()
    from urllib.parse import quote
    try:
        os.startfile("ms-settings:defaultapps?registeredAppUser=" + quote(APP_LABEL))
    except OSError:
        os.startfile("ms-settings:defaultapps")
    msg = ("Windows Ayarları açıldı. “.pdf” satırına tıkla, PDF Stüdyo’yu seç ve “Varsayılan olarak ayarla”ya bas."
           if registered else "Geliştirme sürümü: kayıt yapılmadı, yalnızca Windows Ayarları açıldı.")
    return {"message": msg, **status()}
