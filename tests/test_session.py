import os
import re
import unittest
from socket import AF_INET, AF_INET6

from requests.packages.urllib3.util.connection import allowed_gai_family

from streamlink import NoPluginError, Streamlink
from streamlink.compat import is_py2
from streamlink.plugin import HIGH_PRIORITY, LOW_PRIORITY, NORMAL_PRIORITY, NO_PRIORITY, Plugin, pluginmatcher
from streamlink.session import print_small_exception
from streamlink.stream.akamaihd import AkamaiHDStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.stream.rtmpdump import RTMPStream
from tests.mock import Mock, call, patch


class EmptyPlugin(Plugin):
    def _get_streams(self):
        pass  # pragma: no cover


class TestSession(unittest.TestCase):
    PluginPath = os.path.join(os.path.dirname(__file__), "plugins")

    def setUp(self, load_plugins=True):
        self.session = Streamlink()
        if load_plugins:
            self.session.load_plugins(self.PluginPath)

    def subject(self, **kwargs):
        self.setUp(**kwargs)
        return self.session

    def test_exceptions(self):
        self.assertRaises(NoPluginError, self.session.resolve_url, "invalid url", follow_redirect=False)

    def test_load_plugins(self):
        plugins = self.session.get_plugins()
        self.assertIn("testplugin", plugins)
        self.assertNotIn("testplugin_missing", plugins)
        self.assertNotIn("testplugin_invalid", plugins)

    def test_builtin_plugins(self):
        session = self.subject()
        plugins = session.get_plugins()
        self.assertIn("twitch", plugins)
        self.assertEqual(plugins["twitch"].__module__, "streamlink.plugin.twitch")

    def test_override_plugins(self):
        session = self.subject()
        plugins = session.get_plugins()
        self.assertIn("testplugin", plugins)
        self.assertNotIn("testplugin_override", plugins)
        self.assertEqual(plugins["testplugin"].__name__, "TestPluginOverride")
        self.assertEqual(plugins["testplugin"].__module__, "streamlink.plugin.testplugin_override")

    def test_resolve_url(self):
        session = self.subject()
        plugins = session.get_plugins()
        plugin = session.resolve_url("http://test.se/channel")
        self.assertTrue(isinstance(plugin, Plugin))
        self.assertTrue(isinstance(plugin, plugins["testplugin"]))
        self.assertTrue(hasattr(session.resolve_url, "cache_info"), "resolve_url has a lookup cache")

    def test_resolve_url_scheme(self):
        @pluginmatcher(re.compile("http://insecure"))
        class PluginHttp(EmptyPlugin):
            pass

        @pluginmatcher(re.compile("https://secure"))
        class PluginHttps(EmptyPlugin):
            pass

        session = self.subject(load_plugins=False)
        session.plugins = {
            "insecure": PluginHttp,
            "secure": PluginHttps,
        }

        self.assertRaises(NoPluginError, session.resolve_url, "insecure")
        self.assertIsInstance(session.resolve_url("http://insecure"), PluginHttp)
        self.assertRaises(NoPluginError, session.resolve_url, "https://insecure")

        self.assertIsInstance(session.resolve_url("secure"), PluginHttps)
        self.assertRaises(NoPluginError, session.resolve_url, "http://secure")
        self.assertIsInstance(session.resolve_url("https://secure"), PluginHttps)

    def test_resolve_url_priority(self):
        @pluginmatcher(priority=HIGH_PRIORITY, pattern=re.compile(
            "https://(high|normal|low|no)$"
        ))
        class HighPriority(EmptyPlugin):
            pass

        @pluginmatcher(priority=NORMAL_PRIORITY, pattern=re.compile(
            "https://(normal|low|no)$"
        ))
        class NormalPriority(EmptyPlugin):
            pass

        @pluginmatcher(priority=LOW_PRIORITY, pattern=re.compile(
            "https://(low|no)$"
        ))
        class LowPriority(EmptyPlugin):
            pass

        @pluginmatcher(priority=NO_PRIORITY, pattern=re.compile(
            "https://(no)$"
        ))
        class NoPriority(EmptyPlugin):
            pass

        session = self.subject(load_plugins=False)
        session.plugins = {
            "high": HighPriority,
            "normal": NormalPriority,
            "low": LowPriority,
            "no": NoPriority,
        }
        no = session.resolve_url_no_redirect("no")
        low = session.resolve_url_no_redirect("low")
        normal = session.resolve_url_no_redirect("normal")
        high = session.resolve_url_no_redirect("high")

        self.assertIsInstance(no, HighPriority)
        self.assertIsInstance(low, HighPriority)
        self.assertIsInstance(normal, HighPriority)
        self.assertIsInstance(high, HighPriority)

        session.resolve_url.cache_clear()
        session.plugins = {
            "no": NoPriority,
        }
        with self.assertRaises(NoPluginError):
            session.resolve_url_no_redirect("no")

    @patch("streamlink.session.log")
    def test_resolve_deprecated(self, mock_log):
        # type: (Mock)
        @pluginmatcher(priority=LOW_PRIORITY, pattern=re.compile(
            "https://low"
        ))
        class LowPriority(EmptyPlugin):
            pass

        class DeprecatedNormalPriority(EmptyPlugin):
            # noinspection PyUnusedLocal
            @classmethod
            def can_handle_url(cls, url):
                return True

        class DeprecatedHighPriority(DeprecatedNormalPriority):
            # noinspection PyUnusedLocal
            @classmethod
            def priority(cls, url):
                return HIGH_PRIORITY

        session = self.subject(load_plugins=False)
        session.plugins = {
            "empty": EmptyPlugin,
            "low": LowPriority,
            "dep-normal-one": DeprecatedNormalPriority,
            "dep-normal-two": DeprecatedNormalPriority,
            "dep-high": DeprecatedHighPriority,
        }

        self.assertIsInstance(session.resolve_url_no_redirect("low"), DeprecatedHighPriority)
        if is_py2:
            self.assertEqual(mock_log.info.mock_calls, [
                call("Resolved plugin dep-high with deprecated can_handle_url API"),
            ])
        else:
            self.assertEqual(mock_log.info.mock_calls, [
                call("Resolved plugin dep-normal-one with deprecated can_handle_url API"),
                call("Resolved plugin dep-high with deprecated can_handle_url API")
            ])

    def test_resolve_url_no_redirect(self):
        plugins = self.session.get_plugins()
        channel = self.session.resolve_url_no_redirect("http://test.se/channel")
        self.assertTrue(isinstance(channel, Plugin))
        self.assertTrue(isinstance(channel, plugins["testplugin"]))

    def test_options(self):
        self.session.set_option("test_option", "option")
        self.assertEqual(self.session.get_option("test_option"), "option")
        self.assertEqual(self.session.get_option("non_existing"), None)

        self.assertEqual(self.session.get_plugin_option("testplugin", "a_option"), "default")
        self.session.set_plugin_option("testplugin", "another_option", "test")
        self.assertEqual(self.session.get_plugin_option("testplugin", "another_option"), "test")
        self.assertEqual(self.session.get_plugin_option("non_existing", "non_existing"), None)
        self.assertEqual(self.session.get_plugin_option("testplugin", "non_existing"), None)

    def test_plugin(self):
        channel = self.session.resolve_url("http://test.se/channel")
        streams = channel.streams()

        self.assertTrue("best" in streams)
        self.assertTrue("worst" in streams)
        self.assertTrue(streams["best"] is streams["1080p"])
        self.assertTrue(streams["worst"] is streams["350k"])
        self.assertTrue(isinstance(streams["rtmp"], RTMPStream))
        self.assertTrue(isinstance(streams["http"], HTTPStream))
        self.assertTrue(isinstance(streams["hls"], HLSStream))
        self.assertTrue(isinstance(streams["akamaihd"], AkamaiHDStream))

    def test_plugin_stream_types(self):
        channel = self.session.resolve_url("http://test.se/channel")
        streams = channel.streams(stream_types=["http", "rtmp"])

        self.assertTrue(isinstance(streams["480p"], HTTPStream))
        self.assertTrue(isinstance(streams["480p_rtmp"], RTMPStream))

        streams = channel.streams(stream_types=["rtmp", "http"])

        self.assertTrue(isinstance(streams["480p"], RTMPStream))
        self.assertTrue(isinstance(streams["480p_http"], HTTPStream))

    def test_plugin_stream_sorting_excludes(self):
        channel = self.session.resolve_url("http://test.se/channel")

        streams = channel.streams(sorting_excludes=[])
        self.assertTrue("best" in streams)
        self.assertTrue("worst" in streams)
        self.assertFalse("best-unfiltered" in streams)
        self.assertFalse("worst-unfiltered" in streams)
        self.assertTrue(streams["worst"] is streams["350k"])
        self.assertTrue(streams["best"] is streams["1080p"])

        streams = channel.streams(sorting_excludes=["1080p", "3000k"])
        self.assertTrue("best" in streams)
        self.assertTrue("worst" in streams)
        self.assertFalse("best-unfiltered" in streams)
        self.assertFalse("worst-unfiltered" in streams)
        self.assertTrue(streams["worst"] is streams["350k"])
        self.assertTrue(streams["best"] is streams["1500k"])

        streams = channel.streams(sorting_excludes=[">=1080p", ">1500k"])
        self.assertTrue(streams["best"] is streams["1500k"])

        streams = channel.streams(sorting_excludes=lambda q: not q.endswith("p"))
        self.assertTrue(streams["best"] is streams["3000k"])

        streams = channel.streams(sorting_excludes=lambda q: False)
        self.assertFalse("best" in streams)
        self.assertFalse("worst" in streams)
        self.assertTrue("best-unfiltered" in streams)
        self.assertTrue("worst-unfiltered" in streams)
        self.assertTrue(streams["worst-unfiltered"] is streams["350k"])
        self.assertTrue(streams["best-unfiltered"] is streams["1080p"])

        channel = self.session.resolve_url("http://test.se/UnsortableStreamNames")
        streams = channel.streams()
        self.assertFalse("best" in streams)
        self.assertFalse("worst" in streams)
        self.assertFalse("best-unfiltered" in streams)
        self.assertFalse("worst-unfiltered" in streams)
        self.assertTrue("vod" in streams)
        self.assertTrue("vod_alt" in streams)
        self.assertTrue("vod_alt2" in streams)

    @patch("streamlink.session.sys.stderr")
    def test_short_exception(self, stderr):
        try:
            raise RuntimeError("test exception")
        except RuntimeError:
            print_small_exception("test_short_exception")
            self.assertSequenceEqual(
                [call('RuntimeError: test exception\n'), call('\n')],
                stderr.write.mock_calls)

    def test_set_and_get_locale(self):
        session = Streamlink()
        session.set_option("locale", "en_US")
        self.assertEqual(session.localization.country.alpha2, "US")
        self.assertEqual(session.localization.language.alpha2, "en")
        self.assertEqual(session.localization.language_code, "en_US")

    @patch("streamlink.session.api")
    def test_interface(self, mock_api):
        adapter_http = Mock(poolmanager=Mock(connection_pool_kw={}))
        adapter_https = Mock(poolmanager=Mock(connection_pool_kw={}))
        adapter_foo = Mock(poolmanager=Mock(connection_pool_kw={}))
        mock_api.HTTPSession.return_value = Mock(adapters={
            "http://": adapter_http,
            "https://": adapter_https,
            "foo://": adapter_foo
        })
        session = self.subject(load_plugins=False)
        self.assertEqual(session.get_option("interface"), None)

        session.set_option("interface", "my-interface")
        self.assertEqual(adapter_http.poolmanager.connection_pool_kw, {"source_address": ("my-interface", 0)})
        self.assertEqual(adapter_https.poolmanager.connection_pool_kw, {"source_address": ("my-interface", 0)})
        self.assertEqual(adapter_foo.poolmanager.connection_pool_kw, {})
        self.assertEqual(session.get_option("interface"), "my-interface")

        session.set_option("interface", None)
        self.assertEqual(adapter_http.poolmanager.connection_pool_kw, {})
        self.assertEqual(adapter_https.poolmanager.connection_pool_kw, {})
        self.assertEqual(adapter_foo.poolmanager.connection_pool_kw, {})
        self.assertEqual(session.get_option("interface"), None)

    @patch("streamlink.session.urllib3_connection", allowed_gai_family=allowed_gai_family)
    def test_ipv4_ipv6(self, mock_urllib3_connection):
        session = self.subject(load_plugins=False)
        self.assertEqual(session.get_option("ipv4"), False)
        self.assertEqual(session.get_option("ipv6"), False)
        self.assertEqual(mock_urllib3_connection.allowed_gai_family, allowed_gai_family)

        session.set_option("ipv4", True)
        self.assertEqual(session.get_option("ipv4"), True)
        self.assertEqual(session.get_option("ipv6"), False)
        self.assertNotEqual(mock_urllib3_connection.allowed_gai_family, allowed_gai_family)
        self.assertEqual(mock_urllib3_connection.allowed_gai_family(), AF_INET)

        session.set_option("ipv4", False)
        self.assertEqual(session.get_option("ipv4"), False)
        self.assertEqual(session.get_option("ipv6"), False)
        self.assertEqual(mock_urllib3_connection.allowed_gai_family, allowed_gai_family)

        session.set_option("ipv6", True)
        self.assertEqual(session.get_option("ipv4"), False)
        self.assertEqual(session.get_option("ipv6"), True)
        self.assertNotEqual(mock_urllib3_connection.allowed_gai_family, allowed_gai_family)
        self.assertEqual(mock_urllib3_connection.allowed_gai_family(), AF_INET6)

        session.set_option("ipv6", False)
        self.assertEqual(session.get_option("ipv4"), False)
        self.assertEqual(session.get_option("ipv6"), False)
        self.assertEqual(mock_urllib3_connection.allowed_gai_family, allowed_gai_family)

        session.set_option("ipv4", True)
        session.set_option("ipv6", False)
        self.assertEqual(session.get_option("ipv4"), True)
        self.assertEqual(session.get_option("ipv6"), False)
        self.assertEqual(mock_urllib3_connection.allowed_gai_family, allowed_gai_family)

    def test_https_proxy_default(self):
        session = Streamlink()
        session.set_option("http-proxy", "http://testproxy.com")

        self.assertEqual("http://testproxy.com", session.http.proxies['http'])
        self.assertEqual("http://testproxy.com", session.http.proxies['https'])

    def test_https_proxy_set_first(self):
        session = Streamlink()
        session.set_option("https-proxy", "https://testhttpsproxy.com")
        session.set_option("http-proxy", "http://testproxy.com")

        self.assertEqual("http://testproxy.com", session.http.proxies['http'])
        self.assertEqual("http://testproxy.com", session.http.proxies['https'])

    def test_https_proxy_default_override(self):
        session = Streamlink()
        session.set_option("http-proxy", "http://testproxy.com")
        session.set_option("https-proxy", "https://testhttpsproxy.com")

        self.assertEqual("https://testhttpsproxy.com", session.http.proxies['http'])
        self.assertEqual("https://testhttpsproxy.com", session.http.proxies['https'])

    def test_https_proxy_set_only(self):
        session = Streamlink()
        session.set_option("https-proxy", "https://testhttpsproxy.com")

        self.assertEqual("https://testhttpsproxy.com", session.http.proxies['http'])
        self.assertEqual("https://testhttpsproxy.com", session.http.proxies['https'])

    def test_http_proxy_socks(self):
        session = self.subject(load_plugins=False)
        session.set_option("http-proxy", "socks5://localhost:1234")

        self.assertEqual("socks5://localhost:1234", session.http.proxies["http"])
        self.assertEqual("socks5://localhost:1234", session.http.proxies["https"])

    def test_https_proxy_socks(self):
        session = self.subject(load_plugins=False)
        session.set_option("https-proxy", "socks5://localhost:1234")

        self.assertEqual("socks5://localhost:1234", session.http.proxies["http"])
        self.assertEqual("socks5://localhost:1234", session.http.proxies["https"])
