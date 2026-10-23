
import hashlib
import re
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse

from datetime import datetime, timezone

from sqlalchemy import and_, or_, select

from app.models.permission import DocumentPermission
from app.schemas.permission import ShareRequest, PermissionResponse


router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
    dependencies=[Depends(get_current_user)],
)

# Private directory under the backend project, not a public/static folder.
STORAGE_DIR = Path(__file__).resolve().parents[2] / "private_uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MiB
CHUNK_SIZE = 64 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".docx",
    ".csv",
}


def record_audit(
    db: Session,
    user: User,
    action: str,
    request: Request,
    document_id: int | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_id=user.id,
            document_id=document_id,
            action=action,
            ip_address=(
                request.client.host if request.client else None
            ),
            metadata_json={},
        )
    )


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    request: Request,
    title: str = Form(..., min_length=1, max_length=255),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = title.strip()
    if not title:
        raise HTTPException(400, "Title cannot be blank")

    original_name = Path(file.filename or "").name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="File type not allowed",
        )

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # The user-supplied filename is never used as the storage path.
    storage_name = f"{uuid.uuid4().hex}{extension}"
    storage_path = STORAGE_DIR / storage_name

    digest = hashlib.sha256()
    total_size = 0

    try:
        with storage_path.open("xb") as output:
            while True:
                chunk = file.file.read(CHUNK_SIZE)
                if not chunk:
                    break

                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds the 10 MiB limit",
                    )

                digest.update(chunk)
                output.write(chunk)

        document = Document(
            owner_id=current_user.id,
            title=title,
            storage_key=storage_name,
            sha256=digest.hexdigest(),
        )
        db.add(document)
        db.flush()

        record_audit(
            db,
            current_user,
            "document.upload",
            request,
            document.id,
        )

        db.commit()
        db.refresh(document)
        return document

    except Exception:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise

    finally:
        file.file.close()


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        select(Document)
        .outerjoin(
            DocumentPermission,
            and_(
                DocumentPermission.document_id == Document.id,
                DocumentPermission.user_id == current_user.id,
                DocumentPermission.can_read.is_(True),
                DocumentPermission.revoked_at.is_(None),
            ),
        )
        .where(
            or_(
                Document.owner_id == current_user.id,
                DocumentPermission.id.is_not(None),
            )
        )
        .distinct()
        .order_by(Document.id.desc())
    )

    return db.scalars(query).all()


@router.post(
    "/{document_id}/share",
    response_model=PermissionResponse,
    status_code=201,
)
def share_document(
    document_id: int,
    data: ShareRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if document is None or document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    email = data.email.strip().lower()

    if email == current_user.email.strip().lower():
        raise HTTPException(
            status_code=400,
            detail="You already own this document",
        )

    recipient = db.scalar(
        select(User).where(User.email == email)
    )

    if recipient is None or not recipient.is_active:
        raise HTTPException(
            status_code=404,
            detail="Active recipient account not found",
        )

    permission = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document_id,
            DocumentPermission.user_id == recipient.id,
        )
    )

    now = datetime.now(timezone.utc)

    if permission is None:
        permission = DocumentPermission(
            document_id=document_id,
            user_id=recipient.id,
            can_read=True,
            can_edit=data.can_edit,
            granted_by=current_user.id,
        )
        db.add(permission)
    else:
        permission.can_read = True
        permission.can_edit = data.can_edit
        permission.granted_by = current_user.id
        permission.revoked_at = None
        permission.created_at = now


    db.flush()

    db.add(
        AuditEvent(
            actor_id=current_user.id,
            document_id=document_id,
            action="document.share",
            ip_address=(
                request.client.host if request.client else None
            ),
            metadata_json={
                "recipient_user_id": recipient.id,
                "can_edit": data.can_edit,
            },
        )
    )

    db.commit()
    db.refresh(permission)

    return permission



@router.get(
    "/{document_id}/permissions",
    response_model=list[PermissionResponse],
)
def list_document_permissions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if document is None or document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    return db.scalars(
        select(DocumentPermission)
        .where(DocumentPermission.document_id == document_id)
        .order_by(DocumentPermission.id)
    ).all()


@router.delete("/{document_id}/share/{permission_id}")
def revoke_document_access(
    document_id: int,
    permission_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if document is None or document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    permission = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.id == permission_id,
            DocumentPermission.document_id == document_id,
        )
    )

    if permission is None:
        raise HTTPException(
            status_code=404,
            detail="Permission not found",
        )

    if permission.revoked_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Permission has already been revoked",
        )

    permission.revoked_at = datetime.now(timezone.utc)

    record_audit(
        db,
        current_user,
        "document.revoke",
        request,
        document_id,
    )

    db.commit()

    return {"message": "Document access revoked successfully"}


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    is_owner = document.owner_id == current_user.id

    if not is_owner:
        permission = db.scalar(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == current_user.id,
                DocumentPermission.can_read.is_(True),
                DocumentPermission.revoked_at.is_(None),
            )
        )

        if permission is None:
            db.add(
                AuditEvent(
                    actor_id=current_user.id,
                    document_id=document.id,
                    action="document.access_denied",
                    ip_address=(
                        request.client.host
                        if request.client
                        else None
                    ),
                    metadata_json={
                        "reason": "permission_denied",
                        "operation": "download",
                    },
                )
            )
            db.commit()

            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

    root = STORAGE_DIR.resolve()
    path = (root / document.storage_key).resolve()

    if path.parent != root or not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    record_audit(
        db,
        current_user,
        "document.download",
        request,
        document.id,
    )
    db.commit()

    safe_title = re.sub(
        r"[^A-Za-z0-9._ -]",
        "_",
        document.title,
    ).strip(" .")

    extension = Path(document.storage_key).suffix
    download_name = f"{safe_title or 'document'}{extension}"

    return FileResponse(
        path=str(path),
        filename=download_name,
        media_type="application/octet-stream",
    )
