"""The Python enums and the Postgres types must not drift apart.

If they do, a value that is valid in the app fails on insert, or a filter
silently matches nothing. Cheap check, and it catches the mistake at the
moment someone adds a college and forgets the migration.
"""

import importlib.util
import pathlib

from app import enums

_spec_path = (
    pathlib.Path(__file__).resolve().parents[1]
    / "alembic" / "versions" / "0001_initial_schema.py"
)
_spec = importlib.util.spec_from_file_location("migration_0001", _spec_path)
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)


def _values(python_enum):
    return tuple(m.value for m in python_enum)


def test_every_vocabulary_matches():
    pairs = [
        (enums.College, migration.COLLEGE),
        (enums.Grade, migration.GRADE),
        (enums.Location, migration.LOCATION),
        (enums.Category, migration.CATEGORY),
        (enums.ItemCondition, migration.ITEM_CONDITION),
        (enums.ListingStatus, migration.LISTING_STATUS),
        (enums.EventType, migration.EVENT_TYPE),
    ]
    for python_enum, sql_values in pairs:
        assert _values(python_enum) == sql_values, python_enum.__name__


def test_industry_is_gone():
    """v2.0 removed it. If it comes back, it comes back deliberately."""
    assert not hasattr(enums, "Industry")


def test_all_eight_event_types_exist():
    """Section 4's analysis needs every one of them from day one."""
    assert len(enums.EventType) == 8
