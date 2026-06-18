"""Business dictionary collections — domain reference data the agents read as context.

Two flavors mirror the original system:
- curated: a single shared data dictionary keyed by table/field.
- vendor: per-vendor field definitions (richer: protected-data flags, usage tags, etc.).
"""

from beanie import Document, Indexed


class CuratedDictionaryEntry(Document):
    table_name: Indexed(str)  # type: ignore[valid-type]
    field_name: str
    business_friendly_name: str = ""
    data_type: str = ""
    nullable_flag: str = ""
    business_description: str = ""
    sample_values: str = ""
    category: str = ""
    order_num: int = 0

    class Settings:
        name = "curated_business_dictionary"


class VendorDictionaryEntry(Document):
    vendor_name: Indexed(str)  # type: ignore[valid-type]
    file_category: str = ""
    field_name: str = ""
    business_friendly_name: str = ""
    data_type: str = ""
    business_description: str = ""
    category: str = ""
    nullable_flag: str = ""
    protected_data_flag: str = ""
    usage_tags: str = ""
    glossary_tags: str = ""
    sample_values: str = ""
    edd_tag: str = ""
    filtering_condition: str = ""

    class Settings:
        name = "vendor_business_dictionary"
