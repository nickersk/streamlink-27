"""
$description French live TV channels, live streams and video content, owned by NextRadioTV.
$url bfmtv.com
$url 01net.com
$type live, vod
"""

import logging
import re

from streamlink.compat import urljoin
from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugins.brightcove import BrightcovePlayer
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:[\w-]+\.)+(?:bfmtv|01net)\.com"
))
class BFMTV(Plugin):
    def _brightcove(self, account_id, video_id):
        log.debug("Account ID: {0}".format(account_id))
        log.debug("Video ID: {0}".format(video_id))
        player = BrightcovePlayer(self.session, account_id)

        return dict(player.get_streams(video_id))

    def _streams_brightcove(self, root):
        schema_brightcove = validate.Schema(validate.any(
            validate.all(
                validate.xml_find(".//*[@accountid][@videoid]"),
                validate.union_get("accountid", "videoid")
            ),
            validate.all(
                validate.xml_find(".//*[@data-account][@data-video-id]"),
                validate.union_get("data-account", "data-video-id")
            )
        ))
        try:
            account_id, video_id = schema_brightcove.validate(root)
        except PluginError:
            return

        return self._brightcove(account_id, video_id)

    def _streams_brightcove_js(self, root):
        re_js_src = re.compile(r"^[\w/]+/main\.\w+\.js$")
        re_js_brightcove_video = re.compile(
            r'i\?\([A-Z]="[^"]+",y="(?P<video_id>[0-9]+).*"data-account"\s*:\s*"(?P<account_id>[0-9]+)',
        )
        schema_brightcove_js = validate.Schema(
            validate.xml_findall(r".//script[@src]"),
            validate.filter(lambda elem: re_js_src.search(elem.attrib.get("src"))),
            validate.get(0),
            validate.text,
            validate.transform(lambda src: urljoin(self.url, src))
        )
        schema_brightcove_js2 = validate.Schema(
            validate.transform(re_js_brightcove_video.search),
            validate.union_get("account_id", "video_id")
        )
        try:
            js_url = schema_brightcove_js.validate(root)
            log.debug("JS URL: {0}".format(js_url))
            account_id, video_id = self.session.http.get(js_url, schema=schema_brightcove_js2)
        except (PluginError, TypeError):
            return

        return self._brightcove(account_id, video_id)

    def _streams_dailymotion(self, root):
        schema_dailymotion = validate.Schema(
            validate.xml_xpath_string(".//iframe[contains(@src,'dailymotion.com/')][1]/@src"),
            validate.text,
            validate.transform(lambda src: src.split("/")[-1])
        )
        try:
            video_id = schema_dailymotion.validate(root)
        except PluginError:
            return

        log.debug("Found dailymotion video ID: {0}".format(video_id))

        return self.session.streams("https://www.dailymotion.com/embed/video/{0}".format(video_id))

    def _streams_audio(self, root):
        schema_audio = validate.Schema(validate.any(
            validate.all(
                validate.xml_xpath_string(".//audio/source[contains(@src,'.mp3')][1]/@src"),
                validate.text
            ),
            validate.all(
                validate.xml_xpath_string(".//div[contains(@class,'audio-player')][@data-media-url][1]/@data-media-url"),
                validate.text
            )
        ))
        try:
            audio_url = schema_audio.validate(root)
        except PluginError:
            return

        return {"audio": HTTPStream(self.session, audio_url)}

    def _get_streams(self):
        root = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html()
        ))

        return (
            self._streams_brightcove(root)
            or self._streams_dailymotion(root)
            or self._streams_brightcove_js(root)
            or self._streams_audio(root)
        )


__plugin__ = BFMTV
