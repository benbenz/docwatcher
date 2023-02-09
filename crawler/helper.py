import logging
from functools import lru_cache
from crawler.proxy import ProxyManager
from crawler.core import bcolors , DEFAULT_SLEEP_TIME
import re
import time
import requests
from http import HTTPStatus
from urllib.parse import urlparse,urlunparse
import logging
logger = logging.getLogger("DocCrawler")

pm = ProxyManager()
log = logging.getLogger(__name__)


#
# ACTIVATE HTTP REQUESTS LOGIN
#

# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.

if 0 == 1:

    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1
    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("./requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

#
# (END OF) ACTIVATE HTTP REQUESTS LOGIN
#


def clean_url(url):

    parsed = urlparse(url)

    # add scheme if not available
    if not parsed.scheme:
        parsed = parsed._replace(scheme="http")

        url = urlunparse(parsed)

    # clean text anchor from urls if available
    pattern = r'(.+)(\/#[a-zA-Z0-9]+)$'
    m = re.match(pattern, url)

    if m:
        return m.group(1)
    else:
        # clean trailing slash if available
        pattern = r'(.+)(\/)$'
        m = re.match(pattern, url)

        if m:
            return m.group(1)

    return url


def get_content_type(response):
    if not response or not response.headers:
        return None
    content_type = response.headers.get("content-type")
    if content_type:
        return content_type.split(';')[0]


@lru_cache(maxsize=8192)
def call(session, url, use_proxy=False, retries=0,sleep_time=DEFAULT_SLEEP_TIME):
    if use_proxy:
        proxy = pm.get_proxy()
        if proxy[0]:
            try:
                if sleep_time is not None:
                    time.sleep(sleep_time)
                response = session.get(url, timeout=10, proxies=proxy[0], verify=True)
                response.raise_for_status()
            except Exception as e:
                msg = str(e)
                status_code = e.response.status_code if isinstance(e,requests.exceptions.HTTPError) else None
                if status_code == HTTPStatus.NOT_FOUND:
                    return None , status_code , msg 
                if retries <= 3: 
                    pm.change_proxy(proxy[1])
                    return call(session, url, True, retries + 1)
                else:
                    logger.error("Error fetching url {0}".format(url))
                    return None , status_code , msg
            else:
                return response , response.status_code , None
        else:
            logger.error("Error fetching url. No Proxy available. {0}".format(url))
            return None , None , None
    else:
        try:
            if sleep_time is not None:
                time.sleep(sleep_time)
            response = session.get(url, timeout=10, verify=True)
            response.raise_for_status()
        except requests.exceptions.InvalidSchema as re:
            msg = str(re)
            if url.startswith('tel:') or url.startswith('mailto:'):
                return None , response.status_code if response else None , msg 
            else:
                logger.error(re)
                return None , response.status_code if response else None , msg 
        except Exception as e:
            msg = str(e)
            status_code = e.response.status_code if isinstance(e,requests.exceptions.HTTPError) else None
            if status_code == HTTPStatus.NOT_FOUND: # not found , no need to try proxies
                return None , status_code , msg
            return call(session,url,use_proxy=True)
        else:
            return response , response.status_code if response else None , None


def call_head(session, url, use_proxy=False, retries=0,sleep_time=DEFAULT_SLEEP_TIME):
    if use_proxy:
        proxy = pm.get_proxy()
        if proxy[0]:
            try:
                if sleep_time is not None:
                    time.sleep(sleep_time)
                response = session.head(url, timeout=10, proxies=proxy[0], verify=True)
                response.raise_for_status()
            except Exception as e:
                status_code = e.response.status_code if isinstance(e,requests.exceptions.HTTPError) else None
                if status_code == HTTPStatus.NOT_FOUND:
                    return None
                msg = str(e)
                if retries <= 3:
                    pm.change_proxy(proxy[1])
                    return call_head(session, url, True, retries + 1)
                else:
                    return None
            else:
                return response
        else:
            return None
    else:
        try:
            if sleep_time is not None:
                time.sleep(sleep_time)
            response = session.head(url, timeout=10, verify=True)
            response.raise_for_status()
        except requests.exceptions.InvalidSchema as re:
            msg = str(re)
            if url.startswith('tel:') or url.startswith('mailto:'):
                pass
            else:
                logger.error(re)
            return None
        except Exception as e:
            status_code = e.response.status_code if isinstance(e,requests.exceptions.HTTPError) else None
            if status_code == HTTPStatus.NOT_FOUND:
                return None
            # try with proxy
            return call_head(session,url,use_proxy=True)
        else:
            return response