# -*- coding: utf-8 -*-
import urllib
import urllib2
import re
import os
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs
import traceback
import cookielib,base64
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, BeautifulSOAP
viewmode=None
try:
    from xml.sax.saxutils import escape
except: traceback.print_exc()
try:
    import json
except:
    import simplejson as json
import SimpleDownloader as downloader
import time
tsdownloader=False
hlsretry=False
resolve_url=[]
g_ignoreSetResolved=[]

class NoRedirection(urllib2.HTTPErrorProcessor):
   def http_response(self, request, response):
       return response
   https_response = http_response

REMOTE_DBG=False;
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:
        import pysrc.pydevd as pydevd
    # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
    except ImportError:
        sys.stderr.write("Error: " +
            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
        sys.exit(1)


addon = xbmcaddon.Addon('plugin.video.documented.hd')
addondir = xbmc.translatePath(addon.getAddonInfo('profile') )
addon_version = addon.getAddonInfo('version')
profile = xbmc.translatePath(addon.getAddonInfo('profile').decode('utf-8'))
home = xbmc.translatePath(addon.getAddonInfo('path').decode('utf-8'))
favorites = os.path.join(profile, 'favorites')
history = os.path.join(profile, 'history')
REV = os.path.join(profile, 'list_revision')
icon = os.path.join(home, 'icon.png')
FANART = os.path.join(home, 'fanart.gif')
source_file = os.path.join(profile, 'source_file')
functions_dir = profile

communityfiles = os.path.join(profile, 'LivewebTV')
downloader = downloader.SimpleDownloader()
debug = addon.getSetting('debug')
if os.path.exists(favorites)==True:
    FAV = open(favorites).read()
else: FAV = []
if os.path.exists(source_file)==True:
    SOURCES = open(source_file).read()
else: SOURCES = []


def addon_log(string):
    if debug == 'true':
        xbmc.log("[addon.documented.hd-%s]: %s" %(addon_version, string))

def makeRequest(url, headers=None):
        try:
            if headers is None:
                headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 537.40'}
                
            if '|' in url:
                url,header_in_page=url.split('|')
                header_in_page=header_in_page.split('&')
                
                for h in header_in_page:
                    if len(h.split('='))==2:
                        n,v=h.split('=')
                    else:
                        vals=h.split('=')
                        n=vals[0]
                        v='='.join(vals[1:])
                        #n,v=h.split('=')
                    print n,v
                    headers[n]=v
                    
            req = urllib2.Request(url,None,headers)
            response = urllib2.urlopen(req)
            data = response.read()
            response.close()
            return data
        except urllib2.URLError, e:
            addon_log('URL: '+url)
            if hasattr(e, 'code'):
                addon_log('We failed with error code - %s.' % e.code)
                xbmc.executebuiltin("XBMC.Notification(documented.hd,We failed with error code - "+str(e.code)+",10000,"+icon+")")
            elif hasattr(e, 'reason'):
                addon_log('We failed to reach a server.')
                addon_log('Reason: %s' %e.reason)
                xbmc.executebuiltin("XBMC.Notification(documented.hd,We failed to reach a server. - "+str(e.reason)+",10000,"+icon+")")

def getSources():
        try:
            if os.path.exists(favorites) == True:
                addDir('',4,'' , os.path.join(home, 'fanart.gif'),FANART,'','','','')
            if addon.getSetting("browse_xml_database") == "true":
                addDir('XML Database','http://xbmcplus.xb.funpic.de/www-data/filesystem/',15,icon,FANART,'','','','')
            if addon.getSetting("browse_community") == "true":
                addDir('Community Files','community_files',16,icon,FANART,'','','','')
            if addon.getSetting("searchotherplugins") == "true":
                addDir('Search Other Plugins','Search Plugins',25,icon,FANART,'','','','')
            if os.path.exists(ab)==True:
                ba = json.loads(open(ab,"r").read().decode('base64').decode('base64'))
                #print 'ba',ba
                if len(ba) > 1:
                    for i in ba:
                        try:
                            ## for pre 1.0.8 ba
                            if isinstance(i, list):
                                addDir(i[0].encode('utf-8'),i[1].encode('utf-8'),1,icon,FANART,'','','','','source')
                            else:
                                thumb = icon
                                fanart = FANART
                                desc = ''
                                date = ''
                                credits = ''
                                genre = ''
                                if i.has_key('thumbnail'):
                                    thumb = i['thumbnail']
                                if i.has_key('fanart'):
                                    fanart = i['fanart']
                                if i.has_key('description'):
                                    desc = i['description']
                                if i.has_key('date'):
                                    date = i['date']
                                if i.has_key('genre'):
                                    genre = i['genre']
                                if i.has_key('credits'):
                                    credits = i['credits']
                                addDir(i['title'].encode('utf-8'),i['url'].encode('utf-8'),1,thumb,fanart,desc,genre,date,credits,'source')
                        except: traceback.print_exc()
                else:
                    if len(ba) == 1:
                        if isinstance(ba[0], list):
                            getData(ba[0][1].encode('utf-8'),FANART)
                        else:
                            getData(ba[0]['url'], ba[0]['fanart'])
        except: traceback.print_exc()

def getSoup(url,data=None):
        global viewmode,tsdownloader, hlsretry
        tsdownloader=False
        hlsretry=False
        if url.startswith('http://') or url.startswith('https://'):
            enckey=False
            if '$$TSDOWNLOADER$$' in url:
                tsdownloader=True
                url=url.replace("$$TSDOWNLOADER$$","")
            if '$$HLSRETRY$$' in url:
                hlsretry=True
                url=url.replace("$$HLSRETRY$$","")
            if '$$LSProEncKey=' in url:
                enckey=url.split('$$LSProEncKey=')[1].split('$$')[0]
                rp='$$LSProEncKey=%s$$'%enckey
                url=url.replace(rp,"")
                
            data =makeRequest(url)
            if enckey:
                    import pyaes
                    enckey=enckey.encode("ascii")
                    print enckey
                    missingbytes=16-len(enckey)
                    enckey=enckey+(chr(0)*(missingbytes))
                    print repr(enckey)
                    data=base64.b64decode(data)
                    decryptor = pyaes.new(enckey , pyaes.MODE_ECB, IV=None)
                    data=decryptor.decrypt(data).split('\0')[0]
                    #print repr(data)
            if re.search("#EXTM3U",data) or 'm3u' in url:
#                print 'found m3u data'
                return data
        elif data == None:
            if not '/'  in url or not '\\' in url:
#                print 'No directory found. Lets make the url to cache dir'
                url = os.path.join(communityfiles,url)
            if xbmcvfs.exists(url):
                if url.startswith("smb://") or url.startswith("nfs://"):
                    copy = xbmcvfs.copy(url, os.path.join(profile, 'temp', 'sorce_temp.txt'))
                    if copy:
                        data = open(os.path.join(profile, 'temp', 'sorce_temp.txt'), "r").read()
                        xbmcvfs.delete(os.path.join(profile, 'temp', 'sorce_temp.txt'))
                    else:
                        addon_log("failed to copy from smb:")
                else:
                    data = open(url, 'r').read()
                    if re.match("#EXTM3U",data)or 'm3u' in url:
#                        print 'found m3u data'
                        return data
            else:
                addon_log("Soup Data not found!")
                return
        if '<SetViewMode>' in data:
            try:
                viewmode=re.findall('<SetViewMode>(.*?)<',data)[0]
                xbmc.executebuiltin("Container.SetViewMode(%s)"%viewmode)
                print 'done setview',viewmode
            except: pass
        return BeautifulSOAP(data, convertEntities=BeautifulStoneSoup.XML_ENTITIES)

def processPyFunction(data):
    try:
        if data and len(data)>0 and data.startswith('$pyFunction:'):
            data=doEval(data.split('$pyFunction:')[1],'',None,None )
    except: pass

    return data

def getData(url,icon, data=None):
    os.path.join(home, 'resources', 'fanart.gif')
    import checkbad
    checkbad.do_block_check(False)
    soup = getSoup(url,data)
    #print type(soup)
    if isinstance(soup,BeautifulSOAP):
    #print 'xxxxxxxxxxsoup',soup
    
        if len(soup('search')) > 0:
            search = soup('search')
            for sear in search:

                linkedUrl =  sear('externallink')[0].string

                name = sear('name')[0].string
                try:
                    name=processPyFunction(name)
                except: pass                
                thumbnail = sear('thumbnail')[0].string
                if thumbnail == None:
                    thumbnail = ''
                thumbnail=processPyFunction(thumbnail)
                try:
                    if not sear('fanart'):
                        if addon.getSetting('use_thumb') == "true":
                            fanArt = thumbnail
                        else:
                            fanArt = fanart
                    else:
                        fanArt = sear('fanart')[0].string
                    if fanArt == None:
                        raise
                except:
                    fanArt = fanart

                try:
                    addDir(name.encode('utf-8'),linkedUrl.encode('utf-8'),54,thumbnail,fanArt,'','','',None,'source')
                except:
                    addon_log('There was a problem adding directory from getData(): '+name.encode('utf-8', 'ignore'))
        else:
            addon_log('No Search: getItems')

        if len(soup('channels')) > 0 and addon.getSetting('donotshowbychannels') == 'false':
            channels = soup('channel')
            for channel in channels:
#                print channel

                linkedUrl=''
                lcount=0
                try:
                    linkedUrl =  channel('externallink')[0].string
                    lcount=len(channel('externallink'))
                except: pass
                #print 'linkedUrl',linkedUrl,lcount
                if lcount>1: linkedUrl=''

                name = channel('name')[0].string
                try:
                    name=processPyFunction(name)
                except: pass                
                thumbnail = channel('thumbnail')[0].string
                if thumbnail == None:
                    thumbnail = ''
                thumbnail=processPyFunction(thumbnail)
                try:
                    if not channel('fanart'):
                        if addon.getSetting('use_thumb') == "true":
                            fanArt = thumbnail
                        else:
                            fanArt = fanart
                    else:
                        fanArt = channel('fanart')[0].string
                    if fanArt == None:
                        raise
                except:
                    fanArt = fanart

                try:
                    desc = channel('info')[0].string
                    if desc == None:
                        raise
                except:
                    desc = ''

                try:
                    genre = channel('genre')[0].string
                    if genre == None:
                        raise
                except:
                    genre = ''

                try:
                    date = channel('date')[0].string
                    if date == None:
                        raise
                except:
                    date = ''

                try:
                    credits = channel('credits')[0].string
                    if credits == None:
                        raise
                except:
                    credits = ''

                try:
                    if linkedUrl=='':
                        addDir(name.encode('utf-8', 'ignore'),url.encode('utf-8'),2,thumbnail,fanArt,desc,genre,date,credits,True)
                    else:
                        #print linkedUrl
                        addDir(name.encode('utf-8'),linkedUrl.encode('utf-8'),1,thumbnail,fanArt,desc,genre,date,None,'source')
                except:
                    addon_log('There was a problem adding directory from getData(): '+name.encode('utf-8', 'ignore'))
        else:
            addon_log('No Channels: getItems')
            getItems(soup('item'),fanart)
    else:
        parse_m3u(soup)
        
def getSearchData(url,icon, data=None):

    keyboard = xbmc.Keyboard()
    keyboard.setHeading("Documented.HD Search")
    keyboard.setDefault('')
    keyboard.doModal()
    if keyboard.isConfirmed():
        term =  keyboard.getText()
        term = term.replace(' ','').lower()
    else:
        xbmcgui.Dialog().ok('Documented.HD', 'Blank Searches are not allowed.')
        quit()
    fanart=''
    dontLink=False
    os.path.join(home, 'resources', 'fanart.gif')
    import checkbad
    checkbad.do_block_check(False)
    soup = getSoup(url,data)
    #print type(soup)
    if isinstance(soup,BeautifulSOAP):
    #print 'xxxxxxxxxxsoup',soup
    
        if len(soup('link')) > 0:
            main_item = soup('item')
            
            for ite in main_item:
                sear = ite('link')[0].string
                soup = getSoup(sear,data)
                items = soup('item')        
                total = len(items)
                
                add_playlist = addon.getSetting('add_playlist')
                ask_playlist_items =addon.getSetting('ask_playlist_items')
                use_thumb = addon.getSetting('use_thumb')
                parentalblock =addon.getSetting('parentalblocked')
                parentalblock= parentalblock=="true"
                for item in items:
                    try:

                        isXMLSource=False
                        isJsonrpc = False
                        
                        applyblock='false'
                        try:
                            applyblock = item('parentalblock')[0].string
                        except:
                            addon_log('parentalblock Error')
                            applyblock = ''
                        if applyblock=='true' and parentalblock: continue
                            
                        try:
                            name = item('title')[0].string
                            if name is None:
                                name = 'unknown?'
                            try:
                                name=processPyFunction(name)
                            except: pass
                            
                        except:
                            addon_log('Name Error')
                            name = ''

                        check_name = re.sub('\[.+?\]','',name)
                        if term in check_name.replace(' ','').lower():

                            try:
                                if item('epg'):
                                    if item.epg_url:
                                        addon_log('Get EPG Regex')
                                        epg_url = item.epg_url.string
                                        epg_regex = item.epg_regex.string
                                        epg_name = get_epg(epg_url, epg_regex)
                                        if epg_name:
                                            name += ' - ' + epg_name
                                    elif item('epg')[0].string > 1:
                                        name += getepg(item('epg')[0].string)
                                else:
                                    pass
                            except:
                                addon_log('EPG Error')
                            url = []
                            if len(item('link')) >0:
                                #print 'item link', item('link')

                                for i in item('link'):
                                    if not i.string == None:
                                        url.append(i.string)

                            elif len(item('utube')) >0:
                                for i in item('utube'):
                                    if not i.string == None:
                                        if ' ' in i.string :
                                            utube = 'plugin://plugin.video.youtube/search/?q='+ urllib.quote_plus(i.string)
                                            isJsonrpc=utube
                                        elif len(i.string) == 11:
                                            utube = 'plugin://plugin.video.youtube/play/?video_id='+ i.string
                                        elif (i.string.startswith('PL') and not '&order=' in i.string) or i.string.startswith('UU'):
                                            utube = 'plugin://plugin.video.youtube/play/?&order=default&playlist_id=' + i.string
                                        elif i.string.startswith('PL') or i.string.startswith('UU'):
                                            utube = 'plugin://plugin.video.youtube/play/?playlist_id=' + i.string
                                        elif i.string.startswith('UC') and len(i.string) > 12:
                                            utube = 'plugin://plugin.video.youtube/channel/' + i.string + '/'
                                            isJsonrpc=utube
                                        elif not i.string.startswith('UC') and not (i.string.startswith('PL'))  :
                                            utube = 'plugin://plugin.video.youtube/user/' + i.string + '/'
                                            isJsonrpc=utube
                                    url.append(utube)
                        

                            elif len(item('urlsolve')) >0:
                               
                                for i in item('urlsolve'):
                                    if not i.string == None:
                                        resolver = i.string +'&mode=19'
                                        url.append(resolver)
                            if len(url) < 1:
                                raise

                            try:
                                isXMLSource = item('externallink')[0].string
                            except: pass

                            if isXMLSource:
                                ext_url=[isXMLSource]
                                isXMLSource=True
                            else:
                                isXMLSource=False
                            try:
                                isJsonrpc = item('jsonrpc')[0].string
                            except: pass
                            if isJsonrpc:
                                ext_url=[isJsonrpc]
                                isJsonrpc=True
                            else:
                                isJsonrpc=False
                            try:
                                thumbnail = item('thumbnail')[0].string
                                if thumbnail == None:
                                    raise
                                thumbnail=processPyFunction(thumbnail)
                            except:
                                thumbnail = ''
                            try:
                                if not item('fanart'):
                                    if addon.getSetting('use_thumb') == "true":
                                        fanArt = thumbnail
                                    else:
                                        fanArt = fanart
                                else:
                                    fanArt = item('fanart')[0].string
                                if fanArt == None:
                                    raise
                            except:
                                fanArt = fanart
                            try:
                                desc = item('info')[0].string
                                if desc == None:
                                    raise
                            except:
                                desc = ''

                            try:
                                genre = item('genre')[0].string
                                if genre == None:
                                    raise
                            except:
                                genre = ''

                            try:
                                date = item('date')[0].string
                                if date == None:
                                    raise
                            except:
                                date = ''

                            regexs = None
                            if item('regex'):
                                try:
                                    reg_item = item('regex')
                                    regexs = parse_regex(reg_item)
                                except:
                                    pass
                                
                            if len(url) > 1:
                                alt = 0
                                playlist = []
                                ignorelistsetting=True if '$$LSPlayOnlyOne$$' in url[0] else False
                                
                                for i in url:
                                    if  add_playlist == "false" and not ignorelistsetting:
                                        alt += 1
                                        addLink(i,'%s) %s' %(alt, name.encode('utf-8', 'ignore')),thumbnail,fanArt,desc,genre,date,True,playlist,regexs,total)
                                    elif  (add_playlist == "true" and  ask_playlist_items == 'true') or ignorelistsetting:
                                        if regexs:
                                            playlist.append(i+'&regexs='+regexs)
                                        elif  any(x in i for x in resolve_url) and  i.startswith('http'):
                                            playlist.append(i+'&mode=19')
                                        else:
                                            playlist.append(i)
                                    else:
                                        playlist.append(i)
                                
                                if len(playlist) > 1:       
                                    addLink('', name.encode('utf-8'),thumbnail,fanArt,desc,genre,date,True,playlist,regexs,total)
                            else:
                                
                                if dontLink:
                                    return name,url[0],regexs
                                if isXMLSource:
                                        if not regexs == None: #<externallink> and <regex>
                                            addDir(name.encode('utf-8'),ext_url[0].encode('utf-8'),1,thumbnail,fanArt,desc,genre,date,None,'!!update',regexs,url[0].encode('utf-8'))
                                        else:
                                            addDir(name.encode('utf-8'),ext_url[0].encode('utf-8'),1,thumbnail,fanArt,desc,genre,date,None,'source',None,None)
                                elif isJsonrpc:
                                    addDir(name.encode('utf-8'),ext_url[0],53,thumbnail,fanArt,desc,genre,date,None,'source')
                                else:                    
                                    addLink(url[0],name.encode('utf-8', 'ignore'),thumbnail,fanArt,desc,genre,date,True,None,regexs,total)
                    except: pass
            
def getItems(items,fanart,dontLink=False):
        total = len(items)
        addon_log('Total Items: %s' %total)
        add_playlist = addon.getSetting('add_playlist')
        ask_playlist_items =addon.getSetting('ask_playlist_items')
        use_thumb = addon.getSetting('use_thumb')
        parentalblock =addon.getSetting('parentalblocked')
        parentalblock= parentalblock=="true"
        for item in items:
            isXMLSource=False
            isJsonrpc = False
            
            applyblock='false'
            try:
                applyblock = item('parentalblock')[0].string
            except:
                addon_log('parentalblock Error')
                applyblock = ''
            if applyblock=='true' and parentalblock: continue
                
            try:
                name = item('title')[0].string
                if name is None:
                    name = 'unknown?'
                try:
                    name=processPyFunction(name)
                except: pass
                
            except:
                addon_log('Name Error')
                name = ''


            try:
                if item('epg'):
                    if item.epg_url:
                        addon_log('Get EPG Regex')
                        epg_url = item.epg_url.string
                        epg_regex = item.epg_regex.string
                        epg_name = get_epg(epg_url, epg_regex)
                        if epg_name:
                            name += ' - ' + epg_name
                    elif item('epg')[0].string > 1:
                        name += getepg(item('epg')[0].string)
                else:
                    pass
            except:
                addon_log('EPG Error')
            try:
                url = []
                if len(item('link')) >0:
                    #print 'item link', item('link')

                    for i in item('link'):
                        if not i.string == None:
                            url.append(i.string)

                elif len(item('utube')) >0:
                    for i in item('utube'):
                        if not i.string == None:
                            if ' ' in i.string :
                                utube = 'plugin://plugin.video.youtube/search/?q='+ urllib.quote_plus(i.string)
                                isJsonrpc=utube
                            elif len(i.string) == 11:
                                utube = 'plugin://plugin.video.youtube/play/?video_id='+ i.string
                            elif (i.string.startswith('PL') and not '&order=' in i.string) or i.string.startswith('UU'):
                                utube = 'plugin://plugin.video.youtube/play/?&order=default&playlist_id=' + i.string
                            elif i.string.startswith('PL') or i.string.startswith('UU'):
                                utube = 'plugin://plugin.video.youtube/play/?playlist_id=' + i.string
                            elif i.string.startswith('UC') and len(i.string) > 12:
                                utube = 'plugin://plugin.video.youtube/channel/' + i.string + '/'
                                isJsonrpc=utube
                            elif not i.string.startswith('UC') and not (i.string.startswith('PL'))  :
                                utube = 'plugin://plugin.video.youtube/user/' + i.string + '/'
                                isJsonrpc=utube
                        url.append(utube)
            

                elif len(item('urlsolve')) >0:
                   
                    for i in item('urlsolve'):
                        if not i.string == None:
                            resolver = i.string +'&mode=19'
                            url.append(resolver)
                if len(url) < 1:
                    raise
            except:
                addon_log('Error <link> element, Passing:'+name.encode('utf-8', 'ignore'))
                continue
            try:
                isXMLSource = item('externallink')[0].string
            except: pass

            if isXMLSource:
                ext_url=[isXMLSource]
                isXMLSource=True
            else:
                isXMLSource=False
            try:
                isJsonrpc = item('jsonrpc')[0].string
            except: pass
            if isJsonrpc:

                ext_url=[isJsonrpc]
                #print 'JSON-RPC ext_url',ext_url
                isJsonrpc=True
            else:
                isJsonrpc=False
            try:
                thumbnail = item('thumbnail')[0].string
                if thumbnail == None:
                    raise
                thumbnail=processPyFunction(thumbnail)
            except:
                thumbnail = ''
            try:
                if not item('fanart'):
                    if addon.getSetting('use_thumb') == "true":
                        fanArt = thumbnail
                    else:
                        fanArt = fanart
                else:
                    fanArt = item('fanart')[0].string
                if fanArt == None:
                    raise
            except:
                fanArt = fanart
            try:
                desc = item('info')[0].string
                if desc == None:
                    raise
            except:
                desc = ''

            try:
                genre = item('genre')[0].string
                if genre == None:
                    raise
            except:
                genre = ''

            try:
                date = item('date')[0].string
                if date == None:
                    raise
            except:
                date = ''

            regexs = None
            if item('regex'):
                try:
                    reg_item = item('regex')
                    regexs = parse_regex(reg_item)
                except:
                    pass
            try:
                
                if len(url) > 1:
                    alt = 0
                    playlist = []
                    ignorelistsetting=True if '$$LSPlayOnlyOne$$' in url[0] else False
                    
                    for i in url:
                            if  add_playlist == "false" and not ignorelistsetting:
                                alt += 1
                                addLink(i,'%s) %s' %(alt, name.encode('utf-8', 'ignore')),thumbnail,fanArt,desc,genre,date,True,playlist,regexs,total)
                            elif  (add_playlist == "true" and  ask_playlist_items == 'true') or ignorelistsetting:
                                if regexs:
                                    playlist.append(i+'&regexs='+regexs)
                                elif  any(x in i for x in resolve_url) and  i.startswith('http'):
                                    playlist.append(i+'&mode=19')
                                else:
                                    playlist.append(i)
                            else:
                                playlist.append(i)
                    
                    if len(playlist) > 1:
                        
                        addLink('', name.encode('utf-8'),thumbnail,fanArt,desc,genre,date,True,playlist,regexs,total)
                else:
                    
                    if dontLink:
                        return name,url[0],regexs
                    if isXMLSource:
                            if not regexs == None: #<externallink> and <regex>
                                addDir(name.encode('utf-8'),ext_url[0].encode('utf-8'),1,thumbnail,fanArt,desc,genre,date,None,'!!update',regexs,url[0].encode('utf-8'))
                                #addLink(url[0],name.encode('utf-8', 'ignore')+  '[COLOR yellow]build XML[/COLOR]',thumbnail,fanArt,desc,genre,date,True,None,regexs,total)
                            else:
                                addDir(name.encode('utf-8'),ext_url[0].encode('utf-8'),1,thumbnail,fanArt,desc,genre,date,None,'source',None,None)
                                #addDir(name.encode('utf-8'),url[0].encode('utf-8'),1,thumbnail,fanart,desc,genre,date,None,'source')
                    elif isJsonrpc:
                        addDir(name.encode('utf-8'),ext_url[0],53,thumbnail,fanArt,desc,genre,date,None,'source')
                        #xbmc.executebuiltin("Container.SetViewMode(500)")
                    else:
                        
                        addLink(url[0],name.encode('utf-8', 'ignore'),thumbnail,fanArt,desc,genre,date,True,None,regexs,total)
                    #print 'success'
            except:
                addon_log('There was a problem adding item - '+name.encode('utf-8', 'ignore'))

def parse_regex(reg_item):
                try:
                    regexs = {}
                    for i in reg_item:
                        regexs[i('name')[0].string] = {}
                        regexs[i('name')[0].string]['name']=i('name')[0].string
                        #regexs[i('name')[0].string]['expres'] = i('expres')[0].string
                        try:
                            regexs[i('name')[0].string]['expres'] = i('expres')[0].string
                            if not regexs[i('name')[0].string]['expres']:
                                regexs[i('name')[0].string]['expres']=''
                        except:
                            addon_log("Regex: -- No Referer --")
                        regexs[i('name')[0].string]['page'] = i('page')[0].string
                        try:
                            regexs[i('name')[0].string]['referer'] = i('referer')[0].string
                        except:
                            addon_log("Regex: -- No Referer --")
                        try:
                            regexs[i('name')[0].string]['connection'] = i('connection')[0].string
                        except:
                            addon_log("Regex: -- No connection --")

                        try:
                            regexs[i('name')[0].string]['notplayable'] = i('notplayable')[0].string
                        except:
                            addon_log("Regex: -- No notplayable --")

                        try:
                            regexs[i('name')[0].string]['noredirect'] = i('noredirect')[0].string
                        except:
                            addon_log("Regex: -- No noredirect --")
                        try:
                            regexs[i('name')[0].string]['origin'] = i('origin')[0].string
                        except:
                            addon_log("Regex: -- No origin --")
                        try:
                            regexs[i('name')[0].string]['accept'] = i('accept')[0].string
                        except:
                            addon_log("Regex: -- No accept --")
                        try:
                            regexs[i('name')[0].string]['includeheaders'] = i('includeheaders')[0].string
                        except:
                            addon_log("Regex: -- No includeheaders --")

                            
                        try:
                            regexs[i('name')[0].string]['listrepeat'] = i('listrepeat')[0].string
#                            print 'listrepeat',regexs[i('name')[0].string]['listrepeat'],i('listrepeat')[0].string, i
                        except:
                            addon_log("Regex: -- No listrepeat --")
                    
                            

                        try:
                            regexs[i('name')[0].string]['proxy'] = i('proxy')[0].string
                        except:
                            addon_log("Regex: -- No proxy --")
                            
                        try:
                            regexs[i('name')[0].string]['x-req'] = i('x-req')[0].string
                        except:
                            addon_log("Regex: -- No x-req --")

                        try:
                            regexs[i('name')[0].string]['x-addr'] = i('x-addr')[0].string
                        except:
                            addon_log("Regex: -- No x-addr --")                            
                            
                        try:
                            regexs[i('name')[0].string]['x-forward'] = i('x-forward')[0].string
                        except:
                            addon_log("Regex: -- No x-forward --")

                        try:
                            regexs[i('name')[0].string]['agent'] = i('agent')[0].string
                        except:
                            addon_log("Regex: -- No User Agent --")
                        try:
                            regexs[i('name')[0].string]['post'] = i('post')[0].string
                        except:
                            addon_log("Regex: -- Not a post")
                        try:
                            regexs[i('name')[0].string]['rawpost'] = i('rawpost')[0].string
                        except:
                            addon_log("Regex: -- Not a rawpost")
                        try:
                            regexs[i('name')[0].string]['htmlunescape'] = i('htmlunescape')[0].string
                        except:
                            addon_log("Regex: -- Not a htmlunescape")


                        try:
                            regexs[i('name')[0].string]['readcookieonly'] = i('readcookieonly')[0].string
                        except:
                            addon_log("Regex: -- Not a readCookieOnly")
                        #print i
                        try:
                            regexs[i('name')[0].string]['cookiejar'] = i('cookiejar')[0].string
                            if not regexs[i('name')[0].string]['cookiejar']:
                                regexs[i('name')[0].string]['cookiejar']=''
                        except:
                            addon_log("Regex: -- Not a cookieJar")
                        try:
                            regexs[i('name')[0].string]['setcookie'] = i('setcookie')[0].string
                        except:
                            addon_log("Regex: -- Not a setcookie")
                        try:
                            regexs[i('name')[0].string]['appendcookie'] = i('appendcookie')[0].string
                        except:
                            addon_log("Regex: -- Not a appendcookie")

                        try:
                            regexs[i('name')[0].string]['ignorecache'] = i('ignorecache')[0].string
                        except:
                            addon_log("Regex: -- no ignorecache")
                        #try:
                        #    regexs[i('name')[0].string]['ignorecache'] = i('ignorecache')[0].string
                        #except:
                        #    addon_log("Regex: -- no ignorecache")

                    regexs = urllib.quote(repr(regexs))
                    return regexs
                    #print regexs
                except:
                    regexs = None
                    addon_log('regex Error: '+name.encode('utf-8', 'ignore'))


def getRegexParsed(regexs, url,cookieJar=None,forCookieJarOnly=False,recursiveCall=False,cachedPages={}, rawPost=False, cookie_jar_file=None):#0,1,2 = URL, regexOnly, CookieJarOnly
        if not recursiveCall:
            regexs = eval(urllib.unquote(regexs))
        #cachedPages = {}
        #print 'url',url
        doRegexs = re.compile('\$doregex\[([^\]]*)\]').findall(url)
#        print 'doRegexs',doRegexs,regexs
        setresolved=True
        for k in doRegexs:
            if k in regexs:
                #print 'processing ' ,k
                m = regexs[k]
                #print m
                cookieJarParam=False
                if  'cookiejar' in m: # so either create or reuse existing jar
                    #print 'cookiejar exists',m['cookiejar']
                    cookieJarParam=m['cookiejar']
                    if  '$doregex' in cookieJarParam:
                        cookieJar=getRegexParsed(regexs, m['cookiejar'],cookieJar,True, True,cachedPages)
                        
                        cookieJarParam=True
                    else:
                        cookieJarParam=True
                #print 'm[cookiejar]',m['cookiejar'],cookieJar
                if cookieJarParam:
                    if cookieJar==None:
                        #print 'create cookie jar'
                        cookie_jar_file=None
                        if 'open[' in m['cookiejar']:
                            cookie_jar_file=m['cookiejar'].split('open[')[1].split(']')[0]
#                            print 'cookieJar from file name',cookie_jar_file

                        cookieJar=getCookieJar(cookie_jar_file)
#                        print 'cookieJar from file',cookieJar
                        if cookie_jar_file:
                            saveCookieJar(cookieJar,cookie_jar_file)
                        #import cookielib
                        #cookieJar = cookielib.LWPCookieJar()
                        #print 'cookieJar new',cookieJar
                    elif 'save[' in m['cookiejar']:
                        cookie_jar_file=m['cookiejar'].split('save[')[1].split(']')[0]
                        complete_path=os.path.join(profile,cookie_jar_file)
#                        print 'complete_path',complete_path
                        saveCookieJar(cookieJar,cookie_jar_file)
                if  m['page'] and '$doregex' in m['page']:
                    pg=getRegexParsed(regexs, m['page'],cookieJar,recursiveCall=True,cachedPages=cachedPages)
                    if len(pg)==0:
                        pg='http://regexfailed'
                    m['page']=pg

                if 'setcookie' in m and m['setcookie'] and '$doregex' in m['setcookie']:
                    m['setcookie']=getRegexParsed(regexs, m['setcookie'],cookieJar,recursiveCall=True,cachedPages=cachedPages)
                if 'appendcookie' in m and m['appendcookie'] and '$doregex' in m['appendcookie']:
                    m['appendcookie']=getRegexParsed(regexs, m['appendcookie'],cookieJar,recursiveCall=True,cachedPages=cachedPages)


                if  'post' in m and '$doregex' in m['post']:
                    m['post']=getRegexParsed(regexs, m['post'],cookieJar,recursiveCall=True,cachedPages=cachedPages)
#                    print 'post is now',m['post']

                if  'rawpost' in m and '$doregex' in m['rawpost']:
                    m['rawpost']=getRegexParsed(regexs, m['rawpost'],cookieJar,recursiveCall=True,cachedPages=cachedPages,rawPost=True)
                    #print 'rawpost is now',m['rawpost']

                if 'rawpost' in m and '$epoctime$' in m['rawpost']:
                    m['rawpost']=m['rawpost'].replace('$epoctime$',getEpocTime())

                if 'rawpost' in m and '$epoctime2$' in m['rawpost']:
                    m['rawpost']=m['rawpost'].replace('$epoctime2$',getEpocTime2())


                link=''
                if m['page'] and m['page'] in cachedPages and not 'ignorecache' in m and forCookieJarOnly==False :
                    #print 'using cache page',m['page']
                    link = cachedPages[m['page']]
                else:
                    if m['page'] and  not m['page']=='' and  m['page'].startswith('http'):
                        if '$epoctime$' in m['page']:
                            m['page']=m['page'].replace('$epoctime$',getEpocTime())
                        if '$epoctime2$' in m['page']:
                            m['page']=m['page'].replace('$epoctime2$',getEpocTime2())

                        #print 'Ingoring Cache',m['page']
                        page_split=m['page'].split('|')
                        pageUrl=page_split[0]
                        header_in_page=None
                        if len(page_split)>1:
                            header_in_page=page_split[1]

#                            if 
#                            proxy = urllib2.ProxyHandler({ ('https' ? proxytouse[:5]=="https":"http") : proxytouse})
#                            opener = urllib2.build_opener(proxy)
#                            urllib2.install_opener(opener)

                            
                        
#                        import urllib2
#                        print 'urllib2.getproxies',urllib2.getproxies()
                        current_proxies=urllib2.ProxyHandler(urllib2.getproxies())
        
        
                        #print 'getting pageUrl',pageUrl
                        req = urllib2.Request(pageUrl)
                        if 'proxy' in m:
                            proxytouse= m['proxy']
#                            print 'proxytouse',proxytouse
#                            urllib2.getproxies= lambda: {}
                            if pageUrl[:5]=="https":
                                proxy = urllib2.ProxyHandler({ 'https' : proxytouse})
                                #req.set_proxy(proxytouse, 'https')
                            else:
                                proxy = urllib2.ProxyHandler({ 'http'  : proxytouse})
                                #req.set_proxy(proxytouse, 'http')
                            opener = urllib2.build_opener(proxy)
                            urllib2.install_opener(opener)
                            
                        
                        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:14.0) Gecko/20100101 Firefox/14.0.1')
                        proxytouse=None

                        if 'referer' in m:
                            req.add_header('Referer', m['referer'])
                        if 'accept' in m:
                            req.add_header('Accept', m['accept'])
                        if 'agent' in m:
                            req.add_header('User-agent', m['agent'])
                        if 'x-req' in m:
                            req.add_header('X-Requested-With', m['x-req'])
                        if 'x-addr' in m:
                            req.add_header('x-addr', m['x-addr'])
                        if 'x-forward' in m:
                            req.add_header('X-Forwarded-For', m['x-forward'])
                        if 'setcookie' in m:
