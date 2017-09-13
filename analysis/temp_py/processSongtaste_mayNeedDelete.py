#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
之前写的一些，关于下载博客中出现的Songtaste中的歌曲的Python代码。
也许需要彻底删除
暂时先放这里。

"""

gCfg ={
    'needProcessSt'     : '',
};

gVal = {
    'stInfo'                : {'fileName' : '', 'dirName' : '',},
};

#------------------------------------------------------------------------------
# generate ST music real time address
def genStRtAddr(strUrl, songId):
    reqStRtUrl = ''
    try :
        # Note: here not use urllib.urlencode to encode para, 
        #       for the encoded result will convert some special chars($,:,{,},...) into %XX
        paraDict = {
            'str'   :   '',
            'sid'   :   '',
        }
        paraDict['str'] = str(strUrl)
        paraDict['sid'] = str(songId)
        mainUrl = 'http://www.songtaste.com/time.php'
        reqStRtUrl = genFullUrl(mainUrl, paraDict)
        
        logging.debug("Geneated request ST song real time url=%s",reqStRtUrl)
    except :
        logging.debug("Fail to generate request ST song real time url for songID=%s", songId)
    
    return reqStRtUrl;

#------------------------------------------------------------------------------
# input: http://www.songtaste.com/song/2407245/
# extract ST song real address
# return the music artist and title
def parseStUrl(stSongUrl) :
    parsedOK = False
    songInfoDict = {
        'id'        : '',
        'title'     : '',
        'artist'    : '',
        'realAddr'  : '',
        'strUrl'    : '',
        'suffix'    : '',
        'playUrl'   : '',
    }
    
    try :
        #page = urllib2.urlopen(stSongUrl)
        #soup = BeautifulSoup(page, fromEncoding="GB18030") # page is GB2312

        # 1. extract artist
        # <h1 class="h1singer">Lucky Sunday</h1>
        #foundSinger = soup.find(attrs={"class":"h1singer"})
        #songInfoDict['artist'] = foundSinger.string
        
        # 2. extrac title
        # <p class="mid_tit">Rap(Ice ice baby)Mix</p>
        #foundTitle = soup.find(attrs={"class":"mid_tit"})
        #songInfoDict['title'] = foundTitle.string

        # 3. extrat real addr
        # /playmusic.php?song_id=2407245
        # http://www.songtaste.com/playmusic.php?song_id=2407245
        songId = stSongUrl.split('/')[4]
        playmusicUrl = "http://www.songtaste.com/playmusic.php?song_id=" + songId
        songInfoDict['playUrl'] = playmusicUrl
        
        # <div class="p_songlist" id="songlist">
        # <UL id=songs>
        # <script>
        # WrtSongLine("2407245", "Rap(Ice ice baby)Mix ", "Lucky Sunday ", "0", "0", "http://224.cachefile34.rayfile.com/227b/zh-cn/download/d18c6b179f388d1bf1f1d30946802c8a/preview.mp3", "cachefile34.rayfile.com/227b/zh-cn/download/d18c6b179f388d1bf1f1d30946802c8a/preview");
        # </script>
        # </UL>
        # </DIV> 
        page = urllib2.urlopen(playmusicUrl)
        soup = BeautifulSoup(page, fromEncoding="GB18030")
        foundSonglist = soup.find(id='songlist')
        #print "foundSonglist=",foundSonglist
        #print "foundSonglist.ul=",foundSonglist.ul
        #print "foundSonglist.ul.script=",foundSonglist.ul.script
        wrtSongStr = foundSonglist.ul.script.string
        #                                      1=id     2=title  3=artist                        4=realAddr  5=strUrl
        wrtSongP = re.compile(r'WrtSongLine\("(\d+)",\s*"(.*?)",\s*"(.*?)",\s*"\d+",\s*"\d+",\s*"(.*?)",\s*"(.*?)"\);')
        # note : for rayfile address, eg:
        # -> http://www.songtaste.com/song/2407245/
        # this kind of method can extract the real address:
        # http://224.cachefile34.rayfile.com/227b/zh-cn/download/d18c6b179f388d1bf1f1d30946802c8a/preview.mp3
        # strUrl = cachefile34.rayfile.com/227b/zh-cn/download/d18c6b179f388d1bf1f1d30946802c8a/preview
        # but for : 
        # -> http://www.songtaste.com/song/2460118/
        # the extracted real address is:
        # http://m4.songtaste.com/201201092047/88601655c1388a9511c805807a6532f0/4/44/44cbec83ad2d1d4817c228cc2f2c402f.mp3
        # strUrl = 5aa9ecd9e8a48a612541c722d0d83296f3a2958a7d26c275c8464541b2e9cc4b3f3cdaa848f4efe42f1ced3fe51ffc51
        # but when click to play it, the real address will change to :
        # http://m4.songtaste.com/201201092045/cb7ca1c407a0992955264bdbd1e12250/4/44/44cbec83ad2d1d4817c228cc2f2c402f.mp3
        # http://m4.songtaste.com/201201092103/09e62bed7108ea2ee6f413a6ab53e5c5/4/44/44cbec83ad2d1d4817c228cc2f2c402f.mp3
        # in which, cb7ca1c407a0992955264bdbd1e12250 and 09e62bed7108ea2ee6f413a6ab53e5c5 is depend on time

        foundWrt = wrtSongP.search(wrtSongStr)
        id          = foundWrt.group(1)
        title       = foundWrt.group(2)
        artist      = foundWrt.group(3)
        realAddr    = foundWrt.group(4)
        strUrl      = foundWrt.group(5)

        # (1) process real address
        rayfilePos = strUrl.find('rayfile')
        if rayfilePos > 0 : # is 'rayfile' kind of addr
            logging.debug("Rayfile type realAddr=%s", realAddr)
        else :
            # is songtaste kind of addr
            # generate the url to request the real time address for this song
            reqStRtAddr = genStRtAddr(strUrl, id)
            # returned real time addr is like this:
            # http://m4.songtaste.com/201201092150/02c112717113b01e8ebeba5d16899fe0/4/44/44cbec83ad2d1d4817c228cc2f2c402f.mp3
            page = urllib2.urlopen(reqStRtAddr)
            # paraDict = {
                # 'str'   :   '',
                # 'sid'   :   '',
            # }
            # paraDict['str'] = str(strUrl)
            # paraDict['sid'] = str(id)
            # mainUrl = 'http://www.songtaste.com/time.php'
            # encodedPara = urllib.urlencode(paraDict)
            # stReq = urllib2.Request(mainUrl, encodedPara)
            # stReq.add_header('User-Agent', "Mozilla/4.0 (compatible;MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)")
            # stReq.add_header('User-Agent', "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.63 Safari/535.7")
            # stReq.add_header('Connection', "keep-alive")
            # stReq.add_header('Cache-Control', "max-age=0")
            # stReq.add_header('Host', "www.songtaste.com")
            #page = urllib2.urlopen(stReq)
            
            soup = BeautifulSoup(page)
            realAddr = unicode(soup)

            # TODO:
            # here even got real time address, but when use urllib2.urlopen to open it, will got error:
            # URLError when open http://mc.songtaste.com/201201092326/0236b1e2fa71933486a7315b487fd4b7/c/c0/c0eeecf337478a761c25f9ac9943d86d.mp3, reason=HTTP Error 403: Forbidden
            # need to fix this problem
            #crifanLib.isFileValid(realAddr)
            
            logging.debug("Extracted real addess  =%s", foundWrt.group(4))
            logging.debug("Songtaste type realAddr=%s", realAddr)

        # (2) process title
        title  = title.strip().rstrip()
        # (3) process artist
        artist = artist.strip().rstrip()
        # (4) process suffix
        sufPos = realAddr.rfind('.')
        suffix = realAddr[(sufPos + 1) : ]
        
        # 4. set values
        songInfoDict['id']      = id
        songInfoDict['title']   = title
        songInfoDict['artist']  = artist
        songInfoDict['realAddr']= realAddr
        songInfoDict['strUrl']  = strUrl
        songInfoDict['suffix']  = suffix

        parsedOK = True
        
        logging.debug("For ST song url %s, parsed info: id=%s, title=%s, artist=%s, realAddr=%s, strUrl=%s",
            stSongUrl, id, title, artist, realAddr, strUrl)
    except :
        parsedOK = False
        logging.debug("Fail to parse ST url %s", stSongUrl)

    return (parsedOK, songInfoDict)


#------------------------------------------------------------------------------
# output ST music info
def outputStInfo(info) :
    global gVal
    infoFile = codecs.open(gVal['stInfo']['fileName'], 'a+', 'utf-8')
    infoFile.write(info + '\n')
    infoFile.close()
    return


#------------------------------------------------------------------------------
# extract ST music url 
# download music 
def downloadStMusic(blogContent) :
    global gval
    if gCfg['needProcessSt'] == 'yes' :
        # <a href="http://www.songtaste.com/song/2407245/" target="_blank">
        # [夜店魅音Mix]ICE ICE BABY 炫音超棒Rap风[精神节拍]≈
        # </a>

        # 1. extarct the ST song urls
        stUrlP = r"http://www\.songtaste\.com/song/\d+/"
        stUrlP = re.compile(stUrlP)
        stUrlList = stUrlP.findall(blogContent)
        if stUrlList :
            uniUrlList = crifanLib.uniqueList(stUrlList)
            (filteredList, existedList) = filterList(uniUrlList, gVal['processedStUrlList'])
            if filteredList :
                logging.debug("Found ST song urls to process:")
                for stUrl in filteredList : logging.debug("%s", stUrl)

                for stUrl in filteredList :
                    # no matter following process is OK or not, all means processed
                    gVal['processedStUrlList'].append(stUrl)
                
                    # 2. extract the real song addr for this song url
                    (parsedOK, songInfoDict) = parseStUrl(stUrl)
                    if parsedOK :
                        # 3. download this song
                        # (1) generated the name
                        fullName = songInfoDict['title'] + ' - ' + songInfoDict['artist']
                        fullName += '.' + songInfoDict['suffix']

                        # (2) download and save it
                        dstName = gVal['stInfo']['dirName'] + '/' + fullName # here '/' is also valid in windows dir path
                        crifanLib.downloadFile(songInfoDict['realAddr'], dstName);
                        
                        # (3) output related info
                        # generated quoted name to facilicate later input music url in wordpress
                        fullNameGb18030 = fullName.encode("GB18030")
                        quotedName = urllib.quote(fullNameGb18030)
                        outputStInfo("%s ST Song Info %s" % ('-'*30, '-'*30))
                        outputStInfo("Song    URL: %s" % stUrl)
                        outputStInfo("Song     ID: %s" % songInfoDict['id'])
                        outputStInfo("Playe   URL: %s" % songInfoDict['playUrl'])
                        outputStInfo("Title      : %s" % songInfoDict['title'])
                        outputStInfo("Artist     : %s" % songInfoDict['artist'])
                        outputStInfo("Saved  Name: %s" % fullName)
                        outputStInfo("Quoted Name: %s" % quotedName)
                        outputStInfo("RealAddress: %s" % songInfoDict['realAddr'])
                        outputStInfo("strUrl     : %s" % songInfoDict['strUrl'])
    return

#------------------------------------------------------------------------------
# create output info file for ST music
def initStInfo() :
    global gVal
    gVal['stInfo']['dirName'] = '.' + '/' + 'songtaste'
    if (os.path.isdir(gVal['stInfo']['dirName']) == False) :
        os.makedirs(gVal['stInfo']['dirName']) # create dir recursively
        logging.info("Create dir %s for save downloaded ST music file", gVal['stInfo']['dirName'])
    gVal['stInfo']['fileName'] = gVal['stInfo']['dirName'] + '/' + 'songtasteMusicInfo' + datetime.now().strftime('_%Y%m%d%H%M') + '.txt'
    infoFile = codecs.open(gVal['stInfo']['fileName'], 'w', 'utf-8')
    if infoFile:
        logging.info('Created file %s for store extracted ST info', gVal['stInfo']['fileName'])
        infoFile.close()
    else:
        logging.warning("Can not create output info file: %s", gVal['stInfo']['fileName'])
    return

#------------------------------------------------------------------------------
def postProcessContent(blogContent) :
        # 3. download ST music if necessary
        #downloadStMusic(afterFilter);
        
#------------------------------------------------------------------------------
def main() :
    parser.add_option("-g","--needProcessSt",action="store",type="string",default="no",dest="needProcessSt",help="Need to process songtaste music or not. Default to 'no'.")
    
        gCfg['needProcessSt'] = needProcessSt;
        if gCfg['needProcessSt'] == 'yes' :
            initStInfo();
