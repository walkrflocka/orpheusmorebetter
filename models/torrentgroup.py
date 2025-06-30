from pydantic import BaseModel, Field, ConfigDict

from .torrent import Torrent
from .artist import Artist
from .format import Format

import copy
import re

class TorrentGroup(BaseModel):
    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    id: int = Field(alias = 'groupId')
    name: str = Field(alias = 'groupName')
    year: int = Field(alias = 'groupYear')
    torrent: list[Torrent]
    primary_artists: list[Artist]

    @property
    def formatted_artist_string(self) -> str:
        # prevent mutation of the class copy
        artists = copy.deepcopy(self.primary_artists)
        match len(artists):
            case 0: raise ValueError('Torrent group has no artists!')
            case 1: return artists[0].name
            case 2: return f'{artists[0].name} & {artists[1].name}'
            case _:
                # jam an and into the last artist's name
                artists[-1].name = '& ' + artists[-1].name
                # in this house we believe in the oxford comma
                return ', '.join(map(lambda x: x.name, artists))

    def get_transcode_dirname(
            self,
            source_torrent: Torrent,
            target_format: Format
        ) -> str:
        """Helper function for grabbing the eventual dirname for the transcode.

        Args:
            source_torrent (Torrent): Transcode source torrent.
            artist_name (str): Self explanatory.
            target_format (Literal[&#39;FLAC&#39;, &#39;MP3 320&#39;, &#39;MP3 V0&#39;]): Self explanatory.

        Raises:
            ValueError: Raised if torrent group ID doesn't match this group's ID.

        Returns:
            str: Transcode dirname.
        """
        # maybe this should live on the Torrent model? sheit idk

        if source_torrent.groupId != self.id:
            raise ValueError(f"Provided source torrent group ID does not match group's ID: {source_torrent.groupId} != {self.id}")
        transcode_folder = f"{self.formatted_artist_string} - {self.year} - {self.name} {source_torrent.formatted_media_info} [{target_format.long_name}]"
        transcode_folder = re.sub(r'[\?<>\\*\|":\/]', "_", transcode_folder) # Removes the following from folder names and replaces with underscore: ?<>\*|":/ 
        return transcode_folder