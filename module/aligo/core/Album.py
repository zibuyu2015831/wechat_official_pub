from typing import Iterator

from module.aligo.core import BaseAligo
from module.aligo.core.Config import ADRIVE_V1_ALBUMHOME_ALBUMLIST, ADRIVE_V1_ALBUM_LIST_FILES, ADRIVE_V1_USER_ALBUMS_INFO
from module.aligo.request import AlbumListRequest, AlbumListFilesRequest
from module.aligo.response import AlbumInfoResponse, AlbumListResponse, ListResponse
from module.aligo.types import ListAlbumItem


class Album(BaseAligo):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._album_info = None

    @property
    def album_info(self) -> AlbumInfoResponse:
        if self._album_info is None:
            response = self.post(ADRIVE_V1_USER_ALBUMS_INFO)
            data = response.json()['data']
            self._album_info = AlbumInfoResponse(**data)
        return self._album_info

    def _core_list_album(self, body: AlbumListRequest) -> Iterator[ListAlbumItem]:
        yield from self._list_file(ADRIVE_V1_ALBUMHOME_ALBUMLIST, body, AlbumListResponse)

    def _core_list_album_files(self, body: AlbumListFilesRequest):
        yield from self._list_file(ADRIVE_V1_ALBUM_LIST_FILES, body, ListResponse)
