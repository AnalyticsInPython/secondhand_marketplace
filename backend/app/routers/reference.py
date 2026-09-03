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
    ListingStatus,
    SortOrder,
)
from ..models import User
from ..schemas import CountryOut, ZipOut
from ..security import current_user_optional
from ..services import countries, geo

router = APIRouter(tags=["reference"])


@router.get("/zips", response_model=list[ZipOut])
def search_zips(q: str = "", viewer: User | None = Depends(current_user_optional)):
    """ZIP autocomplete for sign-up (state A7) and the settings screen.

    Ordered by distance from the viewer's own ZIP when we know it, otherwise
    from campus — so the first result is almost always the right one.
    """
    return geo.search(q, origin_zip=viewer.zip_code if viewer else None)


@router.get("/reference/countries", response_model=list[CountryOut])
def list_countries():
    """The nationality picker: the four most common at Columbia first."""
    return countries.all_countries()


@router.get("/reference/enums")
def enums():
    """One call the frontend makes at boot to fill every picker."""
    return {
        "allowed_email_domains": list(settings.domains_ordered),
        "categories": [
            {
                "value": c.value,
                "label": label,
                "subcategories": [
                    {"value": s, "label": SUBCATEGORY_LABELS[s]} for s in SUBCATEGORIES.get(c, [])
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
        "listing_statuses": [{"value": s.value, "label": s.label()} for s in ListingStatus],
        "sort_orders": [s.value for s in SortOrder],
        # The presets under the distance slider. Continuous in between.
        "radius_steps_mi": settings.radius_steps_mi,
        "radius_mi": {
            "min": settings.min_radius_mi,
            "max": settings.max_radius_mi,
            "default": settings.default_radius_mi,
        },
        "photos": {
            "max_per_listing": settings.max_photos_per_listing,
            "max_bytes": settings.max_photo_bytes,
        },
    }
