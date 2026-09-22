try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    _SAML_AVAILABLE = True
except ImportError:
    _SAML_AVAILABLE = False


class SAMLService:
    def __init__(self, org_settings: dict):
        self.org_id = org_settings["org_id"]
        self.settings = {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": f"https://app.hiringoptimizer.ru/saml/{org_settings['org_id']}",
                "assertionConsumerService": {
                    "url": "https://app.hiringoptimizer.ru/auth/saml/callback",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            },
            "idp": {
                "entityId": org_settings["saml_entity_id"],
                "singleSignOnService": {
                    "url": org_settings["saml_sso_url"],
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": org_settings["saml_certificate"],
            },
        }

    def get_login_url(self) -> str:
        if not _SAML_AVAILABLE:
            raise RuntimeError("python3-saml не установлен")
        auth = OneLogin_Saml2_Auth({}, self.settings)
        return auth.login()

    def process_callback(self, request_data: dict) -> dict:
        if not _SAML_AVAILABLE:
            raise RuntimeError("python3-saml не установлен")
        auth = OneLogin_Saml2_Auth(request_data, self.settings)
        auth.process_response()
        if not auth.is_authenticated():
            raise ValueError("SAML аутентификация не прошла")
        attributes = auth.get_attributes()
        email = attributes.get("email", [None])[0]
        if not email:
            raise ValueError("SAML: атрибут email отсутствует в assertion")
        return {
            "email": email,
            "display_name": attributes.get("displayName", [None])[0],
            "department": attributes.get("department", [None])[0],
            "groups": attributes.get("memberOf", []),
        }
