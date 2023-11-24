"""..."""
from dataclasses import dataclass

from module.aligo.types import DatClass


@dataclass
class GetShareInfoRequest(DatClass):
    """..."""
    share_id: str
