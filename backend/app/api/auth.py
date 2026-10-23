
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import Request
from app.models.audit_event import AuditEvent

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
bearer = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    email = data.email.strip().lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists",
        )

    user = User(
        name=data.name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        role="viewer",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user



@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = data.email.strip().lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if (
        not user
        or not verify_password(
            data.password,
            user.password_hash,
        )
        or not user.is_active
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # Record the successful login
    db.add(
        AuditEvent(
            actor_id=user.id,
            document_id=None,
            action="auth.login",
            ip_address=(
                request.client.host if request.client else None
            ),
            metadata_json={},
        )
    )
    db.commit()

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        )

    user = db.get(User, user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User account is unavailable",
        )

    return user


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user
