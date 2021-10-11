import json
import re

from lxml.etree import HTML, XML

from streamlink.compat import is_py2, is_py3, parse_qsl
from streamlink.plugin import PluginError


def _parse(parser, data, name, exception, schema, *args, **kwargs):
    try:
        parsed = parser(data, *args, **kwargs)
    except Exception as err:
        snippet = repr(data)
        if len(snippet) > 35:
            snippet = "{0} ...".format(snippet[:35])

        raise exception("Unable to parse {0}: {1} ({2})".format(name, err, snippet))

    if schema:
        parsed = schema.validate(parsed, name=name, exception=exception)

    return parsed


def parse_json(
    data,
    name="JSON",
    exception=PluginError,
    schema=None,
    *args, **kwargs
):
    """Wrapper around json.loads.

    Provides these extra features:
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    return _parse(json.loads, data, name, exception, schema, *args, **kwargs)


def parse_html(
    data,
    name="HTML",
    exception=PluginError,
    schema=None,
    *args, **kwargs
):
    """Wrapper around lxml.etree.HTML with some extras.

    Provides these extra features:
     - Handles incorrectly encoded HTML
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    if is_py2 and isinstance(data, unicode):
        data = data.encode("utf8")
    elif is_py3 and isinstance(data, str):
        data = bytes(data, "utf8")

    return _parse(HTML, data, name, exception, schema, *args, **kwargs)


def parse_xml(
    data,
    ignore_ns=False,
    invalid_char_entities=False,
    name="XML",
    exception=PluginError,
    schema=None,
    *args, **kwargs
):
    """Wrapper around lxml.etree.XML with some extras.

    Provides these extra features:
     - Handles incorrectly encoded XML
     - Allows stripping namespace information
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    if is_py2 and isinstance(data, unicode):
        data = data.encode("utf8")
    elif is_py3 and isinstance(data, str):
        data = bytes(data, "utf8")
    if ignore_ns:
        data = re.sub(br"\s+xmlns=\"(.+?)\"", b"", data)
    if invalid_char_entities:
        data = re.sub(br"&(?!(?:#(?:[0-9]+|[Xx][0-9A-Fa-f]+)|[A-Za-z0-9]+);)", b"&amp;", data)

    return _parse(XML, data, name, exception, schema, *args, **kwargs)


def parse_qsd(
    data,
    name="query string",
    exception=PluginError,
    schema=None,
    *args, **kwargs
):
    """Parses a query string into a dict.

    Provides these extra features:
     - Unlike parse_qs and parse_qsl, duplicate keys are not preserved in favor of a simpler return value
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    return _parse(lambda d: dict(parse_qsl(d, *args, **kwargs)), data, name, exception, schema)
