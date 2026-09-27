from enum import Enum


class MaterialType(str, Enum):
    NOTES = "NOTES"
    PYQ = "PYQ"
    SYLLABUS = "SYLLABUS"
    REFERENCE = "REFERENCE"


MATERIAL_TYPES = tuple(material_type.value for material_type in MaterialType)