#                            print 'adding cookie',m['setcookie']
                            req.add_header('Cookie', m['setcookie'])
                        if 'appendcookie' in m:
#                            print 'appending cookie to cookiejar',m['appendcookie']
                            cookiestoApend=m['appendcookie']
                            cookiestoApend=cookiestoApend.split(';')
                            for h in cookiestoApend:
                                n,v=h.split('=')
                                w,n= n.split(':')
                                ck = cookielib.Cookie(version=0, name=n, value=v, port=None, port_specified=False, domain=w, domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
                                cookieJar.set_cookie(ck)
                        if 'origin' in m:
                            req.add_header('Origin', m['origin'])
                        if header_in_page:
                            header_in_page=header_in_page.split('&')
                            for h in header_in_page:
                                if h.split('=')==2:
                                    n,v=h.split('=')
                                else:
                                    vals=h.split('=')
                                    n=vals[0]
                                    v='='.join(vals[1:])
                                #n,v=h.split('=')
                                req.add_header(n,v)
                        
                        if not cookieJar==None:
#                            print 'cookieJarVal',cookieJar
                            cookie_handler = urllib2.HTTPCookieProcessor(cookieJar)
                            opener = urllib2.build_opener(cookie_handler, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
                            opener = urllib2.install_opener(opener)
#                            print 'noredirect','noredirect' in m
                            
                            if 'noredirect' in m:
                                opener = urllib2.build_opener(cookie_handler,NoRedirection, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
                                opener = urllib2.install_opener(opener)
                        elif 'noredirect' in m:
                            opener = urllib2.build_opener(NoRedirection, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
                            opener = urllib2.install_opener(opener)
                            

                        if 'connection' in m:
#                            print '..........................connection//////.',m['connection']
                            from keepalive import HTTPHandler
                            keepalive_handler = HTTPHandler()
                            opener = urllib2.build_opener(keepalive_handler)
                            urllib2.install_opener(opener)


                        #print 'after cookie jar'
                        post=None

                        if 'post' in m:
                            postData=m['post']
                            #if '$LiveStreamRecaptcha' in postData:
                            #    (captcha_challenge,catpcha_word,idfield)=processRecaptcha(m['page'],cookieJar)
                            #    if captcha_challenge:
                            #        postData=postData.replace('$LiveStreamRecaptcha','manual_recaptcha_challenge_field:'+captcha_challenge+',recaptcha_response_field:'+catpcha_word+',id:'+idfield)
                            splitpost=postData.split(',');
                            post={}
                            for p in splitpost:
                                n=p.split(':')[0];
                                v=p.split(':')[1];
                                post[n]=v
                            post = urllib.urlencode(post)

                        if 'rawpost' in m:
                            post=m['rawpost']
                            #if '$LiveStreamRecaptcha' in post:
                            #    (captcha_challenge,catpcha_word,idfield)=processRecaptcha(m['page'],cookieJar)
                            #    if captcha_challenge:
                            #       post=post.replace('$LiveStreamRecaptcha','&manual_recaptcha_challenge_field='+captcha_challenge+'&recaptcha_response_field='+catpcha_word+'&id='+idfield)
                        link=''
                        try:
                            
                            if post:
                                response = urllib2.urlopen(req,post)
                            else:
                                response = urllib2.urlopen(req)
                            if response.info().get('Content-Encoding') == 'gzip':
                                from StringIO import StringIO
                                import gzip
                                buf = StringIO( response.read())
                                f = gzip.GzipFile(fileobj=buf)
                                link = f.read()
                            else:
                                link=response.read()
                            
                        
                        
                            if 'proxy' in m and not current_proxies is None:
                                urllib2.install_opener(urllib2.build_opener(current_proxies))
                            
                            link=javascriptUnEscape(link)
                            #print repr(link)
                            #print link This just print whole webpage in LOG
                            if 'includeheaders' in m:
                                #link+=str(response.headers.get('Set-Cookie'))
                                link+='$$HEADERS_START$$:'
                                for b in response.headers:
                                    link+= b+':'+response.headers.get(b)+'\n'
                                link+='$$HEADERS_END$$:'
    #                        print link
                            addon_log(link)
                            addon_log(cookieJar )

                            response.close()
                        except: 
                            pass
                        cachedPages[m['page']] = link
                        #print link
                        #print 'store link for',m['page'],forCookieJarOnly

                        if forCookieJarOnly:
                            return cookieJar# do nothing
                    elif m['page'] and  not m['page'].startswith('http'):
                        if m['page'].startswith('$pyFunction:'):
                            val=doEval(m['page'].split('$pyFunction:')[1],'',cookieJar,m )
                            if forCookieJarOnly:
                                return cookieJar# do nothing
                            link=val
                            link=javascriptUnEscape(link)
                        else:
                            link=m['page']
                if '$pyFunction:playmedia(' in m['expres'] or 'ActivateWindow'  in m['expres'] or 'RunPlugin'  in m['expres']  or '$PLAYERPROXY$=' in url  or  any(x in url for x in g_ignoreSetResolved):
                    setresolved=False
                if  '$doregex' in m['expres']:
                    m['expres']=getRegexParsed(regexs, m['expres'],cookieJar,recursiveCall=True,cachedPages=cachedPages)
                  
                if not m['expres']=='':
                    #print 'doing it ',m['expres']
                    if '$LiveStreamCaptcha' in m['expres']:
                        val=askCaptcha(m,link,cookieJar)
                        #print 'url and val',url,val
                        url = url.replace("$doregex[" + k + "]", val)

                    elif m['expres'].startswith('$pyFunction:') or '#$pyFunction' in m['expres']:
                        #print 'expeeeeeeeeeeeeeeeeeee',m['expres']
                        val=''
                        if m['expres'].startswith('$pyFunction:'):
                            val=doEval(m['expres'].split('$pyFunction:')[1],link,cookieJar,m)
                        else:
                            val=doEvalFunction(m['expres'],link,cookieJar,m)
                        if 'ActivateWindow' in m['expres'] or 'RunPlugin' in m['expres']  : return '',False
                        if forCookieJarOnly:
                            return cookieJar# do nothing
                        if 'listrepeat' in m:
                            listrepeat=m['listrepeat']                            
                            #ret=re.findall(m['expres'],link)
                            #print 'ret',val
                            return listrepeat,eval(val), m,regexs,cookieJar
#                        print 'url k val',url,k,val
                        #print 'repr',repr(val)
                        
                        try:
                            url = url.replace(u"$doregex[" + k + "]", val)
                        except: url = url.replace("$doregex[" + k + "]", val.decode("utf-8"))
                    else:
                        if 'listrepeat' in m:
                            listrepeat=m['listrepeat']
                            #print 'listrepeat',m['expres']
                            #print m['expres']
                            #print 'aaaa'
                            #print link
                            ret=re.findall(m['expres'],link)
                            #print 'ret',ret
                            return listrepeat,ret, m,regexs,cookieJar
                             
                        val=''
                        if not link=='':
                            #print 'link',link
                            reg = re.compile(m['expres']).search(link)                            
                            try:
                                val=reg.group(1).strip()
                            except: traceback.print_exc()
                        elif m['page']=='' or m['page']==None:
                            val=m['expres']
                            
                        if rawPost:
#                            print 'rawpost'
                            val=urllib.quote_plus(val)
                        if 'htmlunescape' in m:
                            #val=urllib.unquote_plus(val)
                            import HTMLParser
                            val=HTMLParser.HTMLParser().unescape(val)
                        try:
                            url = url.replace("$doregex[" + k + "]", val)
                        except: url = url.replace("$doregex[" + k + "]", val.decode("utf-8"))
                        #print 'ur',url
                        #return val
                else:
                    url = url.replace("$doregex[" + k + "]",'')
        if '$epoctime$' in url:
            url=url.replace('$epoctime$',getEpocTime())
        if '$epoctime2$' in url:
            url=url.replace('$epoctime2$',getEpocTime2())

        if '$GUID$' in url:
            import uuid
            url=url.replace('$GUID$',str(uuid.uuid1()).upper())
        if '$get_cookies$' in url:
            url=url.replace('$get_cookies$',getCookiesString(cookieJar))

        if recursiveCall: return url
        #print 'final url',repr(url)
        if url=="":
            return
        else:
            return url,setresolved
def getmd5(t):
    import hashlib
    h=hashlib.md5()
    h.update(t)
    return h.hexdigest()

def decrypt_vaughnlive(encrypted):
    retVal=""
#    print 'enc',encrypted
    #for val in encrypted.split(':'):
    #    retVal+=chr(int(val.replace("0m0","")))
    #return retVal

def playmedia(media_url):
    try:
        import  CustomPlayer
        player = CustomPlayer.MyXBMCPlayer()
        listitem = xbmcgui.ListItem( label = str(name), iconImage = "DefaultVideo.png", thumbnailImage = xbmc.getInfoImage( "ListItem.Thumb" ), path=media_url )
        player.play( media_url,listitem)
        xbmc.sleep(1000)
        while player.is_active:
            xbmc.sleep(200)
    except:
        traceback.print_exc()
    return ''

def kodiJsonRequest(params):
    data = json.dumps(params)
    request = xbmc.executeJSONRPC(data)

    try:
        response = json.loads(request)
    except UnicodeDecodeError:
        response = json.loads(request.decode('utf-8', 'ignore'))

    try:
        if 'result' in response:
            return response['result']
        return None
    except KeyError:
        logger.warn("[%s] %s" % (params['method'], response['error']['message']))
        return None


def setKodiProxy(proxysettings=None):

    if proxysettings==None:
#        print 'proxy set to nothing'
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.usehttpproxy", "value":false}, "id":1}')
    else:
        
        ps=proxysettings.split(':')
        proxyURL=ps[0]
        proxyPort=ps[1]
        proxyType=ps[2]
        proxyUsername=None
        proxyPassword=None
        
        if len(ps)>3 and '@' in ps[3]: #jairox ###proxysettings
            proxyUsername=ps[3].split('@')[0] #jairox ###ps[3]
            proxyPassword=ps[3].split('@')[1] #jairox ###proxysettings.split('@')[-1]

#        print 'proxy set to', proxyType, proxyURL,proxyPort
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.usehttpproxy", "value":true}, "id":1}')
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxytype", "value":' + str(proxyType) +'}, "id":1}')
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxyserver", "value":"' + str(proxyURL) +'"}, "id":1}')
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxyport", "value":' + str(proxyPort) +'}, "id":1}')
        
        
        if not proxyUsername==None:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxyusername", "value":"' + str(proxyUsername) +'"}, "id":1}')
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxypassword", "value":"' + str(proxyPassword) +'"}, "id":1}')

        
def getConfiguredProxy():
    proxyActive = kodiJsonRequest({'jsonrpc': '2.0', "method":"Settings.GetSettingValue", "params":{"setting":"network.usehttpproxy"}, 'id': 1})['value']
#    print 'proxyActive',proxyActive
    proxyType = kodiJsonRequest({'jsonrpc': '2.0', "method":"Settings.GetSettingValue", "params":{"setting":"network.httpproxytype"}, 'id': 1})['value']

    if proxyActive: # PROXY_HTTP
        proxyURL = kodiJsonRequest({'jsonrpc': '2.0', "method":"Settings.GetSettingValue", "params":{"setting":"network.httpproxyserver"}, 'id': 1})['value']
        proxyPort = unicode(kodiJsonRequest({'jsonrpc': '2.0', "method":"Settings.GetSettingValue", "params":{"setting":"network.httpproxyport"}, 'id': 1})['value'])
        proxyUsername = kodiJsonRequest({'jsonrpc': '2.0', "method":"Settings.GetSettingValue", "params":{"setting":"network.httpproxyusername"}, 'id': 1})['value']
        proxyPassword = kodiJsonRequest({'jsonrpc': '2.0', "method":"Settings.GetSettingValue", "params":{"setting":"network.httpproxypassword"}, 'id': 1})['value']

        if proxyUsername and proxyPassword and proxyURL and proxyPort:
            return proxyURL + ':' + str(proxyPort)+':'+str(proxyType) + ':' + proxyUsername + '@' + proxyPassword
        elif proxyURL and proxyPort:
            return proxyURL + ':' + str(proxyPort)+':'+str(proxyType)
    else:
        return None
        
def playmediawithproxy(media_url, name, iconImage,proxyip,port, proxyuser=None, proxypass=None): #jairox

    if media_url==None or media_url=='':
        xbmc.executebuiltin("XBMC.Notification(documented.hd,Unable to play empty Url,5000,"+icon+")")
        return
    progress = xbmcgui.DialogProgress()
    progress.create('Progress', 'Playing with custom proxy')
    progress.update( 10, "", "setting proxy..", "" )
    proxyset=False
    existing_proxy=''
    #print 'playmediawithproxy'
    try:
        
        existing_proxy=getConfiguredProxy()
        print 'existing_proxy',existing_proxy
        #read and set here
        #jairox
        if not proxyuser == None:
            setKodiProxy( proxyip + ':' + port + ':0:' + proxyuser + '@' + proxypass)
        else:
            setKodiProxy( proxyip + ':' + port + ':0')

        print 'proxy setting complete playing',media_url
        proxyset=True
        progress.update( 80, "", "setting proxy complete, now playing", "" )
        

        import  CustomPlayer
        player = CustomPlayer.MyXBMCPlayer()
        player.pdialogue==progress
        listitem = xbmcgui.ListItem( label = str(name), iconImage = iconImage, thumbnailImage = xbmc.getInfoImage( "ListItem.Thumb" ), path=media_url )
        player.play( media_url,listitem)
        xbmc.sleep(1000)
        #while player.is_active:
        #    xbmc.sleep(200)
        import time
        beforestart=time.time()
        try:
            while player.is_active:
                xbmc.sleep(1000)       
                if player.urlplayed==False and time.time()-beforestart>12:
                    print 'failed!!!'
                    xbmc.executebuiltin("XBMC.Notification(documented.hd,Unable to play check proxy,5000,"+icon+")")
                    break
                #xbmc.sleep(1000)
        except: pass

        progress.close()
        progress=None
    except:
        traceback.print_exc()
    if progress:
        progress.close()
    if proxyset:
        print 'now resetting the proxy back'
        setKodiProxy(existing_proxy)
        print 'reset here'
    return ''


def SaveToFile(file_name,page_data,append=False):
    if append:
        f = open(file_name, 'a')
        f.write(page_data)
        f.close()
    else:
        f=open(file_name,'wb')
        f.write(page_data)
        f.close()
        return ''

def LoadFile(file_name):
    f=open(file_name,'rb')
    d=f.read()
    f.close()
    return d

def get_packed_iphonetv_url(page_data):
    import re,base64,urllib;
    s=page_data
    while 'geh(' in s:
        if s.startswith('lol('): s=s[5:-1]
#       print 's is ',s
        s=re.compile('"(.*?)"').findall(s)[0];
        s=  base64.b64decode(s);
        s=urllib.unquote(s);
    print s
    return s

def get_ferrari_url(page_data):
#    print 'get_dag_url2',page_data
    page_data2=getUrl(page_data);
    patt='(http.*)'
    import uuid
    playback=str(uuid.uuid1()).upper()
    links=re.compile(patt).findall(page_data2)
    headers=[('X-Playback-Session-Id',playback)]
    for l in links:
        try:
                page_datatemp=getUrl(l,headers=headers);

        except: pass

    return page_data+'|&X-Playback-Session-Id='+playback


def get_dag_url(page_data):
#    print 'get_dag_url',page_data
    if page_data.startswith('http://dag.total-stream.net'):
        headers=[('User-Agent','Verismo-BlackUI_(2.4.7.5.8.0.34)')]
        page_data=getUrl(page_data,headers=headers);

    if '127.0.0.1' in page_data:
        return revist_dag(page_data)
    elif re_me(page_data, 'wmsAuthSign%3D([^%&]+)') != '':
        final_url = re_me(page_data, '&ver_t=([^&]+)&') + '?wmsAuthSign=' + re_me(page_data, 'wmsAuthSign%3D([^%&]+)') + '==/mp4:' + re_me(page_data, '\\?y=([^&]+)&')
    else:
        final_url = re_me(page_data, 'href="([^"]+)"[^"]+$')
        if len(final_url)==0:
            final_url=page_data
    final_url = final_url.replace(' ', '%20')
    return final_url

def re_me(data, re_patten):
    match = ''
    m = re.search(re_patten, data)
    if m != None:
        match = m.group(1)
    else:
        match = ''
    return match

def revist_dag(page_data):
    final_url = ''
    if '127.0.0.1' in page_data:
        final_url = re_me(page_data, '&ver_t=([^&]+)&') + ' live=true timeout=15 playpath=' + re_me(page_data, '\\?y=([a-zA-Z0-9-_\\.@]+)')

    if re_me(page_data, 'token=([^&]+)&') != '':
        final_url = final_url + '?token=' + re_me(page_data, 'token=([^&]+)&')
    elif re_me(page_data, 'wmsAuthSign%3D([^%&]+)') != '':
        final_url = re_me(page_data, '&ver_t=([^&]+)&') + '?wmsAuthSign=' + re_me(page_data, 'wmsAuthSign%3D([^%&]+)') + '==/mp4:' + re_me(page_data, '\\?y=([^&]+)&')
    else:
        final_url = re_me(page_data, 'HREF="([^"]+)"')

    if 'dag1.asx' in final_url:
        return get_dag_url(final_url)

    if 'devinlivefs.fplive.net' not in final_url:
        final_url = final_url.replace('devinlive', 'flive')
    if 'permlivefs.fplive.net' not in final_url:
        final_url = final_url.replace('permlive', 'flive')
    return final_url


#function equalavent to re.sub('\\b' + aa +'\\b', k[c], p)
def findAndReplaceWord(source_str, word_to_find,replace_with):
    splits=None
    splits=source_str.split(word_to_find)
    if len(splits)>1:
        new_string=[]
        current_index=0
        for current_split in splits:
            #print 'here',i
            new_string.append(current_split)
            val=word_to_find#by default assume it was wrong to split

            #if its first one and item is blank then check next item is valid or not
            if current_index==len(splits)-1:
                val='' # last one nothing to append normally
            else:
                if len(current_split)==0: #if blank check next one with current split value
                    if ( len(splits[current_index+1])==0 and word_to_find[0].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_') or (len(splits[current_index+1])>0  and splits[current_index+1][0].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_'):# first just just check next
                        val=replace_with
                #not blank, then check current endvalue and next first value
                else:
                    if (splits[current_index][-1].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_') and (( len(splits[current_index+1])==0 and word_to_find[0].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_') or (len(splits[current_index+1])>0  and splits[current_index+1][0].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_')):# first just just check next
                        val=replace_with

            new_string.append(val)
            current_index+=1
        #aaaa=1/0
        source_str=''.join(new_string)
    return source_str


def getCookiesString(cookieJar):
    try:
        cookieString=""
        for index, cookie in enumerate(cookieJar):
            cookieString+=cookie.name + "=" + cookie.value +";"
    except: pass
    #print 'cookieString',cookieString
    return cookieString


def saveCookieJar(cookieJar,COOKIEFILE):
    try:
        complete_path=os.path.join(profile,COOKIEFILE)
        cookieJar.save(complete_path,ignore_discard=True)
    except: pass

def getCookieJar(COOKIEFILE):

    cookieJar=None
    if COOKIEFILE:
        try:
            complete_path=os.path.join(profile,COOKIEFILE)
            cookieJar = cookielib.LWPCookieJar()
            cookieJar.load(complete_path,ignore_discard=True)
        except:
            cookieJar=None

    if not cookieJar:
        cookieJar = cookielib.LWPCookieJar()

    return cookieJar

def doEval(fun_call,page_data,Cookie_Jar,m):
    ret_val=''
    #print fun_call
    if functions_dir not in sys.path:
        sys.path.append(functions_dir)

#    print fun_call
    try:
        py_file='import '+fun_call.split('.')[0]
#        print py_file,sys.path
        exec( py_file)
#        print 'done'
    except:
        #print 'error in import'
        traceback.print_exc(file=sys.stdout)
#    print 'ret_val='+fun_call
    exec ('ret_val='+fun_call)
#    print ret_val
    #exec('ret_val=1+1')
    try:
        return str(ret_val)
    except: return ret_val

def doEvalFunction(fun_call,page_data,Cookie_Jar,m):
#    print 'doEvalFunction'
    ret_val=''
    if functions_dir not in sys.path:
        sys.path.append(functions_dir)
        
    f=open(os.path.join(home,'LSProdynamicCode.py'),"wb")
    f.write("# -*- coding: utf-8 -*-\n")
    f.write(fun_call.encode("utf-8"));
    
    f.close()
    import LSProdynamicCode
    ret_val=LSProdynamicCode.GetLSProData(page_data,Cookie_Jar,m)
    try:
        return str(ret_val)
    except: return ret_val
	
def getGoogleRecaptchaResponse(captchakey, cj,type=1): #1 for get, 2 for post, 3 for rawpost
#    #headers=[('User-Agent','Mozilla/5.0 (Windows NT 6.1; rv:14.0) Gecko/20100101 Firefox/14.0.1')]
#    html_text=getUrl(url,noredir=True, cookieJar=cj,headers=headers)
 #   print 'html_text',html_text
    recapChallenge=""
    solution=""
#    cap_reg="recap.*?\?k=(.*?)\""    
#    match =re.findall(cap_reg, html_text)
    
        
#    print 'match',match
    captcha=False
    captcha_reload_response_chall=None
    solution=None
    if len(captchakey)>0: #new shiny captcha!
        captcha_url=captchakey
        if not captcha_url.startswith('http'):
            captcha_url='http://www.google.com/recaptcha/api/challenge?k='+captcha_url+'&ajax=1'
#        print 'captcha_url',captcha_url
        captcha=True

        cap_chall_reg='challenge.*?\'(.*?)\''
        cap_image_reg='\'(.*?)\''
        captcha_script=getUrl(captcha_url,cookieJar=cj)
        recapChallenge=re.findall(cap_chall_reg, captcha_script)[0]
        captcha_reload='http://www.google.com/recaptcha/api/reload?c=';
        captcha_k=captcha_url.split('k=')[1]
        captcha_reload+=recapChallenge+'&k='+captcha_k+'&reason=i&type=image&lang=en'
        captcha_reload_js=getUrl(captcha_reload,cookieJar=cj)
        captcha_reload_response_chall=re.findall(cap_image_reg, captcha_reload_js)[0]
        captcha_image_url='http://www.google.com/recaptcha/api/image?c='+captcha_reload_response_chall
        if not captcha_image_url.startswith("http"):
            captcha_image_url='http://www.google.com/recaptcha/api/'+captcha_image_url
        import random
        n=random.randrange(100,1000,5)
        local_captcha = os.path.join(profile,str(n) +"captcha.img" )
        localFile = open(local_captcha, "wb")
        localFile.write(getUrl(captcha_image_url,cookieJar=cj))
        localFile.close()
        solver = InputWindow(captcha=local_captcha)
        solution = solver.get()
        os.remove(local_captcha)

    if captcha_reload_response_chall:
        if type==1:
            return 'recaptcha_challenge_field='+urllib.quote_plus(captcha_reload_response_chall)+'&recaptcha_response_field='+urllib.quote_plus(solution)
        elif type==2:
            return 'recaptcha_challenge_field:'+captcha_reload_response_chall+',recaptcha_response_field:'+solution
        else:
            return 'recaptcha_challenge_field='+urllib.quote_plus(captcha_reload_response_chall)+'&recaptcha_response_field='+urllib.quote_plus(solution)
    else:
        return ''
        

def getUrl(url, cookieJar=None,post=None, timeout=20, headers=None, noredir=False):


    cookie_handler = urllib2.HTTPCookieProcessor(cookieJar)

    if noredir:
        opener = urllib2.build_opener(NoRedirection,cookie_handler, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
    else:
        opener = urllib2.build_opener(cookie_handler, urllib2.HTTPBasicAuthHandler(), urllib2.HTTPHandler())
    #opener = urllib2.install_opener(opener)
    req = urllib2.Request(url)
    req.add_header('User-Agent','Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
    if headers:
        for h,hv in headers:
            req.add_header(h,hv)

    response = opener.open(req,post,timeout=timeout)
    link=response.read()
    response.close()
    return link;

def get_decode(str,reg=None):
    if reg:
        str=re.findall(reg, str)[0]
    s1 = urllib.unquote(str[0: len(str)-1]);
    t = '';
    for i in range( len(s1)):
        t += chr(ord(s1[i]) - s1[len(s1)-1]);
    t=urllib.unquote(t)
#    print t
    return t

def javascriptUnEscape(str):
    js=re.findall('unescape\(\'(.*?)\'',str)
#    print 'js',js
    if (not js==None) and len(js)>0:
        for j in js:
            #print urllib.unquote(j)
            str=str.replace(j ,urllib.unquote(j))
    return str


def TakeInput(name, headname):


    kb = xbmc.Keyboard('default', 'heading', True)
    kb.setDefault(name)
    kb.setHeading(headname)
    kb.setHiddenInput(False)
    return kb.getText()

   
#########################################################

class InputWindow(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        self.cptloc = kwargs.get('captcha')
        self.img = xbmcgui.ControlImage(335,30,624,60,self.cptloc)
        self.addControl(self.img)
        self.kbd = xbmc.Keyboard()

    def get(self):
        self.show()
        time.sleep(2)
        self.kbd.doModal()
        if (self.kbd.isConfirmed()):
            text = self.kbd.getText()
            self.close()
            return text
        self.close()
        return False

def getEpocTime():
    import time
    return str(int(time.time()*1000))

def getEpocTime2():
    import time
    return str(int(time.time()))

def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                splitparams={}
                splitparams=pairsofparams[i].split('=')
                if (len(splitparams))==2:
                    param[splitparams[0]]=splitparams[1]
        return param


def getFavorites():
        items = json.loads(open(favorites).read())
        total = len(items)
        for i in items:
            name = i[0]
            url = i[1]
            iconimage = i[2]
            try:
                fanArt = i[3]
                if fanArt == None:
                    raise
            except:
                if addon.getSetting('use_thumb') == "true":
                    fanArt = iconimage
                else:
                    fanArt = fanart
            try: playlist = i[5]
            except: playlist = None
            try: regexs = i[6]
            except: regexs = None

            if i[4] == 0:
                addLink(url,name,iconimage,fanArt,'','','','fav',playlist,regexs,total)
            else:
                addDir(name,url,i[4],iconimage,fanart,'','','','','fav')


def addFavorite(name,url,iconimage,fanart,mode,playlist=None,regexs=None):
        favList = []
        try:
            # seems that after
            name = name.encode('utf-8', 'ignore')
        except:
            pass
        if os.path.exists(favorites)==False:
            addon_log('Making Favorites File')
            favList.append((name,url,iconimage,fanart,mode,playlist,regexs))
            a = open(favorites, "w")
            a.write(json.dumps(favList))
            a.close()
        else:
            addon_log('Appending Favorites')
            a = open(favorites).read()
            data = json.loads(a)
            data.append((name,url,iconimage,fanart,mode))
            b = open(favorites, "w")
            b.write(json.dumps(data))
            b.close()


def rmFavorite(name):
        data = json.loads(open(favorites).read())
        for index in range(len(data)):
            if data[index][0]==name:
                del data[index]
                b = open(favorites, "w")
                b.write(json.dumps(data))
                b.close()
                break
        xbmc.executebuiltin("XBMC.Container.Refresh")

def urlsolver(url):
    import urlresolver
    host = urlresolver.HostedMediaFile(url)
    if host:
        resolver = urlresolver.resolve(url)
        resolved = resolver
        if isinstance(resolved,list):
            for k in resolved:
                quality = addon.getSetting('quality')
                if k['quality'] == 'HD'  :
                    resolver = k['url']
                    break
                elif k['quality'] == 'SD' :
                    resolver = k['url']
                elif k['quality'] == '1080p' and addon.getSetting('1080pquality') == 'true' :
                    resolver = k['url']
                    break
        else:
            resolver = resolved
    else:
        xbmc.executebuiltin("XBMC.Notification(documented.hd,Urlresolver donot support this domain. - ,5000)")
        resolver=url
    return resolver
def tryplay(url,listitem,pdialogue=None):    

    if url.lower().startswith('plugin') and 'youtube' not in  url.lower():
        print 'playing via runplugin'
        xbmc.executebuiltin('XBMC.RunPlugin('+url+')') 
        for i in range(8):
            xbmc.sleep(500) ##sleep for 10 seconds, half each time
            try:
                #print 'condi'
                if xbmc.getCondVisibility("Player.HasMedia") and xbmc.Player().isPlaying():
                    return True
            except: pass
        print 'returning now'
        return False
    import  CustomPlayer,time

    player = CustomPlayer.MyXBMCPlayer()
    player.pdialogue=pdialogue
    start = time.time() 
    #xbmc.Player().play( liveLink,listitem)
    print 'going to play'
    import time
    beforestart=time.time()
    player.play( url, listitem)
    xbmc.sleep(1000)
    
    try:
        while player.is_active:
            xbmc.sleep(400)
           
            if player.urlplayed:
                print 'yes played'
                return True
            if time.time()-beforestart>4: return False
            #xbmc.sleep(1000)
    except: pass
    print 'not played',url
    return False
def play_playlist(name, mu_playlist,queueVideo=None):
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        #print 'mu_playlist',mu_playlist
        if '$$LSPlayOnlyOne$$' in mu_playlist[0]:
            mu_playlist[0]=mu_playlist[0].replace('$$LSPlayOnlyOne$$','')
            import urlparse
            names = []
            iloop=0
            progress = xbmcgui.DialogProgress()
            progress.create('Progress', 'Trying Multiple Links')
            for i in mu_playlist:
                

                if '$$lsname=' in i:
                    d_name=i.split('$$lsname=')[1].split('&regexs')[0]
                    names.append(d_name)                                       
                    mu_playlist[iloop]=i.split('$$lsname=')[0]+('&regexs'+i.split('&regexs')[1] if '&regexs' in i else '')                    
                else:
                    d_name=urlparse.urlparse(i).netloc
                    if d_name == '':
                        names.append(name)
                    else:
                        names.append(d_name)
                index=iloop
                iloop+=1
                
                playname=names[index]
                if progress.iscanceled(): return 
                progress.update( iloop/len(mu_playlist)*100,"", "Link#%d"%(iloop),playname  )
                print 'auto playnamexx',playname
                if "&mode=19" in mu_playlist[index]:
                        #playsetresolved (urlsolver(mu_playlist[index].replace('&mode=19','')),name,iconimage,True)
                    liz = xbmcgui.ListItem(playname, iconImage=iconimage, thumbnailImage=iconimage)
                    liz.setInfo(type='Video', infoLabels={'Title':playname})
                    liz.setProperty("IsPlayable","true")
                    urltoplay=urlsolver(mu_playlist[index].replace('&mode=19','').replace(';',''))
                    liz.setPath(urltoplay)
                    #xbmc.Player().play(urltoplay,liz)
                    played=tryplay(urltoplay,liz)
                elif "$doregex" in mu_playlist[index] :
#                    print mu_playlist[index]
                    sepate = mu_playlist[index].split('&regexs=')
#                    print sepate
                    url,setresolved = getRegexParsed(sepate[1], sepate[0])
                    url2 = url.replace(';','')
                    liz = xbmcgui.ListItem(playname, iconImage=iconimage, thumbnailImage=iconimage)
                    liz.setInfo(type='Video', infoLabels={'Title':playname})
                    liz.setProperty("IsPlayable","true")
                    liz.setPath(url2)
                    #xbmc.Player().play(url2,liz)
                    played=tryplay(url2,liz)

                else:
                    url = mu_playlist[index]
                    url=url.split('&regexs=')[0]
                    liz = xbmcgui.ListItem(playname, iconImage=iconimage, thumbnailImage=iconimage)
                    liz.setInfo(type='Video', infoLabels={'Title':playname})
                    liz.setProperty("IsPlayable","true")
                    liz.setPath(url)
                    #xbmc.Player().play(url,liz)
                    played=tryplay(url,liz)
                    print 'played',played
                print 'played',played
                if played: return
            return     
        if addon.getSetting('ask_playlist_items') == 'true' and not queueVideo :
            import urlparse
            names = []
            iloop=0
            for i in mu_playlist:
                if '$$lsname=' in i:
                    d_name=i.split('$$lsname=')[1].split('&regexs')[0]
                    names.append(d_name)                                       
                    mu_playlist[iloop]=i.split('$$lsname=')[0]+('&regexs'+i.split('&regexs')[1] if '&regexs' in i else '')                    
                else:
                    d_name=urlparse.urlparse(i).netloc
                    if d_name == '':
                        names.append(name)
                    else:
                        names.append(d_name)
                    
                iloop+=1
            dialog = xbmcgui.Dialog()
            index = dialog.select('Choose a video source', names)
            if index >= 0:
                playname=names[index]
                print 'playnamexx',playname
                if "&mode=19" in mu_playlist[index]:
                        #playsetresolved (urlsolver(mu_playlist[index].replace('&mode=19','')),name,iconimage,True)
                    liz = xbmcgui.ListItem(playname, iconImage=iconimage, thumbnailImage=iconimage)
                    liz.setInfo(type='Video', infoLabels={'Title':playname})
                    liz.setProperty("IsPlayable","true")
                    urltoplay=urlsolver(mu_playlist[index].replace('&mode=19','').replace(';',''))
                    liz.setPath(urltoplay)
                    xbmc.Player().play(urltoplay,liz)
                elif "$doregex" in mu_playlist[index] :
#                    print mu_playlist[index]
                    sepate = mu_playlist[index].split('&regexs=')
#                    print sepate
                    url,setresolved = getRegexParsed(sepate[1], sepate[0])
                    url2 = url.replace(';','')
                    liz = xbmcgui.ListItem(playname, iconImage=iconimage, thumbnailImage=iconimage)
                    liz.setInfo(type='Video', infoLabels={'Title':playname})
                    liz.setProperty("IsPlayable","true")
                    liz.setPath(url2)
                    xbmc.Player().play(url2,liz)

                else:
                    url = mu_playlist[index]
                    url=url.split('&regexs=')[0]
                    liz = xbmcgui.ListItem(playname, iconImage=iconimage, thumbnailImage=iconimage)
                    liz.setInfo(type='Video', infoLabels={'Title':playname})
                    liz.setProperty("IsPlayable","true")
                    liz.setPath(url)
                    xbmc.Player().play(url,liz)
        elif not queueVideo:
            #playlist = xbmc.PlayList(1) # 1 means video
            playlist.clear()
            item = 0
            for i in mu_playlist:
                item += 1
                info = xbmcgui.ListItem('%s) %s' %(str(item),name))
                # Don't do this as regex parsed might take longer
                try:
                    if "$doregex" in i:
                        sepate = i.split('&regexs=')
#                        print sepate
                        url,setresolved = getRegexParsed(sepate[1], sepate[0])
                    elif "&mode=19" in i:
                        url = urlsolver(i.replace('&mode=19','').replace(';',''))                        
                    if url:
                        playlist.add(url, info)
                    else:
                        raise
                except Exception:
                    playlist.add(i, info)
                    pass #xbmc.Player().play(url)

            xbmc.executebuiltin('playlist.playoffset(video,0)')
        else:

                listitem = xbmcgui.ListItem(name)
                playlist.add(mu_playlist, listitem)


def download_file(name, url):
        if addon.getSetting('save_location') == "":
            xbmc.executebuiltin("XBMC.Notification('documented.hd','Choose a location to save files.',15000,"+icon+")")
            addon.openSettings()
        params = {'url': url, 'download_path': addon.getSetting('save_location')}
        downloader.download(name, params)
        dialog = xbmcgui.Dialog()
        ret = dialog.yesno('documented.hd', 'Do you want to add this file as a source?')
        if ret:
            addSource(os.path.join(addon.getSetting('save_location'), name))

def _search(url,name):
   # print url,name
    pluginsearchurls = ['plugin://plugin.video.youtube/kodion/search/list/',\
             ]
    names = ['Youtube']
    dialog = xbmcgui.Dialog()
    index = dialog.select('Choose a video source', names)

    if index >= 0:
        url = pluginsearchurls[index]
#        print 'url',url
        pluginquerybyJSON(url)

def addDir(name,url,mode,iconimage,fanart,description,genre,date,credits,showcontext=False,regexs=None,reg_url=None,allinfo={}):



        if regexs and len(regexs)>0:
            u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&fanart="+urllib.quote_plus(fanart)+"&regexs="+regexs
        else:
            u=sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&fanart="+urllib.quote_plus(fanart)
        
        ok=True
        if date == '':
            date = None
        else:
            description += '\n\nDate: %s' %date
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        if len(allinfo) <1 :
            liz.setInfo(type="Video", infoLabels={ "Title": name, "Plot": description, "Genre": genre, "dateadded": date, "credits": credits })
        else:
            liz.setInfo(type="Video", infoLabels= allinfo)
        liz.setProperty("Fanart_Image", fanart)
        if showcontext:
            contextMenu = []
            parentalblock =addon.getSetting('parentalblocked')
            parentalblock= parentalblock=="true"
            parentalblockedpin =addon.getSetting('parentalblockedpin')
#            print 'parentalblockedpin',parentalblockedpin
            if len(parentalblockedpin)>0:
                if parentalblock:
                    contextMenu.append(('Disable Parental Block','XBMC.RunPlugin(%s?mode=55&name=%s)' %(sys.argv[0], urllib.quote_plus(name))))
                else:
                    contextMenu.append(('Enable Parental Block','XBMC.RunPlugin(%s?mode=56&name=%s)' %(sys.argv[0], urllib.quote_plus(name))))
                    
            if showcontext == 'source':
            
                if name in str(SOURCES):
                    contextMenu.append(('Remove from Sources','XBMC.RunPlugin(%s?mode=8&name=%s)' %(sys.argv[0], urllib.quote_plus(name))))
                    
                    
            elif showcontext == 'download':
                contextMenu.append(('Download','XBMC.RunPlugin(%s?url=%s&mode=9&name=%s)'
                                    %(sys.argv[0], urllib.quote_plus(url), urllib.quote_plus(name))))
            elif showcontext == 'fav':
                contextMenu.append(('','XBMC.RunPlugin(%s?mode=6&name=%s)'
                                    %(sys.argv[0], urllib.quote_plus(name))))
            if showcontext == '!!update':
                fav_params2 = (
                    '%s?url=%s&mode=17&regexs=%s'
                    %(sys.argv[0], urllib.quote_plus(reg_url), regexs)
                    )
                contextMenu.append(('[COLOR yellow]!!update[/COLOR]','XBMC.RunPlugin(%s)' %fav_params2))
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
        return ok
def ytdl_download(url,title,media_type='video'):
    # play in xbmc while playing go back to contextMenu(c) to "!!Download!!"
    # Trial yasceen: seperate |User-Agent=
    import youtubedl
    if not url == '':
        if media_type== 'audio':
            youtubedl.single_YD(url,download=True,audio=True)
        else:
            youtubedl.single_YD(url,download=True)
    elif xbmc.Player().isPlaying() == True :
        import YDStreamExtractor
        if YDStreamExtractor.isDownloading() == True:

            YDStreamExtractor.manageDownloads()
        else:
            xbmc_url = xbmc.Player().getPlayingFile()

            xbmc_url = xbmc_url.split('|User-Agent=')[0]
            info = {'url':xbmc_url,'title':title,'media_type':media_type}
            youtubedl.single_YD('',download=True,dl_info=info)
    else:
        xbmc.executebuiltin("XBMC.Notification(First Play The Video, [COLOR lime]While playing download[/COLOR] ,10000)")

## Lunatixz PseudoTV feature
def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('ascii', 'ignore')
    return string
def uni(string, encoding = 'utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode):
            string = unicode(string, encoding, 'ignore')
    return string
def removeNonAscii(s): return "".join(filter(lambda x: ord(x)<128, s))

def sendJSON( command):
    data = ''
    try:
        data = xbmc.executeJSONRPC(uni(command))
    except UnicodeEncodeError:
        data = xbmc.executeJSONRPC(ascii(command))

    return uni(data)

def pluginquerybyJSON(url,give_me_result=None,playlist=False):
    if 'audio' in url:
        json_query = uni('{"jsonrpc":"2.0","method":"Files.GetDirectory","params": {"directory":"%s","media":"video", "properties": ["title", "album", "artist", "duration","thumbnail", "year"]}, "id": 1}') %url
    else:
        json_query = uni('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","media":"video","properties":[ "plot","playcount","director", "genre","votes","duration","trailer","premiered","thumbnail","title","year","dateadded","fanart","rating","season","episode","studio","mpaa"]},"id":1}') %url
    json_folder_detail = json.loads(sendJSON(json_query))
    #print json_folder_detail
    if give_me_result:
        return json_folder_detail
    if json_folder_detail.has_key('error'):
        return
    else:

        for i in json_folder_detail['result']['files'] :
            meta ={}
            url = i['file']
            name = removeNonAscii(i['label'])
            thumbnail = removeNonAscii(i['thumbnail'])
            fanart = removeNonAscii(i['fanart'])
            meta = dict((k,v) for k, v in i.iteritems() if not v == '0' or not v == -1 or v == '')
            meta.pop("file", None)
            if i['filetype'] == 'file':
                if playlist:
                    play_playlist(name,url,queueVideo='1')
                    continue
                else:
                    addLink(url,name,thumbnail,fanart,'','','','',None,'',total=len(json_folder_detail['result']['files']),allinfo=meta)
                    #xbmc.executebuiltin("Container.SetViewMode(500)")
                    if i['type'] and i['type'] == 'tvshow' :
                        xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
                    elif i['episode'] > 0 :
                        xbmcplugin.setContent(int(sys.argv[1]), 'episodes')

            else:
                addDir(name,url,53,thumbnail,fanart,'','','','',allinfo=meta)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

def addLink(url,name,iconimage,fanart,description,genre,date,showcontext,playlist,regexs,total,setCookie="",allinfo={}):
        #print 'url,name',url,name,iconimage
        contextMenu =[]
        parentalblock =addon.getSetting('parentalblocked')
        parentalblock= parentalblock=="true"
        parentalblockedpin =addon.getSetting('parentalblockedpin')
#        print 'parentalblockedpin',parentalblockedpin
        if len(parentalblockedpin)>0:
            if parentalblock:
                contextMenu.append(('Disable Parental Block','XBMC.RunPlugin(%s?mode=55&name=%s)' %(sys.argv[0], urllib.quote_plus(name))))
            else:
                contextMenu.append(('Enable Parental Block','XBMC.RunPlugin(%s?mode=56&name=%s)' %(sys.argv[0], urllib.quote_plus(name))))
                    
        try:
            name = name.encode('utf-8')
        except: pass
        ok = True
        isFolder=False
        if regexs:
            mode = '17'
            if 'listrepeat' in regexs:
                isFolder=True
#                print 'setting as folder in link'
            contextMenu.append(('[B][COLOR lime]| Download Video |[/COLOR][/B]','XBMC.RunPlugin(%s?url=%s&mode=21&name=%s)'
                                    %(sys.argv[0], urllib.quote_plus(url), urllib.quote_plus(name))))
        elif  (any(x in url for x in resolve_url) and  url.startswith('http')) or url.endswith('&mode=19'):
            url=url.replace('&mode=19','')
            mode = '19'
            contextMenu.append(('[B][COLOR lime]| Download Video |[/COLOR][/B]','XBMC.RunPlugin(%s?url=%s&mode=21&name=%s)'
                                    %(sys.argv[0], urllib.quote_plus(url), urllib.quote_plus(name))))
        elif url.endswith('&mode=18'):
            url=url.replace('&mode=18','')
            mode = '18'
            contextMenu.append(('[COLOR white]!!Download!![/COLOR]','XBMC.RunPlugin(%s?url=%s&mode=23&name=%s)'
                                    %(sys.argv[0], urllib.quote_plus(url), urllib.quote_plus(name))))
            if addon.getSetting('dlaudioonly') == 'true':
                contextMenu.append(('[B][COLOR blue]| Download Audio |[/COLOR][/B]','XBMC.RunPlugin(%s?url=%s&mode=24&name=%s)'
                                        %(sys.argv[0], urllib.quote_plus(url), urllib.quote_plus(name))))
        else:
            mode = '12'

        if 'plugin://plugin.video.youtube/play/?video_id=' in url:
              yt_audio_url = url.replace('plugin://plugin.video.youtube/play/?video_id=','https://www.youtube.com/watch?v=')

        u=sys.argv[0]+"?"
        play_list = False
        if playlist:
            if addon.getSetting('add_playlist') == "false" and '$$LSPlayOnlyOne$$' not in playlist[0] :
                u += "url="+urllib.quote_plus(url)+"&mode="+mode
            else:
                u += "mode=13&name=%s&playlist=%s" %(urllib.quote_plus(name), urllib.quote_plus(str(playlist).replace(',','||')))
                name = name + '[COLOR magenta] (' + str(len(playlist)) + ' items )[/COLOR]'
                play_list = True
        else:
            u += "url="+urllib.quote_plus(url)+"&mode="+mode
        if regexs:
            u += "&regexs="+regexs
        if not setCookie == '':
            u += "&setCookie="+urllib.quote_plus(setCookie)
        if iconimage and  not iconimage == '':
            u += "&iconimage="+urllib.quote_plus(iconimage)
            
        if date == '':
            date = None
        else:
            description += '\n\nDate: %s' %date
        liz=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
        #if isFolder:
        if allinfo==None or len(allinfo) <1:
            liz.setInfo(type="Video", infoLabels={ "Title": name, "Plot": description, "Genre": genre, "dateadded": date })
        else:
            liz.setInfo(type="Video", infoLabels=allinfo)
        liz.setProperty("Fanart_Image", fanart)
        
        if (not play_list) and not any(x in url for x in g_ignoreSetResolved) and not '$PLAYERPROXY$=' in url:#  (not url.startswith('plugin://plugin.video.f4mTester')):
            if regexs:
                #print urllib.unquote_plus(regexs)
                if '$pyFunction:playmedia(' not in urllib.unquote_plus(regexs) and 'notplayable' not in urllib.unquote_plus(regexs) and 'listrepeat' not in  urllib.unquote_plus(regexs) :
                    #print 'setting isplayable',url, urllib.unquote_plus(regexs),url
                    liz.setProperty('IsPlayable', 'true')
            else:
                liz.setProperty('IsPlayable', 'true')
        else:
            addon_log( 'NOT setting isplayable'+url)
        if showcontext:
            #contextMenu = []
            if showcontext == 'fav':
                contextMenu.append(
                    ('','XBMC.RunPlugin(%s?mode=6&name=%s)'
                     %(sys.argv[0], urllib.quote_plus(name)))
                     )
            elif not name in FAV:
                try:
                    fav_params = (
                        '%s?mode=5&name=%s&url=%s&iconimage=%s&fanart=%s&fav_mode=0'
                        %(sys.argv[0], urllib.quote_plus(name), urllib.quote_plus(url), urllib.quote_plus(iconimage), urllib.quote_plus(fanart))
                        )
                except:
                    fav_params = (
                        '%s?mode=5&name=%s&url=%s&iconimage=%s&fanart=%s&fav_mode=0'
                        %(sys.argv[0], urllib.quote_plus(name), urllib.quote_plus(url), urllib.quote_plus(iconimage.encode("utf-8")), urllib.quote_plus(fanart.encode("utf-8")))
                        )
                if playlist:
                    fav_params += 'playlist='+urllib.quote_plus(str(playlist).replace(',','||'))
                if regexs:
                    fav_params += "&regexs="+regexs
            liz.addContextMenuItems(contextMenu)
        try:
            if not playlist is None:
                if addon.getSetting('add_playlist') == "false":
                    playlist_name = name.split(') ')[1]
                    contextMenu_ = [
                        ('Play '+playlist_name+' PlayList','XBMC.RunPlugin(%s?mode=13&name=%s&playlist=%s)'
                         %(sys.argv[0], urllib.quote_plus(playlist_name), urllib.quote_plus(str(playlist).replace(',','||'))))
                         ]
                    liz.addContextMenuItems(contextMenu_)
        except: pass
        #print 'adding',name
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,totalItems=total,isFolder=isFolder)

        #print 'added',name
        return ok

        
def playsetresolved(url,name,iconimage,setresolved=True,reg=None):
    print 'playsetresolved',url,setresolved
    if url==None: 
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        return
    if setresolved:
        setres=True
        if '$$LSDirect$$' in url:
            url=url.replace('$$LSDirect$$','')
            setres=False
        if reg and 'notplayable' in reg:
            setres=False

        liz = xbmcgui.ListItem(name, iconImage=iconimage, thumbnailImage=iconimage)
        liz.setInfo(type='Video', infoLabels={'Title':name})
        liz.setProperty("IsPlayable","true")
        liz.setPath(url)
        if not setres:
            xbmc.Player().play(url)
        else:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
           
    else:
        xbmc.executebuiltin('XBMC.RunPlugin('+url+')')


##not a generic implemenation as it needs to convert            
def d2x(d, root="root",nested=0):

    op = lambda tag: '<' + tag + '>'
    cl = lambda tag: '</' + tag + '>\n'

    ml = lambda v,xml: xml + op(key) + str(v) + cl(key)
    xml = op(root) + '\n' if root else ""

    for key,vl in d.iteritems():
        vtype = type(vl)
        if nested==0: key='regex' #enforcing all top level tags to be named as regex
        if vtype is list: 
            for v in vl:
                v=escape(v)
                xml = ml(v,xml)         
        
        if vtype is dict: 
            xml = ml('\n' + d2x(vl,None,nested+1),xml)         
        if vtype is not list and vtype is not dict: 
            if not vl is None: vl=escape(vl)
            #print repr(vl)
            if vl is None:
                xml = ml(vl,xml)
            else:
                #xml = ml(escape(vl.encode("utf-8")),xml)
                xml = ml(vl.encode("utf-8"),xml)

    xml += cl(root) if root else ""

    return xml
xbmcplugin.setContent(int(sys.argv[1]), 'movies')

try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
except:
    pass
try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
except:
    pass
try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
except:
    pass
try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_GENRE)
except:
    pass

params=get_params()

url=None
name=None
mode=None
playlist=None
iconimage=None
fanart=FANART
playlist=None
fav_mode=None
regexs=None

try:
    url=urllib.unquote_plus(params["url"]).decode('utf-8')
except:
    pass
try:
    name=urllib.unquote_plus(params["name"])
except:
    pass
try:
    iconimage=urllib.unquote_plus(params["iconimage"])
except:
    pass
try:
    fanart=urllib.unquote_plus(params["fanart"])
except:
    pass
try:
    mode=int(params["mode"])
except:
    pass
try:
    playlist=eval(urllib.unquote_plus(params["playlist"]).replace('||',','))
except:
    pass
try:
    fav_mode=int(params["fav_mode"])
except:
    pass
try:
    regexs=params["regexs"]
except:
    pass
playitem=''
try:
    playitem=urllib.unquote_plus(params["playitem"])
except:
    pass
    
addon_log("Mode: "+str(mode))

ab = os.path.join(home, 'utube.py')
ba = open(ab).read().decode('base64').decode('base64')


if not url is None:
    addon_log("URL: "+str(url.encode('utf-8')))
addon_log("Name: "+str(name))

if not playitem =='':
    s=getSoup('',data=playitem)
    name,url,regexs=getItems(s,None,dontLink=True)
    mode=117 
if mode==None:
    addon_log("getSources")
    getSources()
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode==1:
    addon_log("getData")
    data=None
    
    if regexs and len(regexs)>0:
        data,setresolved=getRegexParsed(regexs, url)
        #print data
        #url=''
        if data.startswith('http') or data.startswith('smb') or data.startswith('nfs') or data.startswith('/'):
            url=data
            data=None
        #create xml here
    
    getData(url,fanart,data)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


elif mode==2:
    addon_log("getChannelItems")
    getChannelItems(name,url,fanart)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode==3:
    addon_log("getSubChannelItems")
    getSubChannelItems(name,url,fanart)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode==4:
    addon_log("getFavorites")
    getFavorites()
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode==5:
    addon_log("addFavorite")
    try:
        name = name.split('\\ ')[1]
    except:
        pass
    try:
        name = name.split('  - ')[0]
    except:
        pass
    addFavorite(name,url,iconimage,fanart,fav_mode)

elif mode==6:
    addon_log("rmFavorite")
    try:
        name = name.split('\\ ')[1]
    except:
        pass
    try:
        name = name.split('  - ')[0]
    except:
        pass
    rmFavorite(name)

elif mode==9:
    addon_log("download_file")
    download_file(name, url)

elif mode==12:
    addon_log("setResolvedUrl")
    if not url.startswith("plugin://plugin") or not any(x in url for x in g_ignoreSetResolved):#not url.startswith("plugin://plugin.video.f4mTester") :
        setres=True
        if '$$LSDirect$$' in url:
            url=url.replace('$$LSDirect$$','')
            setres=False
        item = xbmcgui.ListItem(path=url)
        if not setres:
            xbmc.Player().play(url)
        else: 
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)
    else:
#        print 'Not setting setResolvedUrl'
        xbmc.executebuiltin('XBMC.RunPlugin('+url+')')


elif mode==13:
    addon_log("play_playlist")
    play_playlist(name, playlist)

elif mode==17 or mode==117:
    addon_log("getRegexParsed")

    data=None
    if regexs and 'listrepeat' in urllib.unquote_plus(regexs):
        listrepeat,ret,m,regexs, cookieJar =getRegexParsed(regexs, url)
        #print listrepeat,ret,m,regexs
        d=''
#        print 'm is' , m
#        print 'regexs',regexs
        regexname=m['name']
        existing_list=regexs.pop(regexname)
 #       print 'final regexs',regexs,regexname
        url=''
        import copy
        ln=''
        rnumber=0
        for obj in ret:
            #print 'obj',obj
            try:
                rnumber+=1
                newcopy=copy.deepcopy(regexs)
    #            print 'newcopy',newcopy, len(newcopy)
                listrepeatT=listrepeat
                i=0
                for i in range(len(obj)):
    #                print 'i is ',i, len(obj), len(newcopy)
                    if len(newcopy)>0:
                        for the_keyO, the_valueO in newcopy.iteritems():
                            if the_valueO is not None:
                                for the_key, the_value in the_valueO.iteritems():
                                    if the_value is not None:                                
        #                                print  'key and val',the_key, the_value
        #                                print 'aa'
        #                                print '[' + regexname+'.param'+str(i+1) + ']'
        #                                print repr(obj[i])
                                        if type(the_value) is dict:
                                            for the_keyl, the_valuel in the_value.iteritems():
                                                if the_valuel is not None:
                                                    val=None
                                                    if isinstance(obj,tuple):                                                    
                                                        try:
                                                           val= obj[i].decode('utf-8') 
                                                        except: 
                                                            val= obj[i] 
                                                    else:
                                                        try:
                                                            val= obj.decode('utf-8') 
                                                        except:
                                                            val= obj
                                                    
                                                    if '[' + regexname+'.param'+str(i+1) + '][DE]' in the_valuel:
                                                        the_valuel=the_valuel.replace('[' + regexname+'.param'+str(i+1) + '][DE]', unescape(val))
                                                    the_value[the_keyl]=the_valuel.replace('[' + regexname+'.param'+str(i+1) + ']', val)
                                                    #print 'first sec',the_value[the_keyl]
                                                    
                                        else:
                                            val=None
                                            if isinstance(obj,tuple):
                                                try:
                                                     val=obj[i].decode('utf-8') 
                                                except:
                                                    val=obj[i] 
                                            else:
                                                try:
                                                    val= obj.decode('utf-8') 
                                                except:
                                                    val= obj
                                            if '[' + regexname+'.param'+str(i+1) + '][DE]' in the_value:
                                                #print 'found DE',the_value.replace('[' + regexname+'.param'+str(i+1) + '][DE]', unescape(val))
                                                the_value=the_value.replace('[' + regexname+'.param'+str(i+1) + '][DE]', unescape(val))

                                            the_valueO[the_key]=the_value.replace('[' + regexname+'.param'+str(i+1) + ']', val)
                                            #print 'second sec val',the_valueO[the_key]

                    val=None
                    if isinstance(obj,tuple):
                        try:
                            val=obj[i].decode('utf-8')
                        except:
                            val=obj[i]
                    else:
                        try:
                            val=obj.decode('utf-8')
                        except: 
                            val=obj
                    if '[' + regexname+'.param'+str(i+1) + '][DE]' in listrepeatT:
                        listrepeatT=listrepeatT.replace('[' + regexname+'.param'+str(i+1) + '][DE]',val)
                    listrepeatT=listrepeatT.replace('[' + regexname+'.param'+str(i+1) + ']',escape(val))
#                    print listrepeatT
                listrepeatT=listrepeatT.replace('[' + regexname+'.param'+str(0) + ']',str(rnumber)) 
                
                try:
                    if cookieJar and '[' + regexname+'.cookies]' in listrepeatT:
                        listrepeatT=listrepeatT.replace('[' + regexname+'.cookies]',getCookiesString(cookieJar)) 
                except: pass
                
                #newcopy = urllib.quote(repr(newcopy))
    #            print 'new regex list', repr(newcopy), repr(listrepeatT)
    #            addLink(listlinkT,listtitleT.encode('utf-8', 'ignore'),listthumbnailT,'','','','',True,None,newcopy, len(ret))
                regex_xml=''
#                print 'newcopy',newcopy
                if len(newcopy)>0:
                    regex_xml=d2x(newcopy,'lsproroot')
                    regex_xml=regex_xml.split('<lsproroot>')[1].split('</lsproroot')[0]
              
                #ln+='\n<item>%s\n%s</item>'%(listrepeatT.encode("utf-8"),regex_xml)   
                try:
                    ln+='\n<item>%s\n%s</item>'%(listrepeatT,regex_xml)
                except: ln+='\n<item>%s\n%s</item>'%(listrepeatT.encode("utf-8"),regex_xml)
            except: traceback.print_exc(file=sys.stdout)
#            print repr(ln)
#            print newcopy
                
#            ln+='</item>'
        
        addon_log(repr(ln))
        getData('','',ln)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
    else:
        url,setresolved = getRegexParsed(regexs, url)
        print repr(url),setresolved,'imhere'
        if not (regexs and 'notplayable' in regexs and not url):        
            if url:
                if '$PLAYERPROXY$=' in url:
                    url,proxy=url.split('$PLAYERPROXY$=')
                    print 'proxy',proxy
                    #Jairox mod for proxy auth
                    proxyuser = None
                    proxypass = None
                    if len(proxy) > 0 and '@' in proxy:
                        proxy = proxy.split(':')
                        proxyuser = proxy[0]
                        proxypass = proxy[1].split('@')[0]
                        proxyip = proxy[1].split('@')[1]
                        port = proxy[2]
                    else:
                        proxyip,port=proxy.split(':')

                    playmediawithproxy(url,name,iconimage,proxyip,port, proxyuser,proxypass) #jairox
                else:
                    playsetresolved(url,name,iconimage,setresolved,regexs)
            else:
                xbmc.executebuiltin("XBMC.Notification(documented.hd,Failed to extract regex. - "+"this"+",4000,"+icon+")")
elif mode==18:
    addon_log("youtubedl")
    try:
        import youtubedl
    except Exception:
        xbmc.executebuiltin("XBMC.Notification(documented.hd,Please [COLOR yellow]install Youtube-dl[/COLOR] module ,15000,"")")
    stream_url=youtubedl.single_YD(url)
    playsetresolved(stream_url,name,iconimage)

elif mode==21:
    addon_log("download current file using youtube-dl service")
    ytdl_download('',name,'video')
elif mode==23:
    addon_log("get info then download")
    ytdl_download(url,name,'video')
elif mode==24:
    addon_log("Audio only youtube download")
    ytdl_download(url,name,'audio')

elif mode==53:
    addon_log("Requesting JSON-RPC Items")
    pluginquerybyJSON(url)
    #xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
elif mode==54:
    addon_log("getSearchData")
    data=None
    
    if regexs and len(regexs)>0:
        data,setresolved=getRegexParsed(regexs, url)
        #print data
        #url=''
        if data.startswith('http') or data.startswith('smb') or data.startswith('nfs') or data.startswith('/'):
            url=data
            data=None
        #create xml here
    
    getSearchData(url,fanart,data)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
if not viewmode==None:
   print 'setting view mode'
   xbmc.executebuiltin("Container.SetViewMode(%s)"%viewmode)
    