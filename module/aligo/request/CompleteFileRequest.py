"""..."""
from dataclasses import dataclass, field
from typing import List

from module.aligo.types import DatClass
from module.aligo.types import UploadPartInfo


@dataclass
class CompleteFileRequest(DatClass):
    """..."""
    file_id: str = None
    drive_id: str = None
    upload_id: str = None
    part_info_list: List[UploadPartInfo] = field(default_factory=list, repr=False)
