from __future__ import unicode_literals

import re

from streamlink.plugin import Plugin
from streamlink.plugin.plugin import parse_url_params
from streamlink.stream import HTTPStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.utils import update_scheme


class MuxedStreamPlugin(Plugin):
    _url_re = re.compile(r"muxedstream://(.+)")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        url, params = parse_url_params(self.url)
        urlnoproto = self._url_re.match(url).group(1)
        urlnoproto = update_scheme("http://", urlnoproto)

        self.logger.debug("Video URL: {}", urlnoproto)

        aurlnoproto = params.get("audio")
        aurlnoproto = update_scheme("http://", aurlnoproto)
        quality = params.get("quality", "unknown")

        self.logger.debug("Video Quality: {}", quality)
        self.logger.debug("Audio URL: {}", aurlnoproto)

        streams = {}
        streams[quality] = MuxedStream(
            self.session, HTTPStream(self.session, urlnoproto), HTTPStream(self.session, aurlnoproto)
        )

        return streams


__plugin__ = MuxedStreamPlugin
