"""..."""
from dataclasses import dataclass, field
from typing import List

from module.aligo.types import DatClass


@dataclass
class BatchCancelShareRequest(DatClass):
    """..."""
    share_id_list: List[str] = field(default_factory=list)
