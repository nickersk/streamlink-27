"""
$description Live TV channels and video on-demand service from ARD, a German public, independent broadcaster.
$url ardmediathek.de
$url mediathek.daserste.de
$type live, vod
$region Germany
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:(\w+\.)?ardmediathek\.de/|mediathek\.daserste\.de/)"
))
class ARDMediathek(Plugin):
    _QUALITY_MAP = {
        4: "1080p",
        3: "720p",
        2: "540p",
        1: "360p",
        0: "270p"
    }

    def _get_streams(self):
        data_json = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_findtext(".//script[@id='fetchedContextValue'][@type='application/json']"),
            validate.any(None, validate.all(
                validate.parse_json(),
                {validate.text: dict},
                validate.transform(lambda obj: list(obj.items())),
                validate.filter(lambda item: item[0].startswith("https://api.ardmediathek.de/page-gateway/pages/")),
                validate.any(validate.get((0, 1)), [])
            ))
        ))
        if not data_json:
            return

        schema_data = validate.Schema({
            "id": validate.text,
            "widgets": validate.all(
                [dict],
                validate.filter(lambda item: item.get("mediaCollection")),
                validate.get(0),
                validate.any(None, validate.all(
                    {
                        "geoblocked": bool,
                        "publicationService": {
                            "name": validate.text,
                        },
                        "show": validate.any(None, validate.all(
                            {"title": validate.text},
                            validate.get("title")
                        )),
                        "title": validate.text,
                        "mediaCollection": {
                            "embedded": {
                                "_mediaArray": [validate.all(
                                    {
                                        "_mediaStreamArray": [validate.all(
                                            {
                                                "_quality": validate.any(validate.text, int),
                                                "_stream": validate.url(),
                                            },
                                            validate.union_get("_quality", "_stream")
                                        )]
                                    },
                                    validate.get("_mediaStreamArray"),
                                    validate.transform(dict)
                                )]
                            }
                        },
                    },
                    validate.union_get(
                        "geoblocked",
                        ("mediaCollection", "embedded", "_mediaArray", 0),
                        ("publicationService", "name"),
                        "title",
                        "show",
                    )
                ))
            )
        })
        data = schema_data.validate(data_json)

        log.debug("Found media id: {0}".format(data['id']))
        if not data["widgets"]:
            log.info("The content is unavailable")
            return

        geoblocked, media, self.author, self.title, show = data["widgets"]
        if geoblocked:
            log.info("The content is not available in your region")
            return
        if show:
            self.title = u"{0}: {1}".format(show, self.title)

        if media.get("auto"):
            for s in HLSStream.parse_variant_playlist(self.session, media.get("auto")).items():
                yield s
        else:
            for quality, stream in media.items():
                yield self._QUALITY_MAP.get(quality, quality), HTTPStream(self.session, stream)


__plugin__ = ARDMediathek
