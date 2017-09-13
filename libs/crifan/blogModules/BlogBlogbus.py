#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for Blogbus Blog.

[TODO]

[History]
[v1.2]
1. fix bugs for extract title and date time string


"""

import os;
import re;
import sys;
import math;
import time;
import chardet;
import urllib;
import urllib2;
from datetime import datetime,timedelta;
from BeautifulSoup import BeautifulSoup,Tag,CData,NavigableString;
import logging;
import crifanLib;
import cookielib;
#from xml.sax import saxutils;
import json; # New in version 2.6.
#import random;

#--------------------------------const values-----------------------------------
__VERSION__ = "v1.2";

gConst = {
    'spaceDomain'  : "",
    
    'defaultTimeout': 20, # default timeout seconds for urllib2.urlopen
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',   # maoyushi
    'blogEntryUrl'  : '',   # http://maoyushi.blog.sohu.com
    'cj'            : None, # cookiejar, to store cookies for login mode

    'urlListInfo'   : {
        'inited'        : False,
        #following store related info
        'totalPageNum'  : 0,
    }, 
    
    'urlRelation'   : {
        'inited'        : False, # indicate whether the relation dict is inited or not
        'relationDict'  : {},    # nex link relation dict: { url1:url2, url2:url3, ...}
    }, 
    
    'soupDict'      : {},   # cache the soup for url's html -> url : soup
    
    'processedUrl'  : [], #
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
        #print "get html OK from url=",url;
        
        #logging.debug("before filter, html=%s", html);
        
        # html = html.replace("//禁止右键功能,单击右键将无任何反应", "");
        # html = html.replace("//禁止先择,也就是无法复制", "");
        # html = html.replace("<!--list-->", "");
        # html = html.replace("<!--/list-->", "");
        # html = html.replace("<!-- 74735：右下角弹窗广告 -->", "");
        # html = html.replace("//<![CDATA[", "");
        # html = html.replace("//]]>", "");
        
        # fail parse reason is not the tail, so not remvoe tail
        #html = re.sub("</html>.*$", "</html>", html, re.S);
        # foundTail = re.search("</html>.*$", html, re.S);
        # print "foundTail=",foundTail;
        # if(foundTail):
            # htmlTail = foundTail.group(0);
            # print "htmlTail=",htmlTail;
            # html = html.replace(htmlTail, "</html>");
                

        # http://ronghuihou.blogbus.com/logs/89099700.html
        # inside <head>, it contain script of invalid syntax:
        # <SCRIPT language=JavaScript> 

        # document.oncontextmenu=new Function("event.returnValue=false;"); //禁止右键功能,单击右键将无任何反应 

        # document.onselectstart=new Function( "event.returnValue=false;"); //禁止先择,也就是无法复制 

        # </SCRIPT language=JavaScript>
        
        # which will cause html to soup abnormal -> follow can not find the postHeader from soup

        foundInvliadScript = re.search("<SCRIPT language=JavaScript>.+</SCRIPT language=JavaScript>", html, re.I | re.S );
        logging.debug("foundInvliadScript=%s", foundInvliadScript);
        if(foundInvliadScript):
            invalidScriptStr = foundInvliadScript.group(0);
            logging.debug("invalidScriptStr=%s", invalidScriptStr);
            html = html.replace(invalidScriptStr, "");
            logging.debug("filter out invalid script OK");
        
        soup = htmlToSoup(html);
        #logging.debug("after htmlToSoup, soup=%s", html);
        #print "soup is OK";
        
        # store soup
        gVal['soupDict'][url] = soup;
    
    return soup;

################################################################################
# Implemented Common Functions 
################################################################################

#------------------------------------------------------------------------------
# extract blog user name:
# (1) caochongweiyu from: 
# http://littlebasin.blogbus.com
# http://littlebasin.blogbus.com/
# (2) caochongweiyu from: 
# http://littlebasin.blogbus.com/logs/208796033.html
def extractBlogUser(inputUrl):
    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
    logging.debug("Extracting blog user from url=%s", inputUrl);
    
    try :
        # type1, main url: 
        # http://littlebasin.blogbus.com
        # http://littlebasin.blogbus.com/
        foundMainUrl = re.search("http://(?P<username>[\w-]+)\.blogbus\.com/?", inputUrl);
        if(foundMainUrl) :
            extractedBlogUser = foundMainUrl.group("username");
            generatedBlogEntryUrl = "http://" + extractedBlogUser + ".blogbus.com";
            extractOk = True;
            
        # type2, perma link:
        # http://littlebasin.blogbus.com/logs/208796033.html
        if(not extractOk):
            #foundPermaLink = re.search("http://(?P<username>\w+)\.blog\.sohu\.com/\d+\.html", inputUrl);
            foundPermaLink = re.search("http://(?P<username>[\w-]+)\.blogbus\.com/logs/\d+.html", inputUrl);
            if(foundPermaLink) :
                extractedBlogUser = foundPermaLink.group("username");
                generatedBlogEntryUrl = "http://" + extractedBlogUser + ".blogbus.com";
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
        if(initUrlListInfo()): # to get totalPageNum
            lastPageUrlList = fetchUrlList(gVal['urlListInfo']['totalPageNum']);
            logging.debug("lastPageUrlList=%s", lastPageUrlList);
            if(lastPageUrlList and (len(lastPageUrlList) > 0 )):
                lastPostUrl = lastPageUrlList[-1];
                logging.debug("lastPostUrl=%s", lastPostUrl);
                
                isFound = True;
                retInfo = lastPostUrl;
            else:
                isFound = False;
                errInfo = u"Can not found the item for last page !";
        else:
            isFound = False;
            errInfo = u"init url list info failed !";
    except:
        (isFound, retInfo) = (False, "Unknown error!");

    return (isFound, retInfo);

#------------------------------------------------------------------------------
# extract title
def extractTitle(url, html):
    (needOmit, titleUni) = (False, "");

    try :
        soup = getSoupFromUrl(url);
        #logging.debug("soup.contents=%s", soup.contents);
        foundPostHeader = soup.find(attrs={"class":"postHeader"});
        logging.debug("foundPostHeader=%s", foundPostHeader);
        if(foundPostHeader):
            h2 = foundPostHeader.h2;
            h3 = foundPostHeader.h3;
            
            logging.debug("h2.contents=%s", h2.contents);

            if(h2):
                #following must has h2
                logging.debug("has h2");
                
                if(h3):
                    logging.debug("both has h2 and h3");
                    
                    h2Span = h2.span;
                    h2A = h2.a;
                    
                    if(h2Span and h2A):
                        logging.debug("both has h2 and h3; both has h2 span and h2 a");

                        #http://littlebasin.blogbus.com/logs/1379808.html
                        # <div class="postHeader">
                        #       <h3>2005-08-22</h3>
                        #       <h2>第一篇<span class='category'> - [<a href='/c1396918/'>随笔</a>]</span></h2>
                        # </div>
                        
                        #http://lynnchon.blogbus.com/logs/106189839.html
                        # <div class="postHeader">
                            # <h3>2011-02-21</h3>
                            # <h2>电话是锅血糯米粥<span class='category'> - [<a href='/c3259385/'>又活动呀~~~</a>]</span></h2>
                            # <div class="tags">Tag：<a href="/tag/情侣电话粥/">情侣电话粥</a> </div>
                        # </div>

                        #http://starrysummernight.blogbus.com/logs/100848611.html
                        # <div class="postHeader">
                            # <h2>儿童节的成人礼<span class='category'> - [<a href='/c3822867/'>思维后花园</a>]</span></h2>
                            # <h3>2007-06-01</h3>
                        # </div>

                        h2SoupUniStr = crifanLib.soupContentsToUnicode(h2.contents);
                        logging.debug("h2SoupUniStr=%s", h2SoupUniStr);
                        h2UniNoSpan = re.sub("<span[^<>]*?>.+?</span>", "", h2SoupUniStr);
                        logging.debug("h2UniNoSpan=%s", h2UniNoSpan);
                        
                        titleUni = h2UniNoSpan;
                        
                    elif((not h2Span) and (not h2A)):
                        logging.debug("both has h2 and h3; no h2 span, no h2 a");

                        #http://fsj.blogbus.com/logs/46697205.html
                        # <div class="postHeader">
                            # <h3>2009-09-18</h3>
                            # <h2>Uniqlo</h2>
                        # </div>

                        h2String = h2.string;
                        logging.debug("h2String=%s", h2String);
                        if(h2String):
                            logging.debug("both has h2 and h3; no h2 span, no h2 a; h2 string not null");
                            titleUni = h2String;
                        else:
                            logging.debug("both has h2 and h3; no h2 span, no h2 a; but h2 string is null");
                        
                            #http://kenleung.blogbus.com/logs/219268309.html
                            # <div class="postHeader"><br>
                                # <h3>鐵盒里的影劇院</h3>
                                # <h2></h2>
                            # </div>
                            h3String = h3.string;
                            logging.debug("h3String=%s", h3String);
                            if(h3String):
                                logging.debug("both has h2 and h3; no h2 span, no h2 a; h2 string is null; h3 string not null");
                                titleUni = h3String;
                            else:
                                logging.error("tmp not support: both has h2 and h3; no h2 span, no h2 a; h2 string is null; h3 string also null");
                    elif((not h2Span) and h2A):
                        logging.debug("both has h2 and h3; no h2 span, has h2 a");

                        #http://uk916.blogbus.com/logs/163734653.html
                        # <div class="postHeader">
                            # <h2>海寂&nbsp;&nbsp;[ <a href='/c4044389/'>摄影习作</a> ]</h2>
                            # <h3 class="date">2011-09-27</h3>
                        # </div>
                        h2SoupUniStr = crifanLib.soupContentsToUnicode(h2.contents);
                        logging.debug("h2SoupUniStr=%s", h2SoupUniStr);
                        h2UniNoA = re.sub("\[\s*<a.*?>.+?</a>\s*\]", "", h2SoupUniStr);
                        logging.debug("h2UniNoA=%s", h2UniNoA);
                        h2UniNoNbsp = re.sub("&nbsp;", "", h2UniNoA);
                        logging.debug("h2UniNoNbsp=%s", h2UniNoNbsp);
                        titleUni = h2UniNoNbsp;                        
                    else:
                        logging.error("tmp not support: h2Span=%s, h2A=%s", h2Span, h2A);
                else:
                    logging.debug("has h2, no h3");
                    
                    h2A = h2.a;
                    h2Span = h2.span;

                    if(h2Span and h2A):
                        logging.debug("has h2, no h3; both has h2 span and h2 a");
                        #http://guthrun.blogbus.com/logs/30794012.html
                        # <div class="postHeader">
                            # <div class="c1"></div><div class="c2"></div><div class="c3"></div><div class="c4"></div>
                            # <h2><span class="date">2008-10-30</span>四分之一世纪<span class='category'> - [<a href='/c1982069/'>电影·阅读</a>]</span></h2>
                            # <div class="clear"></div>
                        # </div>
                        
                        h2SoupUniStr = crifanLib.soupContentsToUnicode(h2.contents);
                        logging.debug("h2SoupUniStr=%s", h2SoupUniStr);
                        h2UniNoSpan = re.sub("<span[^<>]*?>.+?</span>", "", h2SoupUniStr);
                        logging.debug("h2UniNoSpan=%s", h2UniNoSpan);
                        
                        titleUni = h2UniNoSpan;
                    elif((not h2Span) and h2A):
                        logging.debug("has h2, no h3; no h2 span, has h2 a");
                    
                        #http://princessbusy.blogbus.com/logs/165961786.html
                        # <div class="postHeader">
                         
                            # <h2><a href="http://princessbusy.blogbus.com/logs/165961786.html ">天府之國，你的寬窄巷子</a></h2>
                         
                        # </div>
                        
                        #http://janexyy.blogbus.com/logs/105359907.html
                        # <div class="postHeader">
                            # <h2>
                                # <a href="http://janexyy.blogbus.com/logs/105359907.html" title="转载时请复制此超链接标明文章原始出处和作者信息">我们，细水长流</a>
                            # </h2>
                        # </div>
                        h2AString = h2.a.string;
                        logging.debug("h2AString=%s", h2AString);
                        
                        titleUni = h2AString;
                    elif((not h2Span) and (not h2A)):
                        #http://tianshizhu.blogbus.com/logs/10327610.html
                        # <div class="postHeader">
                            # <h2>小忧的留言板</h2>
                        # </div>
                        h2String = h2.string;
                        logging.debug("h2String=%s", h2String);
                        
                        titleUni = h2String;
                    else:
                        logging.error("tmp not support: has h2, no h3; h2A=%s, h2Span=%s", h2A, h2Span);
            else:
                logging.error("under postHeader no h2");

                foundInnerBox = foundPostHeader.find(attrs={"class":"innerBox"});
                logging.debug("foundInnerBox=%s", foundInnerBox);
                if(foundInnerBox):
                    innerBoxh2 = foundInnerBox.h2;
                    logging.debug("innerBoxh2=%s", innerBoxh2);
                    
                    if(innerBoxh2):
                        #http://gogodoll.blogbus.com/logs/210877066.html
                        # <div class="postHeader">
                            # <div class="innerBox">
                                # <h2>浮生三日 青岛 DAY3 - May 6, 2012</h2>
                        # ......
                            # </div>
                        # ......
                        # </div>
                        
                        innerBoxh2Str = innerBoxh2.string;
                        logging.debug("innerBoxh2Str=%s", innerBoxh2Str);
                        
                        if(innerBoxh2Str):
                            # remove appended date string
                            foundAppendDateStr = re.search(u" - [\w]{3,4} \d{1,2}, \d{4}$", innerBoxh2Str);
                            logging.debug("foundAppendDateStr=%s", foundAppendDateStr);
                            appendedDateStr = foundAppendDateStr.group(0);
                            innerBoxh2StrNoDate = innerBoxh2Str.replace(appendedDateStr, "");
                            
                            titleUni = innerBoxh2StrNoDate;
                else:
                    logging.error("tmp not support such type: no h2 and under innerBox also no h2");
        else:
            foundPost_Header = soup.find(attrs={"class":"post-header"});
            logging.debug("foundPost_Header=%s", foundPost_Header);
            if(foundPost_Header):
                #http://ajunecat.blogbus.com/logs/190104111.html
                # <div class="post-header">

                # <h2 class="post-title">❤ 彼年。此时 (三)</h2>

                # </div><!-- END POST-HEADER  -->
                postTitle = foundPost_Header.find(attrs={"class":"post-title"});
                logging.debug("postTitle=%s", postTitle);
                if(postTitle):
                    titleUni = postTitle.string;
                    #print "titleUni=",titleUni; # print some special char will cause error !!!
                    logging.debug("post-title type title, titleUni=%s", titleUni);
                else:
                    logging.error("tmp not support: not found post-title, foundPost_Header=%s", foundPost_Header);
            else:
                logging.error("tmp not support: not found post-header, foundPost_Header=%s", foundPost_Header);

        logging.debug("extracted titleUni=%s", titleUni);
    except :
        logging.debug("Fail to extract tiltle from url=%s, html=\n%s", url, html);
        (needOmit, titleUni) = (False, "");

    return (needOmit, titleUni);

#------------------------------------------------------------------------------
# init url list info for latter to get url list
def initUrlListInfo():
    initOk = False;
    
    if(not gVal['urlListInfo']['inited']):
        logging.debug("url list info is not init, so init now");

        blogEntryUrl = gVal['blogEntryUrl'];
        logging.debug("open blogEntryUrl=%s", blogEntryUrl)
        respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
        
        #<div class="pageNavi">共97页   <span>1</span> <a href="/index_2.html">2</a>.............</div>
        #<div class="pageNavi">共1页   <span>1</span>  </div>

        #foundPagenavi = soup.find(attrs={"class":"pageNavi"});
        # makesure here pyhton file is UTF-8 format, for source html is UTF-8
        foundPagenavi = re.search('<div class="pageNavi">共(?P<totalPageNum>\d+)页', respHtml);
        logging.debug("foundPagenavi=%s", foundPagenavi);
        if(foundPagenavi) :
            totalPageNum = foundPagenavi.group("totalPageNum");
            totalPageNum = int(totalPageNum);
            logging.debug("totalPageNum=%s", totalPageNum);
            
            gVal['urlListInfo']['totalPageNum'] = totalPageNum;
            
            gVal['urlListInfo']['inited'] = True;
            logging.debug("init url list info OK");
            
            initOk = True;
        else:
            initOk = False;
    else:
        #print "has inited url list info";
        initOk = True;

    return initOk;

#------------------------------------------------------------------------------
# fetch url list for single page, eg:
#http://gogodoll.blogbus.com/index_1.html
#http://gogodoll.blogbus.com/index_28.html
def fetchUrlList(pageNum):
    logging.debug("now will fetch url list for pageNum=%d", pageNum);

    urlList = [];
    
    if(initUrlListInfo()):
        indexPageUrl = gVal['blogEntryUrl'] + "/index_" + str(pageNum) + ".html";
        logging.debug("indexPageUrl=%s", indexPageUrl);
        
        maxTryNum = 3;
        for tries in range(maxTryNum) :
            try :
                respHtml = crifanLib.getUrlRespHtml(indexPageUrl);
                logging.debug("Fetch url=%s OK", indexPageUrl);
                break # successfully, so break now
            except :
                if tries < (maxTryNum - 1) :
                    logging.warning("Fetch url %s fail, do %d retry", url, (tries + 1));
                    continue;
                else : # last try also failed, so exit
                    logging.error("Has tried %d times to fetch page: %s, all failed!", maxTryNum, url);
        
        soup = htmlToSoup(respHtml);
        foundPosts = soup.findAll(attrs={"class":"postHeader"});
        logging.debug("found %d post list", len(foundPosts));
        #if(foundPosts and len(foundPosts) > 0 ) :
        if(foundPosts) :
            postNumInPage = len(foundPosts);
            logging.debug("postNumInPage=%d", postNumInPage);
            for eachPost in foundPosts:
                # <DIV class="postHeader">
                # <DIV class="innerBox">
                # <H2><A href="http://gogodoll.blogbus.com/logs/74355989.html">你一定要幸福</A> - Sep 
                # 5, 2010</H2></DIV>
                # <DIV class="bgBox"></DIV></DIV>
                postUrl = eachPost.h2.a['href'];
                logging.debug("postUrl=%s", postUrl);
                urlList.append(postUrl);
        
        logging.debug("for pageNum=%d, total fetch %d url", pageNum, len(urlList));
    else:
        logging.debug("fetchUrlList: initUrlListInfo failed !");

    return urlList;

#------------------------------------------------------------------------------
# init next link relation dict
def initNextLinkRelationDict():
    if(not gVal['urlRelation']['inited']):
        try:
            logging.info("begin to init the relation for next link");
            allPageUrlList = [];
            
            if(initUrlListInfo()):
                logging.debug("in initNextLinkRelationDict, initUrlListInfo OK");
                            
                # for output info use
                maxNumReportOnce = 10;
                lastRepTime = 0;                
                
                for pageIdx in range(gVal['urlListInfo']['totalPageNum']):
                    pageNum = pageIdx + 1;
                    logging.debug("pageNum=%d", pageNum);
                    urlList = fetchUrlList(pageNum);
                    
                    # report for each maxNumReportOnce
                    curRepTime = pageIdx/maxNumReportOnce;
                    if(curRepTime != lastRepTime) :
                        # report
                        logging.info("  Has processed url list pages: %5d", pageIdx);
                        # update
                        lastRepTime = curRepTime;
                    
                    logging.debug("fetched urlList=%s", urlList);
                    if(urlList):
                        allPageUrlList.extend(urlList);
                    else:
                        # can not get more, so quit
                        break;
                    logging.debug("has got page url list len=%d", len(allPageUrlList));
            else:
                logging.debug("initNextLinkRelationDict: initUrlListInfo failed !");

            logging.debug("len(allPageUrlList)=%d", len(allPageUrlList));
            logging.debug("allPageUrlList=%s", allPageUrlList)
            if(allPageUrlList):
                allPageUrlList.reverse(); # -> is OK, the self is reversed !!!
                logging.debug("allPageUrlList reverse OK");
                reversedPageUrlList = allPageUrlList;
                logging.debug("reversedPageUrlList=%s", reversedPageUrlList);
                urlListLen = len(reversedPageUrlList);
                logging.debug("urlListLen=%d",urlListLen);
                for i in range(urlListLen):
                    curPemaLink = reversedPageUrlList[i];
                    logging.debug("[%d] curPemaLink=%s", i, curPemaLink);
                    if(i != (urlListLen - 1)):
                        # if not the last one
                        nextPermaLink = reversedPageUrlList[i + 1];
                    else:
                        # last one's next link is empty
                        nextPermaLink = "";
                    logging.debug("nextPermaLink=%s", nextPermaLink);
                    
                    gVal['urlRelation']['relationDict'][curPemaLink] = nextPermaLink;
            
            logging.debug("gVal['urlRelation']['relationDict']=%s", gVal['urlRelation']['relationDict']);
            gVal['urlRelation']['inited'] = True;
            logging.info("init the relation for next link completed");
        except:
            logging.error("Failed to init the relation for next link !");
            sys.exit(2);

    return ;

#------------------------------------------------------------------------------
# get next perma link from the dict
#{'http://gogodoll.blogbus.com/logs/74352746.html':'http://gogodoll.blogbus.com/logs/74355989.html', ...}
def getNextLinkFromDict(curPemaLink):
    logging.debug("curPemaLink=%s", curPemaLink);
    initNextLinkRelationDict();
    
    nextPermaLink = "";
    if(curPemaLink in gVal['urlRelation']['relationDict']) :
        nextPermaLink = gVal['urlRelation']['relationDict'][curPemaLink];
    else:
        nextPermaLink = "";

    return nextPermaLink;

#------------------------------------------------------------------------------
# find next permanent link of current post
def findNextPermaLink(url, html) :
    nextLinkStr = '';
    nextPostTitle = "";

    try :
        #print "TODO: tmp not find next from dict !!!!"
        #eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
        
        # nomally, following (parse next) is work, but some blogbus blog's next/prev disabled,
        # so here use unified get next link from relation dict
        #print "url=",url;
        nextLinkStr = getNextLinkFromDict(url);
        #print "!!!!!!!!!!!!!!!!!!!!!!! tmp not gen next link dict for quick test";
        logging.debug("nextLinkStr=%s", nextLinkStr);
        
        # soup = getSoupFromUrl(url);
        # # <div class="context"><span class="pre"></span> | <span class="top"><a href="http://littlebasin.blogbus.com">首页</a></span> | <span class="next"><a href='/logs/1379836.html'>随手&nbsp;&nbsp;&gt;&gt;</a></span></div>
        # foundNext = soup.find(attrs={"class":"next"});
        # if(foundNext):
            # nextLinkStr = gVal['blogEntryUrl'] + foundNext.a['href'];
            # print "nextLinkStr=",nextLinkStr;
            # nextPostTitle = foundNext.a.string;
            # print "nextPostTitle=",nextPostTitle;
        # else:
            # #last one no next:
            # #http://kenleung.blogbus.com/logs/219506522.html
            # #<center><div class="context"><span class="pre"><a href='/logs/219413565.html'>&lt;&lt;&nbsp;&nbsp;中平里至消失的距離Ⅱ</a></span> | <span class="top"><a href="http://kenleung.blogbus.com">Home</a></span> | <span class="next"></span></div></center>
            # nextLinkStr = "";
            # nextPostTitle = "";

        logging.debug("Found real next permanent link=%s, title=%s", nextLinkStr, nextPostTitle);
    except :
        logging.debug("Fail to extract next perma link from url=%s, html=\n%s", url, html);
        nextLinkStr = '';

    return nextLinkStr;

#------------------------------------------------------------------------------
# extract datetime string
def extractDatetime(url, html) :
    datetimeUni = '';
#try :
    #logging.debug("extractDatetime_html=\n%s", html);
    
    soup = getSoupFromUrl(url);
    pubDateUni = "";
    pubTimeUni = "";
    
    foundFooter = soup.find(attrs={"class":"postFooter"});
    if(foundFooter):
        foundPubTime = foundFooter.find(attrs={"class":"time"});
        logging.debug("foundPubTime=%s", foundPubTime);
        
        foundPubDateInFooter = foundFooter.find(attrs={"class":"date"});
        logging.debug("foundPubDateInFooter=%s", foundPubDateInFooter);
        
        if(foundPubTime):
            pubTimeUni = foundPubTime.string;
            logging.debug("pubTimeUni=%s", pubTimeUni);
            if(pubTimeUni):
                needCheckDate = True;
                
                foundTimeFileds = re.search(u"(?P<dateFields>(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}).*?)?(?P<hour>\d{2})[时|:](?P<minute>\d{2})([分|:](?P<second>\d{2})秒?)?", pubTimeUni);
                logging.debug("foundTimeFileds=%s", foundTimeFileds);
                if(foundTimeFileds):
                    #http://littlebasin.blogbus.com/logs/219132195.html
                    # <div class="postFooter">
                        # ......
                        # <div class="menubar">...... 发表于<span class="time">21:02:00</span> | ......</div>
                    # </div>
                    
                    #http://gogodoll.blogbus.com/logs/210877066.html
                    # <div class="postFooter">
                        # ......
                        # <div class="menubar"><span class="author"><a href="http://home.blogbus.com/profile/GOGODOLL">GOGODOLL</a></span> 发表于<span class="time">15时15分00秒</span> | ......</div>
                    # </div>
                    
                    # must contain time fields:hour/minute/second, possbile also contain date fields: year/month/day
                    hour = foundTimeFileds.group("hour");
                    minute = foundTimeFileds.group("minute");
                    second = foundTimeFileds.group("second");
                    if(not second):
                        #http://kidonly.blogbus.com/logs/17749041.html
                        # <div class="postFooter">
                            # ......
                            # <div class="menubar"><span class="author"><a href="http://home.blogbus.com/profile/kidonly">kidonly</a></span> 发表于<span class="time">12:35</span> | ......</div>
                        # </div>
                        second = "00";
                    pubTimeUni = hour+":"+minute+":"+second;
                    logging.debug("must contain time fileds: hour=%s, minute=%s, second=%s, merged pubTimeUni=%s", hour, minute, second, pubTimeUni);

                    dateFields = foundTimeFileds.group("dateFields");
                    logging.debug("dateFields=%s", dateFields);
                    if(dateFields):
                        #http://kdinsky.blogbus.com/logs/131080138.html
                        # <div class="postFooter">
                            # <div class="menubar"><span class="author"><a href="http://home.blogbus.com/profile/Kdinsky">饭饭</a></span> 发表于<span class="time">2011-05-28 11:29:00</span> | ......</div>
                        # </div>
                        
                        #http://princessbusy.blogbus.com/logs/165961786.html
                        # <div class="postFooter">
                                                            # <div class="menubar"><span class="time">2011-10-13/09:40:00</span> | ......</div>
                        # </div>
                        
                        year = foundTimeFileds.group("year");
                        month = foundTimeFileds.group("month");
                        day = foundTimeFileds.group("day");
                        logging.debug("also find date fileds: year=%s, minute=%s, day=%s", year, month, day);
                        
                        # also find date fields: year/month/day
                        pubDateUni = year+"-"+month+"-"+day;
                        datetimeUni = pubDateUni + " " + pubTimeUni;
                        logging.debug("merged pubDateUni=%s, datetimeUni=%s", pubDateUni, datetimeUni);
                        needCheckDate = False; # infrom latter no need continue check date string
                    else:
                        logging.debug("not find valid date fileds during find time string");
                else:
                    # invalid time string, set null here
                    logging.debug("unknown type of time ( and date) string");
                    pubTimeUni = "";
                    needCheckDate = False; # inform latter here error, no need continue check
                            
                #continue to check data only when pubTimeUni is valid
                if(needCheckDate and pubTimeUni):
                    logging.debug("now check the date string");
                    
                    foundPubDate = soup.find(attrs={"class":"postHeader"});
                    #print "foundPubDate=",foundPubDate;
                    h3 = foundPubDate.h3;
                    h2 = foundPubDate.h2;

                    #print "h3=",h3;
                    #print "h3.contents=",h3.contents;
                    #print "h3.string=",h3.string;
                    
                    if(h3 and h3.string and (re.match(u"^\d{4}[年|-]\d{2}[月|-]\d{2}日?$", h3.string))):
                        #http://littlebasin.blogbus.com/logs/1379808.html
                        # <div class="postHeader">
                        #       <h3>2005-08-22</h3>
                        #       <h2>第一篇<span class='category'> - [<a href='/c1396918/'>随笔</a>]</span></h2>
                        # </div>

                        #http://sweetmelody.blogbus.com/logs/200842078.html
                        # <div class="postHeader">
                            # <h3>2012年03月25日</h3>
                            # <h2>遇見那時的自己。<span class='category'> - [<a href='/c2772915/'>旅程</a>]</span></h2>
                        # </div>
                        
                        foundDateStr = re.search(u"^(?P<year>\d{4})[年|-](?P<month>\d{2})[月|-](?P<day>\d{2})日?$", h3.string);
                        year    = foundDateStr.group("year");
                        month   = foundDateStr.group("month");
                        day     = foundDateStr.group("day");
                        pubDateUni = year + "-" + month + "-" + day;
                        logging.debug("original date string=%s, merged pubDateUni=%s", h3.string, pubDateUni);
                    elif(h3 and h3.string and (re.match(u"^\w+ \d+, \d+$", h3.string))):
                        #http://gogodoll.blogbus.com/logs/210877066.html
                        # <div class="postHeader">
                            # <h3>May 6, 2012</h3>
                            # <h2>浮生三日 青岛 DAY3</h2>
                        # </div>
                        
                        #http://gogodoll.blogbus.com/logs/212749872.html
                        # <div class="postHeader">
                            # <h3>May 13, 2012</h3>
                            # <h2>嘴爸镜头下的丽江</h2>
                        # </div>
                        
                        #http://gogodoll.blogbus.com/logs/216231813.html
                        # <div class="postHeader">
                            # <h3>Jun 3, 2012</h3>
                            # <h2>why not?</h2>
                        # </div>
                        
                        try:
                            h3String = h3.string;
                            logging.debug("h3String=%s", h3String);
                            #8.1.7. strftime() and strptime() Behavior
                            #%b Locale’s abbreviated month name. 
                            #%d Day of the month as a decimal number [01,31]. 
                            #%Y Year with century as a decimal number. 
                            parsedDate = datetime.strptime(h3String, "%b %d, %Y");
                            logging.debug("parsedDate=%s", parsedDate);
                            
                            datetimeUni = parsedDate.strftime("%Y-%m-%d %H:%M:%S");
                            logging.debug("re-generated datetimeUni=%s", datetimeUni);
                        except:
                            logging.debug("parse %s to date failed.", h3String);

                    elif(foundPubDate.find(attrs={"class":"date"})):
                        #http://guthrun.blogbus.com/logs/30794012.html
                        # <div class="postHeader">
                            # <div class="c1"></div><div class="c2"></div><div class="c3"></div><div class="c4"></div>
                            # <h2><span class="date">2008-10-30</span>四分之一世纪<span class='category'> - [<a href='/c1982069/'>电影·阅读</a>]</span></h2>
                            # <div class="clear"></div>
                        # </div>
                        
                        #http://mangobox.blogbus.com/logs/88955088.html
                        # <div class="postHeader">
                            # <h2>老照片的故事~人生有几个30年？！</h2>
                                                    # <h5 class="date">2010-12-14</h5>
                            # <div class="clear"></div>
                        # </div>
                        
                        foundClassDate = foundPubDate.find(attrs={"class":"date"});
                        logging.debug("foundClassDate.string=%s", foundClassDate.string);
                        pubDateUni = foundClassDate.string;
                    elif(foundPubDateInFooter):
                        #http://show-lee.blogbus.com/logs/220010664.html
                        # <div class="postFooter">
                            # ......
                            # <div class="menubar"><span class="author"><a href="http://home.blogbus.com/profile/show-lee">show-lee</a></span> 发表于<span class="time">00:19:00</span><span class="date">2012-07-18</span> |......</div>
                        # </div>
                        pubDateUni = foundPubDateInFooter.string;
                        logging.debug("find date in footer, pubDateUni=%s", pubDateUni);
                    else:
                        #http://gogodoll.blogbus.com/logs/210877066.html
                        # <div class="postHeader">
                            # <div class="innerBox">
                                # <h2>浮生三日 青岛 DAY3 - May 6, 2012</h2>
                        # ......
                            # </div>
                        # ......
                        # </div>
                        logging.debug("not normal h3, so continue check h2. h2=%s", h2);
                        if(h2):
                            h2Str = h2.string;
                            #print "h2Str=",h2Str;
                            foundAppendDate = re.search(u" - (?P<dateStr>[\w]{3,4} \d{1,2}, \d{4})$", h2Str);
                            logging.debug("foundAppendDate=%s", foundAppendDate);
                            if(foundAppendDate):
                                dateStr = foundAppendDate.group("dateStr"); #Sep 5, 2010
                                logging.debug("dateStr=%s", dateStr);
                                
                                #print "type(dateStr)=",type(dateStr);
                                #print "len(dateStr)=",len(dateStr);
                                #dateStr = dateStr.encode("utf-8");
                                #print "type(dateStr)=",type(dateStr);
                                
                                #parsedTime = time.strptime(dateStr, "%b %d, %y");
                                parsedTime = time.strptime(dateStr, "%b %d, %Y");
                                #parsedTime = time.strptime(dateStr, "%B %d, %Y");# here strptime %B will cause UnicodeDecodeError:
                                #http://www.crifan.com/python_strptime_unicodedecodeerror_0xe5_ordinal_not_in_range_128/
                                                            
                                #print "parsedTime.tm_year=",parsedTime.tm_year;
                                #print "parsedTime.tm_mon=",parsedTime.tm_mon;
                                #print "parsedTime.tm_mday=",parsedTime.tm_mday;
                                
                                logging.debug("parsedTime=%s", parsedTime);
                                pubDateUni = time.strftime("%Y-%m-%d", parsedTime);
                                logging.debug("after strftime, pubDateUni=%s", pubDateUni);

                                #parsedDatetime = datetime.strptime(dateStr, "%B %d, %Y");
                                #print "parsedDatetime=",parsedDatetime;
                                #pubDateUni = datetime.strftime("%Y-%m-%d", parsedDatetime);

                    logging.debug("in the end, pubDateUni=%s, pubTimeUni=%s", pubDateUni, pubTimeUni);
                    
                    if(pubDateUni and pubTimeUni):
                        datetimeUni = pubDateUni + " " + pubTimeUni;
            else:
                #http://kenleung.blogbus.com/logs/219268309.html
                #<span class="time"></span>
                
                #if the time part is None 
                #-> must be no valid date and time 
                #-> use current time as its publish time
                curTime = datetime.now();
                #print "curTime=",curTime;
                datetimeUni = curTime.strftime("%Y-%m-%d %H:%M:%S");
                logging.warning("can find class=time, but time string is null, so use current time: %s", datetimeUni);
        else:
            #try to find the date (and/or time) string
            logging.debug('class="time" not in postFooter, foundFooter.contents=%s',foundFooter.contents);
            footerUni = crifanLib.soupContentsToUnicode(foundFooter.contents);
            #print "footerUni=",footerUni; #here can not use print, for the footerUni some char, un-printable in cmd GBK
            foundDatetimeStr = re.search("(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\s*?(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})", footerUni);
            logging.debug("foundDatetimeStr=%s", foundDatetimeStr);
            if(foundDatetimeStr):
                #http://janexyy.blogbus.com/logs/105359907.html
                # <div class="postFooter">
                    # <div>
                        # <a target="_blank" title="点击查看个人信息" href="http://home.blogbus.com/profile/jane%20chan">jane chan <span class="red">
                            # ♥</span> 2011-02-15 16:11:00</a>
                    # </div>
                    # <div>
                        # ......
                    # </div>
                # </div>
                
                #http://tianshizhu.blogbus.com/logs/10327610.html
                # <div class="postFooter">
                    # ......
                    # <div>Post on:<a href="http://tianshizhu.blogbus.com/logs/10327610.html" target="_blank">2000-10-1711:28:17</a></div>
                    # ......
                # </div>
                year = foundDatetimeStr.group("year");
                month = foundDatetimeStr.group("month");
                day = foundDatetimeStr.group("day");
                hour = foundDatetimeStr.group("hour");
                minute = foundDatetimeStr.group("minute");
                second = foundDatetimeStr.group("second");
                datetimeUni = year+"-"+month+"-"+day+" "+hour+":"+minute+":"+second;
                logging.debug("found the date time string, datetimeUni=%s", datetimeUni);
            else:
                # now try to find class="date" in postHeader
                foundPostHeader = soup.find("div", {"class":"postHeader"});
                logging.debug("foundPostHeader=%s", foundPostHeader);
                if(foundPostHeader):
                    foundH3Date = foundPostHeader.find("h3", {"class":"date"});
                    logging.debug("foundH3Date=%s", foundH3Date);

                    if(foundH3Date):
                        #http://uk916.blogbus.com/logs/163734653.html
                        # <div class="postHeader">
                            # <h2>海寂&nbsp;&nbsp;[ <a href='/c4044389/'>摄影习作</a> ]</h2>
                            # <h3 class="date">2011-09-27</h3>
                        # </div>
                        dateUni = foundH3Date.string;
                        logging.debug("dateUni=%s", dateUni);
                        datetimeUni = dateUni + " 00:00:00";
    else:
        #http://ajunecat.blogbus.com/logs/190104111.html
        # no postFooter, only contain:
        # <p class="postmetadata">
        # This entry was posted by [A June Cat] under  <a href='/c2762972/'>上车走人</a>. You can leave your comment.</p>
        curTime = datetime.now();
        #print "curTime=",curTime;
        datetimeUni = curTime.strftime("%Y-%m-%d %H:%M:%S");
        logging.warning("  can not find postFooter, so use current time: %s", datetimeUni);
        
    logging.debug("in the end, datetimeUni=%s", datetimeUni);

    return datetimeUni;

#------------------------------------------------------------------------------
# extract blog item content
def extractContent(url, html) :
    contentUni = '';
    try :
        #logging.debug("extractContent_html=\n%s", html);

        # <div class="postBody">
            # <p class="cc-lisence" style="line-height:180%;">......</p>对很多事情，我都属于慢热的人。Blog都已经在网上热了一年多了，我才想起申请一个。.......我争取。</p>
            # <div class="relpost">......</div>                                    
            # <div class="addfav">......</div>
            # <script type='text/javascript' src='http://partner.googleadservices.com/gampad/google_service.js'></script>
            # <script type='text/javascript'>......</script>
            # <script type='text/javascript'>......</script>
            # <br /><br /><br />
            # <div style="width:468px;">
            # <script type='text/javascript'>......</script>
            # </div>
            # <br />
            # <div class="clear"></div>
        # </div>
        soup = getSoupFromUrl(url);
        
        #print "dir(soup)",dir(soup);
        
        foundPostbody = soup.find(attrs={"class":"postBody"});
        foundPost_Entry = soup.find(attrs={"class":"post-entry"});
        
        contents = None;
        if(foundPostbody):
            # most blogs is this type
            contents = foundPostbody.contents;
        elif(foundPost_Entry):
            #http://ajunecat.blogbus.com/logs/190104111.html
            contents = foundPost_Entry.contents;
        else:
            contentUni = "";

        if(contents):
            logging.debug("processing: p class cc-lisense");
            contents = crifanLib.removeSoupContentsTagAttr(contents, "p", "class", "cc-lisence", True); #版权声明
            logging.debug("processing: div class relpost");
            contents = crifanLib.removeSoupContentsTagAttr(contents, "div", "class", "relpost", True); #历史上的今天, 相关帖子
            logging.debug("processing: div class addfav");
            contents = crifanLib.removeSoupContentsTagAttr(contents, "div", "class", "addfav", True); #收藏到
            
            # here can NOT remove div,style, for maybe it will content valid content !!!
            #contents = crifanLib.removeSoupContentsTagAttr(contents, "div", "style"); 

            #http://kdinsky.blogbus.com/logs/131080138.html
            #remove speical <div class="postFooter"> inside <div class="postBody">
            logging.debug("processing: div class postFooter");
            contents = crifanLib.removeSoupContentsTagAttr(contents, "div", "class", "postFooter", True);

            #remove embedded <script type="text/javascript"> in <div style="padding-left:2em">
            logging.debug("processing: script type text/javascript");
            contents = crifanLib.removeSoupContentsTagAttr(contents, "script", "type", "text/javascript", True);
            
            #<div id="ckepop">
            logging.debug("processing: div id ckepop");
            contents = crifanLib.removeSoupContentsTagAttr(contents, "div", "id", "ckepop", True);
            
            #<p class="postmetadata">
            logging.debug("processing: p class postmetadata");
            contents = crifanLib.removeSoupContentsTagAttr(contents, "p", "class", "postmetadata", True);

            #logging.debug("---soup filtered contents=\n%s", contents);
            
            contentUni = crifanLib.soupContentsToUnicode(contents);
            #print "type(contentUni)=",type(contentUni);
            #logging.debug("original contentUni=%s", contentUni);

    except :
        logging.debug("Fail to extract post content from url=%s, html=\n%s", url, html);
        contentUni = '';
    
    return contentUni;

#------------------------------------------------------------------------------
# extract category
def extractCategory(url, html) :
    catUni = '';
        
    try :
        #logging.debug("extractCategory_html=\n%s", html);
        
        soup = getSoupFromUrl(url);
        
        foundPostHeader = soup.find(attrs={"class":"postHeader"});
        foundPostmetadata = soup.find(attrs={"class":"postmetadata"});
        logging.debug("foundPostHeader=%s", foundPostHeader);
        logging.debug("foundPostmetadata=%s", foundPostmetadata);
        
        if(foundPostHeader):
            foundCategory = foundPostHeader.find(attrs={"class":"category"});
            logging.debug("foundCategory=%s", foundCategory);
            if(foundCategory):
                #http://littlebasin.blogbus.com/logs/1379808.html
                #<h2>第一篇<span class='category'> - [<a href='/c1396918/'>随笔</a>]</span></h2>
                
                #http://lynnchon.blogbus.com/logs/106589756.html
                # <div class="postHeader">
                    # <h3>2011-02-24</h3>
                    # <h2>诗意<span class='category'> - [<a href='/c3172722/'>悟の</a>]</span></h2>
                    # <div class="tags">Tag：<a href="/tag/情怀/">情怀</a> </div>
                # </div>
                catUni = foundCategory.a.string;
                logging.debug("category is in a.string=%s", catUni);
            else:
                #http://janexyy.blogbus.com/logs/105359907.html
                # <div class="postHeader">
                    # <h2>
                        # <a href="http://janexyy.blogbus.com/logs/105359907.html" title="转载时请复制此超链接标明文章原始出处和作者信息">我们，细水长流</a>
                    # </h2>
                # </div>
                # <div class="postFooter">
                    # <div>
                        # <a target="_blank" title="点击查看个人信息" href="http://home.blogbus.com/profile/jane%20chan">jane chan <span class="red">
                            # ♥</span> 2011-02-15 16:11:00</a>
                    # </div>
                    # <div>
                        # 分类： | 标签：<a href="/tag/情侣电话粥/">情侣电话粥</a> <a href="/tag/愛情/">愛情</a> <a href="/tag/小女人/">小女人</a>  | <a href='http://blog.home.blogbus.com/5317343/posts/105359907/form' class='edit'>编辑</a> | ......
                    # </div>
                # </div>
                foundPostFooter = soup.find(attrs={"class":"postFooter"});
                footerUni = crifanLib.soupContentsToUnicode(foundPostFooter.contents);
                #print "type(footerUni)=",type(footerUni);
                #logging.debug("footerUni=%s", footerUni);
                #print "footerUni=",footerUni;
                #foundCatZhcn = re.search(u"分类：(?P<catName>.+)|", footerUni); # ERROR !!!!
                foundCatZhcn = re.search(u"分类：(?P<catName>.*?)\|", footerUni);
                logging.debug("foundCatZhcn=%s", foundCatZhcn);
                if(foundCatZhcn):
                    #print "foundCatZhcn.group(0)=",foundCatZhcn.group(0);
                    #print "foundCatZhcn.group(1)=",foundCatZhcn.group(1);
                    catName = foundCatZhcn.group("catName");
                    logging.debug("found the catName=%s", catName);
                    if(catName):
                        catUni = catName.strip();
                        logging.debug("after strip catUni=%s", catUni);
                        #print "len(catUni)=",len(catUni);
                        #print "type(catUni)=",type(catUni);
                        #noneTest = None;
                        #print "type(noneTest)=",type(noneTest);
        elif(foundPostmetadata):
            #http://ajunecat.blogbus.com/logs/190104111.html
            # <p class="postmetadata">
            # This entry was posted by [A June Cat] under  <a href='/c2762972/'>上车走人</a>. You can leave your comment.</p>
            postmetadataUni = crifanLib.soupContentsToUnicode(foundPostmetadata.contents);
            logging.debug("postmetadataUni=%s", postmetadataUni);
            #foundCatA = re.search("<a href='/c\d+/'>(?P<categoryStr>.+?)</a>", postmetadataUni);
            foundCatA = re.search('<a href="/c\d+/">(?P<categoryStr>.+?)</a>', postmetadataUni);
            logging.debug("foundCatA=%s", foundCatA);
            if(foundCatA):
                categoryStr = foundCatA.group("categoryStr");
                logging.debug("categoryStr=%s", categoryStr);
                catUni = categoryStr;
            
        logging.debug("extracted category=%s", catUni);
    except :
        logging.debug("can not extract category from url=%s", url);
        catUni = "";
    
    return catUni;

#------------------------------------------------------------------------------
# extract tags info
def extractTags(url, html) :
    tagList = [];
    try :
        #logging.debug("extractTags_html=\n%s", html);

        soup = getSoupFromUrl(url);
        foundFooter = soup.find(attrs={"class":"postFooter"});
        #print "foundFooter=",foundFooter;
        foundTags= foundFooter.find(attrs={"class":"tags"});
        # maybe empty, eg: http://kenleung.blogbus.com/logs/219268309.html
        logging.debug("foundTags=%s", foundTags);
        if(foundTags):
            #http://littlebasin.blogbus.com/logs/1379808.html
            # <div class="postFooter">
                # <div class="tags">Tag：<a href="/tag/随手/">随手</a> <a href="/tag/文字/">文字</a> <a href="/tag/心情/">心情</a> </div>
                # ...
            # </div>
            aList = foundTags.findAll("a");
            #aList = foundTags.a;
            logging.debug("tags aList=%s", aList);
            if(aList):
                for eachA in aList:
                    singleTagStr = eachA.string;
                    logging.debug("singleTagStr=%s", singleTagStr);
                    if(singleTagStr):
                        tagList.append(singleTagStr);
        else:
            #http://janexyy.blogbus.com/logs/105359907.html
            # <div class="postFooter">
                # <div>
                    # <a target="_blank" title="点击查看个人信息" href="http://home.blogbus.com/profile/jane%20chan">jane chan <span class="red">
                        # ♥</span> 2011-02-15 16:11:00</a>
                # </div>
                # <div>
                    # 分类： | 标签：<a href="/tag/情侣电话粥/">情侣电话粥</a> <a href="/tag/愛情/">愛情</a> <a href="/tag/小女人/">小女人</a>  | <a href='http://blog.home.blogbus.com/5317343/posts/105359907/form' class='edit'>编辑</a> | ......
                # </div>
            # </div>
            footerUni = crifanLib.soupContentsToUnicode(foundFooter.contents);
            foundTagsStr = re.search(u"标签：(?P<tagsStr>.*?)\|", footerUni);
            logging.debug("foundTagsStr=%s", foundTagsStr);
            if(foundTagsStr):
                tagsStr = foundTagsStr.group("tagsStr");
                logging.debug("tagsStr=%s", tagsStr);
                foundTagsA = re.findall(u'<a href="/tag/(?P<tagName>.+?)/">(?P=tagName)</a>', tagsStr);
                logging.debug("foundTagsA=%s", foundTagsA);
                tagList = foundTagsA;
    except :
        logging.debug("Fail to extract tags from url=%s, html=\n%s", url, html);
        tagList = [];

    return tagList;

#------------------------------------------------------------------------------
# parse single source comment soup into dest comment dict 
def parseSingleCmtDict(destCmtDict, srcCmtDict, cmtId):
    global gVal;
    destCmtDict['id'] = cmtId;
    #print "destCmtDict['id']=",destCmtDict['id'];
    
    logging.debug("--- comment[%d] ---", destCmtDict['id']);
    logging.debug("srcCmtDict=%s", srcCmtDict);

    destCmtDict['author'] = srcCmtDict['authorName'];

    destCmtDict['author_url'] = srcCmtDict['authorUrl'];
    
    localTime = datetime.strptime(srcCmtDict['cmtTime'], '%Y-%m-%d %H:%M:%S');
    #print "localTime=",localTime;
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    #print "gmtTime=",gmtTime;
    destCmtDict['date'] = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");

    destCmtDict['content'] = srcCmtDict['cmtBody'];
    #print "destCmtDict['content']=",destCmtDict['content'];

    if(srcCmtDict['isReplyCmt']):
        #previous is its parent
        destCmtDict['parent'] = cmtId - 1;
    else:
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
    
    for cmtIdx, srcCmtDict in enumerate(allCmtList):
        destCmtDict = {};
        cmtId = cmtIdx + 1;
        parseSingleCmtDict(destCmtDict, srcCmtDict, cmtId);
        parsedCommentsList.append(destCmtDict);

    logging.debug("after parse, got %d comments", len(parsedCommentsList));
    return;

#------------------------------------------------------------------------------
# extract post id from perma link
# 1379808 from http://littlebasin.blogbus.com/logs/1379808.html
def extractPostId(url):
    postId = "";
    found = re.search("http://\w+\.blogbus\.com/logs/(?P<postId>\d+).html", url);
    if(found):
        postId = found.group("postId");
    return postId;

#------------------------------------------------------------------------------
# generate the url for get comments
def genGetCmtUrl(postId, pageNum):
    #http://littlebasin.blogbus.com/logs/1379808.html
    #http://littlebasin.blogbus.com/logs/1379808_c1.html
    #http://littlebasin.blogbus.com/logs/1379808_c2.html
    getCmtUrl = gVal['blogEntryUrl'] + "/logs/" + postId + "_c" + str(pageNum) + ".html";
    logging.debug("getCmtUrl=%s", getCmtUrl);
    return getCmtUrl;

#------------------------------------------------------------------------------
# extract comment dict list from html, containing comments
def extractCmtDictList(url, html):
    curPageCmtList = [];
    
    soup = getSoupFromUrl(url);

    #<ul id="comments"><h2>评论</h2> ......</ul>
    foundComments = soup.find(attrs={"id":"comments"});
    #print "foundComments=",foundComments;
    liList = foundComments.findAll("li");
    #print "liList=",liList;
    logging.debug("len(liList)=%d", len(liList));
    for eachLi in liList:
        cmtDict = {
            'cmtBody'   : "",
            'authorUrl' : "",
            'authorName': "",
            'cmtTime'   : "",
            'isReplyCmt': False,
        };

        # <li><div class='cmtBody'>AC米兰呀，哈哈</div>
        # <div class='menubar'><span class='author'><a href="http://lorn-skater.blogbus.com/"  target="_blank">孤独滑客</a> | </span> 发表于<span class='time'>2005-08-24 23:18:31</span>
        # <span>[<a href="#" onclick="Picobox.showIFrameBox('回复评论', 'http://blog.home.blogbus.com/1062198/comments/1379808/reply?cmid=1807191', {width:310, height:200});return false;" rel="facebox">回复</a>]</span></div></li>
        foundCmtbody = eachLi.find(attrs={"class":"cmtBody"});
        #print "foundCmtbody=",foundCmtbody;
        cmtContents = foundCmtbody.contents;
        #print "cmtContents=",cmtContents;
        cmtBody = crifanLib.soupContentsToUnicode(cmtContents);
        #print "cmtBody=",cmtBody;
        foundAuthor = eachLi.find(attrs={"class":"author"});
        #print "foundAuthor=",foundAuthor;
        authorA = foundAuthor.a;
        #print "authorA=",authorA;
        authorUrl = "";
        authorName = "";
        if(authorA):
            authorUrl = authorA['href'];
            #print "authorUrl=",authorUrl;
            authorName = authorA.string;
            #print "authorName=",authorName;
        else:
            #special:
            #http://littlebasin.blogbus.com/logs/171413104_c1.html
            #<span class='author'>ship888 | </span> 发表于<span class='time'>2012-07-09 14:12:31</span>
            authorStr = foundAuthor.string;
            #print "authorStr=",authorStr;
            authorStr = authorStr.replace("|", "");
            #print "authorStr=",authorStr;
            authorStr = authorStr.strip(" ");
            #print "authorStr=",authorStr;
            authorName = authorStr;

        foundTime = eachLi.find(attrs={"class":"time"});
        #print "foundTime=",foundTime;
        cmtTime = foundTime.string;
        #print "cmtTime=",cmtTime;
        
        cmtDict['cmtBody'] = cmtBody;
        cmtDict['authorUrl'] = authorUrl;
        cmtDict['authorName'] = authorName;
        cmtDict['cmtTime'] = cmtTime;
        
        curPageCmtList.append(cmtDict);
        logging.debug("cmtDict=%s", cmtDict);
        logging.debug("--------single comment -------------");
        
        #special:
        #http://kenleung.blogbus.com/logs/219268309.html
        #contain reply comments:
        #<div class="reCmtBody"><div><span class="author">Kenleung</span>回复<span>huimiedy</span>说：</div><div class="content">：D</div><div class="time">2012-07-13 17:30:27</div></div>
        foundReCmt = eachLi.find(attrs={"class":"reCmtBody"});
        if(foundReCmt):
            reCmtDict = {
                'cmtBody'   : "",
                'authorUrl' : "",
                'authorName': "",
                'cmtTime'   : "",
                'isReplyCmt': True,
            };
            foundAuthor = foundReCmt.find(attrs={"class":"author"});
            #print "foundAuthor=",foundAuthor;
            authorName = foundAuthor.string;
            #print "authorName=",authorName;
            
            foundContent = foundReCmt.find(attrs={"class":"content"});
            #print "foundContent=",foundContent;
            #cmtBody = foundContent.string;
            cmtContents = foundContent.contents;
            cmtBody = crifanLib.soupContentsToUnicode(cmtContents);
            #print "cmtBody=",cmtBody;
            
            foundTime = foundReCmt.find(attrs={"class":"time"});
            #print "foundTime=",foundTime;
            cmtTime = foundTime.string;
            #print "cmtTime=",cmtTime;
            
            reCmtDict['cmtBody'] = cmtBody;
            reCmtDict['authorUrl'] = authorUrl;
            reCmtDict['authorName'] = authorName;
            reCmtDict['cmtTime'] = cmtTime;
            curPageCmtList.append(reCmtDict);
            
            logging.debug("reCmtDict=%s", reCmtDict);
            logging.debug("--------single reply comment -------------");

    return curPageCmtList;

#------------------------------------------------------------------------------
# fetch and parse comments 
# return the parsed dict value
def fetchAndParseComments(url, html):
    parsedCommentsList = [];
    
    try :
        #logging.debug("fetchAndParseComments_html=\n%s", html);
        allCmtList = [];
        
        #http://littlebasin.blogbus.com/logs/171413104.html
        #<div class="cmtPagenav">评论分页：共2页   <span>1</span> <a href="/logs/171413104_c2.html#cmt">2</a> <a href="/logs/171413104_c2.html#cmt" title="下一页">下一页</a> <a href="/logs/171413104_c2.html#cmt" title="最后一页">最后一页</a></div>
        
        # tmp not support comments in
        #http://ajunecat.blogbus.com/logs/190104111.html
        # for it is extremely bad html structure, very hard to parse it !!!
        
        soup = getSoupFromUrl(url);
        foundCmtpagenav = soup.find(attrs={"class":"cmtPagenav"});
        logging.debug("foundCmtpagenav=%s", foundCmtpagenav);
        if(foundCmtpagenav):
            #comments more than one page
            #print "foundCmtpagenav.contents[0]=",foundCmtpagenav.contents[0];
            #print "foundCmtpagenav.string=",foundCmtpagenav.string;
            commentPageStr = foundCmtpagenav.contents[0];
            logging.debug("commentPageStr=%s", commentPageStr);
            foundTotalCmtPage = re.search(u"评论分页：共(?P<totalCmtPageNum>\d+)页", commentPageStr);
            logging.debug("foundTotalCmtPage=%s", foundTotalCmtPage);
            #here foundTotalCmtPage must be non-empty
            totalCmtPageNum = foundTotalCmtPage.group("totalCmtPageNum");
            logging.debug("totalCmtPageNum=%s", totalCmtPageNum);
            totalCmtPageNum = int(totalCmtPageNum);
            #print "totalCmtPageNum=",totalCmtPageNum;
            
            postId = extractPostId(url);
            logging.debug("postId=%s", postId);
            rangeList = range(totalCmtPageNum + 1);
            #print "rangeList=",rangeList;
            rangeList.pop(0);
            #print "rangeList=",rangeList;
            for pageNum in rangeList:
                getCmtUrl = genGetCmtUrl(postId, pageNum);
                logging.debug("[%d] getCmtUrl=%s", pageNum, getCmtUrl);
                respHtml = crifanLib.getUrlRespHtml(getCmtUrl);
                curPageCmtList = extractCmtDictList(getCmtUrl, respHtml);
                logging.debug("current page parsed comments= %d", len(curPageCmtList));
                allCmtList.extend(curPageCmtList);
        else:
            curPageCmtList = extractCmtDictList(url, html);
            logging.debug("comments no more than page, comments num=%d", len(curPageCmtList));
            allCmtList.extend(curPageCmtList);
            
        parseAllCommentsList(allCmtList, parsedCommentsList);
        logging.debug("total parsed comments= %d", len(parsedCommentsList));
    except :
        logging.debug("Error while fetch and parse comment for %s", url);

    return parsedCommentsList;

#------------------------------------------------------------------------------
# download file
def downloadFile(curPostUrl, picInfoDict, dstPicFile) :
    isDownOK = False;
    
    curPicUrl = picInfoDict['picUrl'];
    logging.debug("current file to download=%s", curPicUrl);

    if(picInfoDict['isSelfBlog']):
        try :
            if curPicUrl :
                # if url is invalid, then add timeout can avoid dead
                # download blogbus pic, here specially MUST use referer, otherwise invalid access
                maxTryNum = 3;
                for tries in range(maxTryNum) :
                    try :
                        respHtml = crifanLib.getUrlRespHtml(curPicUrl, useGzip=False, headerDict={"Referer":curPostUrl}, timeout=gConst['defaultTimeout']);
                        logging.debug("get pic url=%s OK", curPicUrl);
                        break # successfully, so break now
                    except :
                        if tries < (maxTryNum - 1) :
                            logging.warning("Fetch url %s fail, do %d retry", curPicUrl, (tries + 1));
                            continue;
                        else : # last try also failed, so exit
                            logging.error("Has tried %d times to fetch page: %s, all failed!", maxTryNum, curPicUrl);
                
                isDownOK = crifanLib.saveBinDataToFile(respHtml, dstPicFile);
            else :
                logging.debug("Input download file url is NULL");
        except urllib.ContentTooShortError(msg) :
            isDownOK = False;
        except :
            isDownOK = False;
    else:
        isDownOK = crifanLib.downloadFile(curPicUrl, dstPicFile);

    logging.debug("download file is %s", isDownOK);
    
    return isDownOK;

#------------------------------------------------------------------------------
#check file validation
def isFileValid(picInfoDict):
    curUrl = picInfoDict['picUrl'];
    if(picInfoDict['isSelfBlog']):
        # here use normal urllib2.urlopen not work, so just assume always blogbus pic is valid
        (picIsValid, errReason) = (True, "");
    else:
        (picIsValid, errReason) = crifanLib.isFileValid(curUrl);
    return (picIsValid, errReason);
 
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
    fd5 = picInfoDict['fields']['fd5'];
    fd6 = picInfoDict['fields']['fd6'];

    if ( ((fd2=='blogbus') and (fd3=='com')) or 
        ((fd2=='blogbuscdn') and (fd3=='com')) ):
        isSelfPic = True;
    else :
        isSelfPic = False;

    logging.debug("isSelfBlogPic: %s", isSelfPic);

    return isSelfPic;
    
#------------------------------------------------------------------------------
def getProcessPhotoCfg():    
    # possible own site pic link:
    # type1:
    # http://uk916.blogbus.com/logs/163734653.html contain:
    # http://filer.blogbus.com/11479332/11479332_1317133443h.jpg
    # html ->
    #<p style="text-align: center;"><img src="http://filer.blogbus.com/11479332/11479332_1317133443h.jpg" border="0" alt="" /></p>
    
    #type2:
    # http://pindao.blogbus.com/sejie/2011092618160.html contain:
    # http://img1.blogbuscdn.com/pindao/2011/9/26/b5966b1ef195d0c69ee80b9594c4d254.jpg
    # it is same with:
    # http://filer.blogbus.com/11479332/11479332_13169658908.jpg
    # in http://uk916.blogbus.com/logs/163484363.html    
    
    # possible othersite pic url:

    #http://kdinsky.blogbus.com/logs/132011462.html
    # can not find out:
    #http://i.6.cn/cvbnm/39/57/92/1391f36df077a3ead3158ad21892f110.jpg
    #http://i.6.cn/cvbnm/bd/e5/fc/1bf6f85b75cd84cb46d6e82d21d49837.jpg
    #http://i.6.cn/cvbnm/3e/d9/b8/b45c4f0c6bc614920de5181b76cd2b64.jpg
    #html:
    #<img src="http://i.6.cn/cvbnm/39/57/92/1391f36df077a3ead3158ad21892f110.jpg" alt="" />

    processPicCfgDict = {
        'allPicUrlPat'      : None,
        'singlePicUrlPat'   : None,
        'getFoundPicInfo'   : None,
        'isSelfBlogPic'     : isSelfBlogPic,
        'genNewOtherPicName': None,
        'isFileValid'       : isFileValid,
        'downloadFile'      : downloadFile,
    };
    
    return processPicCfgDict;

#------------------------------------------------------------------------------
# extract blog title and description
def extractBlogTitAndDesc(blogEntryUrl) :
    (blogTitle, blogDescription) = ("", "");
    logging.debug("input blogEntryUrl=%s", blogEntryUrl);
    
    try:
        logging.debug("blogEntryUrl=%s", blogEntryUrl);
        respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
        #logging.debug("extractBlogTitAndDesc_respHtml=\n%s", respHtml);
        
        soup = htmlToSoup(respHtml);
        #<h1 class="blogName"><a href="http://littlebasin.blogbus.com" title="http://littlebasin.blogbus.com">盆景</a></h1>
        foundBlogname = soup.find(attrs={"class":"blogName"});
        if(foundBlogname):
            blogTitle = foundBlogname.a.string;
            logging.debug("blogTitle=%s", blogTitle);
        
        #<div class="description">盆虽小，却很能装……</div>
        foundDesc = soup.find(attrs={"class":"description"});
        if(foundDesc):
            blogDescription = foundDesc.string;
            logging.debug("blogDescription=%s", blogDescription);
    except:
        (blogTitle, blogDescription) = ("", "");
    
    return (blogTitle, blogDescription);

#------------------------------------------------------------------------------
# parse datetime string into (local=GMT+8) datetime value
def parseDatetimeStrToLocalTime(datetimeStr):
    # possible date format:
    # (1) 2011-07-03 15:04:00
    #print "datetimeStr=",datetimeStr;
    parsedLocalTime = datetime.strptime(datetimeStr, '%Y-%m-%d %H:%M:%S');
    logging.debug("parse %s to %s", datetimeStr, parsedLocalTime);
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
if __name__=="BlogSohu":
    print "Imported: %s,\t%s"%( __name__, __VERSION__);