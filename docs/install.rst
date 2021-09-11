.. |br| raw:: html

  <br />

Installation
============

==================================== ===========================================
Version                              Installing
==================================== ===========================================
`Latest release(pip)`_               .. code-block:: bash

                                        # Current user
                                        pip install --upgrade --user git+https://github.com/Billy2011/streamlink-27/tree/release-1.27.0.0.git

                                        # System wide
                                        sudo pip install --upgrade git+https://github.com/Billy2011/streamlink-27/tree/release-1.27.0.0.git

`Latest release(git)`_               .. code-block:: bash

                                        # Current user
                                        git clone https://github.com/Billy2011/streamlink-27/tree/release-1.27.0.0.git
                                        cd streamlink
                                        python setup.py install --user

                                        # System wide
                                        git clone https://github.com/Billy2011/streamlink-27/tree/release-1.27.0.0.git
                                        cd streamlink
                                        sudo python setup.py install
==================================== ===========================================

.. _git: https://git-scm.com/
.. _Latest release(pip): https://github.com/Billy2011/streamlink-27/tree/release-1.27.0.0
.. _Latest release(git): https://github.com/Billy2011/streamlink-27/tree/release-1.27.0.0

Virtual environment
^^^^^^^^^^^^^^^^^^^

Another method of installing Streamlink in a non-system-wide way is
using `virtualenv`_, which creates a user owned Python environment instead.

.. code-block:: bash

    # Create a new environment
    virtualenv ~/myenv

    # Activate the environment
    source ~/myenv/bin/activate

    # Install Streamlink in the environment
    pip install --upgrade streamlink

    # Use Streamlink in the environment
    streamlink ...

    # Deactivate the environment
    deactivate

    # Use Streamlink without activating the environment
    ~/myenv/bin/streamlink ...

.. note::

    This may also be required on some macOS versions that seem to have weird
    permission issues.

.. _virtualenv: https://virtualenv.readthedocs.io/en/latest/

Dependencies
^^^^^^^^^^^^

To install Streamlink from source you will need these dependencies.

.. rst-class:: table-custom-layout

==================================== ===========================================
Name                                 Notes
==================================== ===========================================
`Python`_                            At least version **2.7** or **3.6**.
`python-setuptools`_

**Automatically installed by the setup script**
--------------------------------------------------------------------------------
`python-futures`_                    Only needed on Python **2.7**.
`python-requests`_                   At least version **2.26.0**
`python-singledispatch`_             Only needed on Python **2.7**.
`pycryptodome`_                      Required to play some encrypted streams
`iso-639`_                           Used for localization settings, provides language information
`iso3166`_                           Used for localization settings, provides country information
`isodate`_                           Used for MPEG-DASH streams
`lxml`_                              Used for processing HTML and XML data
`PySocks`_                           Used for SOCKS Proxies
`websocket-client`_                  At least version **0.58.0**. (used for some plugins)
`shutil_get_terminal_size`_          Only needed on Python **2.7**.
`shutil_which`_                      Only needed on Python **2.7**.

**Optional**
--------------------------------------------------------------------------------
`RTMPDump`_                          Required to play RTMP streams.
`ffmpeg`_                            Required to play streams that are made up of separate
                                     audio and video streams, eg. YouTube 1080p+
==================================== ===========================================

Using pycrypto and pycountry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With these two environment variables it is possible to use `pycrypto`_ instead of
`pycryptodome`_ and `pycountry`_ instead of `iso-639`_ and `iso3166`_.

.. code-block:: console

    $ export STREAMLINK_USE_PYCRYPTO="true"
    $ export STREAMLINK_USE_PYCOUNTRY="true"

.. _Python: https://www.python.org/
.. _python-setuptools: https://pypi.org/project/setuptools/
.. _python-futures: https://pypi.org/project/futures/
.. _python-singledispatch: https://pypi.org/project/singledispatch/
.. _python-requests: https://docs.python-requests.org/en/master/
.. _RTMPDump: https://rtmpdump.mplayerhq.hu/
.. _pycountry: https://pypi.org/project/pycountry/
.. _pycrypto: https://www.dlitz.net/software/pycrypto/
.. _pycryptodome: https://pycryptodome.readthedocs.io/en/latest/
.. _ffmpeg: https://www.ffmpeg.org/
.. _iso-639: https://pypi.org/project/iso-639/
.. _iso3166: https://pypi.org/project/iso3166/
.. _isodate: https://pypi.org/project/isodate/
.. _lxml: https://lxml.de/
.. _PySocks: https://github.com/Anorov/PySocks
.. _websocket-client: https://pypi.org/project/websocket-client/
.. _shutil_get_terminal_size: https://pypi.org/project/backports.shutil_get_terminal_size/
.. _shutil_which: https://pypi.org/project/backports.shutil_which/
.. _#3880: https://github.com/streamlink/streamlink/pull/3880

.. _Development build:
.. _build artifacts: https://github.com/Billy2011/streamlink-27/actions?query=event%3Aschedule+is%3Asuccess+branch%3Amaster
.. _commit log: https://github.com/Billy2011/streamlink-27/commits/master
