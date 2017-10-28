#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for Csdn Blog.

【版本历史】
[v1.3]
1.fixbug: Can not find the first link for http://blog.csdn.net/chdhust

[v1.2]
1.update for download csdn pic.

[v1.1]
1. csdn: Can not find the first link for http://blog.csdn.net/v_JULY_v, error=Unknown error! -> just csdn sometime down, use script for another time
2. fixbug: get next link from url relation dict fail for url lower case not match

[TODO]

"""

import os;
import re;
import sys;
import time;
import chardet;
#import urllib;
#import urllib2;
from datetime import datetime,timedelta;
from BeautifulSoup import BeautifulSoup,Tag,CData;
import logging;
import crifanLib;
#import cookielib;
#from xml.sax import saxutils;
import json; # New in version 2.6.
import random;

#--------------------------------const values-----------------------------------
__VERSION__ = "v1.1";

gConst = {
    'spaceDomain'  : 'http://blog.csdn.net',
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',   # v_JULY_v
    'blogEntryUrl'  : '',   # http://blog.csdn.net/v_JULY_v
    'cj'            : None, # cookiejar, to store cookies for login mode
    
    'soupDict' : {},   # cache the soup for url's html -> url : soup
    
    'urlRelation'   : {
        'inited'            : False, # indicate whether the relation dict is inited or not
        'nextLinkRelation'  : {}, # url, realNextLink
    }, 
    
    'processedUrl'  : [], #

    'dbgSubCmtNum'  : 0,
}

################################################################################
# Internal Functions 
################################################################################

#------------------------------------------------------------------------------
# convert html to soup
def htmlToSoup(html):
    soup = None;
    
    # Note:
    # (1) after BeautifulSoup process, output html content already is utf-8 encoded
    soup = BeautifulSoup(html, fromEncoding="UTF-8");
    
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
# extract article id (int) from post(article) perma link
def extractArticleId(url):
    articleId = "";
    #http://blog.csdn.net/v_july_v/article/details/6543438
    foundArticleId = re.search(r"http://blog\.csdn\.net/\w+/article/details/(?P<articleId>\d+)/?", url);
    #print "foundArticleId=",foundArticleId;
    if(foundArticleId) :
        articleId = foundArticleId.group("articleId");
        articleId = int(articleId);
        #print "articleId=",articleId;
    return articleId;

#------------------------------------------------------------------------------
# generate the perma link from article id( int or string)
# http://blog.csdn.net/v_july_v/article/details/7329314
def genPermaLink(articleId):
    return gConst['spaceDomain'] + "/" + gVal['blogUser'] + "/article/details/" + str(articleId);

################################################################################
# Implemented Common Functions 
################################################################################

#------------------------------------------------------------------------------
# extract blog user name:
# (1) v_JULY_v from: 
# http://blog.csdn.net/v_JULY_v
# http://blog.csdn.net/v_JULY_v/
# (2) v_july_v from:
# http://blog.csdn.net/v_july_v/article/details/6543438
# http://blog.csdn.net/v_july_v/article/details/6543438/
def extractBlogUser(inputUrl):
    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
    logging.debug("Extracting blog user from url=%s", inputUrl);
    
    try :
        # type1, main url: 
        # http://blog.csdn.net/v_JULY_v
        # http://blog.csdn.net/v_JULY_v/
        foundMainUrl = re.search("http://blog\.csdn\.net/(?P<username>\w+)/?", inputUrl);
        if(foundMainUrl) :
            extractedBlogUser = foundMainUrl.group("username");
            generatedBlogEntryUrl = gConst['spaceDomain'] + "/" + extractedBlogUser;
            extractOk = True;
            
        # type2, perma link:
        # http://blog.csdn.net/v_july_v/article/details/6543438
        # http://blog.csdn.net/v_july_v/article/details/6543438/
        if(not extractOk):
            foundPermaLink = re.search("http://blog\.csdn\.net/(?P<username>\w+)/article/details/\d+/?", inputUrl);
            if(foundPermaLink) :
                extractedBlogUser = foundPermaLink.group("username");
                generatedBlogEntryUrl = gConst['spaceDomain'] + "/" + extractedBlogUser;
                extractOk = True;
    except :
        (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
        
    if (extractOk) :
        gVal['blogUser'] = extractedBlogUser;
        gVal['blogEntryUrl'] = generatedBlogEntryUrl;
        
    return (extractOk, extractedBlogUser, generatedBlogEntryUrl);

#------------------------------------------------------------------------------
# find the first permanent link = url of the earliset published blog item
def find1stPermalink():
    (isFound, retInfo) = (False, "Unknown error!");
    
    try:
        #http://blog.csdn.net/chdhust
        # try find last page
        homeUrl = gVal['blogEntryUrl']
        homeRespHtml = crifanLib.getUrlRespHtml(homeUrl);
        logging.debug("homeRespHtml for %s, is:\n%s", homeUrl, homeRespHtml);
        # <a href="/chenglinhust/article/list/22">尾页</a>
        # <span> 1079条  共54页</span><strong>1</strong> <a href="/chenglinhust/article/list/2">2</a> <a href="/chenglinhust/article/list/3">3</a> <a href="/chenglinhust/article/list/4">4</a> <a href="/chenglinhust/article/list/5">5</a> <a href="/chenglinhust/article/list/6">...</a> <a href="/chenglinhust/article/list/2">下一页</a> <a href="/chenglinhust/article/list/54">尾页</a> 

        foundLastListPageUrl = re.search('<a\s+?href="(?P<lastListPageUrl>/\w+?/article/list/\d+)">尾页</a>', homeRespHtml, re.I);
        logging.debug("foundLastListPageUrl=%s", foundLastListPageUrl);

        if(foundLastListPageUrl):
            lastListPageUrl = foundLastListPageUrl.group("lastListPageUrl");
            lastListPageUrl = gConst['spaceDomain'] + lastListPageUrl
            logging.debug("lastListPageUrl=%s", lastListPageUrl);
            # pageNum = 10000;
            # pageNum = lastPageNum;
            # getPostUrl = gVal['blogEntryUrl'] + "/article/list/" + str(pageNum);
            # http://blog.csdn.net/chenglinhust/article/list/54
            respHtml = crifanLib.getUrlRespHtml(lastListPageUrl);
            logging.debug("ret html for %s, is:\n%s", lastListPageUrl, respHtml);
            soup = htmlToSoup(respHtml);
            # <span class="link_title"><a href="/v_july_v/article/details/5934051">
            # 算法面试：精选微软经典的算法面试100题（第1-20题）
            # </a></span>
            foundTitLink = soup.findAll(attrs={"class":"link_title"});
            # logging.debug("found articles=%s", foundTitLink);
            articleNum = len(foundTitLink);
            logging.debug("articleNum=%s", articleNum);
            
            if(foundTitLink) :
                lastArticle = foundTitLink[-1];
                # print "lastArticle=",lastArticle;
                aVal = lastArticle.a;
                # print "aVal=",aVal;
                href = aVal['href'];
                # print "href=",href;
                
                fristLink = gConst['spaceDomain'] + href;
                # print "fristLink=",fristLink;
                retInfo = fristLink;
                isFound = True;

                logging.debug("retInfo=%s,isFound=%s", retInfo, isFound);
    except:
        (isFound, retInfo) = (False, "Unknown error!");
    
    return (isFound, retInfo);

#------------------------------------------------------------------------------
# extract title
def extractTitle(url, html):
    (needOmit, titleUni) = (False, "");
    
    try :
        # <span class="link_title"><a href="/v_july_v/article/details/6543438">
        # <font color="red">[置顶]</font>
        # 程序员面试、算法研究、编程艺术、红黑树4大系列集锦与总结
        # </a></span>

        # <span class="link_title"><a href="/chdhust/article/details/7252155">
        #         windows编程中wParam和lParam消息        
                
        #         </a>
        #         </span>

        foundTitle = re.search('<span class="link_title"><a href="[\w/]+?">\s*(<font color="red">\[置顶\]</font>)?\s*(?P<titleHtml>.+?)\s*</a>\s*</span>', html, re.S);
        logging.debug("foundTitle=%s", foundTitle);

        if(foundTitle):
            titleHtml = foundTitle.group("titleHtml");
            logging.debug("titleHtml=%s", titleHtml);
            
            #titleUni = titleHtml.decode("UTF-8");
            titleUni = titleHtml.decode("UTF-8", 'ignore');
            logging.debug("titleUni=%s", titleUni);

            # for http://blog.csdn.net/hfahe/article/details/5494895
            #print "titleUni=",titleUni;
            # will cause error: 
            #UnicodeEncodeError: 'gbk' codec can't encode character u'\u200e' in position 43: illegal multibyte sequence
            # follow can work:
            # (1)
            #gb18030TypeStr = titleUni.encode("GB18030");
            #print "gb18030TypeStr=",gb18030TypeStr;
            # (2)
            # gbkTypeStr = titleUni.encode("GBK", 'ignore');
            # print "gbkTypeStr=",gbkTypeStr;
            
            # use follow can make print work well
            gbkTypeStr = titleUni.encode("GBK", 'ignore');
            titleUni = gbkTypeStr.decode("GBK");
            logging.debug("gbkTypeStr=%s", gbkTypeStr);
            logging.debug("titleUni=%s", titleUni);

        #------------------
        # following parsed soup has some bug, can not get proper value
        # so use above re.search to handle the title
        #------------------
        
        # soup = getSoupFromUrl(url);
        
        # # <span class="link_title"><a href="/v_july_v/article/details/5934051">
        # # 算法面试：精选微软经典的算法面试100题（第1-20题）
        # # </a></span>
        # foundTitle = soup.find(attrs={"class":"link_title"});
        # print "foundTitle=",foundTitle;
        # if(foundTitle) :
            # titleStr = "";
            
            # aVal = foundTitle.a;
            # print "aVal=",aVal;
            # print "aVal.contents=",aVal.contents;
            # #print "aVal.string=",aVal.string;
            # aValContents = aVal.contents;
            # print "aValContents=",aValContents;
            # aValContentsLen = len(aValContents);
            # print "aValContentsLen=",aValContentsLen;

            # if(aValContentsLen == 1):
                # #http://blog.csdn.net/hfahe/article/details/5494895
                # # <span class="link_title"><a href="/hfahe/article/details/5494895">
                # # 在2008 Beijing Perl 大会的演讲-使用Mason开发高性能的Web站点‎ 
                # # </a></span>
                # titleStr = aValContents[0];
                # print "type(titleStr)=",type(titleStr);
                # print "titleStr=",titleStr; # will cause error !!!
            # else:
                # print "aVal.string is null";
                # titleStr = aVal.string;
                # print "titleStr=",titleStr;
            
                # if( not titleStr) :

                    # #http://blog.csdn.net/v_july_v/article/details/6543438
                    # # <span class="link_title"><a href="/v_july_v/article/details/6543438">
                    # # <font color="red">[置顶]</font>
                    # # 程序员面试、算法研究、编程艺术、红黑树4大系列集锦与总结
                    # # </a></span>
                    # titleStr = aVal.contents[2];
                    # print "titleStr=",titleStr;
            
            # titleUni = unicode(titleStr);
            # print "titleUni=",titleUni;
            # titleUni = titleUni.replace("\r", "");
            # titleUni = titleUni.replace("\n", "");
            # titleUni = titleUni.strip();
            # print "titleUni=",titleUni;
    except : 
        logging.debug("Fail to extract tiltle from url=%s, html=\n%s", url, html);
        (needOmit, titleUni) = (False, "");
    
    if(titleUni):
        gVal['processedUrl'].append(url);
        logging.debug("Added %s to processed url list", url);

    return (needOmit, titleUni);

#------------------------------------------------------------------------------
# fetch url list in article list page, eg:
# http://blog.csdn.net/wclxyn/article/list/3
def fetchUrlList(pageNum):
    (totalUrlNum, totalPageNum, urlList) = (0, 0, []);
    
    articleListUrl = gVal['blogEntryUrl'] + "/article/list/" + str(pageNum);
    logging.debug("from %s to extract url list", articleListUrl);
    respHtml = crifanLib.getUrlRespHtml(articleListUrl);

    #http://blog.csdn.net/aomandeshangxiao/article/list/2
    # <div id="papelist" class="pagelist">
    # <span> 106条数据  共3页</span><strong>1</strong> <a href="/aomandeshangxiao/article/list/2">2</a> <a href="/aomandeshangxiao/article/list/3">3</a> <a href="/aomandeshangxiao/article/list/2">下一页</a> <a href="/aomandeshangxiao/article/list/3">尾页</a> 
    # </div>

    # http://blog.csdn.net/chenglinhust/article/list/54
    # <span> 1079条  共54页</span>
    foundPageNum = re.search("<span>\s*?(?P<totalUrlNum>\d+)条(数据)?\s+?共(?P<totalPageNum>\d+)页</span>", respHtml);
    logging.debug("foundPageNum=%s", foundPageNum);
    if(foundPageNum):
        totalUrlNum = foundPageNum.group("totalUrlNum");
        totalUrlNum = int(totalUrlNum);
        totalPageNum = foundPageNum.group("totalPageNum");
        totalPageNum = int(totalPageNum);
        logging.debug("totalUrlNum=%s, totalPageNum=%s", totalUrlNum, totalPageNum);
                
        # extrat url list
        #<span class="link_title"><a href="/v_july_v/article/details/7382693">
        foundArticleIds = re.findall('<span class="link_title"><a href="/' + gVal['blogUser'] + '/article/details/(\d+)">', respHtml, re.I);
        #print "len(foundArticleIds)=",len(foundArticleIds);
        for eachId in foundArticleIds:
            eachUrl = genPermaLink(eachId);
            #print "eachUrl=",eachUrl;
            urlList.append(eachUrl);

    if(not foundPageNum):
        #logging.debug("Not extract totalUrlNum from respHtml=\n%s", respHtml);
        #http://blog.csdn.net/qq1059458376/article/list/1
        
            # <div class="list_item article_item">

                # <div class="article_title">

            # <span class="ico ico_type_Original"></span>

            # <h3>

                # <span class="link_title"><a href="/qq1059458376/article/details/8145497">

                # 50个Android开发人员必备UI效果源码[转载]

                # </a></span>

            # </h3>

        # </div>
        #...
        # </div>
        soup = htmlToSoup(respHtml);
        foundAllListItem = soup.findAll(name="div", attrs={"class":"list_item article_item"});
        logging.debug("foundAllListItem=%s", foundAllListItem);
        if(foundAllListItem):
            for eachListItem in foundAllListItem:
                foundLinkTitle = eachListItem.find(name="span", attrs={"class":"link_title"});
                logging.debug("foundLinkTitle=%s", foundLinkTitle);
                if(foundLinkTitle):
                    linkTitleA = foundLinkTitle.a;
                    linkTitleAHref = linkTitleA['href'];
                    fullLink = gConst['spaceDomain'] + linkTitleAHref;
                    logging.debug("fullLink=%s", fullLink);
                    urlList.append(fullLink);
        
    logging.debug("for pageNum=%d, extracted info: totalUrlNum=%d, totalPageNum=%d, urlList=%s", pageNum, totalUrlNum, totalPageNum, urlList);
    
    return (totalUrlNum, totalPageNum, urlList);

#------------------------------------------------------------------------------
# get next perma link from the dict
def getNextLinkFromDict(curPemaLink):
    nextPermaLink = "";
    
    validPermaLink = curPemaLink;
    #remove last / if exist, 
    #    http://blog.csdn.net/v_JULY_v/article/details/5934051/
    # -> http://blog.csdn.net/v_JULY_v/article/details/5934051
    if(curPemaLink[-1] == "/"):
        validPermaLink = curPemaLink[:-1];
    
    #   http://blog.csdn.net/v_JULY_v/article/details/5934051
    # ->http://blog.csdn.net/v_july_v/article/details/5934051
    validPermaLink = validPermaLink.lower();
    
    if(validPermaLink in gVal['urlRelation']['nextLinkRelation']) :
        logging.debug("validPermaLink=%s is in nextLinkRelation", validPermaLink);
        nextPermaLink = gVal['urlRelation']['nextLinkRelation'][validPermaLink];
    else:
        logging.debug("validPermaLink=%s is NOT in nextLinkRelation", validPermaLink);
        nextPermaLink = "";
    logging.debug("curPemaLink=%s, nextPermaLink(get from url relation dict)=%s", curPemaLink, nextPermaLink);
    return nextPermaLink;

#------------------------------------------------------------------------------
# find next permanent link of current post
def findNextPermaLink(url, html) :
    nextLinkStr = '';

    try :
        if(not gVal['urlRelation']['inited']):
            #print "-------------only shoud see here at first time ";
            logging.debug("not init the url next perma link relation dict, so init now");
            allPageUrlList = [];
            
            # find total page number
            pageNum = 1;
            (totalUrlNum, totalPageNum, urlList) = fetchUrlList(pageNum);
            allPageUrlList.extend(urlList);
            logging.debug("len(allPageUrlList)=%s", len(allPageUrlList));

            if(totalPageNum > 1):
                # fetch remain page
                for pageIdx in range(totalPageNum) :
                    pageNum = pageIdx + 1;
                    if(pageNum == 1):
                        continue;
                    else:
                        (tmp1, tmp2, urlList) = fetchUrlList(pageNum);
                        allPageUrlList.extend(urlList);
                        #print "len(allPageUrlList)=",len(allPageUrlList);

            # generate relation from all page url list
            if(allPageUrlList):
                logging.debug("allPageUrlList=%s", allPageUrlList);
                #reversedPageUrlList = allPageUrlList.reverse(); # -> is None !!!
                allPageUrlList.reverse(); # -> is OK, the self is reversed !!!
                reversedPageUrlList = allPageUrlList;
                logging.debug("reversedPageUrlList=%s", reversedPageUrlList);
                #print "type(reversedPageUrlList)=",type(reversedPageUrlList);
                urlListLen = len(reversedPageUrlList);
                logging.debug("urlListLen=%d", urlListLen);
                for i in range(urlListLen):
                    curPemaLink = reversedPageUrlList[i];
                    if(i != (urlListLen - 1)):
                        nextPermaLink = reversedPageUrlList[i + 1];
                    else:
                        nextPermaLink = "";

                    curPemaLink = curPemaLink.lower();
                    nextPermaLink = nextPermaLink.lower();
                    gVal['urlRelation']['nextLinkRelation'][curPemaLink] = nextPermaLink;

            gVal['urlRelation']['inited'] = True;
            logging.debug("gVal['urlRelation']=%s", gVal['urlRelation']);
        else:
            logging.debug("has inited the url next perma link relation dict");
    
        nextLinkStr = getNextLinkFromDict(url);
        nextPostTitle = "";
        
        #-----------------------
        # following code are so complex due to special case
        # -> hard to extract next perma link
        # -> use above code to extract the next perma link
        #-----------------------
        
        
    
        # # <li class="next_article">
            # # <span>下一篇：</span>
            # # <a href="http://blog.csdn.net/v_july_v/article/details/5944143">算法面试：精选微软经典的算法面试100题（第21-25题）</a>
        # # </li>
        # soup = getSoupFromUrl(url);
        # foundNext = soup.find(attrs={"class":"next_article"});
        # nextPostTitle = "";
        # #print "foundNext=",foundNext;
        # if foundNext:
            # aVal = foundNext.a;
            # #print "aVal=",aVal;
            # href = aVal['href'];
            # #print "href=",href;
            # nextLinkStr = href;
            # #print "current url=",url;
            # #print "nextLinkStr=",nextLinkStr;
            # nextPostTitle = aVal.string;
            # #print "nextPostTitle=",nextPostTitle;
            
            # if(nextLinkStr):
                # curArticleId = extractArticleId(url);
                # nextArticleId = extractArticleId(nextLinkStr);
                # if(nextArticleId < curArticleId):
                    # # is older post -> abnormal -> should be newer
                    # logging.debug("found fake next link=%s", nextLinkStr);
                    # nextLinkStr = "";
                    # nextPostTitle = "";
                    
                    # # for http://blog.csdn.net/v_JULY_v?viewmode=contents
                    # # check wheter is last/lastest several url's fake nextLink
                    # # whose nextLink is the oldest post's link
                    # # -> fake, and cause the recursive to proecss post
                    # # -> find real next link
                    # if(not gVal['urlRelation']['inited']):
                        # logging.debug("not init the url next perma link relation dict, so init now");
                        # #print "gVal['urlRelation']['inited']=",gVal['urlRelation']['inited'];
                        # viewmodeUrl = gVal['blogEntryUrl'] + "?viewmode=contents";
                        # logging.debug("view mode url=%s", viewmodeUrl);
                        # respHtml = crifanLib.getUrlRespHtml(viewmodeUrl);
                        # logging.debug("for extract real url next link relation, respHtml=\n%s", respHtml);
                        
                        # #http://blog.csdn.net/aomandeshangxiao/article/list/2
                        # # <div id="papelist" class="pagelist">
                        # # <span> 106条数据  共3页</span><strong>1</strong> <a href="/aomandeshangxiao/article/list/2">2</a> <a href="/aomandeshangxiao/article/list/3">3</a> <a href="/aomandeshangxiao/article/list/2">下一页</a> <a href="/aomandeshangxiao/article/list/3">尾页</a> 
                        # # </div>
                        
                        # # 1. extrat url list
                        # #<span class="link_title"><a href="/v_july_v/article/details/7382693">
                        # foundArticleIds = re.findall('<span class="link_title"><a href="/' + gVal['blogUser'] + '/article/details/(\d+)">', respHtml, re.I);
                        # #print "foundArticleIds=",foundArticleIds;
                        # #print "len(foundArticleIds)=",len(foundArticleIds);
                        
                        # idListInt = [];
                        # for idStr in foundArticleIds:
                            # idListInt.append(int(idStr));
                        # print "idListInt=",idListInt;
                        # #reversedIdListInt = idListInt.reverse();
                        # #print "=reversedIdListInt=",reversedIdListInt;
                        
                        # validIdList = [];
                        # for id in idListInt:
                            # if(id >= curArticleId):
                                 # # filter out [置顶] ones -> older ones
                                # validIdList.append(id);
                        # print "validIdList=",validIdList;
                        
                        # # 3. generate relation
                        # validIdListLen = len(validIdList);
                        # curId = curArticleId;
                        # if(validIdList[-1] == curArticleId):# the last one should be curren one
                            # for i in range(validIdListLen):
                                # curIdx = validIdListLen - i - 1;
                                # #print "curIdx=",curIdx;
                                # curId = validIdList[curIdx];
                                # #print "curId=",curId;
                                
                                # curPemaLink = genPermaLink(curId);
                                # if(i == (validIdListLen - 1)):
                                    # # is last one 
                                    # nextPermaLink = "";
                                # else :
                                    # nexId = validIdList[curIdx - 1];
                                    # nextPermaLink = genPermaLink(nexId);

                                # gVal['urlRelation']['nextLinkRelation'][curPemaLink] = nextPermaLink;
                            
                            # logging.debug("generated url next link relation=%s", gVal['urlRelation']['nextLinkRelation']);
                        # gVal['urlRelation']['inited'] = True;
                    # else:
                        # logging.debug("has inited the url next perma link relation dict");
                        # #print "gVal['urlRelation']['inited']=",gVal['urlRelation']['inited'];
                        
                    # if( url in gVal['urlRelation']['nextLinkRelation']):
                        # realNextLink = gVal['urlRelation']['nextLinkRelation'][url];
                        # realNextArticleId = extractArticleId(realNextLink);
                        # if(realNextArticleId > curArticleId):
                            # # newer than current -> is true real next link
                            # nextLinkStr = realNextLink;
                            # logging.debug("real next perma link=%s", realNextLink);

        logging.debug("Found next permanent link=%s, title=%s", nextLinkStr, nextPostTitle);
    except :
        logging.debug("Fail to extract next perma link from url=%s, html=\n%s", url, html);
        nextLinkStr = '';

    return nextLinkStr;

#------------------------------------------------------------------------------
# extract datetime string
def extractDatetime(url, html) :
    datetimeStr = '';
    try :
        #<span class="link_postdate">2010-10-11 18:56</span>
        soup = getSoupFromUrl(url);
        foundPostdate = soup.find(attrs={"class":"link_postdate"});
        if foundPostdate:
            datetimeStr = foundPostdate.string;
            #print "datetimeStr=",datetimeStr;
    except :
        logging.debug("Fail to extract datettime string from url=%s, html=\n%s", url, html);
        datetimeStr = "";
        
    return datetimeStr;

#------------------------------------------------------------------------------
# extract blog item content
def extractContent(url, html) :
    contentUni = '';
    try :
        #<div id="article_content" class="article_content"> ... </div>
        soup = getSoupFromUrl(url);
        foundContent = soup.find(id="article_content");
        #logging.debug("---soup foundContent:\n%s", foundContent);

        #method 1
        mappedContents = map(CData, foundContent.contents);
        #print "type(mappedContents)=",type(mappedContents); #type(mappedContents)= <type 'list'>
        contentUni = ''.join(mappedContents);
        #print "type(contentUni)=",type(contentUni);
    except :
        logging.debug("Fail to extract post content from url=%s, html=\n%s", url, html);
        contentUni = '';

    return contentUni;

#------------------------------------------------------------------------------
# extract category
def extractCategory(url, html) :
    catUni = '';
    try :
        catUni = "";
        # here seems csdn not support real category
        # its categories actually is tags
    except :
        catUni = "";

    return catUni;

#------------------------------------------------------------------------------
# extract tags info
def extractTags(url, html) :
    tagList = [];
    try :
        #logging.debug("extractTags_html=\n%s", html);

        # <span class="link_categories">
        # 分类：
            # <a href="/v_JULY_v/article/category/769275">01.Algorithms（研究）</a> 
            # <a href="/v_JULY_v/article/category/784066">11.TAOPP（编程艺术）</a> 
            # <a href="/v_JULY_v/article/category/771597">24.data structures</a> 
            # <a href="/v_JULY_v/article/category/774945">25.Red-black tree</a> 
            # <a href="/v_JULY_v/article/category/767340">05.MS 100&#39; original</a> 
            # <a href="/v_JULY_v/article/category/896844">30.Recommend&amp;Search</a> 
        # </span>
        soup = getSoupFromUrl(url);
        foundTags = soup.find(attrs={"class":"link_categories"});
        #print "foundTags=",foundTags;
        if(foundTags):
            aList = foundTags.findAll("a");
            #print "aList=",aList;
            #print "len(aList)=",len(aList);
            
            for a in aList :
                tag = a.string;
                #print "tag=",tag;
                tagList.append(tag);
    except :
        logging.debug("Fail to extract tags from url=%s, html=\n%s", url, html);
        tagList = [];

    return tagList;

#------------------------------------------------------------------------------
# parse single source comment soup into dest comment dict 
def parseCmtDict(destCmtDict, srcCmtDict, cmtId, cmtIdRelationDict):
    global gVal;
    
    destCmtDict['id'] = cmtId;
    #print "destCmtDict['id']=",destCmtDict['id'];
    
    logging.debug("--- comment[%d] ---", destCmtDict['id']);
    logging.debug("srcCmtDict=%s", srcCmtDict);
    
    # store realtion
    orginId = srcCmtDict['CommentId'];
    newCmtId = destCmtDict['id']
    cmtIdRelationDict[orginId] = newCmtId;
    #print "id: orginId=%d, newCmtId=%d"%(orginId, newCmtId);
        
    # {
        # "ArticleId": 6543438,
        # "BlogId": 943376,
        # "CommentId": 2177665,
        # "Content": "看了好多篇，收货很多， 看的羨慕妒恨！~~~~~~~~\n虽然有很多之前没看过，很多之气都没听过，现在终于见识了！楼主的无私，很感动，就也无私的推荐给公司研发的所有同事，同事都是大赞！！",
        # "ParentId": 0,
        # "PostTime": "3天前 12:50",
        # "Replies": null,
        # "UserName": "zxyzlx",
        # "Userface": "http://avatar.csdn.net/6/3/7/3_zxyzlx.jpg"
    # }
    
    # {
        # "ArticleId": 6543438,
        # "BlogId": 943376,
        # "CommentId": 2135899,
        # "Content": "牛人 帮助了好多人啊",
        # "ParentId": 0,
        # "PostTime": "2012-03-19 01:02",
        # "Replies": null,
        # "UserName": "pkufgs",
        # "Userface": "http://avatar.csdn.net/B/3/C/3_pkufgs.jpg"
    # }
    
    destCmtDict['author'] = srcCmtDict['UserName'];
    #print "srcCmtDict['UserName']=",srcCmtDict['UserName'];
    cmtUserUrl = gConst['spaceDomain'] + "/" + srcCmtDict['UserName'];
    #print "cmtUserUrl=",cmtUserUrl;
    destCmtDict['author_url'] = cmtUserUrl;
    
    localTime = None;
    cmtTimeStr = srcCmtDict['PostTime'];
    #print "cmtTimeStr=",cmtTimeStr;
    #print "type(cmtTimeStr)=",type(cmtTimeStr);
    #2012-03-19 01:02
    #2012-04-08 15:26
    foundNormalType = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", cmtTimeStr);
    if(foundNormalType):
        #print "foundNormalType=",foundNormalType;
        localTime = datetime.strptime(cmtTimeStr, "%Y-%m-%d %H:%M");
    else:
        # special type:
        #刚刚
        foundSpecial = re.search(u"刚刚", cmtTimeStr);
        if(foundSpecial):
            localTime = datetime.now();
        
        #1分钟前
        if(not foundSpecial):
            foundSpecial = re.search(u"(?P<minutes>\d+)分钟前", cmtTimeStr);
            if(foundSpecial):
                minutes = foundSpecial.group("minutes");
                minutes = int(minutes);
                localTime = datetime.now() - timedelta(minutes=minutes);

        #3小时前
        if(not foundSpecial):
            foundSpecial = re.search(u"(?P<hours>\d+)小时前", cmtTimeStr);
            if(foundSpecial):
                hours = foundSpecial.group("hours");
                hours = int(hours);
                localTime = datetime.now() - timedelta(hours=hours);

        #昨天 20:01
        if(not foundSpecial):
            foundSpecial = re.search(u"昨天 \d{2}:\d{2}", cmtTimeStr);
            if(foundSpecial):
                yestoday = datetime.now() - timedelta(days=1);
                yestodayStr = yestoday.strftime("%Y-%m-%d");
                cmtTimeStr = cmtTimeStr.replace(u"昨天", yestodayStr);
                localTime = datetime.strptime(cmtTimeStr, "%Y-%m-%d %H:%M");
                
        #前天 15:12
        if(not foundSpecial):
            foundSpecial = re.search(u"前天 \d{2}:\d{2}", cmtTimeStr);
            if(foundSpecial):
                dayBeforeYestoday = datetime.now() - timedelta(days=2);
                dayBeforeYestodayStr = dayBeforeYestoday.strftime("%Y-%m-%d");
                cmtTimeStr = cmtTimeStr.replace(u"前天", dayBeforeYestodayStr);
                localTime = datetime.strptime(cmtTimeStr, "%Y-%m-%d %H:%M");

        #3天前 12:50
        #4天前 19:12
        #5天前 21:13
        #6天前 08:11
        if(not foundSpecial):
            foundSpecial = re.search(u"(?P<prevDayStr>(?P<prevDays>\d+)天前) \d{2}:\d{2}", cmtTimeStr);
            #print "天前,foundSpecial=",foundSpecial;
            if(foundSpecial):
                prevDayStr = foundSpecial.group("prevDayStr");

                prevDays = foundSpecial.group("prevDays");
                prevDays = int(prevDays);
                
                prevDaysDatetime = datetime.now() - timedelta(days=prevDays);

                prevDaysRealStr = prevDaysDatetime.strftime("%Y-%m-%d");
                cmtTimeStr = cmtTimeStr.replace(prevDayStr, prevDaysRealStr);
                localTime = datetime.strptime(cmtTimeStr, "%Y-%m-%d %H:%M");

    #print "localTime=",localTime;
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    #print "gmtTime=",gmtTime;
    destCmtDict['date'] = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");
    
    destCmtDict['content'] = srcCmtDict['Content'];
    #print "destCmtDict['content']=",destCmtDict['content'];

    parentId = srcCmtDict['ParentId'];
    if(parentId in cmtIdRelationDict):
        destCmtDict['parent'] = cmtIdRelationDict[parentId];
        gVal['dbgSubCmtNum'] += 1;
    else :
        destCmtDict['parent'] = 0;

    destCmtDict['author_email'] = "";
    destCmtDict['author_IP'] = "";
    destCmtDict['approved'] = 1;
    destCmtDict['type'] = "";
    destCmtDict['user_id'] = 0;
    
    logging.debug("author       =%s", destCmtDict['author']);
    logging.debug("author_url   =%s", destCmtDict['author_url']);
    logging.debug("date         =%s", destCmtDict['date']);
    logging.debug("date_gmt     =%s", destCmtDict['date_gmt']);
    logging.debug("parent       =%s", destCmtDict['parent']);
    logging.debug("content      =%s", destCmtDict['content']);
    
    #print "fill comments %4d OK"%(destCmtDict['id']);
    
    return ;
    
#------------------------------------------------------------------------------
# parse source all comments list into dest comment dict list
def parseAllCommentsList(allCmtList, parsedCommentsList):
    #print "len(allCmtList)=",len(allCmtList);
    cmtListLen = len(allCmtList);
    logging.debug("now will parse all %d comment list", cmtListLen);
    
    cmtIdRelationDict = {}; # used for store the origial comment id and current comment id relation for latter check parent id use
    for cmtIdx, srcCmtDict in enumerate(allCmtList):
        destCmtDict = {};
        cmtId = cmtIdx + 1;
        parseCmtDict(destCmtDict, srcCmtDict, cmtId, cmtIdRelationDict);
        parsedCommentsList.append(destCmtDict);

    logging.debug("after parse, got %d comments", len(parsedCommentsList));
    #print "len(cmtIdRelationDict.keys())=",len(cmtIdRelationDict.keys());    
    return;

#------------------------------------------------------------------------------
# fetch and parse comments 
# return the parsed dict value
def fetchAndParseComments(url, html):
    parsedCommentsList = [];
    
    try :
        #logging.debug("fetchAndParseComments_html=\n%s", html);
        
        soup = getSoupFromUrl(url);
        
        #<span class="link_comments" title="评论次数"><a href="#comments">评论</a>(207)</span>
        foundCmtNum = soup.find(attrs={"class":"link_comments"});
        #print "foundCmtNum=",foundCmtNum;
        if(foundCmtNum):
            #cmtNumStr = foundCmtNum.string;
            #print "foundCmtNum.contents=",foundCmtNum.contents;
            cmtNumStr = foundCmtNum.contents[1];
            #print "cmtNumStr=",cmtNumStr;
            cmtNumStr = cmtNumStr.strip();
            cmtNumStr = cmtNumStr.replace("(", "");
            cmtNumStr = cmtNumStr.replace(")", "");
            #print "cmtNumStr=",cmtNumStr;
            totalCmtNum = int(cmtNumStr);
            #print "totalCmtNum=",totalCmtNum;
            logging.debug("total comment number=%d", totalCmtNum);
            allCmtList = [];
            if(totalCmtNum > 0):
                # fetch comments
                needGetMore = True;
                curCmtPageIdx = 1;
                #http://blog.csdn.net/v_july_v/comment/list/6543438?page=1&_0.8271710660267246
                getCmtMainUrl = gConst['spaceDomain'] + "/" + gVal['blogUser'] + "/comment/list/" + str(extractArticleId(url));
                while(needGetMore):
                    #http://blog.csdn.net/v_july_v/comment/list/6543438?page=1&_0.8271710660267246
                    getCmtUrl = getCmtMainUrl + "?page=" + str(curCmtPageIdx) + "&_" + str(random.random());
                    logging.debug("for get comments, generated url=%s", getCmtUrl);
                    respJson = crifanLib.getUrlRespHtml(getCmtUrl);
                    logging.debug("return comment json string=\n%s", respJson);
                    cmtDict = json.loads(respJson);
                    #print "len(cmtDict)=",len(cmtDict);
                    #{"list":[{"ArticleId":6543438,"BlogId":943376,"CommentId":2177665,"Content":"看了好多篇，收货很多， 看的羨慕妒恨！~~~~~~~~\n虽然有很多之前没看过，很多之气都没听过，现在终于见识了！楼主的无私，很感动，就也无私的推荐给公司研发的所有同事，同事都是大赞！！","ParentId":0,"PostTime":"3天前 12:50","Replies":null,"UserName":"zxyzlx","Userface":"http://avatar.csdn.net/6/3/7/3_zxyzlx.jpg"},
                    cmtList = cmtDict['list'];
                    cmtListLen = len(cmtList);
                    #print "cmtListLen=",cmtListLen;
                    allCmtList.extend(cmtList);
                    logging.debug("Add %d returned comment list into all comment list", cmtListLen);
                    #,"page":{"PageSize":100,"PageIndex":1,"RecordCount":173,"PageCount":2},"fileName":"6543438"}
                    cmtPage = cmtDict['page'];
                    #print "cmtPage=",cmtPage;
                    pageIndex = cmtPage['PageIndex'];
                    #print "pageIndex=",pageIndex;
                    pageCount = cmtPage['PageCount'];
                    #print "pageCount=",pageCount;
                    logging.debug("Returned comment info: page=%s, fileName=%s", cmtDict['page'], cmtDict['fileName']);
                    if(curCmtPageIdx < pageCount):
                        curCmtPageIdx += 1;
                    else :
                        needGetMore = False;
                
                gVal['dbgSubCmtNum'] = 0;
                parseAllCommentsList(allCmtList, parsedCommentsList);
                logging.debug("total parsed %d comments, which include %d sub comments", len(parsedCommentsList), gVal['dbgSubCmtNum']);
                #print "total parsed comments= %d"%(len(parsedCommentsList));
    except :
        logging.debug("Error while fetch and parse comment for %s", url);

    return parsedCommentsList;

#------------------------------------------------------------------------------
# check whether is self blog pic
# depend on following picInfoDict definition
def isSelfBlogPic(picInfoDict):
    isSelfPic = False;
    
    filename = picInfoDict['filename'];
    fd1 = picInfoDict['fields']['fd1'];
    fd2 = picInfoDict['fields']['fd2'];

    #(1) hi.csdn
    #(2) http://my.csdn.net/uploads/201205/03/1336005998_9131.png
    if ((fd1=='hi') or (fd1=='my')) and (fd2=='csdn'):
        isSelfPic = True;
    else :
        isSelfPic = False;

    logging.debug("isSelfBlogPic: %s", isSelfPic);

    return isSelfPic;
 
#------------------------------------------------------------------------------
# download file
def downloadFile(curPostUrl, picInfoDict, dstPicFile) :
    curUrl = picInfoDict['picUrl'];
    #if not add follow user-agent, then download file will 403 forbidden error
    headerDict = {
        'Referer' : curPostUrl,
        'User-Agent' : "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:15.0) Gecko/20100101 Firefox/15.0.1",
    };
    return crifanLib.manuallyDownloadFile(curUrl, dstPicFile, headerDict);

#------------------------------------------------------------------------------
def getProcessPhotoCfg():
    # possible own site pic link:
    # type1:
    # http://blog.csdn.net/v_JULY_v/article/details/6530142 contain:
    # http://hi.csdn.net/attachment/201106/7/8394323_1307440587b6WG.jpg
    # html ->
    #<img alt="" src="http://hi.csdn.net/attachment/201106/7/8394323_1307440587b6WG.jpg" width="569" height="345" />
    
    # possible othersite pic url:
        
    processPicCfgDict = {
        # here only extract last pic name contain: char,digit,-,_
        'allPicUrlPat'      : None,
        'singlePicUrlPat'   : None,
        'getFoundPicInfo'   : None,
        'isSelfBlogPic'     : isSelfBlogPic,
        'genNewOtherPicName': None,
        'isFileValid'       : None,
        'downloadFile'      : downloadFile,
    };
    
    return processPicCfgDict;

#------------------------------------------------------------------------------
# extract blog title and description
def extractBlogTitAndDesc(blogEntryUrl) :
    (blogTitle, blogDescription) = ("", "");
    #print "blogEntryUrl=",blogEntryUrl;
    
    try:
        respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
        #logging.debug("url=%s return html=\n%s", blogEntryUrl, respHtml);
        
        # <div id="blog_title">
            # <h1>
                # <a href="/v_JULY_v">结构之法 算法之道</a></h1>
            # <h2></h2>
            # <div class="clear">
            # </div>
        # </div>
        
        # <div id="blog_title">
            # <h1>
                # <a href="/MoreWindows">MoreWindows</a></h1>
            # <h2>学习不在于学了多少，而在于学会多少。</h2>
            # <div class="clear">
            # </div>
        # </div>
        
        soup = htmlToSoup(respHtml);

        foundTitle = soup.find(id="blog_title");
        #print "foundTitle=",foundTitle;
        
        foundTitleA = foundTitle.a;
        #print "foundTitleA=",foundTitleA;
        titStr = foundTitleA.string;
        #print "titStr=",titStr;
        blogTitle = unicode(titStr);
        
        #h1 = foundTitle.h1;
        h2 = foundTitle.h2;
        #print "h1=",h1;
        #print "h2=",h2;
        #h1Str = h1.string;
        h2Str = h2.string;
        #print "h1Str=",h1Str;
        #print "h2Str=",h2Str;
        
        blogDescription = unicode(h2Str);
        #print "blogDescription=",blogDescription;
    except:
        (blogTitle, blogDescription) = ("", "");

    return (blogTitle, blogDescription);

#------------------------------------------------------------------------------
# parse datetime string into (local=GMT+8) datetime value
def parseDatetimeStrToLocalTime(datetimeStr):
    # possible date format:
    # (1) 2012-04-09 23:17
    #print "datetimeStr=",datetimeStr;
    parsedLocalTime = datetime.strptime(datetimeStr, '%Y-%m-%d %H:%M');
    #print "parsedLocalTime=",parsedLocalTime;
    return parsedLocalTime;

####### Login Mode ######

#------------------------------------------------------------------------------
# log in Blog
def loginBlog(username, password) :
    loginOk = False;
    
    return loginOk;

#------------------------------------------------------------------------------
# check whether this post is private(self only) or not
def isPrivatePost(url, html) :
    isPrivate = False;

    return isPrivate;

#------------------------------------------------------------------------------
# modify post content
def modifySinglePost(newPostContentUni, infoDict, inputCfg):
    (modifyOk, errInfo) = (False, "Unknown error!");
    (modifyOk, errInfo) = (False, "Not support this function yet!");
    return (modifyOk, errInfo);

#------------------------------------------------------------------------------   
if __name__=="BlogCsdn":
    print "Imported: %s,\t%s"%( __name__, __VERSION__);