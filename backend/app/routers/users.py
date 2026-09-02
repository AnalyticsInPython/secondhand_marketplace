"""Profile & account — UX_SPEC.md §6.6."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from ..db import get_db
from ..enums import UserStatus
from ..models import User
from ..schemas import MeOut, ProfileUpdate
from ..security import current_user
from ..services import geo

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("", response_model=MeOut)
def get_profile(user: User = Depends(current_user)):
    return MeOut.model_validate(user)


@router.patch("", response_model=MeOut)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Everything on the settings screen except the email, which has no route.

    Clearing `phone` is a supported operation, not an error: it moves the user's
    listings to the single full-width Email button (UX_SPEC.md §5.1).
    """
    data = payload.model_dump(exclude_unset=True)

    if "zip_code" in data and not geo.is_supported(data["zip_code"]):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{data['zip_code']} is not in the New York metro area.",
        )

    if "username" in data and data["username"] != user.username:
        clash = db.query(User).filter(User.username == data["username"]).first()
        if clash is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken")

    if "nationality" in data and data["nationality"]:
        data["nationality"] = data["nationality"].upper()

    if "phone" in data and not data["phone"]:
        data["phone"] = None  # explicit clear

    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    return MeOut.model_validate(user)


@router.post("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
def deactivate(user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Reversible: signing in with the same Columbia email brings it back."""
    user.status = UserStatus.DEACTIVATED
    db.commit()
