from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

from app.core.config import settings


class GoogleTokenError(ValueError):
    """Raised when a Google ID token cannot establish a verified identity."""


class GoogleAuthService:
    def verify_google_token(self, token: str) -> dict:
        if not settings.GOOGLE_CLIENT_ID:
            raise RuntimeError("GOOGLE_CLIENT_ID is not configured")

        try:
            claims = id_token.verify_oauth2_token(
                token,
                GoogleRequest(),
                audience=settings.GOOGLE_CLIENT_ID,
            )
        except (GoogleAuthError, ValueError) as error:
            raise GoogleTokenError("Invalid Google ID token") from error

        if claims.get("iss") not in {
            "accounts.google.com",
            "https://accounts.google.com",
        }:
            raise GoogleTokenError("Invalid Google token issuer")

        if claims.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise GoogleTokenError("Invalid Google token audience")

        if not claims.get("sub") or not claims.get("email"):
            raise GoogleTokenError(
                "Google token is missing required identity claims"
            )

        if claims.get("email_verified") is not True:
            raise GoogleTokenError(
                "Google email address is not verified"
            )

        return claims

    @staticmethod
    def extract_profile(claims: dict) -> dict:
        return {
            "google_id": claims["sub"],
            "email": claims["email"].strip().lower(),
            "full_name": claims.get("name")
            or claims["email"].split("@", 1)[0],
            "profile_picture": claims.get("picture"),
            "is_verified": claims.get("email_verified") is True,
        }