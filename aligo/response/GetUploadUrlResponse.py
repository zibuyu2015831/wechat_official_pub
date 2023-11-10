"""GetUploadUrlResponse"""
from dataclasses import dataclass, field
from typing import List

from aligo.types import DatClass, UploadPartInfo


@dataclass
class GetUploadUrlResponse(DatClass):
    """GetUploadUrlResponse"""
    domain_id: str = None
    drive_id: str = None
    file_id: str = None
    upload_id: str = None
    create_at: str = None
    part_info_list: List[UploadPartInfo] = field(default_factory=list, repr=False)
