import base64
import hashlib
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from meetiq.config.settings import settings
from meetiq.core.logging import logger

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def build_flow() -> Flow:
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )


def _make_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE (code_verifier, code_challenge) pair using S256.

    We generate these ourselves so we control exactly where the verifier lives
    (session), avoiding the library storing it internally across two separate
    Flow instances (one in /login, one in /callback).
    """
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


@router.get("/login")
async def login(request: Request):
    flow = build_flow()

    # Generate our own PKCE pair so we own the verifier lifecycle
    code_verifier, code_challenge = _make_pkce_pair()

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    request.session["oauth_state"] = state
    request.session["code_verifier"] = code_verifier

    logger.info("oauth_login_initiated")
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(request: Request, code: str, state: str):
    if state != request.session.get("oauth_state"):
        logger.warning("oauth_state_mismatch")
        return RedirectResponse(url=f"{settings.frontend_url}?error=state_mismatch")

    code_verifier = request.session.get("code_verifier")

    flow = build_flow()
    flow.oauth2session.state = state

    flow.fetch_token(
        code=code,
        code_verifier=code_verifier,
    )
    credentials = flow.credentials

    request.session["token"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
    }

    logger.info("oauth_login_success")
    return RedirectResponse(url=settings.frontend_url)


@router.get("/status")
async def status(request: Request):
    token_data = request.session.get("token")
    if not token_data:
        return {"authenticated": False}
    return {"authenticated": True}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    logger.info("user_logged_out")
    return {"message": "Logged out successfully"}
