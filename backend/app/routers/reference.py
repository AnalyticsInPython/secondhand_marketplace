"""Reference data the frontend needs to render dropdowns and autocompletes.

Everything here is static. It lives on the server so the enum values in
`enums.py` stay the single source of truth and the frontend cannot drift.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import settings
from ..enums import (
    CATEGORY_LABELS,
    CONDITION_LABELS,
    GRADUATE_SCHOOLS,
    SUBCATEGORIES,
    SUBCATEGORY_LABELS,
    UNDERGRADUATE_SCHOOLS,
    Grade,
    Source,
)
from ..models import User
from ..schemas import ZipOut
from ..security import current_user_optional
from ..services import geo

router = APIRouter(tags=["reference"])


@router.get("/zips", response_model=list[ZipOut])
def search_zips(q: str = "", viewer: User | None = Depends(current_user_optional)):
    """ZIP autocomplete for sign-up (state A7) and the settings screen.

    Ordered by distance from the viewer's own ZIP when we know it, otherwise
    from campus — so the first result is almost always the right one.
    """
    return geo.search(q, origin_zip=viewer.zip_code if viewer else None)


@router.get("/reference/enums")
def enums():
    """One call the frontend makes at boot to fill every picker."""
    return {
        "categories": [
            {
                "value": c.value,
                "label": label,
                "subcategories": [
                    {"value": s, "label": SUBCATEGORY_LABELS[s]}
                    for s in SUBCATEGORIES.get(c, [])
                ],
            }
            for c, label in CATEGORY_LABELS.items()
        ],
        "conditions": [{"value": c.value, "label": label} for c, label in CONDITION_LABELS.items()],
        "grades": [{"value": g.value, "label": g.label()} for g in Grade],
        "schools": {
            "undergraduate": [{"value": s.value, "label": s.label()} for s in UNDERGRADUATE_SCHOOLS],
            "graduate": [{"value": s.value, "label": s.label()} for s in GRADUATE_SCHOOLS],
        },
        "sources": [{"value": s.value, "label": s.label()} for s in Source],
        # The presets under the distance slider. Continuous in between.
        "radius_steps_mi": [0.5, 1, 2.5, 5, 10],
        # Who may register, so the sign-up and sign-in screens validate
        # against exactly what the API enforces. See app/emails.py.
        "email_domains": list(settings.allowed_domains_ordered),
    }
