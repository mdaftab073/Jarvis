"""Compatibility shim: re-exports Base from app.db.database.

Phase-14 models import from app.db.base_class; this module satisfies that
import without duplicating the declarative Base instance.
"""
from app.db.database import Base  # noqa: F401
