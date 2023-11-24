"""..."""
from dataclasses import dataclass

from module.aligo.types import DatClass


@dataclass
class GetDefaultDriveRequest(DatClass):
    """..."""
    user_id: str
