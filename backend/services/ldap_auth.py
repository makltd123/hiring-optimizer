from config import settings

try:
    from ldap3 import Server, Connection, ALL, NTLM
    _LDAP_AVAILABLE = True
except ImportError:
    _LDAP_AVAILABLE = False


def authenticate_ldap(username: str, password: str) -> dict | None:
    """
    Аутентификация через корпоративный AD.
    Возвращает данные пользователя или None при ошибке.
    Работает только если LDAP_ENABLED=true и ldap3 установлен.
    """
    if not settings.ldap_enabled or not _LDAP_AVAILABLE:
        return None

    try:
        server = Server(settings.ldap_server, get_info=ALL)
        conn = Connection(
            server,
            user=f"{settings.ldap_base_dn}\\{username}",
            password=password,
            authentication=NTLM,
        )
        if not conn.bind():
            return None

        try:
            from ldap3.utils.conv import escape_filter_chars
            safe_username = escape_filter_chars(username)
        except ImportError:
            safe_username = username
        conn.search(
            settings.ldap_base_dn,
            f"(sAMAccountName={safe_username})",
            attributes=["displayName", "mail", "department", "title", "distinguishedName"],
        )
        if not conn.entries:
            return None

        entry = conn.entries[0]
        return {
            "display_name": str(entry.displayName) if entry.displayName else username,
            "email": str(entry.mail) if entry.mail else f"{username}@{settings.ldap_base_dn}",
            "department": str(entry.department) if entry.department else "",
            "title": str(entry.title) if entry.title else "",
            "ldap_dn": str(entry.distinguishedName) if entry.distinguishedName else "",
        }
    except Exception:
        return None


def get_or_create_user_from_ldap(ldap_data: dict, db) -> object:
    """Найти или создать пользователя по данным из AD."""
    from models.models import User

    user = db.query(User).filter(User.email == ldap_data["email"]).first()
    if not user:
        user = User(
            email=ldap_data["email"],
            password_hash="",  # LDAP-пользователи не используют локальный пароль
            plan="start",
            role="hr_manager",
            ldap_dn=ldap_data.get("ldap_dn"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif ldap_data.get("ldap_dn"):
        user.ldap_dn = ldap_data["ldap_dn"]
        db.commit()
    return user
