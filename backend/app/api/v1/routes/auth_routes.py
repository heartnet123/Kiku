from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

import httpx
try:
    from supabase_auth.errors import AuthApiError, AuthRetryableError
except ImportError:
    AuthApiError = Exception
    AuthRetryableError = Exception

from app.core.config import settings
from app.core.auth import (
    _build_user_workspaces,
    _login_response,
    _user_from_auth_user,
    get_access_token,
    get_current_user,
)

from app.domain.identity import User
from app.schemas.workspace import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.supabase_client import create_supabase_client

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_values(session) -> tuple[str | None, str | None]:
    if not session:
        return None, None
    return getattr(session, "access_token", None), getattr(session, "refresh_token", None)


def _sync_public_user(user: User, token: str | None = None) -> None:
    """Sync user record into public.users table."""
    client = create_supabase_client(service_role=True) or (create_supabase_client(token) if token else None)
    if not client:
        return
    try:
        client.table("users").upsert(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
            }
        ).execute()
    except Exception:
        pass


def _set_auth_cookies(response: Response, token: str | None, refresh_token: str | None, max_age: int = 3600) -> None:
    """Attach HttpOnly session cookies. secure follows settings.cookie_secure (HTTPS origins)."""
    kwargs: dict = dict(httponly=True, samesite="lax", secure=settings.cookie_secure)
    if token:
        response.set_cookie("kiku_access_token", token, max_age=max_age, **kwargs)
    if refresh_token:
        response.set_cookie("kiku_refresh_token", refresh_token, max_age=max_age * 4, **kwargs)


def _clear_auth_cookies(response: Response) -> None:
    kwargs: dict = dict(httponly=True, samesite="lax", secure=settings.cookie_secure)
    response.delete_cookie("kiku_access_token", **kwargs)
    response.delete_cookie("kiku_refresh_token", **kwargs)


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, response: Response) -> LoginResponse:
    client = create_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is not configured.",
        )

    try:
        response_auth = client.auth.sign_up(
            {
                "email": str(request.email),
                "password": request.password,
                "options": {"data": {"full_name": request.full_name.strip()}},
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. The email may already be registered or invalid.",
        ) from exc

    auth_user = getattr(response_auth, "user", None)
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration did not create a user.",
        )

    session = getattr(response_auth, "session", None)
    token, refresh_token = _session_values(session)
    user = _user_from_auth_user(auth_user, request.full_name.strip())
    _sync_public_user(user, token)
    workspaces = _build_user_workspaces(user.id, create_supabase_client(token) if token else None)
    if token:
        _set_auth_cookies(response, token, refresh_token)
    return _login_response(
        token,
        refresh_token,
        user,
        workspaces,
        requires_email_confirmation=session is None,
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response) -> LoginResponse:
    client = create_supabase_client()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is not configured.",
        )

    try:
        response_auth = client.auth.sign_in_with_password(
            {"email": str(request.email), "password": request.password}
        )
    except (AuthRetryableError, httpx.RequestError, httpx.HTTPError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication service is currently unavailable.",
        ) from exc
    except AuthApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc

    auth_user = getattr(response_auth, "user", None)
    session = getattr(response_auth, "session", None)
    token, refresh_token = _session_values(session)
    if not auth_user or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email confirmation is required before login.",
        )

    user = _user_from_auth_user(auth_user)
    _sync_public_user(user, token)
    scoped_client = create_supabase_client(token)
    workspaces = _build_user_workspaces(user.id, scoped_client)
    _set_auth_cookies(response, token, refresh_token)
    return _login_response(token, refresh_token, user, workspaces)


@router.get("/me", response_model=LoginResponse)
async def get_me(
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
) -> LoginResponse:
    scoped_client = create_supabase_client(token)
    return _login_response(
        token,
        None,
        user,
        _build_user_workspaces(user.id, scoped_client) if scoped_client else _build_user_workspaces(user.id),
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_session(
    payload: RefreshTokenRequest,
    request: Request,
    response: Response,
) -> LoginResponse:
    # Browsers never see the refresh token; it arrives only as an HttpOnly cookie.
    refresh_token = payload.refresh_token or request.cookies.get("kiku_refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing.",
        )

    client = create_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is not configured.",
        )

    try:
        response_auth = client.auth.refresh_session(refresh_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired.",
        ) from exc

    auth_user = getattr(response_auth, "user", None)
    session = getattr(response_auth, "session", None)
    token, new_refresh_token = _session_values(session)
    if not auth_user or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to refresh authentication session.",
        )

    user = _user_from_auth_user(auth_user)
    scoped_client = create_supabase_client(token)
    _set_auth_cookies(response, token, new_refresh_token)
    return _login_response(
        token,
        new_refresh_token,
        user,
        _build_user_workspaces(user.id, scoped_client),
    )


@router.post("/logout")
async def logout_endpoint(request: Request) -> Response:
    """Revoke the Supabase session, then drop the cookies regardless of outcome."""
    token = request.cookies.get("kiku_access_token")
    if not token:
        header = request.headers.get("authorization") or ""
        if header.lower().startswith("bearer "):
            token = header[7:].strip() or None

    revoke_error: str | None = None
    if token:
        admin = create_supabase_client(service_role=True)
        if not admin:
            revoke_error = "Session revocation unavailable: service role key is not configured."
        else:
            try:
                admin.auth.admin.sign_out(token)
            except Exception as exc:
                # ponytail: an already-expired token also lands here; treat as a
                # reported failure, split on error type if the noise matters.
                revoke_error = f"Session revocation failed: {exc}"

    result: Response = (
        JSONResponse({"detail": revoke_error}, status_code=status.HTTP_502_BAD_GATEWAY)
        if revoke_error
        else Response(status_code=status.HTTP_204_NO_CONTENT)
    )
    _clear_auth_cookies(result)
    return result
