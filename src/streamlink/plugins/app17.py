import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://17\.live/.+/live/(?P<channel>[^/&?]+)"
))
class App17(Plugin):
    def _get_streams(self):
        channel = self.match.group("channel")
        self.session.http.headers.update({"Referer": self.url})
        data = self.session.http.post(
            "https://wap-api.17app.co/api/v1/lives/{0}/viewers/alive".format(channel),
            data={"liveStreamID": channel},
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {"rtmpUrls": [{
                        validate.optional("provider"): validate.any(int, None),
                        "url": validate.url(path=validate.endswith(".flv")),
                    }]},
                    {"errorCode": int, "errorMessage": str},
                ),
            ),
            acceptable_status=(200, 403, 404, 420))
        log.trace("{0!r}".format(data))
        if data.get("errorCode"):
            log.error("{0} - {1}".format(data['errorCode'], data['errorMessage'].replace('Something wrong: ', '')))
            return

        flv_url = data["rtmpUrls"][0]["url"]
        yield "live", HTTPStream(self.session, flv_url)

        if "wansu-" in flv_url:
            hls_url = flv_url.replace(".flv", "/playlist.m3u8")
        else:
            hls_url = flv_url.replace("live-hdl", "live-hls").replace(".flv", ".m3u8")

        s = HLSStream.parse_variant_playlist(self.session, hls_url)
        if not s:
            yield "live", HLSStream(self.session, hls_url)
        else:
            if len(s) == 1:
                for _n, _s in s.items():
                    yield "live", _s
            else:
                for _s in s.items():
                    yield _s


__plugin__ = App17
