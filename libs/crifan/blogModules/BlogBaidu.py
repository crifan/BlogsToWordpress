#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for (new) Baidu space/blog.

[TODO]
[v3.5]
1.update for only support baidu new space

[History]
[v3.4]
1.fix bug for catetory extract, commited by Zhenyu Jiang

[v3.3]
1. support login mode and check private post and modify post for new baidu space
2. new baidu html changed, update to support new title and content

[v2.2]
1. add support for new baidu space
2. support many template for new baidu space, include: 
时间旅程,平行线,边走边看,窗外风景,雕刻时光,粉色佳人,理性格调,清心雅筑,低调优雅,蜕变新生,质感酷黑,经典简洁
3. support non-title post for new baidu space

[v1.3]
1. support old baidu space

"""

import os;
import re;
import sys;
import time;
import chardet;
import urllib;
import urllib2;
from datetime import datetime,timedelta;
from BeautifulSoup import BeautifulSoup,Tag,CData;
import logging;
import crifanLib;
import cookielib;
from xml.sax import saxutils;
import random;
import json; # New in version 2.6.
import binascii;

#import ast;

#--------------------------------const values-----------------------------------
__VERSION__ = "v3.5";

gConst = {
    'baiduSpaceDomain'  : 'http://hi.baidu.com',
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',   # serial_story
    'blogEntryUrl'  : '',   # http://hi.baidu.com/recommend_music
    'cj'            : None, # cookiejar, to store cookies for login mode
    'spToken'       : '',
    
    'soupDict'      : {},   # cache the soup for url's html -> url : soup
    
    'isNewBaiduSpace': False,   # indicate is new baidu space or not
                                # old: http://hi.baidu.com/serial_story
                                # new: http://hi.baidu.com/new/serial_story
    'songsDict'     : {},   # store songId,songInfDict, note songId is str type
    'noTitleItemsDict': {}, # url,songId
}

################################################################################
# Internal baidu space Functions 
################################################################################

def htmlToSoup(html):
    soup = None;
    
    if(gVal['isNewBaiduSpace']):
        # new baidu space use utf8 charset
        soup = BeautifulSoup(html, fromEncoding="UTF-8");
    else:
        # Note:
        # (1) baidu and 163 blog all use charset=gbk, but some special blog item:
        # http://chaganhu99.blog.163.com/blog/static/565262662007112245628605/
        # will messy code if use default gbk to decode it, so set GB18030 here to avoid messy code
        # (2) after BeautifulSoup process, output html content already is utf-8 encoded
        soup = BeautifulSoup(html, fromEncoding="GB18030");
        #prettifiedSoup = soup.prettify();
        #logging.debug("Got post html\n---------------\n%s", prettifiedSoup);
    return soup;

#------------------------------------------------------------------------------
# get url's soup
def getSoupFromUrl(url):
    soup = None;
    
    if(url in gVal['soupDict']) :
        logging.debug("%s exist in soupDict, so get soup from cache", url);
        soup = gVal['soupDict'][url];
    else :
        logging.debug("%s not in soupDict, so get html then get soup", url);
        
        # get url's soup
        html = crifanLib.getUrlRespHtml(url);
        soup = htmlToSoup(html);
        
        # store soup
        gVal['soupDict'][url] = soup;
    
    return soup;

#------------------------------------------------------------------------------
# forcely convert some char into %XX, XX is hex value for the char
# eg: recommend_music -> recommend%5Fmusic
def doForceQuote(originStr) :
    quotedStr = '';
    specialList = ['_']; # currently only need to convert the '_'

    for c in originStr :
        if c in specialList :
            cHex = binascii.b2a_hex(c);
            cHexStr = '%' + str(cHex).upper();
            quotedStr += cHexStr;
        else :
            quotedStr += c;

    return quotedStr;

#------------------------------------------------------------------------------
#extract baidu blog user name
# 1. old baidu space
# eg: recommend_music
# (1)   http://hi.baidu.com/recommend_music
#       http://hi.baidu.com/recommend_music/
#       http://hi.baidu.com/recommend_music/blog
#       http://hi.baidu.com/recommend_music/blog/
# (2)   http://hi.baidu.com/recommend_music/blog/item/f36b071112416ac3a6ef3f0e.html
# 2. new baidu space
# (1)   http://hi.baidu.com/new/serial_story
#       http://hi.baidu.com/new/serial_story/
#       http://hi.baidu.com/new/serial_story/blog
#       http://hi.baidu.com/new/serial_story/blog/
# (2)   http://hi.baidu.com/serial_story/item/5625cfbbabf08fa7ebba9319
#       http://hi.baidu.com/serial_story/item/5625cfbbabf08fa7ebba9319/
def extractBlogUser(inputUrl):
    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
    logging.debug("Extracting blog user from url=%s", inputUrl);
        
    try :
        #now only support baidu new space, for baidu self not support old space anymore
        gVal['isNewBaiduSpace'] = True;
        logging.info("Now only support the new baidu space for baidu officially not support its old space anymore.");
        
        # type1: main url or post item url
        #http://hi.baidu.com/rec_music
        #http://hi.baidu.com/rec_music/
        #http://hi.baidu.com/rec_music/item/e1c214c3b824037ecfd4f8aa
        #http://hi.baidu.com/rec_music/item/e1c214c3b824037ecfd4f8aa/
        foundMainOrItemUrl = re.search("http://hi\.baidu\.com/(?P<username>[\w\-_]+)(/item/\w+)?/?$", inputUrl);
        logging.debug("foundMainOrItemUrl=%s", foundMainOrItemUrl);
        if(foundMainOrItemUrl) :
            extractedBlogUser   = foundMainOrItemUrl.group("username");

            generatedBlogEntryUrl = gConst['baiduSpaceDomain'] + "/" + extractedBlogUser;
            extractOk = True;
    except :
        (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
        
    if (extractOk) :
        gVal['blogUser'] = extractedBlogUser;
        gVal['blogEntryUrl'] = generatedBlogEntryUrl;
        logging.debug("blogUser=%s, blogEntryUrl=%s", gVal['blogUser'], gVal['blogEntryUrl']);

    return (extractOk, extractedBlogUser, generatedBlogEntryUrl);

#------------------------------------------------------------------------------
# generate url to get post
def genGetPostUrl(size, year, portrait, page, month):

    getPostUrl = "";
    #http://hi.baidu.com/new/data/timeline?qing_request_source=new_request&size=20&year=2007&portrait=292273657269616c5f73746f72794f02&page=1&month=4&b1342777001818=1
    #http://hi.baidu.com/new/data/timeline?qing_request_source=new_request&size=20&year=2007&portrait=292273657269616c5f73746f72794f02&page=1&month=4&b1342796162384=1

    # Note: here not use urllib.urlencode to encode para, 
    #       for the encoded result will convert some special chars($,:,{,},...) into %XX
    paraDict = {
        'qing_request_source'   : "new_request",
        'size'                  : str(size),
        'year'                  : str(year),
        'portrait'              : str(portrait),
        'page'                  : str(page),
        'month'                 : str(month),
        # tmp not add b value here
    };
        
    mainUrl = "http://hi.baidu.com/new/data/timeline";

    getPostUrl = crifanLib.genFullUrl(mainUrl, paraDict);
    logging.debug("generated url is %s",getPostUrl);

    return getPostUrl;

#------------------------------------------------------------------------------
# find the earlist year month and number of posts from dict
def findEarliestYearMonth(timeFillingInfoDict):
    (foundEarlist, earliestDict) = (False, {});
    
    earliestDict = {
        'year'      : 9999,
        'month'     : 0,
        'postNum'   : 0,
    }

    # find earliest year
    for yearStr in timeFillingInfoDict:
        logging.debug("yearStr=%s", yearStr);
        yearInt = int(yearStr);
        #logging.info("yearInt=%s", yearInt);
        totalCountStr = timeFillingInfoDict[yearStr]['totalCount'];
        logging.debug("totalCountStr=%s", totalCountStr);
        totalCountInt = int(totalCountStr);
        #logging.info("totalCountInt=%s", totalCountInt);
        if((totalCountInt > 0) and (yearInt < earliestDict['year'])):
            earliestDict['year'] = yearInt;
   
    logging.debug("found earliestDict['year']=%s", earliestDict['year']);
    earyliestYearStr = str(earliestDict['year']);
    earliestYearDict = timeFillingInfoDict[earyliestYearStr];
    logging.debug("found earliestYearDict=%s", earliestYearDict);
    logging.debug("earyliestYear: totalCount=%s, month=%s", earliestYearDict['totalCount'], earliestYearDict['month']);

    monthList = earliestYearDict['month'];
    logging.debug("monthList=%s", monthList);

    for monthIdx in range(12):
        logging.debug("monthIdx=%s", monthIdx);
        postNum = monthList[monthIdx];
        logging.debug("postNum=%s", postNum);
        if(postNum > 0):
            earliestDict['month'] = monthIdx + 1;
            earliestDict['postNum'] = postNum;
            logging.debug("found the earliest monthNumber=%d, postNumber=%d", earliestDict['month'], earliestDict['postNum']);
            foundEarlist = True;
            break;
    
    logging.debug("earliestDict=%s", earliestDict);
    
    return (foundEarlist, earliestDict);

#------------------------------------------------------------------------------
# get the last page html from page info
# Note: input value type is int
def getLastPageHtmlFromPageInfo(allCount, pageSize):
    maxPageNum = allCount/pageSize;
    logging.debug("maxPageNum=%d", maxPageNum);
    if(0 != (allCount - maxPageNum*pageSize)):
        maxPageNum = maxPageNum + 1;
    logging.debug("found max page number = %d", maxPageNum);
    
    # gen max page url
    #http://hi.baidu.com/new/serial_story?page=88
    lastPageUrl = gVal['blogEntryUrl'] + "?page=" + str(maxPageNum);
    logging.debug("last Page Url=%s", lastPageUrl);

    # get last page html
    lastPageHtml = crifanLib.getUrlRespHtml(lastPageUrl);
    logging.debug("lastPageHtml=%s", lastPageHtml);
    
    return lastPageHtml;

#------------------------------------------------------------------------------
# extract the last (post) item url from the page html
def extractLastItemUrlFromPageHtml(pageHtml):
    (found, retInfo) = (False, "");
       
    #http://hi.baidu.com/new/serial_story?page=88
    #theme: 边走边看
    # (function() {

         # var data = {

            # count: 3,

            # items: [ ".........." ]

         # };

         # qing.dom.ready(function() {

             # qhome.load(data);

         # });
    
    #http://hi.baidu.com/new/serial_story?page=88
    #theme: 平行线
    # (function() {

        # var data = {

            # count: 3,

            # items: [ "......" ]

        # };

        # qhome.initPageBar({

            # container: 'pageBar',

            # allCount: 873,

            # pageSize: 10,

            # curPage: 88

        # });

        # qhome.load(data);

    # })();
    
    foundItemsJson = re.search("\(function\(\)\s*?\{\s*?var\s+?data\s*?=\s*?\{\s*?count\s*?:\s*?(?P<count>\d+),\s*?items\s*?:\s*?(?P<items>\[\s*?\".+?\"\s*\])\s*?\};", pageHtml);
    logging.debug("foundItemsJson=%s", foundItemsJson);
    if(foundItemsJson):
        count = foundItemsJson.group("count");
        logging.debug("count=%s", count);
        items = foundItemsJson.group("items");
        logging.debug("items=%s", items);
        
        itemsList = json.loads(items);
        logging.debug("itemsList=%s", itemsList);
        lastItemStr = itemsList[-1];
        logging.debug("lastItemStr=%s", lastItemStr);
        
        postSoup = htmlToSoup(lastItemStr);
        logging.debug("postSoup=%s", postSoup);

        #http://hi.baidu.com/new/serial_story?page=88
        #<div class=mod-blogitem-title> <a target=_blank href="/serial_story/item/0c450a1440b768088fbde426">为什么幸运的人总幸运倒霉的人老倒霉-1   斯宾塞·约翰逊著</a> </div>
        
        #http://hi.baidu.com/new/choklk?page=1
        #<div class=mod-blogitem-title> <a target=_blank href="/choklk/item/6a189ccb30ac35cc9644523a"> 美呢 </a> </div>
        
        #http://hi.baidu.com/new/xsen1216?page=11
        #<div class=mod-blogitem-title> <a target=_blank href="/xsen1216/item/1e6ad8c4fbcc457188ad9e7b">没你的天空要快乐</a> </div>
        foundBlogitem = postSoup.find(attrs={"class":"mod-blogitem-title"});
        logging.debug("foundBlogitem=%s", foundBlogitem);
        if(foundBlogitem):
            itemAHref = foundBlogitem.a['href']; #/serial_story/item/0c450a1440b768088fbde426
            lastItemUrl = gConst['baiduSpaceDomain'] + itemAHref; # http://hi.baidu.com/serial_story/item/0c450a1440b768088fbde426
            
            found = True;
            retInfo = lastItemUrl;
        else:
            found = False;
            retInfo = "Can't not find class mod-blogitem-title for earliest item";
    else:
        found = False;
        retInfo = "Can't not find items json string";

    return (found, retInfo);

#------------------------------------------------------------------------------
# find the first permanent link = url of the earliset published blog item
# Note: make sure the gVal['blogUser'] is valid before call this func
def find1stPermalink():
    global gConst;
    global gVal;
    
    fristLink = "";
    
    (isFound, retInfo) = (False, "Unknown error!");
    
    linkNode = '';
    
    try :
        if(gVal['isNewBaiduSpace']):
            #find max page num
            page0Url = gVal['blogEntryUrl'];
            logging.debug("Begin to find max page number from url=%s", page0Url);
            respHtml = crifanLib.getUrlRespHtml(page0Url);
            #logging.debug("respHtml=%s", respHtml);
            soup = htmlToSoup(respHtml);
            
            # type 1
            #foundPageRelatedInfo = re.search("(?P<pageBar>container\s*?:\s*? 'pageBar',\s*?)?allCount\s*?:\s*?'?(?P<allCount>\d+)'?,\s+?pageSize\s*?:\s*?'?(?P<pageSize>\d+)'?,\s+?curPage\s*?:\s*?'?(?P<curPage>\d+)'?\s*?}", respHtml);
            foundPageRelatedInfo = re.search("(?P<pageBar>container\s*?:\s*? 'pageBar',\s*?)?allCount\s*?:\s*?'?(?P<allCount>\d+)'?,\s+?pageSize\s*?:\s*?'?(?P<pageSize>\d+)'?,\s+?curPage\s*?:\s*?'?(?P<curPage>\d+)'?(?P<linkCount>,\s*?linkCount\s*?:\s*?\d+,.+?)?\s*?\}", respHtml, re.S);
            logging.debug("foundPageRelatedInfo=%s", foundPageRelatedInfo);
            
            # type 2
            foundTimeFillingInfo = re.search(r"var qTimeFilingInfo = (?P<timeFillingInfoJson>{.+?});\s", respHtml, re.S);
            logging.debug("foundTimeFillingInfo=%s", foundTimeFillingInfo);
            
            #type 3
            foundItemInfo = re.search("qhome.init\(\{\s*?allItemCount\s*?:\s*?(?P<allItemCount>\d+),\s*?pageItemCount\s*?:\s*?(?P<pageItemCount>\d+),\s*?currentPage\s*?:\s*?(?P<currentPage>\d+)", respHtml);
            logging.debug("foundItemInfo=%s", foundItemInfo);
            
            if(foundPageRelatedInfo):
                pageBar     = foundPageRelatedInfo.group("pageBar");
                
                allCount    = foundPageRelatedInfo.group("allCount");
                pageSize    = foundPageRelatedInfo.group("pageSize");
                curPage     = foundPageRelatedInfo.group("curPage");
                
                linkCount   = foundPageRelatedInfo.group("linkCount");
                logging.debug("pageBar=%s, allCount=%s, pageSize=%s, curPage=%s, linkCount=%s", pageBar, allCount, pageSize, curPage, linkCount);
                
                allCount = int(allCount);
                pageSize = int(pageSize);
                curPage = int(curPage);
                
                lastPageHtml = getLastPageHtmlFromPageInfo(allCount, pageSize);
                
                soup = htmlToSoup(lastPageHtml);

                if(pageBar):
                    # supported theme: 平行线
                    #http://hi.baidu.com/new/serial_story
                    # qhome.initPageBar({

                        # container: 'pageBar',

                        # allCount: 873,

                        # pageSize: 10,

                        # curPage: 0

                    # });
                    
                    #http://hi.baidu.com/new/serial_story?page=88
                    # (function() {

                        # var data = {

                            # count: 3,

                            # items: [ "............" ]

                        # };

                        # qhome.initPageBar({
                    
                    logging.debug("Exist extral pageBar");

                    (isFound, retInfo) = extractLastItemUrlFromPageHtml(lastPageHtml);
                elif(linkCount):
                    # supported theme: 窗外风景
                    
                    #http://hi.baidu.com/new/serial_story
                    # var PagerInfo = {
                        # allCount : '878',
                        # pageSize : '10',
                        # curPage : '0',
                        # linkCount : 5,
                        # button : [
                            # 'number',
                            # 'prev',
                            # 'next'
                        # ],
                        # tpl : {
                            # nextNone : '<span class="first none"></span>',
                            # prevNone : '<span class="prev none"></span>'
                        # },
                        # text : {
                            # next : '',
                            # prev : ''
                        # }
                    # };
                    logging.debug("Exist extral linkCount");
                    
                    # <div class=blog-list>
                        # <a href="http://hi.baidu.com/serial_story/item/7d86d17b537d643c70442326" class="blog-item blog-text block0" id="23498943" target=_blank data-timestamp="1181265955"><div class=text-container><span class=quote-left>&nbsp;</span>I/O-Programming_HOWTO(上)zz<span class=quote-right>&nbsp;</span></div></a>
                        # ......
                        # <a href="http://hi.baidu.com/serial_story/item/0c450a1440b768088fbde426" class="blog-item blog-text block7" id="23498876" target=_blank data-timestamp="1177462065"><div class=text-container><span class=quote-left>&nbsp;</span>为什么幸运的人总幸运倒霉的人老倒霉-1   斯宾塞·约翰逊著<span class=quote-right>&nbsp;</span></div></a>
                        # <span class="blog-item-empty block8"></span>
                        # <span class="blog-item-empty block9"></span>
                     # </div>
                    foundBlogList = soup.find(attrs={"class":"blog-list"});
                    #logging.info("foundBlogList=%s", foundBlogList);
                    if(foundBlogList):
                        foundAList = foundBlogList.findAll("a");
                        logging.debug("len(foundAList)=%s", len(foundAList));
                        #logging.info("foundAList=%s", foundAList);
                        lastA = foundAList[-1];
                        logging.debug("lastA=%s", lastA);
                        #logging.info("lastA.contents=%s", lastA.contents);
                        lastAHref = lastA['href'];
                        logging.debug("lastAHref=%s", lastAHref);
                        
                        isFound = True;
                        retInfo = lastAHref;
                    else:
                        isFound = False;
                        retInfo = "Can't not find class=blog-list";
                else:
                    # supported theme: 蜕变新生，经典简洁，质感酷黑，低调优雅，清心雅筑，理性格调，粉色佳人，雕刻时光
                    
                    #http://hi.baidu.com/new/serial_story
                    # <section id=pagerBar class=mod-blog-pagerbar> <script>
                                        # var PagerInfo = {
                                            # allCount : '878',
                                            # pageSize : '10',
                                            # curPage : '0'
                                        # };
                                    # </script> </section>
                                    
                    #http://hi.baidu.com/new/serial_story?page=8
                    # <section id=pagerBar class=mod-blog-pagerbar> <script>
                                        # var PagerInfo = {
                                            # allCount : '878',
                                            # pageSize : '10',
                                            # curPage : '8'
                                        # };
                                    # </script> </section>

                    
                    
                    #<div class=item-head><div class="hide q-username"><a href="/new/serial_story" class=a-normal target=_blank>againinput4</a></div><a href="/serial_story/item/7d86d17b537d643c70442326" class="a-incontent a-title" target=_blank>I/O-Programming_HOWTO(上)zz</a></div>
                    
                    #<div class="item-head"><div class="hide q-username"><a href="/new/serial_story" class="a-normal" target="_blank">againinput4</a></div><a href="/serial_story/item/0c450a1440b768088fbde426" class="a-incontent a-title cs-contentblock-hoverlink" target="_blank">为什么幸运的人总幸运倒霉的人老倒霉-1   斯宾塞·约翰逊著</a></div>
                    foundItemHeaders = soup.findAll(attrs={"class":"item-head"});
                    logging.debug("foundItemHeaders=%s", foundItemHeaders);
                    if(foundItemHeaders):
                        lastItem = foundItemHeaders[-1];
                        logging.debug("lastItem=%s", lastItem);
                        logging.debug("lastItem.contents=%s", lastItem.contents);
                        titleP = re.compile("a-incontent a-title(\s+?\w+)?");# also match a-incontent a-title cs-contentblock-hoverlink
                        foundIncontentTitle = lastItem.find(attrs={"class":titleP});
                        logging.debug("foundIncontentTitle=%s", foundIncontentTitle);
                        if(foundIncontentTitle):
                            lastItemAHref = foundIncontentTitle['href'];
                            logging.debug("lastItemAHref=%s", lastItemAHref);
                            #/serial_story/item/7d86d17b537d643c70442326
                            lastPermaLink = gConst['baiduSpaceDomain'] + lastItemAHref;
                            #http://hi.baidu.com/serial_story/item/7d86d17b537d643c70442326
                            logging.debug("lastPermaLink=%s", lastPermaLink);
                            
                            isFound = True;
                            retInfo = lastPermaLink;
                        else:
                            isFound = False;
                            retInfo = "Can't not find class=a-incontent a-title";
                    else:
                        isFound = False;
                        retInfo = "Can't not find class=item-head";
            elif(foundTimeFillingInfo):
                # support theme: 时间旅行
                timeFillingInfoJson = foundTimeFillingInfo.group("timeFillingInfoJson");
                logging.debug("timeFillingInfoJson=%s", timeFillingInfoJson);
                
                timeFillingInfoJson = timeFillingInfoJson.replace("month", '"month"');
                timeFillingInfoJson = timeFillingInfoJson.replace("totalCount", '"totalCount"');
                timeFillingInfoJson = timeFillingInfoJson.replace("\t", "");
                timeFillingInfoJson = timeFillingInfoJson.replace("\r", "");
                timeFillingInfoJson = timeFillingInfoJson.replace("\n", "");
                timeFillingInfoJson = timeFillingInfoJson.replace("'", '"');
                #timeFillingInfoJson = timeFillingInfoJson.replace('"', "'");
                
                #http://hi.baidu.com/new/secret
                #{"2012" : {"month" : [0,0,0,0,1,3,0,-1,-1,-1,-1,-1],"totalCount" : "4"},"2011" : {"month" : [10,2,1,1,4,,1,1,0,0,0,0],"totalCount" : "20"},"2010" : {"month" : [4,0,0,9,2,5,18,,0,1,0,7],"totalCount" : "46"},"2009" : {"month" : [-1,-1,-1,-1,11,6,10,5,0,3,5,11],"totalCount" : "51"}}
                timeFillingInfoJson = re.sub(",\s*?,", ",0,", timeFillingInfoJson);
                timeFillingInfoJson = re.sub("\[\s*?,", "\[0,", timeFillingInfoJson);
                timeFillingInfoJson = re.sub(",\s*?\]", ",0\]", timeFillingInfoJson);
                logging.debug("after filter, timeFillingInfoJson=%s", timeFillingInfoJson);
                
                timeFillingInfoDict = json.loads(timeFillingInfoJson);
                logging.debug("timeFillingInfoDict=%s", timeFillingInfoDict);
                                
                (foundEarlist, earliestDict) = findEarliestYearMonth(timeFillingInfoDict);
                
                if(foundEarlist):# found earliest
                    #http://hi.baidu.com/new/datasoldier
                    #window.qUserInfo={"userName":"dtminer","portrait":"e57864617461736f6c646965726207",
                    
                    #http://hi.baidu.com/new/serial_story
                    #window.qUserInfo={"userName":"againinput4","portrait":"292273657269616c5f73746f72794f02",
                    
                    #http://hi.baidu.com/new/tmcsyy123
                    #window.qUserInfo={"userName":"田明春","portrait":"cc67746d637379793132336a06",
                    
                    foundPortrait = re.search(r'window.qUserInfo={"userName":".+?","portrait":"(?P<portrait>\w+)",', respHtml);
                    logging.debug("foundPortrait=%s", foundPortrait);
                    if(foundPortrait):
                        portrait = foundPortrait.group("portrait");
                        logging.debug("portrait=%s", portrait);
                        
                        size = earliestDict['postNum'];
                        page = 1;
                        month = earliestDict['month'];
                        year = earliestDict['year'];
                    
                        getPostUrl = genGetPostUrl(size, year, portrait, page, month);
                        logging.debug("getPostUrl=%s", getPostUrl);
                        respPostJson = crifanLib.getUrlRespHtml(getPostUrl);
                        logging.debug("respPostJson=%s", respPostJson);
                        
                        # search all post, and find the last one
                        
                        #,id : '0c450a1440b768088fbde426',url : 'http:\/\/hi.baidu.com\/serial_story\/item\/0c450a1440b768088fbde426',title : '为什么幸运的人总幸运倒霉的人老倒霉-1   斯宾塞·约翰逊著',
                        #foundUrlList = re.findall("url\s*?:\s*?'(?P<url>http:\\/\\/hi\.baidu\.com\\/\w+?\\/item\\/\w+?)'", respPostJson);# strange, not work !!!
                        
                        #foundUrlList = re.findall("url\s*?:\s*?'(?P<url>http:.+?)'", respPostJson); # work
                        #but result for: http://hi.baidu.com/new/youya280
                        #foundUrlList=['http:\\/\\/hi.baidu.com\\/youya280\\/item\\/38168cab7b56a6596cd455f4', 'http:\\/\\/b.hiphotos.baidu.com\\/space\\/abpic\\/item\\/aec379310a55b3198aa72dde43a98226cffc173a.jpg', 'http:\\/\\/b.hiphotos.baidu.com\\/space\\/pic\\/item\\/aec379310a55b3198aa72dde43a98226cffc173a.jpg']
                        
                        #foundUrlList = re.findall("url\s*?:\s*?'(?P<url>http:.+?hi\.baidu\.com.+?)'", respPostJson);
                        #foundUrlList = re.findall("url\s*?:\s*?'(?P<url>http:\\/\\/hi\.baidu\.com\\/.+?\\/item\\/\w+?)'", respPostJson);
                        foundUrlList = re.findall("url\s*?:\s*?'(?P<url>http:\\\/\\\/hi\.baidu\.com\\\/.+?\\\/item\\\/\w+?)'", respPostJson);
                        logging.debug("foundUrlList=%s", foundUrlList);
                        if(foundUrlList):
                            postUrlLen = len(foundUrlList);
                            logging.debug("postUrlLen=%d", postUrlLen);
                        
                            lastUrl = foundUrlList[-1];
                            logging.debug("lastUrl=%s", lastUrl);
                            lastUrl = lastUrl.replace("\\/", "/");
                            logging.debug("lastUrl=%s", lastUrl);
                            
                            isFound = True;
                            retInfo = lastUrl;
                        else:
                            isFound = False;
                            retInfo = "Can not find url list";
                    else:
                        isFound = False;
                        retInfo = "Can not find portrait";
                else:
                    isFound = False;
                    retInfo = "Can not find earliest info: year, month, post number";
            elif(foundItemInfo):
                # support theme: 边走边看
                
                #http://hi.baidu.com/new/serial_story
                # qhome.init({
                    # allItemCount: 878,
                    # pageItemCount: 10,
                    # currentPage: 0
                # });
                
                allItemCount    = foundItemInfo.group("allItemCount");
                pageItemCount   = foundItemInfo.group("pageItemCount");
                currentPage     = foundItemInfo.group("currentPage");
                logging.debug("allItemCount=%s, pageItemCount=%s, currentPage=%s", allItemCount, pageItemCount, currentPage);
                
                allCount = int(allItemCount);
                pageSize = int(pageItemCount);
                curPage = int(currentPage);
                
                lastPageHtml = getLastPageHtmlFromPageInfo(allCount, pageSize);

                (isFound, retInfo) = extractLastItemUrlFromPageHtml(lastPageHtml);
            else:
                isFound = False;
                retInfo = "Not support current theme of new baidu space";
        else:
            # visit "http://hi.baidu.com/againinput_tmp/blog/index/10000"
            # will got the last page -> include 1 or more earliest blog items
            maxIdxNum = 10000;
            url = gVal['blogEntryUrl'] + '/blog/index/' + str(maxIdxNum);

            titList = [];
            logging.info("Begin to connect to %s",url);
            resp = crifanLib.getUrlResponse(url);
            
            logging.info("Connect successfully, now begin to find the first blog item");
            soup = BeautifulSoup(resp);
            #logging.debug("------prettified html page for: %s\n%s", url, soup.prettify());

            titList = soup.findAll(attrs={"class":"tit"});
            
            titListLen = len(titList);
            # here tit list contains:
            # [0]= blog main link
            # [1-N] rest are blog item relative links if exist blog items
            # so titListLen >= 1
            if titListLen > 1 :
                # here we just want the last one, which is the earliest blog item
                linkNode = titList[titListLen - 1].a;

            if linkNode :
                #linkNodeHref = url.split('com/',1)[0]+'com'+linkNode["href"];
                linkNodeHref = gConst['baiduSpaceDomain'] + linkNode["href"];
                
                isFound = True;
                retInfo = linkNodeHref;
            else :
                retInfo = "Can't find the link node.";
                isFound = False;
    except:
        (isFound, retInfo) = (False, "Unknown error!");

    return (isFound, retInfo);

#------------------------------------------------------------------------------
# extract title fom url, html
def extractTitle(url, html):
    (needOmit, titleUni) = (False, "");
    try :
        soup = getSoupFromUrl(url);
        
        if(gVal['isNewBaiduSpace']):
            #http://hi.baidu.com/serial_story/item/0c450a1440b768088fbde426
            #<h2 class="title content-title">为什么幸运的人总幸运倒霉的人老倒霉-1   斯宾塞·约翰逊著</h2>
            foundContentTitle = soup.find(attrs={"class":"title content-title"});
            logging.debug("foundContentTitle=%s", foundContentTitle);
            if(foundContentTitle):
                titleUni = foundContentTitle.string;
                logging.debug("titleUni=%s", titleUni);
            else:
                # here also support post without title -> contain song related:
                #http://hi.baidu.com/tmcsyy123/item/68233ec076948cbd0c0a7b18
                #http://hi.baidu.com/choklk/item/5ef51e23331d77966e2cc329
                
                #http://hi.baidu.com/hyzhhyzhhyzh/item/04847eda5cf7933ae2108fd9
                # <div class="mod-music-content mod-post-content">   
                               # <div class="content-head clearfix">  <div class=content-other-info> <span>2012-06-14 16:38</span> </div>  </div> <div id=content class="content clearfix">  <img src="http://qukufile2.qianqian.com/data2/pic/2489900/2489900.jpg" alt="Valder Fields" onload="qext.fn.resizeImgSize(this,{maxwidth:758})">  <div class=music-player>  <iframe id=musicPlayer src="http://ting.baidu.com/widget/iframe/index.html?id=10358445&ref=space" scrolling=no width=300 height=35 frameborder=no></iframe>  </div> </div>   <div class=description> <p>很喜欢的一首歌</p> </div>    <div class="mod-post-info clearfix"> <div class="tag-box clearfix">  <a class=tag href="/tag/%E9%9F%B3%E4%B9%90/feeds">#音乐</a>  </div> <div class=op-box> <span class=pv>浏览(8)</span><a class=comment-bnt id=commentBnt href="#" onclick="return false">评论<span class=comment-nub></span></a><a href="#" id=shareBnt onclick="return false" class=share-bnt>转载<span id=shareNub class=share-nub></span></a> </div></div>              </div>
                # now to try generate the title for this (non-title) post
                # current use its recommand song info as its title

                # 1. find song id
                #<iframe id=musicPlayer src="http://ting.baidu.com/widget/iframe/index.html?id=10358445&ref=space" scrolling=no width=300 height=35 frameborder=no></iframe>
                foundSongId = re.search('<iframe.+?src="http://ting\.baidu\.com/widget/iframe/index\.html\?id=(?P<songId>\d+)&ref=space".+?>.*?</iframe>', html);
                logging.debug("foundSongId=%s", foundSongId);
                if(foundSongId):
                    songId = foundSongId.group("songId");
                    logging.debug("songId=%s", songId);
                    
                    gVal['noTitleItemsDict'][url] = songId;
                    logging.debug("added non title post into dict, url=%s, songId=%s", url, songId);
                    
                    # 2. get song info json from song id
                    songlinkUrl = "http://ting.baidu.com/data/music/songlink";
                    #songId = 10358445; #{"errorCode":22000,"data":{"xcode":"f2af45a1e33d52fd674e52aa74965028","songList":[{"songId":10358446,"songName":"Lichen And Bees (The Fever Of Small Tiwn Ventures)","artistId":"1643","artistName":"Tamas Wells","albumId":10358018,"albumName":"A Plea En Vendredi","songPicSmall":"http:\/\/c.hiphotos.baidu.com\/ting\/pic\/item\/810a19d8bc3eb1350a67f7fca61ea8d3fc1f44d0.jpg","songPicBig":"http:\/\/b.hiphotos.baidu.com\/ting\/pic\/item\/11385343fbf2b2117cbbc509ca8065380dd78ee4.jpg","songPicRadio":"http:\/\/b.hiphotos.baidu.com\/ting\/pic\/item\/4b90f603738da977d422a98ab051f8198618e306.jpg","lrcLink":"\/data2\/lrc\/14962895\/14962895.lrc","version":"","copy_type":1,"time":186,"linkCode":22000,"songLink":"http:\/\/zhangmenshiting5.baidu.com\/data2\/music\/10381202\/103584461342875661.mp3","format":"mp3","rate":128,"size":2936012}]}}
                    #songId = 10358456; #{"errorCode":22000,"data":{"xcode":"f2af45a1e33d52fd10a0c31806938d9e","songList":[{"songId":10358456,"songName":"En Chantant","artistId":"596041","artistName":"Mondialito","albumId":10358064,"albumName":"Cher Mon Amoureux(\u604b\u4eba\u7d6e\u8bed)","songPicSmall":"http:\/\/b.hiphotos.baidu.com\/ting\/pic\/item\/d0c8a786c9177f3ea1af3f4b70cf3bc79e3d56d9.jpg","songPicBig":"http:\/\/a.hiphotos.baidu.com\/ting\/pic\/item\/faf2b2119313b07eba2f934e0cd7912396dd8ce2.jpg","songPicRadio":"http:\/\/b.hiphotos.baidu.com\/ting\/pic\/item\/a2cc7cd98d1001e958363baeb80e7bec54e7970c.jpg","lrcLink":"","version":"","copy_type":1,"time":209,"linkCode":22000,"songLink":"http:\/\/zhangmenshiting5.baidu.com\/data2\/music\/10395825\/103584561342911661.mp3","format":"mp3","rate":128,"size":3250585}]}}
                    #songId = 10458446; # {"errorCode":22012,"data":""}
                    
                    songId = str(songId);
                    postDict = {
                        'songIds'   : songId,
                        'type'      : "",
                        'speed'     : "",
                    };
                    respSongJson = crifanLib.getUrlRespHtml(songlinkUrl, postDict);
                    logging.debug("songlinkUrl respSongJson=%s", respSongJson);
                    
                    # 3. extract song info from song json
                    songInfoDict = json.loads(respSongJson);
                    logging.debug("songInfoDict=%s", songInfoDict);
                    if(songInfoDict['data']):
                        songList = songInfoDict['data']['songList'];
                        #logging.info("songList=%s", songList);
                        singleSongDict = songList[0];
                        #logging.info("singleSongDict=%s", singleSongDict);

                        songName    = singleSongDict['songName'];
                        artistName  = singleSongDict['artistName'];
                        albumName   = singleSongDict['albumName'];
                        logging.debug("songName=%s, artistName=%s, albumName=%s", songName, artistName, albumName);
                        
                        gVal['songsDict'][songId] = singleSongDict;
                        logging.debug("added songId=%s into global songsDict", songId);
                        
                        # 4. generate title from song info
                        if(albumName and artistName):
                            titleUni = "[Music] " + songName + " - " + artistName + " (" + albumName + ")";
                        elif(artistName):
                            titleUni = "[Music] " + songName + " - " + artistName;
                        else:
                            titleUni = "[Music] " + songName;
                        logging.debug("generated title is %s", titleUni);
        else:
            tit = soup.findAll(attrs={"class":"tit"})[1];
            
            if(tit) :
                titStr = "";
                
                if tit.string :
                    # 正常的帖子
                    titStr = tit.string.strip();
                else :
                    # 【转】的帖子：
                    # <div class="tit"><span style="color:#E8A02B">【转】</span>各地区关于VPI/VCI值</div>        
                    titStr = tit.contents[0].string + tit.contents[1].string;
                    
                titleUni = unicode(titStr);
    except : 
        (needOmit, titleUni) = (False, "");

    return (needOmit, titleUni);

#------------------------------------------------------------------------------
# find next permanent link from url, html
def findNextPermaLink(url, html) :
    nextLinkStr = '';

    try :
        if(gVal['isNewBaiduSpace']):
            soup = getSoupFromUrl(url);
            
            #http://hi.baidu.com/hispace/item/f2fdcddc12f99c6addf9beec
            # <div class="mod-detail-pager clearfix">
                                    # <div class="detail-nav-pre">
                       # <a href="http://hi.baidu.com/hispace/item/a079b121270815342b0f1c05" hidefocus title="上一篇"></a>
                    # </div>
                                                    # <div class="detail-nav-next">
                        # <a  href="http://hi.baidu.com/hispace/item/5ab47f3459cf37d32784f4ff" hidefocus title="下一篇"></a>
                    # </div>
                            # </div>
            
            #http://hi.baidu.com/leresa/item/fe29bd1557bdda58f0090e6d
            # <div class="mod-detail-pager clearfix">
                                    # <div class="detail-nav-pre">
                       # <a href="http://hi.baidu.com/leresa/item/8ad5d924b7c05f52c28d5962" hidefocus title="上一篇"></a>
                    # </div>
                                            # </div>
            
            foundNavNext = soup.find(attrs={"class":"detail-nav-next"});
            logging.debug("foundNavNext=%s", foundNavNext);
            if(foundNavNext):
                nextLinkStr = foundNavNext.a['href'];
        else:
            #soup = htmlToSoup(html);
            #prettifiedSoup = soup.prettify();
            #logging.debug("---prettifiedSoup:\n%s", prettifiedSoup);
            
            #extrat next (later published) blog item link
            #match = re.search(r"var pre = \[(.*?),.*?,.*?,'(.*?)'\]", prettifiedSoup, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            # var post = [true,'军训断章','军训断章', '\/yangsheng6810/blog/item/45706242bca812179313c6ce.html'];
            # var post = [false,'','', '\/serial_story/blog/item/.html'];
            #match = re.search(r"var post = \[(?P<boolVal>.*),\s?'.*',\s?'.*',\s?'(?P<relativeLink>.*)'\]", prettifiedSoup, re.DOTALL | re.IGNORECASE | re.MULTILINE);
            match = re.search(r"var post = \[(?P<boolVal>.*),\s?'.*',\s?'.*',\s?'(?P<relativeLink>.*)'\]", html, re.DOTALL | re.IGNORECASE | re.MULTILINE);
            if match:
                if match.group("boolVal") == "true":
                    relativeLink = match.group("relativeLink")[1:];
                    nextLinkStr = gConst['baiduSpaceDomain'] + relativeLink;

        logging.debug("Found next permanent link %s", nextLinkStr);
    except :
        nextLinkStr = '';
        logging.debug("Can not find next permanent link.");

    return nextLinkStr;

#------------------------------------------------------------------------------
# extract datetime fom url, html
def extractDatetime(url, html) :
    datetimeStr = '';
    try :
        soup = getSoupFromUrl(url);
        
        if(gVal['isNewBaiduSpace']):
            #http://hi.baidu.com/serial_story/item/0c450a1440b768088fbde426
            #<div class=content-other-info> <span>2007-04-25 08:47</span> </div>
            
            #http://hi.baidu.com/dannie007zxl/item/d3560b2b85bcc9c7ef10f148
            #<div class=content-other-info> <span class=wise-ico title="来自空间手机版">&nbsp;</span><span>2011-04-03 11:30</span>
            
            foundContentOtherInfo = soup.find(attrs={"class":"content-other-info"});
            logging.debug("foundContentOtherInfo=%s", foundContentOtherInfo);
            if(foundContentOtherInfo):
                allSpan = foundContentOtherInfo.findAll("span");
                lastSpan = allSpan[-1];
                datetimeStr = lastSpan.string;
        else:
            date = soup.find(attrs={"class":"date"});
            datetimeStr = date.string.strip(); #2010-11-19 19:30, 2010年11月19日 星期五 下午 7:30, ...
        
        logging.debug("extracted date time string=%s", datetimeStr);
    except :
        logging.warning("Error while parse date time for %s", url);
        datetimeStr = "";

    return datetimeStr;

#------------------------------------------------------------------------------
# extract blog item content fom url, html
def extractContent(url, html) :
    contentUni = '';
    try :
        soup = getSoupFromUrl(url);
        
        if(gVal['isNewBaiduSpace']):
            soupContents = None;
            foundContent = None;
            
            #http://hi.baidu.com/hispace/item/f2fdcddc12f99c6addf9beec
            #<div id=content class="content clearfix">......</div>
            #foundContentClearfix = soup.find(attrs={"class":"content clearfix"});
            #logging.info("foundContentClearfix=%s", foundContentClearfix);
            
            #http://hi.baidu.com/serial_story/item/0c450a1440b768088fbde426
            #<div id=content class="content text-content clearfix">......</div>
            #foundTextContent = soup.find(attrs={"class":"content text-content clearfix"});
            #logging.info("foundTextContent=%s", foundTextContent);
            
            #new baidu space html changed to:
            #http://hi.baidu.com/serial_story/item/0c450a1440b768088fbde426
            #<div id=content class="content mod-cs-content text-content clearfix">......</div>
            contentClearfixP = re.compile("content (\s+?[\w-]+?)*?clearfix");
            foundContentClearfix = soup.find(attrs={"class":contentClearfixP});
            #logging.info("foundContentClearfix=%s", foundContentClearfix);

            if(foundContentClearfix):
                if(url in gVal['noTitleItemsDict']):
                    # special post witout title
                    logging.debug("%s is non title post", url);
                    
                    # 1. add orignal iframe html content
                    contentUni = crifanLib.soupContentsToUnicode(foundContentClearfix.contents);
                    
                    # 2. add description content
                    #http://hi.baidu.com/hyzhhyzhhyzh/item/04847eda5cf7933ae2108fd9
                    #<div id=content class="content clearfix">  <img src="http://qukufile2.qianqian.com/data2/pic/2489900/2489900.jpg" alt="Valder Fields" onload="qext.fn.resizeImgSize(this,{maxwidth:758})">  <div class=music-player>  <iframe id=musicPlayer src="http://ting.baidu.com/widget/iframe/index.html?id=10358445&ref=space" scrolling=no width=300 height=35 frameborder=no></iframe>  </div> </div>   <div class=description> <p>很喜欢的一首歌</p> </div>
                    foundDesciption= soup.find(attrs={"class":"description"});
                    #logging.info("foundDesciption=%s", foundDesciption);
                    if(foundDesciption):
                        contentUni += crifanLib.soupContentsToUnicode(foundDesciption.contents);
                        logging.debug("added additional description conent for non title post's content");
                    
                    # 3. add addpend musci info
                    #url: "http://ting.baidu.com/data/music/songlink";
                    #songId = 10358445;
                    #{"songId":10358446,"songName":"Lichen And Bees (The Fever Of Small Tiwn Ventures)","artistId":"1643","artistName":"Tamas Wells","albumId":10358018,"albumName":"A Plea En Vendredi","songPicSmall":"http:\/\/c.hiphotos.baidu.com\/ting\/pic\/item\/810a19d8bc3eb1350a67f7fca61ea8d3fc1f44d0.jpg","songPicBig":"http:\/\/b.hiphotos.baidu.com\/ting\/pic\/item\/11385343fbf2b2117cbbc509ca8065380dd78ee4.jpg","songPicRadio":"http:\/\/b.hiphotos.baidu.com\/ting\/pic\/item\/4b90f603738da977d422a98ab051f8198618e306.jpg","lrcLink":"\/data2\/lrc\/14962895\/14962895.lrc","version":"","copy_type":1,"time":186,"linkCode":22000,"songLink":"http:\/\/zhangmenshiting5.baidu.com\/data2\/music\/10381202\/103584461342875661.mp3","format":"mp3","rate":128,"size":2936012}
                    songId = gVal['noTitleItemsDict'][url];
                    logging.debug("url=%s songId=%s", url, songId);
                    songInfoDict = gVal['songsDict'][songId];
                    logging.debug("songId=%s songInfoDict=%s", songId, songInfoDict);
                    
                    def genSongInfoHtml(songInfoDict):
                        songInfoHtml = "<p>==========Current song info==========</p>";
                        for eachKey in songInfoDict:
                            singleSongInfoHtml = "<p>";
                            singleSongInfoHtml += unicode(eachKey) + "\t\t:" + unicode(songInfoDict[eachKey]);
                            singleSongInfoHtml += "</p>";
                            
                            songInfoHtml += "\r\n" + singleSongInfoHtml;
                        return songInfoHtml;
                    
                    songInfoHtml = genSongInfoHtml(songInfoDict);
                    contentUni += songInfoHtml;
                    logging.debug("added song info to post's content");
                else:
                    logging.debug("normal post with title");
                    contentUni = crifanLib.soupContentsToUnicode(foundContentClearfix.contents);
            #elif(foundTextContent):
            #    logging.debug("normal post contain: content text-content clearfix");
            #    contentUni = crifanLib.soupContentsToUnicode(foundTextContent.contents);
            else:
                logging.warning("Unsupported blog content type");
                contentUni = "";
        else:
            blogText = soup.find(id='blog_text');
            contentUni = crifanLib.soupContentsToUnicode(blogText.contents);
        
        #logging.debug("got contentUni=%s", contentUni);
    except :
        contentUni = '';
    
    return contentUni;

#------------------------------------------------------------------------------
# extract category from url, html
def extractCategory(url, html) :
    catUni = '';
    try :
        soup = getSoupFromUrl(url);
        
        if(gVal['isNewBaiduSpace']):
            #http://hi.baidu.com/serial_story/item/0c450a1440b768088fbde426
            #<div class="tag-box clearfix">  <a class=tag href="/tag/%E6%8A%80%E6%9C%AF%E4%BA%BA%E7%94%9F/feeds">#技术人生</a>  </div>
            
            #http://hi.baidu.com/hispace/item/f2fdcddc12f99c6addf9beec
            # <div class="tag-box clearfix">
                                            # <a class="tag" href="/tag/%E6%8F%92%E7%94%BB/feeds">#插画</a>
                                            # <a class="tag" href="/tag/%E8%89%BA%E6%9C%AF/feeds">#艺术</a>
                                            # <a class="tag" href="/tag/%E8%AE%BE%E8%AE%A1/feeds">#设计</a>
                                            # <a class="tag" href="/tag/%E5%88%9B%E6%84%8F/feeds">#创意</a>
                                    # </div>
            
            #here use the first tag as category
            #foundTagBox = soup.find(attrs={"class":"tag-box clearfix"});
            foundTagBox = soup.find(attrs={"class":"mod-tagbox clearfix"});
            logging.debug("foundTagBox=%s", foundTagBox);
            if(foundTagBox):
                tagBoxString = foundTagBox.a.string;
                logging.debug("tagBoxString=%s", tagBoxString);
                #tagBoxString = tagBoxString.replace("#", "");
                #http://hi.baidu.com/jfojfo/item/d82ca1070052b98b03ce1b34
                ##python&#47;js&#47;php&#47;html&#47;mysql&#47;http/feeds
                tagBoxString = tagBoxString.lstrip('#');
                catUni = tagBoxString;
        else:
            foundCat = soup.find(attrs={"class":"opt"}).findAll('a')[0];
            catStr = foundCat.string.strip();
            
            unicodeCat = u'类别：';
            # also can use following line:
            #unicodeCat = ('类别：').decode('utf-8'); # makesure current file is UTF-8 format, then '类别：' is UTF-8, and ('类别：').decode('utf-8') can work
            catStr = catStr.replace(unicodeCat, '');
            
            catUni = unicode(catStr);
        logging.debug("catUni=%s", catUni);
    except :
        catUni = "";

    return catUni;

#------------------------------------------------------------------------------
# extract tags info from url, html
def extractTags(url, html) :
    tagList = [];

    soup = getSoupFromUrl(url);
    
    if(gVal['isNewBaiduSpace']):
        # new baidu space support tags
        
        # if just one tag, it actually is the old space's category, such as:
        #http://hi.baidu.com/serial_story/item/0c450a1440b768088fbde426
        #<div class="tag-box clearfix">  <a class=tag href="/tag/%E6%8A%80%E6%9C%AF%E4%BA%BA%E7%94%9F/feeds">#技术人生</a>  </div>

        #http://hi.baidu.com/hispace/item/f2fdcddc12f99c6addf9beec
        # <div class="tag-box clearfix">
                                        # <a class="tag" href="/tag/%E6%8F%92%E7%94%BB/feeds">#插画</a>
                                        # <a class="tag" href="/tag/%E8%89%BA%E6%9C%AF/feeds">#艺术</a>
                                        # <a class="tag" href="/tag/%E8%AE%BE%E8%AE%A1/feeds">#设计</a>
                                        # <a class="tag" href="/tag/%E5%88%9B%E6%84%8F/feeds">#创意</a>
                                # </div>
        foundTagBoxClearfix = soup.find(attrs={"class":"tag-box clearfix"});
        logging.debug("foundTagBoxClearfix=%s", foundTagBoxClearfix);
        if(foundTagBoxClearfix):
            foundAllTagList = soup.findAll(attrs={"class":"tag"});
            for eachTagBox in foundAllTagList:
                singleTagBoxString = eachTagBox.string;
                logging.debug("singleTagBoxString=%s", singleTagBoxString);
                singleTagBoxString = singleTagBoxString.replace("#", "");
                logging.debug("singleTagBoxString=%s", singleTagBoxString);
                tagList.append(singleTagBoxString);
    else:
        # old baidu space not support tags
        tagList = [];
    
    logging.debug("tagList=%s", tagList);
    
    return tagList;

#------------------------------------------------------------------------------
# handle some special condition 
# to makesure the content is valid for following decode processing
def validateCmtContent(cmtContent):
    #logging.debug("[validateCmtContent]input comment content:\n%s", cmtContent)
    validCmtContent = cmtContent;
    
    if validCmtContent : # if not none
        # special cases:

        # 1. end of the comment contains odd number of backslash, eg: 'hello\\\\\'
        # -> here just simplely replace the last backslash with '[backslash]'
        if (validCmtContent[-1] == "\\") :
            validCmtContent = validCmtContent[0:-1];
            validCmtContent += '[backslash]';

    #logging.debug("[validateCmtContent]validated comment content:\n%s", validCmtContent)
    return validCmtContent;

#------------------------------------------------------------------------------
# remove some special char, for which, the wordpress not process it
def filterHtmlTag(cmtContent) :
    filteredComment = cmtContent;

    #(1)
    #from : 谢谢~<img src="http:\/\/img.baidu.com\/hi\/jx\/j_0003.gif">
    #to   : 谢谢~<img src="http://img.baidu.com/hi/jx/j_0003.gif">
    filter = re.compile(r"\\/");
    filteredComment = re.sub(filter, "/", filteredComment);

    return filteredComment;

#------------------------------------------------------------------------------
# do some filter for comment contents to make it valid for wordpress
def postProcessCmtContent(origCmtContent):
    # handle some speical condition
    noTailSlash = validateCmtContent(origCmtContent);
    #logging.debug("after remove tail slash, coment content:\n%s", noTailSlash);
    noHtmlTag = filterHtmlTag(noTailSlash);
    #logging.debug("after filtered html tag, coment content:\n%s", noHtmlTag);
    
    return noHtmlTag;

#------------------------------------------------------------------------------
# fill source comments dictionary into destination comments dictionary
# note all converted filed in dict is Unicode, so no need do decode here !
def fillComments(destCmtDict, srcCmtDict):
    #fill all comment field
    destCmtDict['id'] = srcCmtDict['id'];
    logging.debug("--- comment[%d] ---", destCmtDict['id']);
    
    destCmtDict['author'] = srcCmtDict['user_name'];
    destCmtDict['author_email'] = '';

    if srcCmtDict['user_name'] :
        cmturl = 'http://hi.baidu.com/sys/checkuser/' + srcCmtDict['user_name'] + '/1';
    else :
        cmturl = '';
    destCmtDict['author_url'] = saxutils.escape(cmturl);
    destCmtDict['author_IP'] = srcCmtDict['user_ip'];

    epoch = int(srcCmtDict['create_time']);
    localTime = time.localtime(epoch);
    gmtTime = time.gmtime(epoch);
    destCmtDict['date'] = time.strftime("%Y-%m-%d %H:%M:%S", localTime);
    destCmtDict['date_gmt'] = time.strftime("%Y-%m-%d %H:%M:%S", gmtTime);

    destCmtDict['content'] = postProcessCmtContent(srcCmtDict['content']);

    destCmtDict['approved'] = 1;
    destCmtDict['type'] = '';
    destCmtDict['parent'] = 0;
    destCmtDict['user_id'] = 0;

    logging.debug("author=%s", destCmtDict['author']);
    logging.debug("author_url=%s", destCmtDict['author_url']);
    logging.debug("date=%s", destCmtDict['date']);
    logging.debug("date_gmt=%s", destCmtDict['date_gmt']);
    logging.debug("content=%s", destCmtDict['content']);

    return destCmtDict;

#------------------------------------------------------------------------------
# get comments for input url of one blog item
# return the converted dict value
def getComments(url):
    onceGetNum = 100; # get 100 comments once

    retDict = {"err_no":0,"err_msg":"", "total_count":'', "response_count":0, "err_desc":"","body":{"total_count":0, "real_ret_count":0, "data":[]}};

    try :
        # init before loop
        retDict = {"err_no":0,"err_msg":"", "total_count":'', "response_count":0, "err_desc":"","body":{"total_count":0, "real_ret_count":0, "data":[]}};
        respDict = {};
        needGetMoreCmt = True;
        startCmtIdx = 0;
        cmtRespJson = '';
    
        while needGetMoreCmt :
            cmtUrl = genReqCmtUrl(url, startCmtIdx, onceGetNum);
            
            cmtRespJson = crifanLib.getUrlRespHtml(cmtUrl);

            if cmtRespJson == '' :
                logging.warning("Can not get the %d comments for blog item: %s", startCmtIdx, url);
                break;
            else :
                # here eval and ast.literal_eval both will fail to convert the json into dict                
                #logging.debug("original comment response\n----------------------------\n%s", cmtRespJson);
                respDict = json.loads(cmtRespJson);
                #logging.debug("after convert to dict \n----------------------------\n%s", respDict);

                # validate comments response
                if respDict['err_no'] != 0:
                    # error number no 0 -> errors happened
                    needGetMoreCmt = False;
                    logging.warning("Reponse error for get %d comments for %s, error number=%d, error description=%s, now do retrt.",
                                startCmtIdx, url, respDict['err_no'], respDict['err_desc']);
                    break;
                else :
                    # merge comments
                    retDict['err_no'] = respDict['err_no'];
                    retDict['err_msg'] = respDict['err_msg'];
                    retDict['total_count'] = respDict['total_count'];
                    retDict['response_count'] += respDict['response_count'];
                    retDict['err_desc'] = respDict['err_desc'];       
                    retDict['body']['total_count'] = respDict['body']['total_count'];
                    retDict['body']['real_ret_count'] += respDict['body']['real_ret_count'];
                    retDict['body']['data'].extend(respDict['body']['data']);
                    
                    # check whether we have done for get all comments
                    if int(retDict['body']['real_ret_count']) < int(retDict['body']['total_count']) :
                        # not complete, continue next get
                        needGetMoreCmt = True;
                        startCmtIdx += onceGetNum;
                        logging.debug('Continue to get next %d comments start from %d for %s', onceGetNum, startCmtIdx, url);
                    else :
                        # complete, quit
                        needGetMoreCmt = False;
                        logging.debug('get all comments successfully for %s', url);
                        break;
            logging.debug("In get comments while loop end, startCmtIdx=%d, onceGetNum=%d, needGetMoreCmt=%s", startCmtIdx, onceGetNum, needGetMoreCmt);
    except:
        logging.debug("Error while get comments for %s", url);

    logging.debug('before return all comments done');
    
    return retDict;


################################################################################
# Implemented Common Functions 
################################################################################

#------------------------------------------------------------------------------
# 1. old baidu space
# extract 5fe2e923cee1f55e93580718 from
#http://hi.baidu.com/recommend_music/blog/item/5fe2e923cee1f55e93580718.html
# 2. new baidu space
# extract c260a3d575252069fb5768ed from
# http://hi.baidu.com/hispace/item/c260a3d575252069fb5768ed
# http://hi.baidu.com/hispace/item/c260a3d575252069fb5768ed/
def extractThreadId(baiduUrl):
    postId = "";
    
    if(gVal['isNewBaiduSpace']):
        # http://hi.baidu.com/hispace/item/c260a3d575252069fb5768ed
        # http://hi.baidu.com/hispace/item/c260a3d575252069fb5768ed/
        foundNewPostUrl = re.search("http://hi\.baidu\.com/[\w-]+/item/(?P<postId>\w+)/?$", baiduUrl);
        logging.debug("foundNewPostUrl=%s", foundNewPostUrl);
        if(foundNewPostUrl) :
            postId = foundNewPostUrl.group("postId");
    else:
        idx_last_slash = baiduUrl.rfind("/");
        start = idx_last_slash + 1; # jump the last '/'
        end = idx_last_dot = baiduUrl.rfind(".");
        postId = baiduUrl[start:end];
    
    logging.debug("Extract postId=%s from %s", postId, baiduUrl);
    
    return postId;

#------------------------------------------------------------------------------
# generate request comment URL from blog item URL
def genReqCmtUrl(blogItemUrl, startCmtIdx, reqCmtNum):
    threadIdEnc = extractThreadId(blogItemUrl);

    if(gVal['isNewBaiduSpace']):
        #http://hi.baidu.com/hispace/item/c260a3d575252069fb5768ed
        #http://hi.baidu.com/qcmt/data/cmtlist?qing_request_source=&thread_id_enc=c260a3d575252069fb5768ed&start=0&count=20&orderby_type=1&favor=2&type=smblog&b1342684795971=1
        #http://hi.baidu.com/qcmt/data/cmtlist?qing_request_source=&thread_id_enc=c260a3d575252069fb5768ed&start=20&count=20&orderby_type=1&favor=2&type=smblog&b1342685008403=1
        
        # code generated:
        #http://hi.baidu.com/qcmt/data/cmtlist?count=20&thread_id_enc=c260a3d575252069fb5768ed&orderby_type=1&favor=2&start=0&qing_request_source=&type=smblog
        
        orderby_type = 1;
        favor = 2;
        type = "smblog";
        #bStrKey = crifanLib.getCurTimestamp();
        #logging.info("bStrKey=%d", bStrKey);
        #bStrVal = 1;

        # Note: here not use urllib.urlencode to encode para, 
        #       for the encoded result will convert some special chars($,:,{,},...) into %XX
        paraDict = {
            'qing_request_source'   : "",
            'thread_id_enc'         : str(threadIdEnc),
            'start'                 : str(startCmtIdx),
            'count'                 : str(reqCmtNum),
            'orderby_type'          : str(orderby_type),
            'favor'                 : str(favor),
            'type'                  : str(type),
            #str(bStrKey)                   : str(bStrVal),
        };
        
        mainUrl = "http://hi.baidu.com/qcmt/data/cmtlist";
    else:
        #http://hi.baidu.com/cmt/spcmt/get_thread?asyn=1&thread_id_enc=5fe2e923cee1f55e93580718&callback=_Space.commentOperate.viewCallBack&start=0&count=50&orderby_type=0&t=0.2307618197294
        #http://hi.baidu.com/cmt/spcmt/get_thread?asyn=1&thread_id_enc=5fe2e923cee1f55e93580718&start=0&count=1000&orderby_type=0&t=0.2307618197294

        # Note: here not use urllib.urlencode to encode para, 
        #       for the encoded result will convert some special chars($,:,{,},...) into %XX
        paraDict = {
            'asyn'          : '1',
            'thread_id_enc' : str(threadIdEnc),
            'start'         : str(startCmtIdx),
            'count'         : str(reqCmtNum),
            'orderby_type'  : '0',
            't'             : str(random.random()),
        };
            
        mainUrl = "http://hi.baidu.com/cmt/spcmt/get_thread";

    getCmtUrl = crifanLib.genFullUrl(mainUrl, paraDict);
    logging.debug("getCmtUrl=%s",getCmtUrl);
    
    return getCmtUrl;

#------------------------------------------------------------------------------
# process the returned comment json string to make sure it is valid, then latter json.loads can work
def makesureJsonValid(respCmtJson):
    # original returned json string is invalid
    # here filter it to make it valid
    
    # 1. key not quote by ""
    #{"errorNo" : "0","errorMsg" : "success","data": [ {total_count : '3',real_ret_count : '', .............
    #more can refer: http://www.crifan.com/python_json_loads_valueerror_expecting_property_name/
    respCmtJson = re.sub(r"(,?)(\w+?)\s+?:", r"\1'\2' :", respCmtJson); # add two single quote for key
    
    # 2. repace all ' to ""
    respCmtJson = respCmtJson.replace("'", "\""); # change single quote ' to double quote "
        
    # 3. repalce \x22 to \"
    #http://hi.baidu.com/serial_story/item/5625cfbbabf08fa7ebba9319/
    # content : '回复suzp1984: 为什么我在linux的终端里用“dos2unix filename\x22后，................',
    # Tip: 
    # here also can not do replace, and latter use ast.literal_eval to convert json to dict, is also OK
    # but should note the ast converted dict's content is UTF-8, not json.loads converted Unicode
    respCmtJson = respCmtJson.replace("\\x22", "\\\"");

    # 4. replace \x27 to '
    #http://hi.baidu.com/hispace/item/cb86aafbeb0833e70dd1c8f7
    # the comment index=51(number=52) :
    #"content": ";\x27",
    respCmtJson = respCmtJson.replace("\\x27", "'");
    
    # Warning:
    #http://hi.baidu.com/hispace/item/387cff8ebf4fa2edb17154aa contain some special control char:
    #"un" : "难过王",......,"content" : "xxx",
    # xxx is \xBF\xB4\xBC\xFB\xC1\xCB
    # for this post, even the new baidu space itself can not show comments
    # so here is acceptable for just fail to process it

    #logging.debug("filted respCmtJson=%s", respCmtJson);
    
    return respCmtJson;

#------------------------------------------------------------------------------
# convert baidu comment json to comment dict
def cmtJsonToCmtDict(respCmtJson):
    cmtDict = {};
    
    try:
        respCmtJson = makesureJsonValid(respCmtJson);

        # method 1
        cmtDict = json.loads(respCmtJson);

        # possible method 2:
        #cmtDict = ast.literal_eval(respCmtJson);
        #astDecContent = cmtDict['data'][0]['items'][0]['content'];
        #possibleCharset = crifanLib.getStrPossibleCharset(astDecContent);
        #logging.info("type(astDecContent)=%s, possibleCharset=%s", type(astDecContent), possibleCharset);

        # maybe method 3
        #cmtDict = eval(respCmtJson);
        
        #logging.info("type(cmtDict)=%s", type(cmtDict));
        
        #logging.debug("cmtDict=%s", cmtDict);
    except:
        logging.debug("Fail to convert comment json to comment dict, respCmtJson=%s", respCmtJson);
    
    return cmtDict;

#------------------------------------------------------------------------------
# get all comment list
# each single comment is a dict
def getAllCmtList(url):
    allCmtList = [];
    cmtDict = {};
    
    #fetch comments response
    cmtNumPerPage = 100;
    curCmtIdx = 0;
    
    try:
        while(True):
            curGetCmtUrl = genReqCmtUrl(url, curCmtIdx, cmtNumPerPage);
            logging.debug("now will get comments from %s", curGetCmtUrl);
            
            respCmtJson = crifanLib.getUrlRespHtml(curGetCmtUrl);
            #logging.debug("type(respCmtJson)=%s", type(respCmtJson));
            #logging.debug("return comment json=%s", respCmtJson);
            
            cmtDict = cmtJsonToCmtDict(respCmtJson);
            if(cmtDict):
                logging.debug("errorNo=%s, errorMsg=%s, total_count=%s", cmtDict['errorNo'], cmtDict['errorMsg'], cmtDict['data'][0]['total_count']);
                if(cmtDict['errorNo'] != "0"):
                    logging.warning("Error while fetch comment from %s, errorNo=%s, errorMsg=%s", curGetCmtUrl, cmtDict['errorNo'], cmtDict['errorMsg']);
                    logging.debug("returned comment json string=%s", respCmtJson);
                    break;
                else:
                    cmtDictList = cmtDict['data'][0]['items'];

                    curCmtNum = len(cmtDictList);
                    if(curCmtNum == 0):
                        # there is no comments returned(returned 0):
                        #{"errorNo" : "0","errorMsg" : "success","data": [ {total_count : '139',real_ret_count : '',items : []} ]}
                        logging.debug("no more comments returned, current allCmtList len=%d", len(allCmtList));
                        break;
                    elif(curCmtNum < cmtNumPerPage):
                        # has got the last page comments(want to get 100, returned 39)
                        allCmtList.extend(cmtDictList);
                        logging.debug("got the last page %d comments, after add, allCmtList len=%d", curCmtNum, len(allCmtList));
                        break;
                    else:#curCmtNum == cmtNumPerPage
                        allCmtList.extend(cmtDictList);
                        logging.debug("got current page %d comments, after add, allCmtList len=%d", curCmtNum, len(allCmtList));
                        
                        curCmtIdx = curCmtIdx + cmtNumPerPage;
            else:
                logging.warning("Fail to parse comment json to dict for %s", curGetCmtUrl);
                break;
    except:
        logging.warning("unkown error while fetch comments from %s", curGetCmtUrl);
        logging.debug("curCmtIdx=%d, cmtNumPerPage=%d, respCmtJson=%s, cmtDict=%s", curCmtIdx, cmtNumPerPage, respCmtJson, cmtDict);
        
    #logging.debug("allCmtList=%s", allCmtList);

    return allCmtList;

#------------------------------------------------------------------------------
# parse single source comment soup into dest comment dict
# Note: here input content is Unicode ( previously use json.loads)
def parseSingleCmtDict(destCmtDict, srcCmtDict, cmtId):
    # {
        # reply_id_enc: '343c7b19a59dad0de65c36db',
        # thread_id_enc: '173e40ead770ccf7e1a5d459',
        # parent_id_enc: 'a0cfd2e1b047c6b42e140bf4',
        # reply_count: '0',
        # score: '0',
        # like_count: '0',
        # dislike_count: '0',
        # favor: '0',
        # is_top: '0',
        # cdatetime: '1275805412',
        # portrait: '038a2f676f2f636865636b3f706f7274726169743d303338613636363136623635366130366a06',
        # un: 'suzp1984',
        # area: '',
        # title: '',
        # reserved1: '0',
        # content: '用dos2unix就可以了，为了这个我一开始还写了一个脚本，后来才发现了这个命令！',
        # replyee_portrait: '',
        # replyee_qurl: '',
        # replyee_name: '',
        # avatar: 'http://hiphotos.baidu.com/space/scrop=40;q=100/sign=b656b6d4ad345982c1d4a2cd7cc9059d/54fbb2fb43166d226ec13734462309f79152d2df.jpg',
        # qurl: '\/go\/check?portrait=038a66616b656a06'
    # }

   #fill all comment field
    destCmtDict['id'] = cmtId;
    logging.debug("--- comment[%d] ---", destCmtDict['id']);
    
    #logging.info("srcCmtDict['un']=%s", srcCmtDict['un']);
    destCmtDict['author'] = srcCmtDict['un'];

    #logging.info("srcCmtDict['qurl']=%s", srcCmtDict['qurl']);
    qurl = srcCmtDict['qurl'];
    #qurl = qurl.repalce("\\/", "/");
    qurl = re.sub("\\/", "/", qurl)
    #logging.info("qurl=%s", qurl);
    #http://hi.baidu.com/go/check?portrait=038a66616b656a06
    authorUrl = gConst['baiduSpaceDomain'] + qurl;
    #logging.info("authorUrl=%s", authorUrl);
    destCmtDict['author_url'] = authorUrl;
    
    localTime = crifanLib.timestampToDatetime(srcCmtDict['cdatetime']);
    #logging.info("localTime=%s", localTime);
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    #logging.info("gmtTime=%s", gmtTime);
    destCmtDict['date'] = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");

    destCmtDict['content'] = postProcessCmtContent(srcCmtDict['content']);
    
    destCmtDict['author_email'] = '';
    destCmtDict['author_IP'] = "";
    destCmtDict['approved'] = 1;
    destCmtDict['type'] = '';
    destCmtDict['parent'] = 0; # here tmp not parse 回复xxxx：......
    destCmtDict['user_id'] = 0;

    logging.debug("author       =%s", destCmtDict['author']);
    logging.debug("author_url   =%s", destCmtDict['author_url']);
    logging.debug("date         =%s", destCmtDict['date']);
    logging.debug("date_gmt     =%s", destCmtDict['date_gmt']);
    logging.debug("parent       =%s", destCmtDict['parent']);
    logging.debug("content      =%s", destCmtDict['content']);
    
    #logging.info("fill comments %4d OK", destCmtDict['id']);

    return ;

#------------------------------------------------------------------------------
# parse source all comments list into dest comment dict list
def parseAllCommentsList(allCmtList, parsedCommentsList):
    #print "len(allCmtList)=",len(allCmtList);
    cmtListLen = len(allCmtList);
    logging.debug("now will parse all %d comment list", cmtListLen);
    
    for cmtIdx, srcCmtDict in enumerate(allCmtList):
        destCmtDict = {};
        cmtId = cmtIdx + 1;
        parseSingleCmtDict(destCmtDict, srcCmtDict, cmtId);
        parsedCommentsList.append(destCmtDict);

    logging.debug("after parse, got %d comments", len(parsedCommentsList));
    return;

#------------------------------------------------------------------------------
# fetch and parse comments 
# return the parsed dict value
def fetchAndParseComments(url, html):
    parsedCommentsList = [];
    try :
        if(gVal['isNewBaiduSpace']):

            allCmtList = getAllCmtList(url);
                    
            # parse comments list
            parseAllCommentsList(allCmtList, parsedCommentsList);
        else:
            #extract comments if exist
            cmtRespDict = getComments(url);
            
            #logging.debug("cmtRespDict=%s", cmtRespDict);
            
            if cmtRespDict :
                # got valid comments, now proess it
                cmtRealNum = int(cmtRespDict['body']['real_ret_count']);
                if cmtRealNum > 0 :
                    logging.debug("Real get comments for this blog item : %d\n", cmtRealNum);
                    cmtLists = cmtRespDict['body']['data'];

                    idx = 0;
                    for idx in range(cmtRealNum):
                        comment = {};

                        originCmtInfo = cmtLists[idx];
                        originCmtInfo['id'] = idx + 1;

                        #fill all comment field
                        #logging.debug("originCmtInfo=%s", originCmtInfo);
                        
                        comment = fillComments(comment, originCmtInfo);
                        parsedCommentsList.append(comment);

                        idx += 1;

                    logging.debug('Total extracted comments for this blog item = %d', len(parsedCommentsList));
                else :
                    logging.debug("No comments for this blog item: %s", url);

        logging.debug("total parsed comments= %d", len(parsedCommentsList));
    except :
        logging.debug("Error while fetch and parse comment for %s", url);

    return parsedCommentsList;

#------------------------------------------------------------------------------
# parse several datetime format string into local datetime
# 1. old baidu space
# possible date format:
# (1) 2010-11-19
# (2) 2010/11/19
# (3) 2010年11月19日
# (4) 2010年11月19日 星期五
# possible time format:
# (1) 18:50
# (2) 7:29 P.M.
# (3) 下午 7:30
# whole datetime format = date + ' ' + time, eg:
# (1) 2008-04-19 19:37
# (2) 2010-11-19 7:30 P.M.
# (3) 2010-11-19 下午 7:30
# (4) 2010/11/19 19:30
# (5) 2010/11/19 7:30 P.M.
# (6) 2010/11/19 下午 7:30
# (7) 2010-11-19 19:30:14
# (8) 2008年04月19日 6:47 P.M.
# (9) 2010年11月19日 下午 7:30
# (10)2010年11月19日 星期五 19:30
# (11)2010年11月19日 星期五 7:30 P.M.
# (12)2010年11月19日 星期五 下午 7:30
# 2. new baidu space
# 2012-05-01 23:57
def parseDatetimeStrToLocalTime(datetimeStr):
    #                   1=year   2=month   3=day [4=星期几] [5=上午/下午] 6=hour 7=minute [8= A.M./P.M.]
    datetimeP = r"(\d{4})\D(\d{2})\D(\d{2})\D? ?(\S{0,3}) ?(\S{0,2}) (\d{1,2}):(\d{2}) ?(([A|P].M.)?)"
    foundDatetime = re.search(datetimeP, datetimeStr);

    datetimeStr = foundDatetime.group(0);
    year = foundDatetime.group(1);
    month = foundDatetime.group(2);
    day = foundDatetime.group(3);
    weekdayZhcn = foundDatetime.group(4);
    morningOrAfternoonUni = foundDatetime.group(5);
    
    hour = foundDatetime.group(6);
    minute = foundDatetime.group(7);
    amPm = foundDatetime.group(8);
    
    logging.debug("datetimeStr=%s, year=%s, month=%s, day=%s, hour=%s, minute=%s, weekdayZhcn=%s, morningOrAfternoonUni=%s, amPm=%s", 
                datetimeStr, year, month, day, hour, minute, weekdayZhcn, morningOrAfternoonUni, amPm);

    if morningOrAfternoonUni :
        unicodeAfternoon = u"下午";
        if morningOrAfternoonUni == unicodeAfternoon:
            hour = str(int(hour) + 8);

    if amPm :
        if amPm == "P.M." :
            hour = str(int(hour) + 8);

    # group parsed field -> translate to datetime value
    datetimeStr = year + "-" + month + "-" + day + " " + hour + ":" + minute
    parsedLocalTime = datetime.strptime(datetimeStr, '%Y-%m-%d %H:%M') # here is GMT+8 local time
    
    logging.debug("parsed datetimeStr=%s to %s", datetimeStr, parsedLocalTime);
    
    return parsedLocalTime;

#------------------------------------------------------------------------------
# check whether is self blog pic
# depend on following picInfoDict definition
def isSelfBlogPic(picInfoDict):
    isSelfPic = False;
    
    filename = picInfoDict['filename'];
    fd1 = picInfoDict['fields']['fd1'];
    fd2 = picInfoDict['fields']['fd2'];
    fd3 = picInfoDict['fields']['fd3'];
    fd4 = picInfoDict['fields']['fd4'];

    if(gVal['isNewBaiduSpace']):
        if (fd2=='hiphotos') and (fd3=='baidu') and (fd4=='com') :
            isSelfPic = True;
        else :
            isSelfPic = False;

    if(not isSelfPic):
        if (fd1=='hiphotos') and (fd2=='baidu') and (fd3=='com') :
            isSelfPic = True;
        else :
            isSelfPic = False;
        
    logging.debug("isSelfPic=%s", isSelfPic);

    return isSelfPic;

#------------------------------------------------------------------------------
def getProcessPhotoCfg():
    #---------------------------------------------------------------------------
    # old baidu space:
    
    # possible own site pic link:
    # http://hiphotos.baidu.com/againinput_tmp/pic/item/069e0d89033b5bb53d07e9b536d3d539b400bce2.jpg
    # http://hiphotos.baidu.com/recommend_music/pic/item/221ebedfa1a34d224954039e.jpg
    # http://hiphotos.baidu.com/recommend_music/abpic/item/df5cf5ce3ff2b12bb600c88e.jpg
    # http://hiphotos.baidu.com/recommend%5Fmusic/pic/item/59743562b26681cfe6113a78.jpg
    # http://hiphotos.baidu.com/recommend%5Fmusic/abpic/item/df5cf5ce3ff2b12bb600c88e.jpg
    # http://hiphotos.baidu.com/recommend%5Fmusic/pic/item/6d7dea46b215a62a6b63e580.jpe
    # http://hiphotos.baidu.com/recommend%5Fmusic/mpic/item/6d7dea46b215a62a6b63e580.jpg

    # possible othersite pic url:
    # http://images.dsqq.cn/news/2010-09-10/20100910134306672.jpg
    # http://www.yunhepan.com/uploads/allimg/100909/1305253345-0.jpg
    # http://www.dg163.cn/tupian/adminfiles/2011-5/21/9342g9ij68de3i6haj.jpg
    # http://images.china.cn/attachement/jpg/site1000/20110408/000d87ad444e0f089c8d15.jpg
    # http://bbs.wangluodan.net/attachment/Mon_1007/3_35499_40623c813e04d94.jpg
    # http://beauty.pba.cn/uploads/allimg/c110111/1294G0I9200Z-2b3F.jpg
    # http://house.hangzhou.com.cn/lsxw/ylxw/images/attachement/jpg/site2/20100823/0023aea5a8210ddc161d36.jpg
    # http://photo.bababian.com/20061125/C90C3EDF9AC2E2E79D50F865FB4EB3B8_500.jpg
    # http://img.blog.163.com/photo/NT166ikVSUCOVvSLJfOrNQ==/3734609990997279604.jpg
    # http://a1.phobos.apple.com/r10/Music/y2005/m02/d24/h13/s05.lvnxldzq.170x170-75.jpg
    
    #---------------------------------------------------------------------------
    # new baidu space:
    
    #http://hi.baidu.com/hispace/item/8877102b0e1029a1af48f5de
    #<img width="560" height="747" src="http://f.hiphotos.baidu.com/space/pic/item/730e0cf3d7ca7bcb5f011f83be096b63f624a820.jpg" />

    processPicCfgDict = {
        'allPicUrlPat'      : None,
        'singlePicUrlPat'   : None,
        'getFoundPicInfo'   : None,
        'isSelfBlogPic'     : isSelfBlogPic,
        'genNewOtherPicName': None,
        'isFileValid'       : None,
        'downloadFile'      : None,
    };
    
    return processPicCfgDict;

#------------------------------------------------------------------------------
# extract blog title and description
def extractBlogTitAndDesc(blogEntryUrl) :
    (blogTitle, blogDescription) = ("", "");
    
    logging.debug("input blogEntryUrl=%s", blogEntryUrl);
    
    if(gVal['isNewBaiduSpace']):
        #http://hi.baidu.com/serial_story/item/5625cfbbabf08fa7ebba9319
        #<div class=container><h1><a class=space-name href="/new/serial_story">Work and Job</a></h1><p class=space-description>关于工作的一些故事和文章</p></div>
        respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
        soup = htmlToSoup(respHtml);
        foundSpaceName = soup.find(attrs={"class":"space-name"});
        logging.debug("foundSpaceName=%s", foundSpaceName);
        if(foundSpaceName):
            blogTitle = foundSpaceName.string;
            
        foundSpaceDesc = soup.find(attrs={"class":"space-description"});
        logging.debug("foundSpaceDesc=%s", foundSpaceDesc);
        if(foundSpaceDesc):
            blogDescription = foundSpaceDesc.string;
    else:
        mainUrl = blogEntryUrl + '/blog';
        
        respHtml = crifanLib.getUrlRespHtml(mainUrl);
        soup = htmlToSoup(respHtml);
        
        try:
            blogTitle = soup.find(attrs={"class":"titlink"}).string;
            blogDescription = soup.find(attrs={"class":"desc"}).string;
        except:
            (blogTitle, blogDescription) = ("", "");
    
    logging.debug("extracted blogTitle=%s, blogDescription=%s", blogTitle, blogDescription);

    return (blogTitle, blogDescription);

####### Login Mode ######

#------------------------------------------------------------------------------
# log in baidu space
def loginBlog(username, password) :
    baiduSpaceEntryUrl = gVal['blogEntryUrl'];

    loginOk = False;
    isHostNotice = "You are the host of this space.";

    #old:
    #baiduSpaceEntryUrl = "http://hi.baidu.com/motionhouse";
    #baiduSpaceEntryUrl = "http://hi.baidu.com/wwwhaseecom";
    
    #new:
    #baiduSpaceEntryUrl= http://hi.baidu.com/new/serial_story
    
    #http://www.darlingtree.com/wordpress/archives/242
    gVal['cj'] = cookielib.CookieJar();
    
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(gVal['cj']));
    urllib2.install_opener(opener);
    resp = urllib2.urlopen(baiduSpaceEntryUrl);

    # respInfo = resp.info();
    # for key in respInfo.__dict__.keys() :
        # print "[",key,"]=",respInfo.__dict__[key]

    #here got cookie: BAIDUID for latter login
    # for index, cookie in enumerate(gVal['cj']):
        # print '[',index, ']';
        # print "name=",cookie.name;
                
        # # cookie.__class__,cookie.__dict__,dir(cookie)

        # print "value=",cookie.value;
        # print "domain=",cookie.domain;
        #print "expires=",cookie.expires;
        #print "path=",cookie.path;
        #print "version=",cookie.version;
        #print "port=",cookie.port;
        #print "secure=",cookie.secure;
        # print "comment=",cookie.comment;
        # print "comment_url=",cookie.comment_url;
        # print "rfc2109=",cookie.rfc2109;
        # print "port_specified=",cookie.port_specified;
        # print "domain_specified=",cookie.domain_specified;
        # print "domain_initial_dot=",cookie.domain_initial_dot;
        # print "--- not in spec --- ";
        # print "is_expired()=",cookie.is_expired();
        # print "is_expired=",cookie.is_expired;
        
    # retInfo = resp.info();    
    # retUrl = resp.geturl()
    
    # ContentType = retInfo['Content-Type'];
    # print "Content-Type=",ContentType

    if(gVal['isNewBaiduSpace']):
        getapiUrl = "https://passport.baidu.com/v2/api/?getapi&class=login&tpl=qing";
        # resp = crifanLib.getUrlResponse(getapiUrl);
        # respInfo = resp.info();
        # for key in respInfo.__dict__.keys() :
            # print "[",key,"]=",respInfo.__dict__[key];
        
        respHtml = crifanLib.getUrlRespHtml(getapiUrl);
        logging.debug("url=%s, respHtml=%s", getapiUrl, respHtml);
        #bdPass.api.params.login_token='9f2627392b620efb12fcc3a5254318df';
        foundToken = re.search("login_token='(?P<login_token>\w+)';", respHtml);
        logging.debug("foundToken=%s", foundToken);
        if(foundToken):
            loginToken = foundToken.group("login_token");
            logging.debug("loginToken=%s", loginToken);
        else:
            logging.error("Login fail for extract login_token !");
            return loginOk;

        loginBaiduUrl = "https://passport.baidu.com/v2/api/?login";
        
        #space/blog page login:
        # charset=UTF-8&
        # codestring=&
        # token=4eb67e297f7061127b93d79a935aa3f9&
        # isPhone=false&
        # index=0&
        # u=&
        # safeflag=0&
        # staticpage=http%3A%2F%2Fhi.baidu.com%2Fcom%2Fshow%2Fproxy%3Fparent%3Dparent%26fun%3Dcallback.login.submited&
        # loginType=1&
        # tpl=qing&
        # username=againinput4&
        # password=xxxxxx&
        # verifycode=&
        # mem_pass=on
        
        #main page login
        # ppui_logintime=6765&
        # charset=utf-8&
        # codestring=&
        # token=d143ee580b35a8f40f46e9aeae5061a6&
        # isPhone=false&
        # index=0&
        # u=&
        # safeflg=0&
        # staticpage=http%3A%2F%2Fwww.baidu.com%2Fcache%2Fuser%2Fhtml%2Fjump.html&
        # loginType=1&
        # tpl=mn&
        # callback=parent.bdPass.api.login._postCallback&
        # username=againinput4&
        # password=xxxx&
        # verifycode=&
        # mem_pass=on

        postDict = {
            'username'  : username,
            'password'  : password,
            'mem_pass'  : 'on',
            
            'charset'   : "UTF-8",
            'isPhone'   : "false",
            'index'     : "0",
            'safeflag'  : "0",
            #'staticpage': "http://hi.baidu.com/com/show/proxy?parent=parent&fun=callback.login.submited",
            'loginType' : "1",
            'tpl'       : "qing",
            'token'     : loginToken,
            };
        resp = crifanLib.getUrlResponse(loginBaiduUrl, postDict);
        
        respInfo = resp.info();
        logging.debug("url=%s, respInfo is:\n", loginBaiduUrl);
        for key in respInfo.__dict__.keys() :
            logging.debug("[%s]=%s",key, respInfo.__dict__[key]);

        # check whether the cookie is OK
        cookieNameList = ["BDUSS", "PTOKEN", "STOKEN", "SAVEUSERID"];
        loginOk = crifanLib.checkAllCookiesExist(cookieNameList, gVal['cj']);
        if (loginOk) :
            logging.info("Login new baidu space successfully.");
        else:
            logging.error("Login fail for not all expected cookies exist !");
            return loginOk;
        
        #check whether login is OK and is your self blog(is host)
        respHtml = crifanLib.getUrlRespHtml(baiduSpaceEntryUrl);
        logging.debug("url=%s, respHtml=\n%s", baiduSpaceEntryUrl, respHtml);
        
        #normal use againinput4 login
        #window.qUserInfo={"userName":"againinput4","portrait":"292273657269616c5f73746f72794f02","qingUrl":"\/serial_story","spaceName":"Work and Job","right":"0","avatarStatus":"1","flagNeedInvite":"0","flagNotInvited":"0","version":"2"};window.qVisitorInfo={"userName":"againinput4","portrait":"292273657269616c5f73746f72794f02","isHost":true,"loginStatus":"activated","qingUrl":"\/serial_story","right":"0","version":"2"};
        
        #use againinput3 login againinput4
        #window.qUserInfo={"userName":"againinput4","portrait":"292273657269616c5f73746f72794f02","qingUrl":"\/serial_story","spaceName":"Work and Job","right":"0","avatarStatus":"1","flagNeedInvite":"0","flagNotInvited":"0","version":"2"};window.qVisitorInfo={"userName":"againinput3","portrait":"193f616761696e696e707574334802","isHost": false,"loginStatus":"not_activate","qingUrl":"","right":"0","version":"0"};
        
        foundVisitorInfo = re.search('"isHost":\s*?(?P<isHost>\w+),"loginStatus":"(?P<loginStatus>\w+)",', respHtml);
        logging.debug("foundVisitorInfo=%s", foundVisitorInfo);
        if(foundVisitorInfo):
            loginStatus = foundVisitorInfo.group("loginStatus");
            isHost = foundVisitorInfo.group("isHost");
            
            logging.debug("isHost=%s, loginStatus=%s", isHost, loginStatus);
            
            if(isHost == "true"):
                logging.info(isHostNotice);
                loginOk = True;
            else : # "isHost": false,
                logging.error("isHost is not true: seems that your username and password OK, but not login yourself's space.");
                loginOk = False;
        else:
            logging.error("Login fail for not found window.qVisitorInfo !");
            return loginOk;
    else:
        
        loginBaiduUrl = "https://passport.baidu.com/?login";
        #username=%D0%C4%C7%E9%C6%DC%CF%A2%B5%D8&password=xxx&mem_pass=on
        postDict = {
            'username'  : username,
            'password'  : password,
            'mem_pass'  : 'on',
            };
        resp = crifanLib.getUrlResponse(loginBaiduUrl, postDict);

        # check whether the cookie is OK
        cookieNameList = ["USERID", "PTOKEN", "STOKEN"];
        loginOk = crifanLib.checkAllCookiesExist(cookieNameList, gVal['cj']);
        if (not loginOk) :
            logging.error("Login fail for not all expected cookies exist !");
            return loginOk;

        # respInfo = resp.info();
        # # for key in respInfo.__dict__.keys() :
            # # print "[",key,"]=",respInfo.__dict__[key]

        # respSoup = BeautifulSoup(resp);
        # prettifiedSoup = respSoup.prettify();
        # logging.debug("login returned html:\r\n" + prettifiedSoup);

        baiduSpaceHomeUrl = baiduSpaceEntryUrl + "/home";
        resp = crifanLib.getUrlResponse(baiduSpaceHomeUrl);

        #respInfo = resp.info();
        #print "for: ",baiduSpaceHomeUrl;
        #print "resp.getcode()=",resp.getcode();
        #for key in respInfo.__dict__.keys() :
        #    print "[",key,"]=",respInfo.__dict__[key];
        
        respSoup = BeautifulSoup(resp, fromEncoding="GB18030");
        prettifiedSoup = respSoup.prettify();
        #logging.debug("space home returned html:\r\n%s", prettifiedSoup);    
        #spToken: '59a906953de03230cc41f75452ea2229',
        matched = re.search(r"spToken:\s*?'(?P<spToken>\w+?)',", prettifiedSoup);
        #print "matched=",matched;
        if( matched ) :
            gVal['spToken'] = matched.group("spToken");
            #print "found spToken = ",gVal['spToken'];
            logging.debug("Extrat out spToken=%s", gVal['spToken']);
        else :
            logging.error("Fail to extract out spToken for baidu splace home url %s", baiduSpaceHomeUrl);
            loginOk = False;

        if (not loginOk) :
            return loginOk;

        #isLogin: !true,
        #isLogin: true,
        foundLogin = re.search(r"isLogin:\s*?(?P<isLogin>[^\s]+?),", prettifiedSoup);
        if (foundLogin) :
            loginValue = foundLogin.group("isLogin");
            if (loginValue.lower() == "true") :
                logging.info("Login baidu space successfully.");
            else : # !true
                logging.error("Login fail for isLogin is not true !");
                loginOk = False;
        else :
            logging.error("Can not extract isLogin info !");
            loginOk = False;

        if (not loginOk) :
            return loginOk;

        #isHost: 1,
        #isHost: 0,
        #isHost: "",
        #isHost: "1",
        foundHost = re.search(r'isHost:\s*"?(?P<isHost>\d?)"?,', prettifiedSoup);
        if (foundHost) :
            hostValue = foundHost.group("isHost");
            #print "hostValue=",hostValue;
            if (hostValue == "1") :
                logging.info(isHostNotice);
            else : # !true, ""
                logging.error("isHost is not '1': seems that your username and password OK, but not login yourself's space.");
                loginOk = False;
        else :
            logging.error("Can not extract isHost info !");
            loginOk = False;

        if (not loginOk) :
            return loginOk;

        # #logging.debug("space home returned html:\r\n%s", resp.read());
        # # gzipedData = resp.read();
        # # print "before decompress, len=",len(gzipedData);
        # # decompressed = zlib.decompress(gzipedData, 16+zlib.MAX_WBITS);
        # # print "after decompress, len=",len(decompressed);
        
        # respSoup = BeautifulSoup(resp, fromEncoding="GB18030");
        # prettifiedSoup = respSoup.prettify();
        # logging.debug("space home returned html:\r\n" + prettifiedSoup);

    return loginOk;

#------------------------------------------------------------------------------
# check whether this post is private(self only) or not
def isPrivatePost(url, html) :
    isPrivate = False;
    
    soup = htmlToSoup(html);
    
    try :
        if(gVal['isNewBaiduSpace']):
            #private pos contain:
            #<div class="q-private4host">该内容已被原作者设为仅自己可见</div>
            #publich post not contain above info
            #no friend only post type
            foundPrivate = soup.find(attrs={"class":"q-private4host"});
            logging.debug("foundPrivate=%s", foundPrivate);
            if(foundPrivate):
                isPrivate = True;
                logging.info("found private post: %s", url);
        else:
            
            blogOption = soup.find(id='blogOpt');
            if blogOption and blogOption.contents :
                #print "type(blogOption.contents)=",type(blogOption.contents);
                #print "len(blogOption.contents)=",len(blogOption.contents);
                #keyDict = dict(blogOption.contents);
                #print "keyDict=",keyDict;
                #for i in range(len(blogOption.contents)) :
                for i, content in enumerate(blogOption.contents) :
                    #print "[",i,"]:";
                    # print "contents.string=",blogOption.contents[i].string;
                    # print "contents:",blogOption.contents[i];
                    #curStr = blogOption.contents[i].string;
                    #curStr = blogOption.contents[i];
                    #print "content=",content;
                    
                    #print "type(content)=",type(content);
                    # type(content)= <class 'BeautifulSoup.NavigableString'>
                    # type(content)= <type 'instance'>
                    
                    curStr = unicode(content);
                    
                    if(curStr == u"该文章为私有"):
                        #print "------------found:",curStr;
                        isPrivate = True;
                        break;
    except :
        isPrivate = False;
        logging.error("Error while check whether post is private");

    return isPrivate;

#------------------------------------------------------------------------------
# modify post content
# Note:
# (1) title should be unicode 
# (2) here modify post, sometime will flush out the original content,
# for example: 
# http://hi.baidu.com/goodword/blog/item/c38a9418e6d6a40634fa41c9.html
# now has empty content, for it is overwritten by this modify post.
# but after check the detail in debug info, the post data is right,
# so seems just the baidu system is abnormal, 
# which sometime will lead to missing out some content even if your modify post request is no problem !
def modifySinglePost(newPostContentUni, infoDict, inputCfg):
    (modifyOk, errInfo) = (False, "Unknown error!");
    
    url = infoDict['url'];

    if(gVal['isNewBaiduSpace']):
        #http://hi.baidu.com/serial_story/item/7ecc2ae29bd5ddabc00d75aa
        foundQbid = re.search(r"/item/(?P<qbid>\w+)\s*?", url);
        logging.debug("foundQbid=%s", foundQbid);
        if(foundQbid):
            qbid = foundQbid.group("qbid");
            logging.debug("Extracted qbid=%s", qbid);
        else:
            modifyOk = False;
            errInfo = "Can't extract post qbid !";
            return (modifyOk, errInfo);
        
        respHtml = infoDict['respHtml'];
        #window.qBdsToken="bba5a5f57809453aab94d7eab8e344cb";
        foundQbdstoken = re.search('window.qBdsToken="(?P<bdstoken>\w+)";', respHtml);
        logging.debug("foundQbdstoken=%s", foundQbdstoken);
        if(foundQbdstoken):
            bdstoken = foundQbdstoken.group("bdstoken");
            logging.debug("Extracted bdstoken=%s", bdstoken);
        else:
            modifyOk = False;
            errInfo = "Fail to find window.qBdsToken";
            return (modifyOk, errInfo);

        contentEncoding = "UTF-8";
        #contentEncoding = "GB18030";
        titleEncoded = infoDict['title'].encode(contentEncoding);
        logging.debug("titleEncoded=%s", titleEncoded);
        newPostContentEncoded = newPostContentUni.encode(contentEncoding);
        logging.debug("newPostContentEncoded=%s", newPostContentEncoded);
        refer = url;
        #multimedia = "undefined#undefined#undefined#undefined";
        multimedia = "";
        
        # title=测试公开日志
        # content=<p>这个是公开的日志<%2Fp><p>发帖时，设置为“所有人可见”的那种。<%2Fp><p>111%26nbsp;测试更改内容<%2Fp>
        # private=0
        # imgnum=0
        # bdstoken=bba5a5f57809453aab94d7eab8e344cb
        # qbid=7ecc2ae29bd5ddabc00d75aa
        # refer=http:%2F%2Fhi.baidu.com%2Fserial_story%2Fitem%2F7ecc2ae29bd5ddabc00d75aa
        # multimedia[]=undefined%23undefined%23undefined%23undefined
        # private1=0
        # qing_request_source=
        postDict = {
            "title"     : titleEncoded,
            "content"   : newPostContentEncoded,
            "private"   : "0", # tmp set all post to non-private == public
            "private1"  : "0", # ???
            "imgnum"    : "0", #tmp not support photo/video type post, only support text type post
            "bdstoken"  : bdstoken,
            "qbid"      : qbid,
            "refer"     : refer,
            "multimedia[]"          : multimedia, #tmp not support multimedia(photo/audio/video)
            "qing_request_source"   : "",
        }
        
        
        headerDict = {
            'x-requested-with'  : "XMLHttpRequest",
            'Referer'           : "http://hi.baidu.com/pub/show/modifytext?qbid="+qbid,
        }
        
        modifyTextUrl = "http://hi.baidu.com/pub/submit/modifytext";
        respJson = crifanLib.getUrlRespHtml(modifyTextUrl, postDict, headerDict);
        logging.debug("modifyPost respJson=%s", respJson);
        
        #{"errorNo" : "0","errorMsg" : "","data": [  ]}
        foundRespJson = re.search('{"errorNo"\s*?:\s*?"(?P<errorNo>\d+)","errorMsg"\s*?:\s*?"(?P<errorMsg>.*?)",', respJson);
        logging.debug("foundRespJson=%s", foundRespJson);
        if(foundRespJson):
            errorNo = foundRespJson.group("errorNo");
            errorMsg = foundRespJson.group("errorMsg");
            logging.debug("errorNo=%s, errorMsg=%s", errorNo, errorMsg);
            errorMsgUni = errorMsg.decode("UTF-8");
            if(errorNo == "0"):
                modifyOk = True;
                errInfo = "Modify post OK";
            else:
                modifyOk = False;
                errInfo = errorMsgUni;
                return (modifyOk, errInfo);
        else:
            modifyOk = False;
            errInfo = "Fail to find response json after modify post !";
            return (modifyOk, errInfo);
    else:
        # upload new blog content
        #logging.debug("New blog content to upload=\r\n%s", newPostContentUni);
        
        modifyUrl = gVal['blogEntryUrl'] + "/blog/submit/modifyblog";
        #logging.debug("Modify Url is %s", modifyUrl);
        
        #http://hi.baidu.com/wwwhaseecom/blog/item/79188d1b4fa36f068718bf79.html
        foundSpBlogID = re.search(r"blog/item/(?P<spBlogID>\w+?).html", url);
        if(foundSpBlogID) :
            spBlogID = foundSpBlogID.group("spBlogID");
            logging.debug("Extracted spBlogID=%s", spBlogID);
        else :
            modifyOk = False;
            errInfo = "Can't extract post spBlogID !";
            return (modifyOk, errInfo);

        newPostContentGb18030 = newPostContentUni.encode("GB18030");
        categoryGb18030 = infoDict['category'].encode("GB18030");
        titleGb18030 = infoDict['title'].encode("GB18030");
        
        postDict = {
            "bdstoken"      : gVal['spToken'],
            "ct"            : "1",
            "mms_flag"      : "0",
            "cm"            : "2",
            "spBlogID"      : spBlogID,
            "spBlogCatName_o": categoryGb18030, # old catagory
            "edithid"       : "",
            "previewImg"    : "",
            "spBlogTitle"   : titleGb18030,
            "spBlogText"    : newPostContentGb18030,
            "spBlogCatName" : categoryGb18030, # new catagory
            "spBlogPower"   : "0",
            "spIsCmtAllow"  : "1",
            "spShareNotAllow":"0",
            "spVcode"       : "",
            "spVerifyKey"   : "",
        }
                
        headerDict = {
            # 如果不添加Referer，则返回的html则会出现错误："数据添加的一般错误"
            "Referer" : gVal['blogEntryUrl'] + "/blog/modify/" + spBlogID,
            }
        #resp = crifanLib.getUrlResponse(modifyUrl, postDict, headerDict);
        respHtml = crifanLib.getUrlRespHtml(modifyUrl, postDict, headerDict);
        
        #respInfo = resp.info();
        #print "respInfo.__dict__=",respInfo.__dict__;
        
        #soup = BeautifulSoup(resp, fromEncoding="GB18030");
        soup = htmlToSoup(respHtml);
        prettifiedSoup = soup.prettify();
        #logging.debug("Modify post return html\n---------------\n%s\n", prettifiedSoup);
        
        # check whether has modify OK
        editOkUni = u"您的文章已经修改成功";
        #editOkGb18030 = editOkUni.encode("GB18030");
        editOkUft8 = editOkUni.encode("utf-8");
        editOkPat = re.compile(editOkUft8);        
        #writestr("您的文章已经修改成功。");
        # Note:
        # here for prettifiedSoup is utf-8, so should use utf-8 type str to search,
        # otherwise search can not found !
        foundEditOk = editOkPat.search(prettifiedSoup);
        if (foundEditOk) :
            modifyOk = True;
        else :
            #find error detail
            # <div id="errdetail" class="f14">
            #   您必须输入分类名称，请检查。
            # ...
            # </div>
            errDetail = soup.find(id='errdetail');
            if errDetail and errDetail.contents[0] :
                errDetailStr = errDetail.contents[0].string;
                errDetailStr = unicode(errDetailStr);
                
                if((inputCfg['autoJumpSensitivePost'] == 'yes') and (re.search(u'包含不合适内容', errDetailStr))) :
                    #文章标题包含不合适内容，请检查
                    #文章内容包含不合适内容，请检查
                    logging.info("  Automatically omit modify this post for %s .", errDetailStr);
                    #infoDict['omit'] = True;
                    modifyOk = True;
                else :
                    modifyOk = False;
                    errInfo = "Modify blog post falied for %s !"%(errDetailStr);
                    return (modifyOk, errInfo); 
            else :
                modifyOk = False;
                errInfo = "Modify blog post falied for unknown reason !";
                return (modifyOk, errInfo); 
        
    # sleep some time to avoid: 您的操作过于频繁，请稍后再试。
    sleepSeconds = 6;
    logging.info(u"  begin to sleep %s seconds to void '您的操作过于频繁，请稍后再试' ...", sleepSeconds);
    time.sleep(sleepSeconds);
    logging.info("  end sleep");

    return (modifyOk, errInfo);

#------------------------------------------------------------------------------   
if __name__=="BlogBaidu":
    print "Imported: %s,\t%s"%( __name__, __VERSION__);