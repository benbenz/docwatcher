from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import datetime
from crawler.downloaders import get_user_agent
import re
import random

random.seed()

class ProxyManager:

    def __init__(self, requests_limit=10):

        self.last_updated = None
        self.proxies = []
        self.update_interval_min = 10
        self.requests_limit = requests_limit
        self.current_index = 0
        self.requests_counter = 0
        self.blacklisted = []

    def get_list(self,force=False):

        ua = get_user_agent()
        
        # @benbenz
        if not force and len(self.proxies)>0 and random.random()<0.8:
            return

        self.proxies = []
        self.current_index = 0
        self.requests_counter = 0

        proxies_req = Request('https://www.sslproxies.org/')
        proxies_req.add_header('User-Agent', ua)
        proxies_doc = urlopen(proxies_req).read().decode('utf8')

        soup = BeautifulSoup(proxies_doc, 'html.parser')
        proxies_tables = soup.find_all('table')

        if proxies_tables:

            for table in proxies_tables:

                if not table.tbody:
                    continue

                for row in table.tbody.find_all('tr'):

                    tds = row.find_all('td')
                    if not tds or len(tds)<2:
                        continue

                    ip   = tds[0].string
                    port = tds[1].string

                    if re.match(r'[0-9\.]+',ip) and re.match(r'[0-9]+',port):

                        if ip not in self.blacklisted and ip not in [x['ip'] for x in self.proxies]:
                            self.proxies.append({
                                'ip': ip,
                                'port': port,
                            })

        self.last_updated = datetime.datetime.now()

    def change_proxy(self, add_ip_to_blacklist=None):

        if add_ip_to_blacklist is not None:
            self.blacklisted.append(add_ip_to_blacklist)

        self.current_index += 1
        self.requests_counter = 0

        if self.current_index >= len(self.proxies):
            self.get_list(True)

    def get_proxy(self):

        # get proxy list
        if self.last_updated is None or int((datetime.datetime.now() - self.last_updated).total_seconds() / 60) > self.update_interval_min:
            self.get_list()

        if len(self.proxies) == 0:
            return {}, None

        self.requests_counter += 1

        if self.requests_counter > self.requests_limit:
            self.change_proxy()

            if len(self.proxies) == 0:
                return {}, None

        proxy_dict = {
            'http': "http://" + self.proxies[self.current_index]['ip'] + ":" + self.proxies[self.current_index]['port'],
            'https': "http://" + self.proxies[self.current_index]['ip'] + ":" + self.proxies[self.current_index]['port']
        }
        return proxy_dict, self.proxies[self.current_index]['ip']
