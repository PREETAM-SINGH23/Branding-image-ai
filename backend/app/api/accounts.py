from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Account, Dealership, User
from app.schemas import AccountOut, DealershipOut

router = APIRouter(prefix="/api", tags=["accounts"])


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[Account]:
    return db.query(Account).order_by(Account.name).all()


@router.get("/accounts/{account_id}/dealerships", response_model=list[DealershipOut])
def list_dealerships(
    account_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[Dealership]:
    exists = db.query(Account.id).filter(Account.id == account_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return (
        db.query(Dealership)
        .filter(Dealership.account_id == account_id)
        .order_by(Dealership.name)
        .all()
    )
