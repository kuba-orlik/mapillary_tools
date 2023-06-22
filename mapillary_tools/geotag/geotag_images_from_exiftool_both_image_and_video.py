import logging
import typing as T
from pathlib import Path

from .. import exiftool_read, types, utils
from . import (
    geotag_images_from_exiftool,
    geotag_images_from_video,
    geotag_videos_from_exiftool_video,
)
from .geotag_from_generic import GeotagImagesFromGeneric


LOG = logging.getLogger(__name__)


class GeotagImagesFromExifToolBothImageAndVideo(GeotagImagesFromGeneric):
    def __init__(
        self,
        image_paths: T.Sequence[Path],
        xml_path: Path,
        offset_time: float = 0.0,
    ):
        self.image_paths = image_paths
        self.xml_path = xml_path
        self.offset_time = offset_time
        super().__init__()

    def to_description(self) -> T.List[types.ImageMetadataOrError]:
        # will return this list
        final_image_metadatas: T.List[types.ImageMetadataOrError] = []

        # find the images that can be geotagged from EXIF
        image_metadatas_from_exiftool = (
            geotag_images_from_exiftool.GeotagImagesFromExifTool(
                self.image_paths, self.xml_path
            ).to_description()
        )

        maybe_sample_image_paths = []
        for image_metadata in image_metadatas_from_exiftool:
            if isinstance(image_metadata, types.ErrorMetadata):
                maybe_sample_image_paths.append(image_metadata.filename)
            else:
                final_image_metadatas.append(image_metadata)

        # find all video paths in self.xml_path
        rdf_description_by_path = exiftool_read.index_rdf_description_by_path(
            [self.xml_path]
        )
        video_paths = utils.find_videos(
            [Path(pathstr) for pathstr in rdf_description_by_path.keys()],
            skip_subfolders=True,
            check_file_suffix=True,
        )

        # find all video paths that have sample images
        image_samples_by_video_path = utils.find_all_image_samples(
            maybe_sample_image_paths, video_paths
        )
        video_paths_with_image_samples = list(image_samples_by_video_path.keys())

        video_metadatas = (
            geotag_videos_from_exiftool_video.GeotagVideosFromExifToolVideo(
                video_paths_with_image_samples,
                self.xml_path,
            ).to_description()
        )

        image_metadatas_from_video = geotag_images_from_video.GeotagImagesFromVideo(
            self.image_paths, video_metadatas, offset_time=self.offset_time
        ).to_description()
        final_image_metadatas.extend(image_metadatas_from_video)

        assert len(final_image_metadatas) <= len(self.image_paths)
        return final_image_metadatas
