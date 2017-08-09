# -*- coding: utf-8 -*-

'''
    Covenant Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''



import re,urllib,urlparse

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import debrid

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['scenedown.in']
        self.base_link = 'http://scenedown.in'
        self.search_link = '/search/%s/feed/rss2/'
        self.search_link_2 = '/?s=%s&submit=Find'


    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urllib.urlencode(url)
            return url
        except:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url == None: return

            url = urlparse.parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urllib.urlencode(url)
            return url
        except:
            return


    def sources(self, url, hostDict, hostprDict):
        try:
            sources = []

            if url == None: return sources

            if debrid.status() == False: raise Exception()

            hostDict = hostprDict + hostDict

            data = urlparse.parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            imdb = data['imdb']

            content = 'episode' if 'tvshowtitle' in data else 'movie'

            query = '%s S%02dE%02d' % (data['tvshowtitle'], int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (data['title'], data['year'])
            query = re.sub('(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)


            try:
                #if feed == True: raise Exception()

                url = self.search_link_2 % urllib.quote_plus(query)
                url = urlparse.urljoin(self.base_link, url)
                myheaders = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0',
                   'Host': 'scenedown.in',
                   'Connection': 'keep-alive',
                   'Accept-Encoding': 'gzip, deflate, sdch'
                }
                r = client.request(url, headers=myheaders)

                posts = client.parseDOM(r, 'div', attrs={'class': 'post'})

                items = [] ; dupes = []

                for post in posts:
                    try:
                        t = client.parseDOM(post, 'a')[0]

                        if content == 'movie':
                            x = re.findall('/(tt\d+)', post)[0]
                            if not x == imdb: raise Exception()
                            q = re.findall('<strong>\s*Video\s*:\s*</strong>.+?\s(\d+)', post)[0]
                            if not int(q) == 1280: raise Exception()
                            if len(dupes) > 3: raise Exception()
                            dupes += [x]

                        elif content == 'episode':
                            x = re.sub('(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d*|3D)(\.|\)|\]|\s|)(.+|)', '', t)
                            if not cleantitle.get(title) in cleantitle.get(x): raise Exception()
                            y = re.findall('[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', t)[-1].upper()
                            if not y == hdlr: raise Exception()
                            if len(dupes) > 0: raise Exception()
                            dupes += [x]

                        u = client.parseDOM(post, 'a', ret='href')[0]
                        myheaders['Referer'] = url
                        r = client.request(u, headers=myheaders).replace('\n', '')

                        u = client.parseDOM(r, 'div', attrs={'class': 'postContent'})[0]
                        u = re.split('id\s*=\s*"more-\d+"', u)[-1]

                        if content == 'episode':
                            u = re.compile('(?:<strong>|)(.+?)</strong>(.+?)(?:<strong>|$)', re.MULTILINE|re.DOTALL).findall(u)
                            u = [(re.sub('<.+?>|</.+?>|>', '', i[0]), i[1]) for i in u]
                            u = [i for i in u if '720p' in i[0].lower()][0]
                            u, r, t = u[1], u[1], u[0]

                        u = client.parseDOM(u, 'p')
                        u = [client.parseDOM(i, 'a', ret='href') for i in u]
                        u = [i[0] for i in u if len(i) == 1]
                        if not u: raise Exception()

                        s = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+) (?:GB|GiB|MB|MiB))', r)
                        s = s[0] if s else '0'

                        items += [(t, i, s) for i in u]
                    except:
                        pass
            except:
                pass


            for item in items:
                try:
                    name = item[0]
                    name = client.replaceHTMLCodes(name)

                    t = re.sub('(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d*|3D)(\.|\)|\]|\s|)(.+|)', '', name)

                    if not cleantitle.get(t) == cleantitle.get(title): raise Exception()

                    y = re.findall('[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', name)[-1].upper()

                    if not y == hdlr: raise Exception()

                    fmt = re.sub('(.+)(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d*)(\.|\)|\]|\s)', '', name.upper())
                    fmt = re.split('\.|\(|\)|\[|\]|\s|\-', fmt)
                    fmt = [i.lower() for i in fmt]

                    if any(i.endswith(('subs', 'sub', 'dubbed', 'dub')) for i in fmt): raise Exception()
                    if any(i in ['extras'] for i in fmt): raise Exception()

                    if '1080p' in fmt: quality = '1080p'
                    elif '720p' in fmt: quality = 'HD'
                    else: quality = 'SD'
                    if any(i in ['dvdscr', 'r5', 'r6'] for i in fmt): quality = 'SCR'
                    elif any(i in ['camrip', 'tsrip', 'hdcam', 'hdts', 'dvdcam', 'dvdts', 'cam', 'telesync', 'ts'] for i in fmt): quality = 'CAM'

                    info = []

                    if '3d' in fmt: info.append('3D')

                    try:
                        size = re.findall('((?:\d+\.\d+|\d+\,\d+|\d+) (?:GB|GiB|MB|MiB))', item[2])[-1]
                        div = 1 if size.endswith(('GB', 'GiB')) else 1024
                        size = float(re.sub('[^0-9|/.|/,]', '', size))/div
                        size = '%.2f GB' % size
                        info.append(size)
                    except:
                        pass

                    if any(i in ['hevc', 'h265', 'x265'] for i in fmt): info.append('HEVC')

                    info = ' | '.join(info)

                    url = item[1]
                    if any(x in url for x in ['.rar', '.zip', '.iso']): raise Exception()
                    url = client.replaceHTMLCodes(url)
                    url = url.encode('utf-8')

                    host = re.findall('([\w]+[.][\w]+)$', urlparse.urlparse(url.strip().lower()).netloc)[0]
                    if not host in hostDict: raise Exception()
                    host = client.replaceHTMLCodes(host)
                    host = host.encode('utf-8')

                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True})
                except:
                    pass

            check = [i for i in sources if not i['quality'] == 'CAM']
            if check: sources = check

            return sources
        except:
            return sources


    def resolve(self, url):
        return url
