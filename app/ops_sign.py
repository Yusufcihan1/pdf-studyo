"""Dijital (sertifikalı) imza: kendi sertifikanı oluştur, PDF'i imzala, imzaları doğrula."""
import datetime
import io
import logging
import os

from core import DATA_DIR, SESSION, UserError, ask_open, ask_save, load_settings, save_settings, stem

CERT_PATH = os.path.join(DATA_DIR, "sertifika.p12")
# Kendi imzalı sertifikada "güvenilir kök yok" uyarısı normaldir; sonucu arayüzde gösteriyoruz.
for _name in ("pyhanko", "pyhanko_certvalidator"):
    logging.getLogger(_name).setLevel(logging.CRITICAL)


def op_cert_status(s, a, job):
    st = load_settings()
    path = st.get("cert_path") or (CERT_PATH if os.path.exists(CERT_PATH) else "")
    info = None
    if path and os.path.exists(path):
        info = {"path": path, "name": st.get("cert_name", os.path.basename(path))}
    return {"cert": info}


def op_cert_create(s, a, job):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

    name = (a.get("name") or "").strip()
    password = a.get("password") or ""
    if not name or len(password) < 4:
        raise UserError("Ad soyad ve en az 4 karakterli bir parola gerekli.")
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    attrs = [x509.NameAttribute(NameOID.COMMON_NAME, name)]
    if a.get("email"):
        attrs.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, a["email"].strip()))
    if a.get("org"):
        attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, a["org"].strip()))
    subject = x509.Name(attrs)
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(minutes=5))
            .not_valid_after(now + datetime.timedelta(days=365 * 5))
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=True, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False, key_cert_sign=False,
                                         crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), critical=False)
            .sign(key, hashes.SHA256()))
    data = pkcs12.serialize_key_and_certificates(name.encode(), key, cert, None,
                                                 serialization.BestAvailableEncryption(password.encode()))
    with open(CERT_PATH, "wb") as f:
        f.write(data)
    st = load_settings()
    st["cert_path"] = CERT_PATH
    st["cert_name"] = name
    save_settings(st)
    return {"cert": {"path": CERT_PATH, "name": name},
            "message": "Kişisel sertifikan oluşturuldu. Bu imza belgenin sonradan değiştirilmediğini kanıtlar; resmî e-imza yerine geçmez."}


def op_cert_import(s, a, job):
    path = ask_open("Sertifika dosyasını seç (.p12 / .pfx)", [("Sertifika", "*.p12 *.pfx")])
    if not path:
        return {"cancelled": True}
    st = load_settings()
    st["cert_path"] = path
    st["cert_name"] = os.path.basename(path)
    save_settings(st)
    return {"cert": {"path": path, "name": os.path.basename(path)}}


def op_digital_sign(s, a, job):
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import fields, signers

    doc = s.require()
    if s.index != s.saved_index or not s.path:
        raise UserError("İmzalamadan önce belgeyi kaydet (imzadan sonra yapılan her değişiklik imzayı bozar).")
    st = load_settings()
    cert = st.get("cert_path")
    if not cert or not os.path.exists(cert):
        raise UserError("Önce bir sertifika oluştur ya da içe aktar.")
    try:
        signer = signers.SimpleSigner.load_pkcs12(pfx_file=cert, passphrase=(a.get("password") or "").encode())
    except Exception:
        signer = None
    if signer is None:
        raise UserError("Sertifika parolası yanlış.")
    page = doc[int(a.get("page", 0))]
    x0, y0, x1, y1 = a.get("rect") or [page.rect.width - 230, page.rect.height - 110, page.rect.width - 40, page.rect.height - 40]
    h = page.rect.height
    target = ask_save("İmzalı belgeyi kaydet", f"{stem(s.name)} (imzalı).pdf")
    if not target:
        return {"cancelled": True}
    with open(s.path, "rb") as f:
        data = f.read()
    w = IncrementalPdfFileWriter(io.BytesIO(data), strict=False)
    field_name = f"Imza{len(list(_embedded(data))) + 1}"
    fields.append_signature_field(w, sig_field_spec=fields.SigFieldSpec(
        field_name, on_page=page.number, box=(x0, h - y1, x1, h - y0)))
    meta = signers.PdfSignatureMetadata(field_name=field_name, reason=a.get("reason") or None,
                                        location=a.get("location") or None)
    out = signers.sign_pdf(w, meta, signer=signer)
    with open(target, "wb") as f:
        f.write(out.getvalue())
    s.open_path(target)
    return {"changed": True, "opened": True, "saved": target,
            "message": "Belge dijital olarak imzalandı. Bundan sonra yapılan değişiklikler imzayı geçersiz kılar."}


def _embedded(data):
    from pyhanko.pdf_utils.reader import PdfFileReader
    try:
        return PdfFileReader(io.BytesIO(data), strict=False).embedded_signatures
    except Exception:
        return []


def op_verify_signatures(s, a, job):
    from pyhanko.sign.validation import validate_pdf_signature
    s.require()
    data = s.history[s.index] if s.index != s.saved_index or not s.path else open(s.path, "rb").read()
    sigs = _embedded(data)
    out = []
    for sig in sigs:
        try:
            status = validate_pdf_signature(sig)
            signer = sig.signer_cert.subject.human_friendly
            when = status.signer_reported_dt.strftime("%d.%m.%Y %H:%M") if status.signer_reported_dt else ""
            intact = bool(status.intact and status.valid)
            covers = sig.coverage.name if hasattr(sig, "coverage") else ""
            out.append({"field": sig.field_name, "signer": signer, "when": when, "intact": intact,
                        "trusted": bool(status.trusted), "covers_all": "ENTIRE" in covers})
        except Exception as e:
            out.append({"field": getattr(sig, "field_name", "?"), "signer": "", "when": "", "intact": False,
                        "trusted": False, "error": str(e)[:200]})
    return {"signatures": out}


SIGN_OPS = {k[3:]: v for k, v in globals().items() if k.startswith("op_") and callable(v)}
