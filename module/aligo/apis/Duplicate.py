"""..."""
import itertools
from typing import List

from module.aligo.core import Core
from module.aligo.request import ListToCleanRequest
from module.aligo.response import DuplicateItem
from module.aligo.types import BaseFile


class Duplicate(Core):
    """..."""

    def duplicate_list(self, drive_id: str = None) -> List[DuplicateItem]:
        """..."""
        return list(self._core_duplicate_list(drive_id))

    def list_to_clean(self, album_drive_id: str, size: int = 200, drive_id: str = None) -> List[BaseFile]:
        """..."""
        if drive_id is None:
            drive_id = self.default_drive_id
        ll = []
        for i in itertools.islice(
                self._core_list_to_clean(ListToCleanRequest(drive_id=drive_id, album_drive_id=album_drive_id)), size):
            ll.append(i)
        return ll
