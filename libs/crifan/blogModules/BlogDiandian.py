#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for Diandian qing Blog.

[TODO]

[History]
[v2.4]
1. fix post content and next perma link for http://remixmusic.diandian.com
2. fix title for post title:
BlogsToWordpress.py -f http://remixmusic.diandian.com/?p=669 -l 1
BlogsToWordpress.py -f http://remixmusic.diandian.com/?p=316 -l 1
BlogsToWordpress.py -f http://remixmusic.diandian.com/?p=18117 -l 1
BlogsToWordpress.py -f http://remixmusic.diandian.com/post/2013-05-13/40051897352 -l 1
3. fix post content for:
BlogsToWordpress.py -f http://remixmusic.diandian.com/post/2013-05-13/40051897352 -l 1

[v2.0]
1. fix bug now support http://googleyixia.com/ to find first perma link, next perma link, extract title, tags

"""

import os;
import re;
import sys;
import time;
#import math;
#import urllib;
#import urllib2;
from datetime import datetime,timedelta;
from BeautifulSoup import BeautifulSoup,Tag,CData;
import logging;
import crifanLib;
#import cookielib;
#from xml.sax import saxutils;
import json; # New in version 2.6.
#import random;

#--------------------------------const values-----------------------------------
__VERSION__ = "v2.4";

gConst = {
    'spaceDomain'   : 'http://www.diandian.com',

    'htmlCharset'   : "UTF-8",
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',   # hanhan--
    'blogEntryUrl'  : '',   # http://hanhan--.diandian.com
    'blogTitle'     : "",   # 韩韩==
    'blogDescription':"",   # 我的生活还要继续
                                #好不容易
    'cj'            : None, # cookiejar, to store cookies for login mode
    
    'soupDict' : {},   # cache the soup for url's html -> url : soup
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
    soup = BeautifulSoup(html, fromEncoding=gConst['htmlCharset']);
    
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
# extract date(year,month,day) from perma link
# 2011-09-07 from http://matchachiharu.diandian.com/post/2011-09-07/4803218
#              or http://www.zoushijie.com/post/2012-09-22/40038845472
def extractDateStrFromPermaLink(url):
    dateStr = "";
    #http://matchachiharu.diandian.com/post/2011-09-07/4803218
    #http://www.zoushijie.com/post/2012-09-22/40038845472
    foundDateStr = re.search(r"http://\w+\.\w+\.com/post/(?P<dateStr>\d{4}-\d{2}-\d{2})/\d+/?", url);
    if(foundDateStr) :
        dateStr = foundDateStr.group("dateStr");
        logging.debug("extracted dateStr=%s from perma link=%s", dateStr, url);
    else:
        #http://www.zoushijie.com/post/2012-09-28/40039054394
        #prev post is: http://www.zoushijie.com/0000/0015
        #so not contain date
        #use fake date here
        dateStr = datetime.now().strftime("%Y-%m-%d");
        logging.debug("generated fake current date string is %s", dateStr);

    return dateStr;

################################################################################
# Implemented Common Functions 
################################################################################

#------------------------------------------------------------------------------
# extract blog user name:
# (1) stephenwei from: 
# http://stephenwei.diandian.com
# http://stephenwei.diandian.com/
# http://hanhan--.diandian.com
# (2) stephenwei from permanent link:
# http://stephenwei.diandian.com/post/2012-05-15/17622180
# http://stephenwei.diandian.com/post/2012-05-15/17622180/
# (3) zoushijie from:
#http://www.zoushijie.com
#http://blog.nuandao.com
#http://nosta1gie.com
#http://www.sankin77.com
#http://www.zoushijie.com/post/2012-09-22/40038845472
def extractBlogUser(inputUrl):

    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
    logging.info("Extracting blog user from url=%s", inputUrl);
    
    blogId = "";
    
    try :
        # type1, main url:
        # http://stephenwei.diandian.com
        # http://stephenwei.diandian.com/
        foundMainUrl = re.search("http://(?P<blogUser>[\w-]+)\.diandian\.com/?", inputUrl);
        logging.debug("foundMainUrl=%s", foundMainUrl);
        if(foundMainUrl) :
            extractedBlogUser = foundMainUrl.group("blogUser");
            generatedBlogEntryUrl = "http://" + extractedBlogUser + ".diandian.com";
            extractOk = True;
        
        # type2, perma link:
        # http://stephenwei.diandian.com/post/2012-05-15/17622180
        # http://stephenwei.diandian.com/post/2012-05-15/17622180/
        if(not extractOk):
            foundPermalink = re.search("http://(?P<blogUser>[\w-]+)\.diandian\.com/post/[\d-]+/\d+/?", inputUrl);
            logging.debug("foundPermalink=%s", foundPermalink);
            if(foundPermalink) :
                extractedBlogUser = foundPermalink.group("blogUser");
                generatedBlogEntryUrl = "http://" + extractedBlogUser + ".diandian.com";
                extractOk = True;
        
        # type3, self domain:
        #http://www.zoushijie.com
        #http://blog.nuandao.com
        #http://nosta1gie.com
        #http://www.sankin77.com
        #http://www.zoushijie.com/post/2012-09-22/40038845472
        #http://googleyixia.com/
        if(not extractOk):
            #foundDomain = re.search("http://([(www)|(blog)]\.)?(?P<domainName>\w+)\.com(/post/\d{4}-\d{2}-\d{2}/\d+)?/?", inputUrl);
            #foundDomain = re.search("(?P<blogEntryUrl>http://([(www)|(blog)]\.)?(?P<domainName>\w+)\.com)(/post/\d{4}-\d{2}-\d{2}/\d+)?/?", inputUrl);
            foundDomain = re.search("(?P<blogEntryUrl>http://((www\.)|(blog\.))?(?P<domainName>[\w-]+)\.com)(/post/\d{4}-\d{2}-\d{2}/\d+)?/?", inputUrl);
            #foundDomain = re.search("(?P<blogEntryUrl>http://([(www\.)|(blog\.)]{1})?(?P<domainName>\w+)\.com)(/post/\d{4}-\d{2}-\d{2}/\d+)?/?", inputUrl);
            logging.debug("foundDomain=%s", foundDomain);
            if(foundDomain) :
                extractedBlogUser = foundDomain.group("domainName");
                #generatedBlogEntryUrl = "http://www." + extractedBlogUser + ".com";
                generatedBlogEntryUrl = foundDomain.group("blogEntryUrl");
                extractOk = True;
    except :
        (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
        
    if (extractOk) :
        gVal['blogUser']    = extractedBlogUser;
        gVal['blogEntryUrl']= generatedBlogEntryUrl;
    
    logging.debug("extractOk=%s, gVal['blogUser']=%s, gVal['blogEntryUrl']=%s", extractOk, gVal['blogUser'], gVal['blogEntryUrl']);

    return (extractOk, extractedBlogUser, generatedBlogEntryUrl);

#------------------------------------------------------------------------------
# find the first permanent link = url of the earliset published blog item
def find1stPermalink():
    (isFound, retInfo) = (False, "Unknown error!");
    
    try:
        #http://matchachiharu.diandian.com/archive
        archiveUrl = gVal['blogEntryUrl'] + "/archive";
        logging.debug("archiveUrl=%s", archiveUrl);
        archiveUrlRespHtml = crifanLib.getUrlRespHtml(archiveUrl);
        logging.debug("archiveUrlRespHtml=%s", archiveUrlRespHtml);

        # <div class="mega-timeline-selector" id="J_MegaTimeLineSelector"><ul class="mega-timeline-list selected">
        # <li>
        # <a id="J_Year_2012" class="year">2012年</a>
        # </li><li class="month-li">
        # <a data-yearmonth="2012年 十月" data-month="201210" data-postcount="4" id="J_Month_201210"
        # class="month active">十月</a>
        # </li><li class="month-li">
        # ......
        # </ul><ul class="mega-timeline-list ">
        # <li>
        # <a id="J_Year_2011" class="year">2011年</a>
        # </li>
        # ......
        # <li class="month-li">
        # <a data-yearmonth="2011年 十月" data-month="201110" data-postcount="7" id="J_Month_201110"
        # class="month ">十月</a>
        # </li><li class="month-li">
        # <a data-yearmonth="2011年 九月" data-month="201109" data-postcount="14" id="J_Month_201109"
        # class="month ">九月</a>
        # </li></ul></div>
        soup = htmlToSoup(archiveUrlRespHtml);
        foundAllMonthLi = soup.findAll(attrs={"class":"month-li"});
        logging.debug("foundAllMonthLi=%s", foundAllMonthLi);
        if(foundAllMonthLi):
            lastMonthLi = foundAllMonthLi[-1];
            logging.debug("lastMonthLi=%s", lastMonthLi);
            liA = lastMonthLi.a;
            logging.debug("liA=%s", liA);
            liADatamonth = liA['data-month'];
            logging.debug("liADatamonth=%s", liADatamonth);
            
            #for debug
            #if input url is http://googleyixia.diandian.com
            #current archiveUrl will be http://googleyixia.diandian.com/archive/
            #then following lastMonthRespHtml can not get the last month(200806) resp html, but only get current latest month(201306) resp html
            #archiveUrl = "http://googleyixia.com/archive/";
            # headerDict = {
                # 'Referer'           : archiveUrl,
                # 'X-Requested-With'  : "XMLHttpRequest",
                # #Content-Type	application/x-www-form-urlencoded; charset=UTF-8
            # };
            postDict = {
                'lite'  : "1",
                'month' : liADatamonth,
            };
            logging.debug("archiveUrl=%s", archiveUrl);
            #lastMonthRespHtml = crifanLib.getUrlRespHtml(archiveUrl, postDict=postDict, headerDict=headerDict);
            lastMonthRespHtml = crifanLib.getUrlRespHtml(archiveUrl, postDict=postDict);
            logging.debug("lastMonthRespHtml=%s", lastMonthRespHtml);
            
            # <div class="post-li">
            # <div class="post photo" id="J_Post_1f2c0750-d938-11e0-93e5-782bcb383994"   data-postcontentid="4828285">
            # <div class="post-inner">
            # <div class="post-content">
            # <img src="http://m3.img.libdd.com/farm2/158/A959BE1F55FA828C0A5C1B65F636619E_250_250.jpg" width="125" height="125">
            # </div></div>
            # <a class="post-meta" target="_blank" href="http://matchachiharu.diandian.com/post/2011-09-07/4828285">
            # <div class="meta-date">九月 07日</div>
            # <div class="meta-notes">3 热度</div>
            # </a>
            # </div>
            # </div><div class="post-li">
            # <div class="post photo" id="J_Post_15225820-d8fe-11e0-ba42-782bcb32ff27"   data-postcontentid="4803218">
            # <div class="post-inner">
            # <div class="post-content">
            # <img src="http://m1.img.libdd.com/farm2/126/285A150AAFC89F6A0B7EC866C3B89E7E_250_250.jpg" width="125" height="125">
            # </div></div>
            # <a class="post-meta" target="_blank" href="http://matchachiharu.diandian.com/post/2011-09-07/4803218">
            # <div class="meta-date">九月 07日</div>
            # <div class="meta-notes">11 热度</div>
            # </a>
            # </div>
            # </div>
            lastMonthSoup = htmlToSoup(lastMonthRespHtml);
            foundAllPostMeta = lastMonthSoup.findAll(attrs={"class":"post-meta"});
            logging.debug("foundAllPostMeta=%s", foundAllPostMeta);
            if(foundAllPostMeta):
                lastPostMeta = foundAllPostMeta[-1];
                logging.debug("lastPostMeta=%s", lastPostMeta);
                lastHref = lastPostMeta['href'];
                logging.debug("lastHref=%s", lastHref);
                if(lastHref):
                    retInfo = lastHref;
                    isFound = True;
    except:
        (isFound, retInfo) = (False, "Unknown error!");

    return (isFound, retInfo);

#------------------------------------------------------------------------------
# extract blog title and description
def extractBlogTitAndDesc(blogEntryUrl) :
    (blogTitle, blogDescription) = ("", "");

    try:
        foundTitDesc = False;
        logging.debug("Now extract blog title and description from blogEntryUrl=%s", blogEntryUrl);
        
        respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
        #logging.debug("blogEntryUrl=%s return html=\n%s", blogEntryUrl, respHtml);
        soup = htmlToSoup(respHtml);
        
        #------seems all type of blog has title and meta content, so use them to extract title and desc
        
        #http://blog.nuandao.com/
        #<title>暖岛</title>
        
        #http://matchachiharu.diandian.com/
        #<title>千阳</title>
        
        #http://www.zoushijie.com/
        #<title>走世界</title>
        
        foundMetaTitle = soup.find(name="title");
        logging.debug("foundMetaTitle=%s", foundMetaTitle);
        if(foundMetaTitle):
            metaTitleStr = foundMetaTitle.string;
            logging.debug("metaTitleStr=%s", metaTitleStr);
            if(metaTitleStr):
                blogTitle = metaTitleStr;
                
                #http://blog.nuandao.com/
                # <meta name="description" content="暖岛的一切都与设计有关。
                 # 我们关注标新立异的设计产品，
                 #...
                # 小站：http://site.douban.com/122843/" />
                
                #http://matchachiharu.diandian.com/
                # <meta name="description" content="我想要找个窝，

                # 它会是我的城，

                # 应该是一座有记忆的城。" />
                
                #http://www.zoushijie.com/
                #<meta name="description" content="世界风景名胜大搜集，陪你一起潇洒走世界！QQ:859102" />
        
                foundMetaDesc = soup.find(name="meta", attrs={"name":"description"});
                logging.debug("foundMetaDesc=%s", foundMetaDesc);
                if(foundMetaDesc):
                    metaContent = foundMetaDesc['content'];
                    logging.debug("metaContent=%s", metaContent);
                    if(metaContent):
                        blogDescription = metaContent;
                        foundTitDesc = True;

        #------so not use following complex methods 

        # #----------------------------------------------------------------------
        # # <div class="overview" style="left:0;top:0;">
            
            # # <h1><a href="http://matchachiharu.diandian.com">千阳</a></h1>
            # # <p class="blog-desc">我想要找个窝，<br /><br />它会是我的城，<br /><br />应该是一座有记忆的城。</p>

        # foundOverview = soup.find(attrs={"class":"overview"});
        # logging.info("foundOverview=%s", foundOverview);
        # if(foundOverview):
            # h1 = foundOverview.h1;
            # h1a = h1.a;
            # logging.info("h1a=%s", h1a);
            # h1aStr = h1a.string;
            # logging.info("h1aStr=%s", h1aStr);
            # blogTitle = h1aStr;
            # logging.info("blogTitle=%s", blogTitle);
            
            # foundBlogdesc = foundOverview.find(attrs={"class":"blog-desc"});
            # logging.info("foundBlogdesc=%s", foundBlogdesc);
            # blogDescription = crifanLib.soupContentsToUnicode(foundBlogdesc.contents);
            # logging.info("blogDescription=%s", blogDescription);
            # foundTitDesc = True;
        
        # if(not foundTitDesc):
            # #http://stephenwei.diandian.com/
            # # <div class="info">
            # # <h1 class="title">
            # # <a href="/">Stephen</a>
            # # </h1>
            # # <p id="description">Movie Fan</p>
            # # </div>
            
            # foundH1Title = soup.find(name="h1", attrs={"class":"title"});
            # logging.info("foundH1Title=%s", foundH1Title);
            # if(foundH1Title):
                # h1TitleA = foundH1Title.a;
                # logging.info("h1TitleA=%s", h1TitleA);
                # if(h1TitleA):
                    # aStr = h1TitleA.string;
                    # logging.info("aStr=%s", aStr);
                    # blogTitle = aStr;
                    
                    # foundIdDesc = soup.find(name="p", attrs={"id":"description"});
                    # logging.info("foundIdDesc=%s", foundIdDesc);
                    # if(foundIdDesc):
                        # descStr = foundIdDesc.string;
                        # logging.info("descStr=%s", descStr);
                        # blogDescription = descStr;
                        # foundTitDesc = True;
        
        # if(not foundTitDesc):
            # #http://www.zoushijie.com/
            # # <div class="header_top" id="top"> <a href="http://www.zoushijie.com">走世界

            # # </a></div>
            # foundHeaderTop = soup.find(name="div", attrs={"class":"header_top", "id":"top"});
            # logging.info("foundHeaderTop=%s", foundHeaderTop);
            # if(foundHeaderTop):
                # headerTopA = foundHeaderTop.a;
                # logging.info("headerTopA=%s", headerTopA);
                # if(headerTopA):
                    # headerTopAStr = headerTopA.string;
                    # logging.info("headerTopAStr=%s", headerTopAStr);
                    # blogTitle = headerTopAStr;
                    # blogDescription = "";
                    # foundTitDesc = True;
        
        # if(not foundTitDesc):
            # #http://blog.nuandao.com/
            # # <div id="header">       
                # # <div id="logo">
                    # # <a href="http://www.nuandao.com"><img ... src="http://nuandao.com/Public/images/web/nuandao-logo.png" /></a>        
                # # </div>  
            # foundIdLogo = soup.find(name="div", attrs={"id":"logo"});
            # logging.info("foundIdLogo=%s", foundIdLogo);
            # if(foundIdLogo):
                # #this kind of blog no title and desc
                # #extract them from header
                
                # #titile:
                # #<title>暖岛</title>
                # foundMetaTitle = soup.find(name="title");
                # logging.info("foundMetaTitle=%s", foundMetaTitle);
                # if(foundMetaTitle):
                    # metaTitleStr = foundMetaTitle.string;
                    # logging.info("metaTitleStr=%s", metaTitleStr);
                    # if(metaTitleStr):
                        # blogTitle = metaTitleStr;
                        
                        # #desc
                        # # <meta name="description" content="暖岛的一切都与设计有关。
                         # # 我们关注标新立异的设计产品，
                         # #...
                        # # 小站：http://site.douban.com/122843/" />
                        # foundMetaDesc = foundHeaderTop = soup.find(name="meta", attrs={"name":"description"});
                        # logging.info("foundMetaDesc=%s", foundMetaDesc);
                        # if(foundMetaDesc):
                            # metaContent = foundMetaDesc['content'];
                            # logging.info("metaContent=%s", metaContent);
                            # if(metaContent):
                                # blogDescription = metaContent;
                                # foundTitDesc = True;
                    
        if(foundTitDesc):
            gVal['blogTitle']       = blogTitle;
            gVal['blogDescription'] = blogDescription;
    except:
        (blogTitle, blogDescription) = ("", "");

    return (blogTitle, blogDescription);

#------------------------------------------------------------------------------
# extract title
def extractTitle(url, html):
    (needOmit, titleUni) = (False, "");

    try :
        logging.debug("in extractTitle, url=%s", url);

        soup = getSoupFromUrl(url);
        found = False;
        
        #Note: tmp not support http://nosta1gie.com -> http://nosta1gie.com/post/2012-04-30/18466821
        
        #http://matchachiharu.diandian.com/post/2011-09-07/4803218
        # <div class="post photo">
            # <h2 class="title"><a href="http://matchachiharu.diandian.com/post/2011-09-07/4803218">我的城</a></h2>
        foundH2ClassTitle = soup.find(name="h2", attrs={"class":"title"});
        logging.debug("foundH2ClassTitle=%s", foundH2ClassTitle);
        if(foundH2ClassTitle):
            titleA = foundH2ClassTitle.a;
            logging.debug("titleA=%s", titleA);
            if(titleA):
                titleAStr = titleA.string;
                logging.debug("titleAStr=%s", titleAStr);
                titleUni = titleAStr;
                found = True;
            else:
                #http://shuizhixiu.diandian.com/post/2012-10-30/40041936379
                #<h2 class="title">我心似海洋</h2>
        
                #http://hanhan--.diandian.com/post/2012-05-07/17227064
                # <div class="main">
                    # <div class="content">
                        # <!-- 内容头部区域 -->
                        
                            # <h2 class="title">这一场空梦</h2>
                
                titleStr = foundH2ClassTitle.string;
                logging.debug("titleStr=%s", titleStr);
                if(titleStr):
                    titleUni = titleStr;
                    found = True;
        
        if(not found):
            #http://blog.nuandao.com/post/2011-05-03/670526
            #<h1 class="title" id="returntitle"><span><a href="http://blog.nuandao.net/">回到博客</a></span><a href="http://blog.nuandao.com/post/2011-05-03/670526">欢迎你来暖岛！</a></h1>
            foundH1ClassTitleId = soup.find(name="h1", attrs={"class":"title", "id":"returntitle"});
            logging.debug("foundH1ClassTitleId=%s", foundH1ClassTitleId);
            if(foundH1ClassTitleId):
                contents = foundH1ClassTitleId.contents;
                logging.debug("contents=%s", contents);
                if(foundH1ClassTitleId):
                    h1ClassTitleLastA = foundH1ClassTitleId.contents[1];
                    logging.debug("h1ClassTitleLastA=%s", h1ClassTitleLastA);
                    if(h1ClassTitleLastA):
                        returntitleAStr = h1ClassTitleLastA.string;
                        logging.debug("returntitleAStr=%s", returntitleAStr);
                        if(returntitleAStr):
                            titleUni = returntitleAStr;
                            found = True;
        
        if(not found):
            #http://googleyixia.com/node/727
            # <div class="content"><div class="entry">
                # <h1 class="title">“Google一下”成立</h1>
            foundDivClassContent = soup.find(name="div", attrs={"class":"content"});
            logging.debug("foundDivClassContent=%s", foundDivClassContent);
            if(foundDivClassContent):
                foundDivClassEntry = foundDivClassContent.find(name="div", attrs={"class":"entry"});
                logging.debug("foundDivClassEntry=%s", foundDivClassEntry);
                if(foundDivClassEntry):
                    foundH1ClassTitle = foundDivClassEntry.find(name="h1", attrs={"class":"title"});
                    logging.debug("foundH1ClassTitle=%s", foundH1ClassTitle);
                    if(foundH1ClassTitle):
                        titleUni = unicode(foundH1ClassTitle.string);
                        found = True;

        if(not found):
            #http://remixmusic.diandian.com/?p=669
            # <article class="hentry writing">
                # <header>
                    # <a class="entry-hide open" href="#" title="Close this Card"></a>
                    # <h1 class="entry-title">
                           # 文字
                    # </h1>
            
            #http://remixmusic.diandian.com/post/2013-05-13/40051897352
            # <article class="hentry link">
                # <header>
                    # <a class="entry-hide open" href="#" title="Close this Card"></a>
                    # <h1 class="entry-title">
                           # <a href="http://www.junodjs.com">http://www.junodjs.com</a>
                        # </h1>
                # </header>
            #foundArticleHentry = soup.find(name="article", attrs={"class":re.compile("hentry\s+(link|writing)")});
            foundArticleHentry = soup.find(name="article", attrs={"class":re.compile("hentry\s+\w+")});
            logging.debug("foundArticleHentry=%s", foundArticleHentry);
            if(foundArticleHentry):
                foundHeader = foundArticleHentry.find(name="header");
                logging.debug("foundHeader=%s", foundHeader);
                if(foundHeader):
                    foundH1ClassEntryTitle = foundHeader.find(name="h1", attrs={"class":"entry-title"});
                    logging.debug("foundH1ClassEntryTitle=%s", foundH1ClassEntryTitle);
                    if(foundH1ClassEntryTitle):
                        foundAHref = foundH1ClassEntryTitle.find(name="a", attrs={"href":True});
                        logging.debug("foundAHref=%s", foundAHref);
                        if(foundAHref):
                            titleUni = unicode(foundAHref.string);
                        else:
                            titleUni = unicode(foundH1ClassEntryTitle.string);
                        
                        if(titleUni):
                            titleUni = titleUni.strip();
                        found = True;

        if(not found):
            # here just use html title as post title, such as:
            #http://www.zoushijie.com/post/2012-09-22/40038845472
            #<title>紫禁城里的故事_走世界</title>
            foundMetaTitle = soup.find(name="title");
            logging.debug("foundMetaTitle=%s", foundMetaTitle);
            if(foundMetaTitle):
                metaTitleStr = foundMetaTitle.string;
                logging.debug("metaTitleStr=%s", metaTitleStr);
                if(metaTitleStr):
                    #check whether is xxx_title, if yes, remove _title
                    if(gVal['blogTitle']):
                        foundTitleSuf = re.search(".+?_"+gVal['blogTitle'], metaTitleStr);
                        logging.debug("foundTitleSuf=%s", foundTitleSuf);
                        if(foundTitleSuf):
                            metaTitleStrNotTitile = re.sub("(?P<origTitle>.+?)_"+gVal['blogTitle'], "\g<origTitle>", metaTitleStr);
                            logging.debug("After remove title suffix, origTitle=%s", metaTitleStrNotTitile);
                            metaTitleStr = metaTitleStrNotTitile;
                        
                    titleUni = metaTitleStr;
        
        # if(not found):
            # #http://matchachiharu.diandian.com/post/2012-07-02/40029798415
            # #http://stephenwei.diandian.com/post/2012-05-15/17622180
            # #http://www.zoushijie.com/post/2012-09-22/40039678723

            # defaultTitle = u'NoTitle';
            # logging.info("Can not find title, so set to %s", defaultTitle);
            # titleUni = defaultTitle;
        
        logging.debug("titleUni=%s", titleUni);
    except :
        logging.warning("Error while extract title from %s", url);
        logging.debug("Fail to extract tiltle from url=%s, html=\n%s", url, html);
        (needOmit, titleUni) = (False, "");
        
    return (needOmit, titleUni);

#------------------------------------------------------------------------------
# find next permanent link of current post
def findNextPermaLink(url, html) :
    nextLinkStr = '';
    nextPostTitle = "";

    try :
        foundNext = False;
        soup = getSoupFromUrl(url);
        
        if(not foundNext):
            #http://matchachiharu.diandian.com/post/2011-09-07/4803218
            # <div class="page clear">
                # <a href="http://matchachiharu.diandian.com/post/2011-09-07/4828285" class="prev">上一篇</a>
                
            # </div>
            foundPrev = soup.find(name="a", attrs={"class":"prev"});
            logging.debug("foundPrev=%s", foundPrev);
            if(foundPrev):
                prevHref = foundPrev['href'];
                logging.debug("prevHref=%s", prevHref);
                if(prevHref):
                    nextLinkStr = prevHref;
                    foundNext = True;
        
        if(not foundNext):
            #http://www.zoushijie.com/post/2012-09-22/40038845472
                        # <a href="http://www.zoushijie.com/post/2012-09-25/40039034807" class="next_page">
                        
            # 上一篇</a>
                     # ...
                        # <a href="http://www.zoushijie.com/post/2012-09-22/40039124532" class="next_page">
                        
                         # 下一篇</a>
            #Note: both are 'next_page', here find the first one

            # but special one:
            #http://www.zoushijie.com/huoshanhu
                         # <a class="jump_page" href="http://www.zoushijie.com/random">随机文章</a>
                          # <!--循环输出页号-->
                        
            # <!--判断是否有下一页-->
                        
                            # <a href="http://www.zoushijie.com/post/2012-10-12/40040664173" class="next_page">
                            
                             # 下一篇</a>
            # so use follow code:
            # note: here code is UTF-8 and html is UTF-8
            foundNextPage = soup.find(name="a", attrs={"class":"next_page"});
            logging.debug("foundNextPage=%s", foundNextPage);
            if(foundNextPage):
                nextStr = foundNextPage.string;
                logging.debug("nextStr=%s", nextStr);
                if(nextStr):
                    foundShangYiPian = re.search(u"上一篇", nextStr);
                    logging.debug("foundShangYiPian=%s", foundShangYiPian);
                    if(foundShangYiPian):
                        nextHref = foundNextPage['href'];
                        logging.debug("nextHref=%s", nextHref);
                        if(nextHref):
                            nextLinkStr = nextHref;
                            foundNext = True;
        
        if(not foundNext):
            #http://hanhan--.diandian.com/post/2012-05-06/17805652
            # <a href="http://hanhan--.diandian.com/post/2012-05-06/18328800" class="pagination-prev">Prev</a>
            
            #http://hanhan--.diandian.com/post/2012-05-06/18328800
            # <a href="http://hanhan--.diandian.com/post/2012-05-06/17805652" class="pagination-next">Next</a>
            # <a href="http://hanhan--.diandian.com/post/2012-05-06/17041187" class="pagination-prev">Prev</a>
            foundPaginationPrev = soup.find(name="a", attrs={"class":"pagination-prev"});
            logging.debug("foundPaginationPrev=%s", foundPaginationPrev);
            if(foundPaginationPrev):
                paginationPrevHref = foundPaginationPrev['href'];
                logging.debug("paginationPrevHref=%s", paginationPrevHref);
                if(paginationPrevHref):
                    nextLinkStr = paginationPrevHref;
                    foundNext = True;
        
        if(not foundNext):
            #http://stephenwei.diandian.com/post/2012-05-15/17622180
            #<a class="prevPost" href="http://stephenwei.diandian.com/post/2012-05-15/18856917">上一页</a>
            
            #http://stephenwei.diandian.com/post/2012-05-15/18856917
            # <a class="prevPost" href="http://stephenwei.diandian.com/post/2012-05-15/19857379">上一页</a>
            # <a class="nextPost" href="http://stephenwei.diandian.com/post/2012-05-15/17622180">下一页</a>
            foundPrevPost = soup.find(name="a", attrs={"class":"prevPost"});
            logging.debug("foundPrevPost=%s", foundPrevPost);
            if(foundPrevPost):
                prevPostHref = foundPrevPost['href'];
                logging.debug("prevPostHref=%s", prevPostHref);
                if(prevPostHref):
                    nextLinkStr = prevPostHref;
                    foundNext = True;
        
        if(not foundNext):
            #http://googleyixia.com/node/727
            #<a class="pagination-link prev" href="http://googleyixia.com/node/725">上一篇<span class="icon"></span></a>
            foundLinkPrev = soup.find(name="a", attrs={"class":"pagination-link prev"});
            logging.debug("foundLinkPrev=%s", foundLinkPrev);
            if(foundLinkPrev):
                linkPrevHref = foundLinkPrev['href'];
                logging.debug("linkPrevHref=%s", linkPrevHref);
                if(linkPrevHref):
                    nextLinkStr = linkPrevHref;
                    foundNext = True;
        
        if(not foundNext):
            #http://remixmusic.diandian.com/?p=15022
            # <div id="navigation">    
                # <header>
                    # <a class="entry-hide open" href="#" title="Close this Card"></a>
                    # <h1 class="entry-title">分页</h1>
                # </header>
                # <div class="entry-content">
                    # <a href="http://remixmusic.diandian.com/post/2011-04-14/40050272483">
            # ← 上一篇</a>&nbsp;&nbsp;
                # </div>
            # </div>
            foundDivIdNavigation = soup.find(name="div", attrs={"id":"navigation"});
            logging.debug("foundDivIdNavigation=%s", foundDivIdNavigation);
            if(foundDivIdNavigation):
                foundDivClassEntryContent = foundDivIdNavigation.find(name="div", attrs={"class":"entry-content"});
                logging.debug("foundDivClassEntryContent=%s", foundDivClassEntryContent);
                if(foundDivClassEntryContent):
                    foundAHref = foundDivClassEntryContent.find(name="a", attrs={"href":True});
                    logging.debug("foundAHref=%s", foundAHref);
                    if(foundAHref):
                        aHrefStr = foundAHref.string;
                        logging.debug("aHrefStr=%s", aHrefStr);
                        logging.debug("type(aHrefStr)=%s", type(aHrefStr));
                        aHrefStrUni = unicode(aHrefStr);
                        logging.debug("aHrefStrUni=%s", aHrefStrUni);
                        foundPrevPost = re.search(u"上一篇", aHrefStrUni);
                        logging.debug("foundPrevPost=%s", foundPrevPost);
                        if(foundPrevPost):
                            linkAHref = foundAHref['href'];
                            logging.debug("linkAHref=%s", linkAHref);
                            if(linkAHref):
                                nextLinkStr = linkAHref;
                                foundNext = True;

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
        #http://matchachiharu.diandian.com/post/2011-09-07/4803218
        #<div class="info">1年前 / <a href="http://matchachiharu.diandian.com/post/2011-09-07/4803218#notes">11℃ </a> / </div>
        # the "1年前" is not the exact datetime, so extract date from perma link
        datetimeStr = extractDateStrFromPermaLink(url);
        logging.debug("datetimeStr=%s", datetimeStr);
    except :
        logging.debug("Fail to extract datettime string from url=%s, html=\n%s", url, html);
        datetimeStr = "";

    return datetimeStr;

#------------------------------------------------------------------------------
# extract blog item content
def extractContent(url, html) :
    contentUni = '';
    try :
        foundContent = "";
        
        soup = getSoupFromUrl(url);
    
        #http://matchachiharu.diandian.com/post/2011-09-07/4803218
        # <div class="post photo">
            # <h2 class="title"><a href="http://matchachiharu.diandian.com/post/2011-09-07/4803218">我的城</a></h2>
        # ......
            # <div class="info">1年前 / <a href="http://matchachiharu.diandian.com/post/2011-09-07/4803218#notes">11℃ </a> / </div>
            # <div class="tags">标签：<a href="/?tag=%E5%A4%8F">夏</a> <a href="/?tag=%E4%B8%8A%E6%B5%B7">上海</a> <a href="/?tag=nex3">nex3</a> <a href="/?tag=%E6%91%84%E5%BD%B1">摄影</a> </div>
        # </div>
    
    
        #http://stephenwei.diandian.com/post/2012-05-15/17622180
        # <div id="post-05f7ac50-9e52-11e1-9538-782bcb383994" data-tags="" class="post photo isotope-item"><!--start post_type-->
        # <div class="postInner"><!--start postInner-->
        # ...
        # <a href="http://m2.img.libdd.com/farm3/83/B5E9A6B9F6F8A917D3D1F3EC2AA98753_1013_1500.JPEG">
        # <img src="http://m2.img.libdd.com/farm3/83/B5E9A6B9F6F8A917D3D1F3EC2AA98753_1013_1500.JPEG" /></a>
        # ...
        # <div class="photoSetLink"><a href="http://stephenwei.diandian.com/post/2012-05-15/18856917">相册</a></div>

        # <div class="caption rich-content"><p>奥兰多...2012<br /></p></div>
        # ...
        # <div class="seperator"></div>
        # <div class="meta">
        # ...
        # <div class="date">...</div><!--date-->
        # <div class="permaLink">...</div><!--permalink-->
        # <div class="tags">...</div>
        # </div><!--end meta-->
        # </div><!--end postInner-->
        # </div><!--end post_type-->
        
        
        #http://stephenwei.diandian.com/post/2012-05-15/17584313
        # <div class="postInner"><!--start postInner-->
        # <!--TEXT--------------------------->
        # <!--endif text-->
        # <!--LINK--------------------------->
        # <!--endif link-->
        # <!--AUDIO---------------------------->
        # <!--VIDEO---------------------->
        # <div class="videoPlayer">...</div>
        # <div class="videoWatch">...</div><!--videoWatch-->
        # <div class="caption rich-content">...</div><!--end caption-->
        # <!--PHOTOSET&PHOTO------------------------>
        # <div class="seperator"></div>
        # <div class="meta">...</div><!--end meta-->
        # </div><!--end postInner-->
        
        
        #http://www.zoushijie.com/post/2012-09-22/40038845472
            # <div class="inner ">
              
              # <!--判断为单张图片-->
              # ...
           # <div class="clear"></div>

        # </div>
        
        #http://hanhan--.diandian.com/post/2012-05-06/17805652
        #<div class="content-entry entry-photo rich-content">...</div>
        
        #http://hanhan--.diandian.com/post/2012-05-07/17227064
        #<div class="content-entry entry-text rich-content">...</div>
        
        
        #http://matchachiharu.diandian.com/post/2011-09-12/4979599
        # <div class="post text">
              # <p>...不知怎么的，不断的浮现一些似曾相识的画面...</p>
            # <p></p>
            # <div class="info">1年前 / <a href="http://matchachiharu.diandian.com/post/2011-09-12/4979599#notes">0℃ </a> / </div>
        # </div>

        #http://googleyixia.com/node/727
                # <div class="rich-content">
                    # 两个月前注册了这个另Google欢喜百度忧的域名，这个站点定位我曾一度徘徊在把它建成一个Google产品边缘化的站点还是一个内容
        # <strong><a href="http://googleyixia.com/node/category/interesting-fresh">有趣新鲜</a></strong>的站点。想了又想之后，发现自己对Google产品了解并不是那么的深刻，最终还很有可能落下一个误导视听、贻笑大方的名头，那么既然如此……
        # <br /> 松一口气，该准备的都准备好了，那么今天
        # <strong>Google一下</strong>也就开张啦。
        # <br /> 我们的目标是做最好的中文
        # <strong>奇趣</strong>社区，我们网站的Googler每天为您带来全球最新、最富有
        # <strong><a href="http://googleyixia.com/node/tag/%E5%88%9B%E6%84%8F">创意</a></strong>、最有趣新鲜的消息，让你在全天任何一个时刻都有一个充满活力的大脑。我们希望每一个Googler在
        # <a href="http://googleyixia.com" title="Google一下">Google一下</a>的Google过程中都能有意外收获，这就是我们一直的目标。
                # </div>
        
        #foundContent = soup.find(attrs={"class":re.compile("post [(text)|(photo)|(audio)|(video)|(link)]")});
        
        #foundContentPhoto = soup.find(attrs={"class":"post photo"});
        #foundContentPhotoIsotope = soup.find(attrs={"class":"post photo isotope-item"});

        if(not foundContent):
            foundContent = soup.find(name="div", attrs={"class":re.compile("post [(text)|(photo)|(audio)|(video)|(link)]")});

        if(not foundContent):
            foundContent = soup.find(name="div", attrs={"class":"postInner"});

        if(not foundContent):
            foundContent = soup.find(name="div", attrs={"class":"inner "});

        if(not foundContent):
            #foundDivClassRichContent = soup.find(name="div", attrs={"class":"content-entry entry-photo rich-content"});
            foundContent = soup.find(name="div", attrs={"class":re.compile("(content-entry entry-\w+ )?rich-content")});

        if(not foundContent):
            #<div class="entry-content clearfix j_text">
            foundContent = soup.find(name="div", attrs={"class":"entry-content clearfix j_text"});

        if(not foundContent):
            #http://remixmusic.diandian.com/post/2013-05-13/40051897352
            # <article class="hentry link">
            # ...
                # <div class="entry-content">
                   
                   
                # </div>
            foundContent = soup.find(name="div", attrs={"class":"entry-content"});

        logging.debug("foundContent=%s", foundContent);
        if(foundContent):
            #post photo
            foundContent = crifanLib.removeSoupContentsTagAttr(foundContent, "h2", "class", "title"); # remove <h2 class="title">
            #logging.info('removed <h2 class="title">');
            foundContent = crifanLib.removeSoupContentsTagAttr(foundContent, "div", "class", "info"); # remove <div class="info">
            #logging.info('removed <div class="info">');
            foundContent = crifanLib.removeSoupContentsTagAttr(foundContent, "div", "class", "tags"); # remove <div class="tags">
            #logging.info('removed <div class="tags">');
            
            #post photo isotope-item
            foundContent = crifanLib.removeSoupContentsTagAttr(foundContent, "div", "class", "photoSetLink"); # remove <div class="photoSetLink">
            #logging.info('removed <div class="photoSetLink">');
            
            foundContent = crifanLib.removeSoupContentsTagAttr(foundContent, "div", "class", "seperator"); # remove <div class="seperator">
            #logging.info('removed <div class="seperator">');
            
            foundContent = crifanLib.removeSoupContentsTagAttr(foundContent, "div", "class", "meta"); # remove <div class="meta">
            #logging.info('removed <div class="meta">');

            foundContent = crifanLib.removeSoupContentsTagAttr(foundContent, "div", "class", "clear"); # remove <div class="clear"></div>
            #logging.info('removed <div class="clear"></div>');

            contentUni = crifanLib.soupContentsToUnicode(foundContent);
            
            # remove some special xml comments
            # <!--start postInner-->
            # <!--TEXT--------------------------->
            # <!--endif text-->
            # <!--LINK--------------------------->
            # <!--endif link-->
            # <!--AUDIO---------------------------->
            # <!--VIDEO---------------------->
            # <!--PHOTOSET&PHOTO------------------------>
            # <!--end meta-->
            contentUni = contentUni.replace("<!--start postInner-->", "");
            contentUni = contentUni.replace("<!--TEXT--------------------------->", "");
            contentUni = contentUni.replace("<!--endif text-->", "");
            contentUni = contentUni.replace("<!--LINK--------------------------->", "");
            contentUni = contentUni.replace("<!--endif link-->", "");
            contentUni = contentUni.replace("<!--AUDIO---------------------------->", "");
            contentUni = contentUni.replace("<!--VIDEO---------------------->", "");
            contentUni = contentUni.replace("<!--PHOTOSET&PHOTO------------------------>", "");
            contentUni = contentUni.replace("<!--end meta-->", "");
            
            #<!--判断为单张图片-->
            contentUni = contentUni.replace(u"<!--判断为单张图片-->", "");
            
            logging.debug("contentUni=%s", contentUni);
        else:
            logging.error("Can not found content soup for url=%s, html=\r\n%s", url, html);
    except :
        logging.debug("Fail to extract post content from url=%s, html=\n%s", url, html);
        contentUni = '';
    
    return contentUni;

#------------------------------------------------------------------------------
# extract category
def extractCategory(url, html) :
    catUni = '';
    try :
        #no catrgory for DianDian Blog
        catUni = "";
    except :
        catUni = "";

    return catUni;

#------------------------------------------------------------------------------
# extract tags info
def extractTags(url, html) :
    tagList = [];
    try :
        foundTag = False;
        soup = getSoupFromUrl(url);
        
        if(not foundTag):
            #http://matchachiharu.diandian.com/post/2011-09-07/4803218
            #<div class="tags">标签：<a href="/?tag=%E5%A4%8F">夏</a> <a href="/?tag=%E4%B8%8A%E6%B5%B7">上海</a> <a href="/?tag=nex3">nex3</a> <a href="/?tag=%E6%91%84%E5%BD%B1">摄影</a> </div>
            foundDivClassTags = soup.find(name="div", attrs={"class":"tags"});
            logging.debug("foundDivClassTags=%s", foundDivClassTags);
            if(foundDivClassTags):
                foundAllA = foundDivClassTags.findAll("a");
                logging.debug("foundAllA=%s", foundAllA);
                if(foundAllA):
                    for eachA in foundAllA:
                        logging.debug("eachA=%s", eachA);
                        tagUni = eachA.string;
                        logging.debug("tagUni=%s", tagUni);
                        tagList.append(tagUni);
                    foundTag = True;

        if(not foundTag):
            #http://www.zoushijie.com/post/2012-09-25/40038097755
            # <div class="meta_info">
                         
                        # <a href="/?tag=%E6%97%85%E6%B8%B8" target="_blank">旅游</a>
                         
                        # <a href="/?tag=%E6%97%85%E8%A1%8C" target="_blank">旅行</a>
                         
                        # <a href="/?tag=%E6%97%85%E8%A1%8C%E5%AE%B6" target="_blank">旅行家</a>
                         
            # </div>
            foundDivClassMetainfo = soup.find(name="div", attrs={"class":"meta_info"});
            logging.debug("foundDivClassMetainfo=%s", foundDivClassMetainfo);
            if(foundDivClassMetainfo):
                foundAllTagA = foundDivClassMetainfo.findAll(name="a", attrs={"href":re.compile("/\?tag=.+?")});
                logging.debug("foundAllTagA=%s", foundAllTagA);
                if(foundAllTagA):
                    for eachTagA in foundAllTagA:
                        logging.debug("eachTagA=%s", eachTagA);
                        tagAUni = eachTagA.string;
                        logging.debug("tagAUni=%s", tagAUni);
                        tagList.append(tagAUni);
                    foundTag = True;
        
        if(not foundTag):
            #http://googleyixia.com/node/727
            # <dl class="tags">
                # <dt><span class="post-type icon-tags">标签</span></dt>
                
                # <dd><a href="/?tag=%E7%AB%99%E7%82%B9%E6%97%A5%E5%BF%97" target="_blank">站点日志</a></dd>
                
                # <dd><a href="/?tag=%E6%88%90%E7%AB%8B" target="_blank">成立</a></dd>
                
                # <dd><a href="/?tag=Google%E4%B8%80%E4%B8%8B" target="_blank">Google一下</a></dd>
                
            # </dl>
            foundDlClassTags = soup.find(name="dl", attrs={"class":"tags"});
            logging.debug("foundDlClassTags=%s", foundDlClassTags);
            if(foundDlClassTags):
                foundAllTagA = foundDlClassTags.findAll(name="a", attrs={"href":re.compile("/\?tag=.+?")});
                logging.debug("foundAllTagA=%s", foundAllTagA);
                if(foundAllTagA):
                    for eachTagA in foundAllTagA:
                        logging.debug("eachTagA=%s", eachTagA);
                        tagAUni = eachTagA.string;
                        logging.debug("tagAUni=%s", tagAUni);
                        tagList.append(tagAUni);
                    foundTag = True;
        
        # no tags:
        #http://www.zoushijie.com/post/2012-09-22/40038845472
    except :
        logging.debug("Fail to extract tags from url=%s, html=\n%s", url, html);
        tagList = [];
    
    return tagList;

#------------------------------------------------------------------------------
# parse single src comment dict into dest comment dict
def parseCmtDict(destCmtDict, srcCmtDict, cmtId, postType):
    global gVal;
    
    destCmtDict['id'] = cmtId;
    #print "destCmtDict['id']=",destCmtDict['id'];
    
    logging.debug("--- comment[%d] ---", destCmtDict['id']);
    logging.debug("srcCmtDict=%s", srcCmtDict);

    #type1: like
    #素素很喜欢此图片 
    # {
        # "id" : 19325449,
        # "canBlock" : false,
        # "authorName" : "素素",
        # "authorDiandian" : true,
        # "authorImageUrl" : "http://m1.img.libdd.com/farm3/95/74DE8C7F30869D428D74BB9C348D525F_64_64.jpg",
        # "authorUrl" : "bbwind.diandian.com",
        # "canReport" : false,
        # "type" : 1,
        # "authorId" : 413618
    # }

    #type2: reproduce
    #蒹葭从 华中鄂人 转载了此图片 
    # {
        # "fromBlogName" : "华中鄂人",
        # "fromBlogCName" : "chinastory.diandian.com",
        # "toBlogName" : "蒹葭",
        # "authorDiandian" : true,
        # "fromBlogId" : 13012082,
        # "authorImageUrl" : "http://m3.img.libdd.com/farm2/52/62CA77AE9E1A0CA6BB513A2407FDE134_64_64.jpg",
        # "toBlogCName" : "1130018286.diandian.com",
        # "type" : 2,
        # "toBlogImageUrl" : "http://m3.img.libdd.com/farm2/52/62CA77AE9E1A0CA6BB513A2407FDE134_64_64.jpg",
        # "authorId" : 9716385,
        # "fromBlogImageUrl" : "http://m2.img.libdd.com/farm3/33/4CF5D9AD543EBB6967A23EDEB7233921_64_64.jpg",
        # "id" : 18378788,
        # "toBlogId" : 10689034,
        # "fromPostId" : "2530fd30-04b7-11e2-84e7-782bcb383994",
        # "canBlock" : false,
        # "authorName" : "蒹葭",
        # "fromBlogUrl" : "chinastory",
        # "authorUrl" : "1130018286.diandian.com",
        # "canReport" : false,
        # "comment" : "",
        # "toBlogUrl" : "1130018286"
    # }
    
    #type3:reply
    #走过在 途客们的旅行梦回应了此图片 
    # {
        # "fromBlogName" : "途客们的旅行梦",
        # "fromBlogCName" : "tukeq.diandian.com",
        # "authorDiandian" : true,
        # "fromBlogId" : 13383756,
        # "authorImageUrl" : "http://m2.img.libdd.com/farm5/2012/1017/01/E7368E3C850CEAC52EC383E73420AE38F43AD91F8661E_64_64.jpg",
        # "type" : 3,
        # "authorId" : 40970756,
        # "fromBlogImageUrl" : "http://m1.img.libdd.com/farm3/233/043316511C24062E3EC2087F61DF66E9_64_64.jpg",
        # "id" : 19047564,
        # "canReply" : true,
        # "toUserId" : 40970756,
        # "fromPostId" : "50d70640-049a-11e2-a67e-782bcb383976",
        # "canBlock" : false,
        # "authorName" : "走过",
        # "fromBlogUrl" : "tukeq",
        # "authorUrl" : "shuizhixiu.diandian.com",
        # "canReport" : false,
        # "comment" : "紫禁城是每次去北京都要去的地方，庄严神圣，宛如隔世，想着要是我穿越到那个时代，会是怎样的故事，不由得想着明天一定去买本史记来看，可每每这样的想法都是一逝而过，哈哈",
        # "canDel" : false
    # }
    
    #for "postType" : "text",
    #韩韩==就算是换来对不起，我还是可以说服自己 
    # {
        # "fromBlogName" : "韩韩==",
        # "fromBlogCName" : "hanhan--.diandian.com",
        # "authorDiandian" : true,
        # "fromBlogId" : 16667601,
        # "authorImageUrl" : "http://m1.img.libdd.com/farm4/2012/1029/23/8905503B1A5CA284ED76C9439BB0AF753884B25714B39_64_64.jpg",
        # "type" : 3,
        # "authorId" : 16623033,
        # "fromBlogImageUrl" : "http://m1.img.libdd.com/farm4/2012/1029/23/8905503B1A5CA284ED76C9439BB0AF753884B25714B39_64_64.jpg",
        # "id" : 13128722,
        # "canReply" : true,
        # "toUserId" : 16623033,
        # "fromPostId" : "392632e0-9817-11e1-91ce-782bcb32ff27",
        # "canBlock" : false,
        # "authorName" : "韩韩==",
        # "fromBlogUrl" : "hanhan--",
        # "authorUrl" : "hanhan--.diandian.com",
        # "canReport" : false,
        # "comment" : "就算是换来对不起，我还是可以说服自己",
        # "canDel" : false
    # }

    #type4: recommend
    #不二飞的飞将该图片推荐到了 城市 标签下 
    # {
        # "id" : 18260316,
        # "tag" : "城市",
        # "canBlock" : false,
        # "authorName" : "不二飞的飞",
        # "authorDiandian" : true,
        # "authorImageUrl" : "http://m1.img.libdd.com/farm5/2012/0920/19/C12FEE7A3EDDE913A32B17D7B58841F23A2E4B1651CF_64_64.jpg",
        # "authorUrl" : "www.buerfei.com",
        # "canReport" : false,
        # "type" : 4,
        # "tagUrl" : "/tag/%E5%9F%8E%E5%B8%82",
        # "authorId" : 10933169
    # }
    
    destCmtDict['author'] = srcCmtDict['authorName'];
    #print "destCmtDict['author']=",destCmtDict['author'];
    
    if(srcCmtDict['authorUrl']):
        fullAuthorUrl = "http://" + srcCmtDict['authorUrl'];
        logging.debug("fullAuthorUrl=%s", fullAuthorUrl);
        destCmtDict['author_url'] = fullAuthorUrl;
    else:
        #http://www.zoushijie.com/post/2012-09-30/40040622782
        # has special comment:
        #南方的南方(QQ空间) 在 走世界回应了此图片
        # its authorUrl is None after convert to json
        
        # {
            # "fromBlogName" : "走世界",
            # "fromBlogCName" : "www.zoushijie.com",
            # "authorDiandian" : false,
            # "fromBlogId" : 31576869,
            # "authorImageUrl" : "http://m1.img.libdd.com/farm5/2012/1010/19/7C71E14F16B9B7ADC5F0EF9FD612F97E0E67292421FC_50_50.jpg",
            # "type" : 3,
            # "authorId" : 0,
            # "fromBlogImageUrl" : "http://m1.img.libdd.com/farm4/2012/0922/20/16DAA2A246BE7F1A7FF05519E3A3ED411B9FA45EF698_100_130.GIF",
            # "canReply" : true,
            # "id" : 18805950,
            # "toUserId" : 0,
            # "fromPostId" : "f94e5aa0-0b05-11e2-b2b3-782bcb32ff27",
            # "canBlock" : false,
            # "authorName" : "南方的南方(QQ空间)",
            # "fromBlogUrl" : "zousj",
            # "authorUrl" : null,
            # "authorUuid" : "dbeee089-7011-4e5e-bfbe-4b83b0810952",
            # "canReport" : false,
            # "comment" : "我也喜欢~",
            # "canDel" : false
        # }
        
        # so here set to empty
        destCmtDict['author_url'] = "";
        
    #print "destCmtDict['author_url']=",destCmtDict['author_url'];
    
    #fake time
    localTime = datetime.now();
    #print "localTime=",localTime;
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    #print "gmtTime=",gmtTime;
    destCmtDict['date']     = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");

    type = srcCmtDict['type'];
    content = u"";
    postTypeStr = "";
    if(postType == "photo"):
        postTypeStr = u"图片";
    #process comment content
    if(type == 1):
        if(destCmtDict['author_url']):
            content = u'<a href="'+destCmtDict['author_url'] + u'">'+destCmtDict['author'] + u"<a/>很喜欢此" + postTypeStr; #u"素素很喜欢此图片"
        else:
            content = destCmtDict['author'] + u" 很喜欢此" + postTypeStr; #u"素素很喜欢此图片"
    elif(type == 2):
        #蒹葭从 华中鄂人 转载了此图片 
        content = destCmtDict['author'] + u"从"+ ' <a href="' + "http://" + srcCmtDict['fromBlogCName'] + '">' + srcCmtDict['fromBlogName'] + u"</a> 转载了此"+postTypeStr;
        if(srcCmtDict['comment']):
            content += u"<br />"+srcCmtDict['comment'];
    elif(type == 3):
        content = srcCmtDict['comment'];
    elif(type == 4):
        #不二飞的飞将该图片推荐到了 城市 标签下 
        content = destCmtDict['author'] + u"将该"+postTypeStr+u"推荐到了 "+'<a href="http://www.diandian.com'+ srcCmtDict['tagUrl']+'">' +srcCmtDict['tag'] +u"</a> 标签下"; 
    
    destCmtDict['content'] = content;
    #print "destCmtDict['content']=",destCmtDict['content']; # some char will raise error fro gbk can not show it

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
    
    #print "-------fill comments %4d OK"%(destCmtDict['id']);

    return ;
    
#------------------------------------------------------------------------------
# parse source all comment dict list into dest comment dict list
def parseAllCommentsList(allCmtDictList, parsedCommentsList, postType):
    cmtListLen = len(allCmtDictList);
    logging.debug("Now to parse total %d comment dict list", cmtListLen);
    
    for cmtIdx, srcCmtDict in enumerate(allCmtDictList):
        destCmtDict = {};
        cmtId = cmtIdx + 1;
        parseCmtDict(destCmtDict, srcCmtDict, cmtId, postType);
        parsedCommentsList.append(destCmtDict);

    logging.debug("after parse, got %d comments", len(parsedCommentsList));
    return;

#------------------------------------------------------------------------------
# get all notes(comments) dict list
def getAllNotesDictList(postId, sPostId, notesCount):
    logging.debug("Inputed postId=%s, sPostId=%s, notesCount=%s", postId, sPostId, notesCount);
    
    (allNotesDictList, postType) = ([], "");
    notesCountInt = int(notesCount);
    
    needGetMore = True;
    lastNoteId = "";
    while(needGetMore):
        notesCountFixedInt = 100;
        countInt = notesCountFixedInt;
        #1. generate url to get notes
        
        #http://www.diandian.com/notes?postId=5de46000-c3cf-11e1-996f-782bcb38253b&sPostId=5de46000-c3cf-11e1-996f-782bcb38253b&count=100&types=1%2C2%2C3%2C4&t=1351598216214
        
        #more than 100 comments:
        #http://www.zoushijie.com/post/2012-09-22/40038845472
        # first page:
        #http://www.diandian.com/notes?postId=e3b27ed0-04af-11e2-995c-782bcb32ff27&sPostId=50d70640-049a-11e2-a67e-782bcb383976&count=100&types=1%2C2%2C3%2C4&t=1351599989672
        # seond page:
        #http://www.diandian.com/notes?postId=e3b27ed0-04af-11e2-995c-782bcb32ff27&sPostId=50d70640-049a-11e2-a67e-782bcb383976&count=100&types=1%2C2%2C3%2C4&t=1351600053600&lastNoteId=18260175
        
        #code: http://www.diandian.com/notes?postId=e3b27ed0-04af-11e2-995c-782bcb32ff27&sPostId=50d70640-049a-11e2-a67e-782bcb383976&count=100&lastNoteId=18259745
        #IE9:  http://www.diandian.com/notes?postId=e3b27ed0-04af-11e2-995c-782bcb32ff27&sPostId=50d70640-049a-11e2-a67e-782bcb383976&count=100&types=1%2C2%2C3%2C4&t=1351667530616&lastNoteId=18260175
        getNotesUrl = "http://www.diandian.com/notes";
        getNotesUrl += "?postId=" + postId;
        getNotesUrl += "&sPostId=" + sPostId;
        getNotesUrl += "&count=" + str(countInt);
        #timestamp = crifanLib.getCurTimestamp();
        #timestampStr = str(timestamp);
        #getNotesUrl += "&t=" + timestampStr; # Note: here timestamp only 10 bits: 1351671098, not 13 bits show in above url: 1351599989672
        typesStr = "1,2,3,4"; #1%2C2%2C3%2C4
        getNotesUrl += "&types=" + typesStr;
        if(lastNoteId):
            getNotesUrl += "&lastNoteId=" + lastNoteId;
        logging.debug("getNotesUrl=%s", getNotesUrl);
        
        #Note: need clear some value
        lastNoteId = "";
        
        #get comments json
        notesRespJson = crifanLib.getUrlRespHtml(getNotesUrl);
        logging.debug("notesRespJson=%s", notesRespJson);
        
        #2.parse return json
        # {
            # "postType" : "photo",
            # "canComment" : -1,
            # "hasPrevious" : false,
            # "hasNext" : true,
            # "commentCount" : 0,
            # "sevenDayLimit" : false,
            # "notes" : [{...}, {...}, ...
            # ],
            # "notesCount" : 107
        # }

        # {
            # "postType" : "photo",
            # "canComment" : -1,
            # "commentCount" : 0,
            # "sevenDayLimit" : false,
            # "notes" : [......
            # ],
            # "notesCount" : 107
        # }
        
        # {
            # "postType" : "text",
            # "canComment" : -1,
            # "hasPrevious" : false,
            # "hasNext" : false,
            # "commentCount" : 1,
            # "sevenDayLimit" : false,
            # "notes" : [......
            # ],
            # "notesCount" : 1
        # }

        
        
        notesJsonDict = json.loads(notesRespJson);
        logging.debug("notesJsonDict=%s", notesJsonDict);
        
        postType = notesJsonDict['postType'];
        logging.debug("postType=%s", postType);

        curNotesDictList = notesJsonDict['notes'];
        logging.debug("Current resp json notes dict list len=%d", len(curNotesDictList));
        allNotesDictList.extend(curNotesDictList);
        
        if('hasNext' in notesJsonDict):
            logging.debug("hasNext is in resp json dict");
            hasNext = notesJsonDict['hasNext'];
            logging.debug("hasNext=%s", hasNext);

            needGetMore = hasNext;
            if(needGetMore):
                # if hasNext, continue to get
                logging.debug("hasNext is true, need get more comments");
                lastNote = notesJsonDict['notes'][-1];
                logging.debug("lastNote=%s", lastNote);
                lastNoteIdInt = lastNote['id'];
                lastNoteId = str(lastNoteIdInt);
                logging.debug("found lastNoteId=%s", lastNoteId);
        else:
            logging.debug("hasNext not in resp json dict, seems no comments to get, so quit here");
            needGetMore = False;

    logging.debug("Total got resp notes dict list len=%d", len(allNotesDictList));
    
    return (allNotesDictList, postType);

#------------------------------------------------------------------------------
# fetch and parse comments 
# return the parsed dict value
def fetchAndParseComments(url, html):
    parsedCommentsList = [];
        
    try :
        #logging.debug("fetchAndParseComments_html=\n%s", html);
        
        soup = getSoupFromUrl(url);
        
        # <iframe id="diandian_comments" frameborder="0" scrolling="no" allowtransparency="true" height="0" width="100%" src="http://www.diandian.com/n/common/comment?feedId=5de46000-c3cf-11e1-996f-782bcb38253b&amp;notesTextColor=%23000000&amp;notesLinkColor=%234691c1&amp;notesBlockQuoteColor=&amp;notesBlockBgColor=%23000000&amp;notesBlockBorderColor=&amp;notesBlockBgOpacity=0&amp;notesOperationLinkColor=&amp;notesEnableBorderRadius=true&amp;notesIframeId="></iframe>

        
        # <iframe id="diandian_comments" frameborder="0" scrolling="no" allowtransparency="true" height="0" width="510" src="http://www.diandian.com/n/common/comment?feedId=e3b27ed0-04af-11e2-995c-782bcb32ff27&amp;notesTextColor=%23000&amp;notesLinkColor=%23000&amp;notesBlockQuoteColor=&amp;notesBlockBgColor=&amp;notesBlockBorderColor=&amp;notesBlockBgOpacity=0&amp;notesOperationLinkColor=&amp;notesEnableBorderRadius=false&amp;notesIframeId="></iframe>
        
        foundDiandianComments = soup.find(name="iframe", attrs={"id":"diandian_comments"});
        logging.debug("foundDiandianComments=%s", foundDiandianComments);
        if(foundDiandianComments):
            commentUrl = foundDiandianComments['src'];
            logging.debug("commentUrl=%s", commentUrl);
            #http://www.diandian.com/n/common/comment?feedId=5de46000-c3cf-11e1-996f-782bcb38253b&notesTextColor=%23000000&notesLinkColor=%234691c1&notesBlockQuoteColor=&notesBlockBgColor=%23000000&notesBlockBorderColor=&notesBlockBgOpacity=0&notesOperationLinkColor=&notesEnableBorderRadius=true&notesIframeId=
            commentRespHtml = crifanLib.getUrlRespHtml(commentUrl);
            logging.debug("commentRespHtml=%s", commentRespHtml);
            
            #get postId and sPostId
            # window.DDformKey = '';ENV.PAGE_VARS = {
            # urlDomain   : 'matchachiharu.diandian.com',
            # postId      : '5de46000-c3cf-11e1-996f-782bcb38253b',
            # sPostId     : '5de46000-c3cf-11e1-996f-782bcb38253b',
            # notesCount  : '9',
            # commentCount: '0',
            # startTab    : 'notes',
            # iframeId    : 'diandian_comments'
            # };
            foundPageVars = re.search("postId\s*:\s*'(?P<postId>[\w\-]+)',\s*sPostId\s*:\s*'(?P<sPostId>[\w\-]+)',\s*notesCount\s*:\s*'(?P<notesCount>\d+)'", commentRespHtml, re.S);
            logging.debug("foundPageVars=%s", foundPageVars);
            if(foundPageVars):
                postId = foundPageVars.group("postId");
                sPostId = foundPageVars.group("sPostId");
                notesCount = foundPageVars.group("notesCount");
                logging.debug("postId=%s, sPostId=%s, notesCount=%s", postId, sPostId, notesCount);

                (allNotesDictList, postType) = getAllNotesDictList(postId, sPostId, notesCount);
                
                logging.debug("len(allNotesDictList)=%s", len(allNotesDictList));
                parseAllCommentsList(allNotesDictList, parsedCommentsList, postType);
                logging.debug("total parsed %d comments", len(parsedCommentsList));
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
    fd3 = picInfoDict['fields']['fd3'];
    fd4 = picInfoDict['fields']['fd4'];
    
    logging.debug("fd1=%s,fd2=%s,fd3=%s,fd4=%s", fd1, fd2, fd3, fd4);

    if ((fd2=='img')and(fd3=='libdd')and(fd4=='com')):
        isSelfPic = True;
    else :
        isSelfPic = False;

    logging.debug("isSelfBlogPic: %s", isSelfPic);

    return isSelfPic;

#------------------------------------------------------------------------------
def getProcessPhotoCfg():
    # possible own site pic link:
    # type1:
    # http://shuizhixiu.diandian.com/post/2012-10-30/40041936379 contain:
    # http://m1.img.libdd.com/farm5/2012/1029/14/C0C146BFCE687D52A1CD05B5958F56491D147C5457322_500_500.jpg
    #
    #http://www.zoushijie.com/post/2012-09-22/40038845472 contain:
    #http://m2.img.libdd.com/farm5/2012/0922/13/680500791768CBF0EEB84839D18DF546BA06338D7D8E_500_331.jpg
    
    # possible othersite pic url:
        
    processPicCfgDict = {
        # here only extract last pic name contain: char,digit,-,_
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
# parse datetime string into (local=GMT+8) datetime value
def parseDatetimeStrToLocalTime(datetimeStr):
    # possible date format:
    # (1) 2012-09-22
    logging.debug("datetimeStr=%s", datetimeStr);
    parsedLocalTime = datetime.strptime(datetimeStr, '%Y-%m-%d');
    logging.debug("parsedLocalTime=%s", parsedLocalTime);
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