import hmac
import secrets
from io import BytesIO
import base64

try:
    import pyotp
    import qrcode
    _MFA_AVAILABLE = True
except ImportError:
    _MFA_AVAILABLE = False


class MFAService:
    def generate_secret(self, user_email: str) -> dict:
        if not _MFA_AVAILABLE:
            raise RuntimeError("pyotp и qrcode не установлены. pip install pyotp qrcode[pil]")
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=user_email, issuer_name="HiringOptimizer")
        qr = qrcode.make(provisioning_uri)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_b64 = base64.b64encode(buffer.getvalue()).decode()
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_b64}",
            "manual_entry": secret,
        }

    def verify_code(self, secret: str, code: str, last_used_at: int | None = None) -> bool:
        """Проверить TOTP-код. last_used_at — timestamp последнего успешного кода (защита от replay)."""
        if not _MFA_AVAILABLE:
            return False
        totp = pyotp.TOTP(secret)
        import time
        now_counter = int(time.time()) // 30
        if not totp.verify(code, valid_window=1):
            return False
        # Replay protection: отклоняем если counter уже использовался
        if last_used_at is not None and now_counter <= last_used_at:
            return False
        return True

    def current_totp_counter(self) -> int:
        import time
        return int(time.time()) // 30

    def generate_backup_codes(self) -> list[str]:
        # 128 бит энтропии на код (16 байт hex = 32 символа)
        return [secrets.token_hex(16).upper() for _ in range(10)]

    def verify_backup_code(self, code: str, backup_codes: list[str]) -> tuple[bool, list[str]]:
        normalized = code.upper().strip()
        found = False
        for stored in backup_codes:
            if hmac.compare_digest(normalized, stored):
                found = True
                break
        if found:
            remaining = [c for c in backup_codes if not hmac.compare_digest(c, normalized)]
            return True, remaining
        return False, backup_codes


mfa_service = MFAService()
