#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for Sohu Blog.

[TODO]

"""

import os;
import re;
import sys;
import math;
import time;
import chardet;
#import urllib;
#import urllib2;
from datetime import datetime,timedelta;
from BeautifulSoup import BeautifulSoup,Tag,CData;
import logging;
import crifanLib;
import cookielib;
#from xml.sax import saxutils;
import json; # New in version 2.6.
import random;

#--------------------------------const values-----------------------------------
__VERSION__ = "v1.3";

gConst = {
    'spaceDomain'  : "",
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',   # maoyushi
    'blogEntryUrl'  : '',   # http://maoyushi.blog.sohu.com
    'cj'            : None, # cookiejar, to store cookies for login mode
    
    'soupDict'      : {},   # cache the soup for url's html -> url : soup

    'urlListInfo'   : {
        'inited'    : False,
        'ebi'       : "",
        'itemPerPage': 0,
        'totalCount' : 0,
        'lastPageNum': 0,
    }, 
    
    'urlRelation'   : {
        'inited'            : False, # indicate whether the relation dict is inited or not
        'nextLinkRelation'  : {}, # url, realNextLink
    }, 
    
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
    soup = BeautifulSoup(html, fromEncoding="GB18030"); # sohu use GBK
    
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
        soup = htmlToSoup(html);
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
# http://caochongweiyu.blog.sohu.com
# http://caochongweiyu.blog.sohu.com/
# http://caochongweiyu.blog.sohu.com/entry
# http://caochongweiyu.blog.sohu.com/entry/
# (2) caochongweiyu from: 
# http://caochongweiyu.blog.sohu.com/206655492.html
def extractBlogUser(inputUrl):
    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
    logging.debug("Extracting blog user from url=%s", inputUrl);
    
    try :
        # type1, main url: 
        # http://caochongweiyu.blog.sohu.com
        # http://caochongweiyu.blog.sohu.com/
        foundMainUrl = re.search("http://(?P<username>\w+)\.blog\.sohu\.com/?(entry)?/?", inputUrl);
        if(foundMainUrl) :
            extractedBlogUser = foundMainUrl.group("username");
            generatedBlogEntryUrl = "http://" + extractedBlogUser + ".blog.sohu.com";
            extractOk = True;
            
        # type2, perma link:
        # http://caochongweiyu.blog.sohu.com/206655492.html
        if(not extractOk):
            foundPermaLink = re.search("http://(?P<username>\w+)\.blog\.sohu\.com/\d+\.html", inputUrl);
            if(foundPermaLink) :
                extractedBlogUser = foundPermaLink.group("username");
                generatedBlogEntryUrl = "http://" + extractedBlogUser + ".blog.sohu.com";
                extractOk = True;
    except :
        (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
        
    if (extractOk) :
        gVal['blogUser'] = extractedBlogUser;
        gVal['blogEntryUrl'] = generatedBlogEntryUrl;
        
    return (extractOk, extractedBlogUser, generatedBlogEntryUrl);

#------------------------------------------------------------------------------
# init url list info for latter to get url list
def initUrlListInfo():
    if(not gVal['urlListInfo']['inited']):
        logging.debug("url list info is not init, so init now");
        
        #http://caochongweiyu.blog.sohu.com/entry/ -> get ebi
        mainUrl = gVal['blogEntryUrl'] + "/entry/";
        respHtml = crifanLib.getUrlRespHtml(mainUrl);
        logging.debug("mainUrl=%s return html=\n%s", mainUrl, respHtml);
        
        #var _ebi = 'fa46752992';
        foundEbi = re.search(r"var\s+?_ebi\s+?=\s*?'(?P<ebi>\w+)';", respHtml);
        #print "foundEbi=",foundEbi;
        if(foundEbi):
            ebi = foundEbi.group("ebi");
            logging.debug("found ebi=%s", ebi);            

            # var category = 0;
            # var tag = '';
            # var curPage = 0;
            # var itemPerPage = 20;
            # var startPage = 1;
            # var totalCount = 38;
            foundPageInfo = re.search("var itemPerPage = (?P<itemPerPage>\d+);.+?var totalCount = (?P<totalCount>\d+);", respHtml, re.S);
            #print "foundPageInfo=",foundPageInfo;
            if(foundPageInfo):
                itemPerPage = foundPageInfo.group("itemPerPage");
                itemPerPage = int(itemPerPage);
                totalCount = foundPageInfo.group("totalCount");
                totalCount = int(totalCount);
                
                lastPageNumFloat = float(totalCount)/float(itemPerPage);
                lastPageNumCeil = math.ceil(lastPageNumFloat);
                lastPageNum = int(lastPageNumCeil);
                logging.debug("itemPerPage=%d, totalCount=%d, lastPageNumFloat=%f, lastPageNumCeil=%f, lastPageNum=%d", itemPerPage, totalCount, lastPageNumFloat, lastPageNumCeil, lastPageNum);

                # store values
                gVal['urlListInfo']['ebi'] = ebi;
                gVal['urlListInfo']['itemPerPage'] = itemPerPage;
                gVal['urlListInfo']['totalCount'] = totalCount;
                gVal['urlListInfo']['lastPageNum'] = lastPageNum;
                
                gVal['urlListInfo']['inited'] = True;
                logging.debug("init url list info OK");
    return;

#------------------------------------------------------------------------------
# fetch url list in article list page, eg:
#http://caochongweiyu.blog.sohu.com/action/v_frag-ebi_fa46752992/entry/
#http://caochongweiyu.blog.sohu.com/action/v_frag-ebi_fa46752992-pg_2/entry/
def fetchUrlList(pageNum):
    logging.debug("now will fetch url list for pageNum=%d", pageNum);
    
    initUrlListInfo();
    
    if(gVal['urlListInfo']['inited']):
        urlList = [];
        
        if(pageNum == 1):
            #http://caochongweiyu.blog.sohu.com/action/v_frag-ebi_fa46752992/entry/
            getUrlListUrl = gVal['blogEntryUrl'] + "/action/v_frag-ebi_" + gVal['urlListInfo']['ebi'] + "/entry/";
        else:
            #http://caochongweiyu.blog.sohu.com/action/v_frag-ebi_fa46752992-pg_2/entry/
            getUrlListUrl = gVal['blogEntryUrl'] + "/action/v_frag-ebi_" + gVal['urlListInfo']['ebi'] + "-pg_" + str(pageNum) + "/entry/";

        logging.debug("url for get url list is %s", getUrlListUrl);
        respHtml = crifanLib.getUrlRespHtml(getUrlListUrl);
        #logging.debug("for get url list, respHtml=\n%s", respHtml);
        
        # (1) normal:
        # <h3>2012-03-22&nbsp;|&nbsp;<a href="http://caochongweiyu.blog.sohu.com/208414980.html" target="_blank">张棻:民国天津势力犬牙交错的&#8220;五大道&#8221;</a>
        # </h3>
        # (2) for special one, eg:
        #http://yetanyetan.blog.sohu.com/action/v_frag-ebi_99869d3792-pg_132/entry/
        #http://yetanyetan.blog.sohu.com/action/v_frag-ebi_99869d3792-pg_134/entry/
        # got 20 posts, but only get 19 url, for some of them is:
        #<h3>该日志已隐藏 </h3>
        # (3) if exceed max num, eg:
        #http://yetanyetan.blog.sohu.com/action/v_frag-ebi_99869d3792-pg_150/entry/
        # return html is like this:
        #<h3><img src="http://js.pp.sohu.com/ppp/blog/styles/images/spacer.gif" alt="Toggle this item" class="arrow-up" onclick="toggleItem(this)" />&nbsp;欢迎您成为我的搜狐用户，创造网络新生活：）</h3>
        soup = htmlToSoup(respHtml);
        foundPosts = soup.findAll("h3");
        logging.debug("found %d post list", len(foundPosts));
        for i, eachPost in enumerate(foundPosts):
            #logging.debug("foundPosts[%d]=%s", i, eachPost);
            #print "eachPost.a=",eachPost.a;
            if(eachPost.a and eachPost.a['href']):
                href = eachPost.a['href']; #http://caochongweiyu.blog.sohu.com/208414980.html
                #print "href=",href; 
                urlList.append(href);

        logging.debug("for pageNum=%d, total fetch %d url", pageNum, len(urlList));
    
    return urlList;

#------------------------------------------------------------------------------
# init next link relation dict
def initNextLinkRelationDict():
    if(not gVal['urlRelation']['inited']):
        logging.info("begin to init the relation for next link");
        allPageUrlList = [];
        
        initUrlListInfo();
        if(gVal['urlListInfo']['inited']):
            totalPageNum = gVal['urlListInfo']['lastPageNum'];
            for pageIdx in range(totalPageNum):
                pageNum = pageIdx + 1;
                urlList = fetchUrlList(pageNum);
                if(urlList):
                    allPageUrlList.extend(urlList);
                else:
                    # can not get more, so quit
                    break;
                logging.debug("has got page url list len=%d", len(allPageUrlList));
        
        if(allPageUrlList):
            allPageUrlList.reverse(); # -> is OK, the self is reversed !!!
            reversedPageUrlList = allPageUrlList;
            urlListLen = len(reversedPageUrlList);
            for i in range(urlListLen):
                curPemaLink = reversedPageUrlList[i];
                if(i != (urlListLen - 1)):
                    # if not the last one
                    nextPermaLink = reversedPageUrlList[i + 1];
                else:
                    # last one's next link is empty
                    nextPermaLink = "";
                    
                gVal['urlRelation']['nextLinkRelation'][curPemaLink] = nextPermaLink;
        
        gVal['urlRelation']['inited'] = True;
        logging.info("init the relation for next link completed");

    return ;

#------------------------------------------------------------------------------
# find the first permanent link = url of the earliset published blog item
def find1stPermalink():
    (isFound, retInfo) = (False, "Unknown error!");
    
    try:
        initUrlListInfo(); # -> then can get lastPageNum
        if(gVal['urlListInfo']['inited']):
            # to get last page url list
            urlList = fetchUrlList(gVal['urlListInfo']['lastPageNum']);
            if(urlList):
                # last one of last page
                fristLink = urlList[-1];
                retInfo = fristLink;
                #print "fristLink=",fristLink;
                logging.debug("fristLink=%s", fristLink);
                isFound = True;
    except:
        (isFound, retInfo) = (False, "Unknown error!");

    return (isFound, retInfo);

#------------------------------------------------------------------------------
# extract title for normal valid post
def extractTitleForValidPost(url, html):
    titleUni = "";
    
    try :
        #logging.debug("extractTitleForValidPost_html=\n%s", html);
        
        # <div class="item-title">
          # <h3>苏联克格勃训练性间谍内容纪实
            # <span style="position:absolute; height:0px; width:0px;"><img style="position:absolute; left:50px; top:-40px;" src="http://js.pp.sohu.com/ppp/blog/styles_ppp/images/stamp_jian.gif" alt="该日志已被收录" title="该日志已被收录" align="absmiddle" /></span>
          # </h3>
          # <div class="item-label">
          # <span class="itemOpr"><a onmousedown="CA.q('blog_entryview_share_topright');" href="javascript:void(0);" entryTitle="苏联克格勃训练性间谍内容纪实" data-shareType="31" data-title="#{@entryTitle}" data-url="http://caochongweiyu.blog.sohu.com/202840469.html" data-abstracts="#{#main-content@innerText<51}" data-ext="{v:'1',xpt:'#{$_xpt}'}" onclick="shareIt(this)" style="margin-right:10px;"><img src="http://js2.pp.sohu.com.cn/ppp/blog/styles_ppp/images/btn_share_s2.gif" alt="分享" title="分享" /></a></span><span id="itemId_202840469" class="itemOpr"></span>
          # </div>
          # <div class="clear"></div>
        # </div>
        soup = getSoupFromUrl(url);
        foundTitle = soup.find(attrs={"class":"item-title"});
        #print "foundTitle=",foundTitle;
        h3 = foundTitle.h3;
        #print "h3=",h3;
        #print "h3.contents=",h3.contents;
        #titleStr = h3.string; # not work !!!
        titleStr = h3.contents[0];
        #print "titleStr=",titleStr;
        titleUni = unicode(titleStr);
        #print "titleUni=",titleUni;
        titleUni = titleUni.replace("\r", "");
        titleUni = titleUni.replace("\n", "");
        titleUni = titleUni.strip();
        #print "titleUni=",titleUni;
    except :
        htmlUni = html.decode("GB18030", 'ignore');
        #logging.debug("Fail to extract tiltle for valid post, from url=%s, html=\n%s", url, html);
        logging.debug("Fail to extract tiltle for valid post, from url=%s, html=\n%s", url, htmlUni);
        titleUni = "";

    return titleUni;
    
#------------------------------------------------------------------------------
# extract title
def extractTitle(url, html):
    (needOmit, titleUni) = (False, "");
    
    try :
        titleUni = extractTitleForValidPost(url, html);
        #print "titleUni=",titleUni;
        if(not titleUni):
            # check whether is invalid or hidden post
            #<div class="ts_txt">此文章已被外星人劫持或被博主隐藏！</div>
            htmlUni = html.decode("GB18030", 'ignore');
            #print "htmlUni="htmlUni;
            foundInvalid = re.search(u'<div class="ts_txt">此文章已被外星人劫持或被博主隐藏！</div>', htmlUni);
            #print "foundInvalid=",foundInvalid;
            if(foundInvalid):
                needOmit = True;
                titleUni = u"此文章已被外星人劫持或被博主隐藏！";
    except :
        logging.debug("Fail to extract tiltle from url=%s, html=\n%s", url, html);
        (needOmit, titleUni) = (False, "");

    return (needOmit, titleUni);

#------------------------------------------------------------------------------
# find next permanent link of valid post
def findNextLinkForValidPost(url) :
    (nextLink, nextTitle) = ("", "");

    try :
        # sohu here previous is next perma link:
        # <div class="previous_txt">上一篇：</div>
        # <div class="previous_txt"><a onmousedown="CA.q('blog_entryview_previous');" href="http://caochongweiyu.blog.sohu.com/202983304.html"> 蔡锷誓为四万万人的人格而战</a>  </div>
        soup = getSoupFromUrl(url);
        foundPrev = soup.findAll(attrs={"class":"previous_txt"});
        #print "foundPrev=",foundPrev;
        #print "len(foundPrev)=",len(foundPrev);
        if(foundPrev):
            prevSoup = foundPrev[-1];
            #print "prevSoup=",prevSoup;
            if(prevSoup and prevSoup.a):
                aVal = prevSoup.a;
                #print "aVal=",aVal;
                href = aVal['href'];
                #print "href=",href;
                nextLink = href;
                nextTitle = aVal.string;
                nextTitle = nextTitle.strip();
                #print "nextTitle=",nextTitle;

            logging.debug("Found next post: link=%s, title=%s", nextLink, nextTitle);
    except :
        logging.debug("Fail to extract next link for url=%s", url);

    return (nextLink, nextTitle);
    
#------------------------------------------------------------------------------
# find next permanent link of invalid post
def findNextLinkForInvalidPost(html) :
    (invalidNextLink, invalidNextTitle) = ("", "");

    try :
        # <div class="ts_foot">
        # <div class="ts_l">上一篇：<a href="http://maoyushi.blog.sohu.com/43359413.html">转制国家对企业家存有偏见</a></div>
        # <div class="ts_s"></div>
        # <div class="ts_l">下一篇：<a href="http://maoyushi.blog.sohu.com/33825654.html">从财富创造和财富分配看中国经济</a></div>
        # </div>
        htmlUni = html.decode("GB18030", 'ignore');
        #print "htmlUni=",htmlUni;
        foundNext = re.search(u'<div class="ts_l">上一篇：<a href="(?P<invalidNextLink>.+?)">(?P<invalidNextTitle>.+?)</a></div>', htmlUni);
        #print "foundNext=",foundNext;
        if(foundNext):
            invalidNextLink = foundNext.group("invalidNextLink");
            #print "invalidNextLink=",invalidNextLink;
            invalidNextTitle = foundNext.group("invalidNextTitle");
            #print "invalidNextTitle=",invalidNextTitle;

            logging.debug("Found invalid post's next: link=%s, title=%s", invalidNextLink, invalidNextTitle);
    except :
        logging.debug("Fail to extract next link from html=\n%s", htmlUni);

    return (invalidNextLink, invalidNextTitle);

#------------------------------------------------------------------------------
# get next perma link from the dict
#{'#http://yetanyetan.blog.sohu.com/19660479.html':'http://yetanyetan.blog.sohu.com/19660848.html', ...}
def getNextLinkFromDict(curPemaLink):
    initNextLinkRelationDict();
    
    nextPermaLink = "";
    if(curPemaLink in gVal['urlRelation']['nextLinkRelation']) :
        nextPermaLink = gVal['urlRelation']['nextLinkRelation'][curPemaLink];
    else:
        nextPermaLink = "";

    return nextPermaLink;

#------------------------------------------------------------------------------
# find next permanent link of current post
def findNextPermaLink(url, html) :
    nextLinkStr = '';

    try :
        #logging.debug("findNextPermaLink_html=\n%s", html);
        
        # here should get next link from dict first
        # for some old post, eg:
        # http://yetanyetan.blog.sohu.com/19786679.html
        # do not have prev and next link 
        # so need to build the next link relation dict
        # then get the next link from dict
        
        nextLinkStr = getNextLinkFromDict(url);
        logging.debug("for next link, get from dict is %s", nextLinkStr);
        nextPostTitle = "";

        if(not nextLinkStr):
            # can not find the next link from dict, then try extract out
            (nextLink, nextTitle) = findNextLinkForValidPost(url);
            #print "nextLink=",nextLink," nextTitle=",nextTitle;
            if(not nextLink):
                # maybe is invalid or hidden post
                (nextLink, nextTitle) = findNextLinkForInvalidPost(html);
                #print "after findNextLinkForInvalidPost, nextLink=",nextLink," nextTitle=",nextTitle;

            (nextLinkStr, nextPostTitle) = (nextLink, nextTitle);

        logging.debug("Found real next permanent link=%s, title=%s", nextLinkStr, nextPostTitle);
    except :
        logging.debug("Fail to extract next perma link from url=%s, html=\n%s", url, html);
        nextLinkStr = '';

    return nextLinkStr;

#------------------------------------------------------------------------------
# extract datetime string
def extractDatetime(url, html) :
    datetimeStr = '';
    try :
        #logging.debug("extractDatetime_html=\n%s", html);
        
        #<span class="revoRight">2012-02-05 17:17</span>
        soup = getSoupFromUrl(url);
        foundDatetime = soup.find(attrs={"class":"revoRight"});
        #print "foundDatetime=",foundDatetime;
        if foundDatetime:
            datetimeStr = foundDatetime.string;
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
        #logging.debug("extractContent_html=\n%s", html);
        
        #<div class="item-content" id="main-content">
        # ......
        #</div>
        soup = getSoupFromUrl(url);
        foundContent = soup.find(id="main-content");
        #logging.debug("---soup foundContent=\n%s", foundContent);

        # divs = foundContent.findAll("div");
        # print "len(divs)=",len(divs);
        # print "---------------------";
        # #for i in range(5):
        # #    print "div[",(i+7),"]=",divs[i+7];
        # for i, div in enumerate(divs):
           # print "[",i,"]=",div;
           # logging.debug("divs[%d]=%s", i, div);
        # foundContent = foundContent.contents[1];
        # print "---------------------";
                
        #method 1
        mappedContents = map(CData, foundContent.contents);
        #print "mappedContents OK";
        #print "type(mappedContents)=",type(mappedContents); #type(mappedContents)= <type 'list'>
        contentUni = ''.join(mappedContents);
        #print "type(contentUni)=",type(contentUni);
        #logging.debug("original contentUni=%s", contentUni);
        
        # should remove following:
        
        #(0) remove 精彩阅读 or 更多阅读 or 更多文章推荐阅读
        # http://musangdaozhang.blog.sohu.com/206594401.html contain:
        # <p>精彩阅读</p>
        # <p>...</p>
        #print "prev readEliteP: len(contentUni)=\t",len(contentUni);
        # readEliteP = ur'<p>精彩阅读</p>.*?<p>.+?</p>';
        # contentUni = re.sub(readEliteP, "", contentUni, flags=(re.I | re.S)); # can work
        foundPFields = foundContent.findAll("p");
        for i, eachP in enumerate(foundPFields):
            if(eachP and eachP.string):
                #print "[",i,"]=",eachP.string;
                pTitleStr = eachP.string;
                if(pTitleStr == u"精彩阅读"):
                    # omit this and next 'p'
                    #print u"found 精彩阅读";
                    contentUni = contentUni.replace(unicode(foundPFields[i]), "");
                    contentUni = contentUni.replace(unicode(foundPFields[i + 1]), "");
        #print "post readEliteP: len(contentUni)=\t",len(contentUni);
        #logging.debug("after readEliteP: contentUni=%s", contentUni);
        
        #print "prev readMoreP: len(contentUni)=\t",len(contentUni);
        # #<p><font style="BACKGROUND-COLOR: #ffffff" color="#666666">更多阅读</font></p><p>.../p>
        # #readMoreP = ur'<p>(<font[^<^>]+?>)?更多阅读(</font>)?</p>\s*?<p>[^<^>]+?</p>';
        # readMoreP = ur'<p><font style="BACKGROUND-COLOR: #ffffff" color="#666666">更多阅读</font></p>.*?<p>[^<^>]+?</p>';
        # contentUni = re.sub(readMoreP, "", contentUni, flags=(re.I | re.S)); # can work
        foundPFields = foundContent.findAll("p");
        for i, eachP in enumerate(foundPFields):
            if(eachP and eachP.font and eachP.font.string):
                #print "[",i,"]=",eachP.font.string;
                pTitleStr = eachP.font.string;
                if(pTitleStr == u"更多阅读"):
                    # omit this and next 'p'
                    #print u"found 更多阅读";
                    contentUni = contentUni.replace(unicode(foundPFields[i]), "");
                    contentUni = contentUni.replace(unicode(foundPFields[i + 1]), "");
        #print "post readMoreP: len(contentUni)=\t",len(contentUni);
        logging.debug("after readMoreP: contentUni=%s", contentUni);
        
        # some post:
        # http://caochongweiyu.blog.sohu.com/206655492.html
        # no 精彩阅读 or 更多阅读:
        # <p></p> <p></p>
        # <p>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a><strong><font color="#ff33cc" size="3"> </font></strong>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a><strong><font color="#ff33cc" size="3"> <br /></font></strong>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a><strong><font color="#ff33cc" size="3">&nbsp; </font></strong>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a><strong><font color="#ff33cc" size="3"> <br /></font></strong>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a><strong><font color="#ff33cc" size="3"> </font></strong>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx<br /></font></strong></a>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a><strong><font color="#ff33cc" size="3">&nbsp; <br /></font></strong>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a><strong><font color="#ff33cc" size="3"> </font></strong>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a><strong><font color="#ff33cc" size="3">&nbsp; <br /></font></strong>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a><strong><font color="#ff33cc" size="3"> </font></strong>
        # <a href="http://www.3g2y.com/?chaochong" target="_blank"><strong><font color="#ff33cc" size="3">xxx</font></strong></a>
        # </p>
        #print "prev readMoreNoTitleP: len(contentUni)=\t",len(contentUni);
        readMoreNoTitleP = ur'<p>\s*?(<a href=".+?" target="_blank"><strong><font color="#\w+?" size="\d+?".+?(<br />)?</font></strong></a>(<strong><font color="#\w+?" size="\d+?">.+?</font></strong>)?)+?</p>';
        contentUni = re.sub(readMoreNoTitleP, "", contentUni, flags=(re.I | re.S)); # can work
        #print "post readMoreNoTitleP: len(contentUni)=\t",len(contentUni);
        #logging.debug("after readMoreNoTitleP: contentUni=%s", contentUni);
        
        # <p align="center"><font color="#000000" size="4"><strong>&darr;&darr;更多文章推荐阅读&darr;&darr;&nbsp;</strong></font></p><font color="#000000">
        # </font><p>...............</p>
        
        #<p align="center"><font color="#000000" size="4"><strong>&darr;&darr;更多文章推荐阅读&darr;&darr;&nbsp;</strong></font></p>
        #<p>.........</p>
        
        #<p align="center"><strong><font color="#000000" size="4">&darr;&darr;更多文章推荐阅读&darr;&darr;&nbsp;</font></strong></p>
        #<p>.........</p>
        
        #<p align="center"><strong><font color="#ff0000" size="4">&darr;&darr;更多文章推荐阅读&darr;&darr;&nbsp;</font></strong></p>
        #<p>.........</p>
        
        #print "prev moreArticleRecReadP: len(contentUni)=\t",len(contentUni);
        moreArticleRecReadP = ur'<p align="center">(<strong>)?<font color="#\w+" size="\d+?">(<strong>)?(&darr;&darr;)?更多文章推荐阅读(&darr;&darr;)?(&nbsp;)?(</strong>)?</font>(</strong>)?</p>(<font color="#\w+">)?\s*?(</font>)?<p>.+?</p>';
        contentUni = re.sub(moreArticleRecReadP, "", contentUni, flags=(re.I | re.S)); # can work
        #print "post moreArticleRecReadP: len(contentUni)=\t",len(contentUni);
        #logging.debug("after moreArticleRecReadP: contentUni=%s", contentUni);
        
        #<p align="left"><font color="#000000" size="2"><strong>日志延伸阅读：<br />.............</font></p>
        #<p><font color="#000000" size="2"><strong>日志延伸阅读：<br />....................</font></p>
        #print "prev blogExtReadP: len(contentUni)=\t",len(contentUni);
        blogExtReadP = ur'<p( align="left")?><font color="#\w+" size="\d+">(<strong>)?日志延伸阅读：.+?</p>';
        contentUni = re.sub(blogExtReadP, "", contentUni, flags=(re.I | re.S)); # can work
        #print "post blogExtReadP: len(contentUni)=\t",len(contentUni);
        #logging.debug("after blogExtReadP: contentUni=%s", contentUni);
        
        #(1) remove 体验新版博客
        #<div style="_width:92px;margin-top: 15px;float: right; height: 23px; border: #dfac63 1px solid; -webkit-border-radius: 4px; -moz-border-radius: 4px; border-radius: 4px;">
        #<a style="line-height: 22px; height: 22px; padding: 0 8px; text-align: center; color: #000; display: block; border: #fdf7dd 1px solid; background: #f8e888; border-bottom: 0; -webkit-border-radius: 4px; -moz-border-radius: 4px; border-radius: 4px; text-decoration: none;" href="http://caochongweiyu.i.sohu.com/blog/view/206655492.htm" target="_blank">体验新版博客</a>
        #</div>
        #print "prev newBlogP: len(contentUni)=\t\t",len(contentUni);
        
        tryNewBlogDivAStr = "";
        foundAllDiv = foundContent.findAll("div");
        for i, eachDiv in enumerate(foundAllDiv):
            if(eachDiv and eachDiv.a and eachDiv.a.string):
                #print "[",i,"]=",eachDiv.a.string;
                divAStr = eachDiv.a.string;
                if(divAStr == u"体验新版博客"):
                    # omit this and next 'p'
                    #print u"found 体验新版博客";
                    tryNewBlogDivAStr = unicode(foundAllDiv[i]);
                    #print "tryNewBlogDivAStr=",tryNewBlogDivAStr;
                    contentUni = contentUni.replace(tryNewBlogDivAStr, "");
        
        #newBlogP = ur'<div style="[^<^>]+?">\s*?<a style="[^<^>]+?">体验新版博客</a>.*?</div>';
        #contentUni = re.sub(newBlogP, "", contentUni, flags=(re.I | re.S)); # can work
        #print "post newBlogP: len(contentUni)=\t\t",len(contentUni);
        #logging.debug("after newBlogP: contentUni=%s", contentUni);
        
        #(2) remove 分享到搜狐微博
        # <div class="shareToTblog" style="float:right;margin-top: 10px;"><a onmousedown="CA.q('blog_entryview_share_bottomright');" href="javascript:void(0);" entrytitle="蒋介石老照片" data-sharetype="31" data-title="#{@entryTitle}" data-url="http://caochongweiyu.blog.sohu.com/206655492.html" data-abstracts="#{#main-content@innerText&lt;51}"><51}" data-ext="{v:'1',xpt:'#{$_xpt}'}"id="shareMenuButton1" onclick="shareTo('mini')">分享到搜狐微博</a>
        # </div>
        #print "prev shareBlogP: len(contentUni)=\t",len(contentUni);
        foundShareToTBlog = foundContent.find("div", attrs={"class":"shareToTblog"});
        #print "foundShareToTBlog=",foundShareToTBlog;
        if(foundShareToTBlog):
            #print u"found 分享到搜狐微博";
            shareToTBlogStr = unicode(foundShareToTBlog);
            contentUni = contentUni.replace(shareToTBlogStr, "");
        # shareBlogP = ur'<div class="shareToTblog" style=".+?>分享到搜狐微博</a>.*?</div>';
        # contentUni = re.sub(shareBlogP, "", contentUni, flags=(re.I | re.S)); # can work
        #print "post shareBlogP: len(contentUni)=\t",len(contentUni);
        #logging.debug("after shareBlogP: contentUni=%s", contentUni);
        
        #(3) remove clear, 上一篇，下一篇
        # <div class="clear"></div>
        # <div class="pn_na">
        # <div class="previous">
        # <div class="previous_l"></div>
        # <div class="previous_txt">上一篇：</div>
        # <div class="previous_txt"><a onmousedown="CA.q('blog_entryview_previous');" href="http://caochongweiyu.blog.sohu.com/206661995.html"> 50年代流行的沙滩美女写真照</a> </div>
        # </div>
        # <div class="next">
        # <div class="next_txt">下一篇：</div>
        # <div class="next_txt"><a onmousedown="CA.q('blog_entryview_next');" href="http://caochongweiyu.blog.sohu.com/206655138.html">一代歌后邓丽君(珍贵照片）之一 </a></div>
        # <div class="next_r"></div>
        # </div>
        # </div>
        # <div class="clear"></div>
        
        #print "prev prevNextP: len(contentUni)=\t",len(contentUni);
        foundPrevNext = foundContent.find(attrs={"class":"pn_na"});
        #print "foundPrevNext=",foundPrevNext;
        if(foundPrevNext):
            #print "found pn_na";
            prevNextStr = unicode(foundPrevNext);
            contentUni = contentUni.replace(prevNextStr, "");

        foundClears = foundContent.findAll(attrs={"class":"clear"});
        #print "foundClears=",foundClears;
        if(foundClears):
            #print "found clear";
            for eachClear in foundClears:
                clearStr = unicode(eachClear);
                contentUni = contentUni.replace(clearStr, ""); 
        
        # prevNextP = ur'<div class="clear"></div>.*?<div class="pn_na">.+?</div>.*?<div class="clear"></div>';
        # contentUni = re.sub(prevNextP, "", contentUni, flags=(re.I | re.S)); # can work
        #print "post prevNextP: len(contentUni)=\t",len(contentUni);
        #logging.debug("after prevNextP: contentUni=%s", contentUni);
        
        # (4) remove 我的相关日志
        # http://tyjzlcl.blog.sohu.com/197745682.html contain:
        # <div style="FONT-WEIGHT: bold">我的相关日志：</div>
        #<p><br />2011-10-18&nbsp;|&nbsp;<a title="石秀是个喜欢偷窥女性的人吗？" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/187881292.html" target="_blank">石秀是个喜欢偷窥女性的人吗？</a><br />2011-09-29&nbsp;|&nbsp;<a title="新水浒把好汉当好人来演绎" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/186086369.html" target="_blank">新水浒把好汉当好人来演绎</a><br />2011-09-05&nbsp;|&nbsp;<a title="新水浒突破原著的地方" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/183542269.html" target="_blank">新水浒突破原著的地方</a><br />2011-08-28&nbsp;|&nbsp;<a title="梁山将董平和吴三桂哪个更让人烦" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/182735925.html" target="_blank">梁山将董平和吴三桂哪个更让人烦</a><br />2011-08-26&nbsp;|&nbsp;<a title="宋朝女人爱美导致梁山起义" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/182551746.html" target="_blank">宋朝女人爱美导致梁山起义</a><br />2011-08-12&nbsp;|&nbsp;<a title="水浒原来不是水泊梁山" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/181075056.html" target="_blank">水浒原来不是水泊梁山</a><br />2011-07-21&nbsp;|&nbsp;<a title="梁山上具有女性光辉的顾大嫂是二婚" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/178964636.html" target="_blank">梁山上具有女性光辉的顾大嫂是二婚</a><br />2011-06-20&nbsp;|&nbsp;<a title="宋江的“假招安”" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/176623946.html" target="_blank">宋江的&ldquo;假招安&rdquo;</a><br />2011-06-13&nbsp;|&nbsp;<a title="经济基础决定梁山的出路只能是招安" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/176042765.html" target="_blank">经济基础决定梁山的出路只能是招安</a><br />2009-02-11&nbsp;|&nbsp;<a title="宋朝的文化繁荣把好汉逼上梁山" href="http://blog.sohu.com/people/!dHlqemxjbEBzb2h1LmNvbQ==/110020042.html" target="_blank">宋朝的文化繁荣把好汉逼上梁山</a><br /><br /></p>

        #print "post myBlogP: len(contentUni)=\t\t",len(contentUni);
        
        #myBlogP = ur'<div style="FONT-WEIGHT: bold">我的相关日志：</div>.+?(?=</div>)';
        myBlogP = ur'<div style="FONT-WEIGHT: bold">我的相关日志：</div>\s*?<p>.+?</p>';
        #contentUni = re.sub(myBlogP, "", contentUni, re.I | re.S); # not work here !!!
        #contentUni = re.sub(myBlogP, "", contentUni, 2, re.I | re.S); # can work
        #contentUni = re.sub(myBlogP, "", contentUni, 1, re.I | re.S); # can work
        contentUni = re.sub(myBlogP, "", contentUni, flags=(re.I | re.S)); # can work

        myBlogNoFontP = ur'<p><strong>我的相关日志：</strong></p>\s*?<p>.+?</p>';
        contentUni = re.sub(myBlogNoFontP, "", contentUni, flags=(re.I | re.S)); # can work

        #print "post myBlogP: len(contentUni)=\t\t",len(contentUni);
        #logging.debug("after myBlogP: contentUni=%s", contentUni);
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
        
        # <div  class="item-title revoArtlabel">
        # <span class="revoLeft">标签：
         # <a href="http://tag.blog.sohu.com/%C1%BA%C9%BD/" target="_blank">梁山</a>&nbsp;
         # <a href="http://tag.blog.sohu.com/%D0%EC%C4%FE/" target="_blank">徐宁</a>&nbsp;
         # <a href="http://tag.blog.sohu.com/%C1%D6%B3%E5/" target="_blank">林冲</a>&nbsp;
         # <a href="http://tag.blog.sohu.com/%C7%C0%BD%D9/" target="_blank">抢劫</a>&nbsp;
         # <a href="http://tag.blog.sohu.com/%CB%CE%BD%AD/" target="_blank">宋江</a>&nbsp;
        # </span>
        # <span class="revoLeft">分类：
        # <a href="http://tyjzlcl.blog.sohu.com/entry/7076377/">水浒研究</a>
        # </span>
        # <span class="revoRight">2011-12-10 15:47</span>
        # </div>
        soup = getSoupFromUrl(url);
        foundCategory = soup.find(attrs={"class":"item-title revoArtlabel"});
        #print "foundCategory=",foundCategory;
        foundRevoLeft = foundCategory.findAll(attrs={"class":"revoLeft"});
        #print "foundRevoLeft=",foundRevoLeft;
        if(foundRevoLeft):
            for eachRevoLeft in foundRevoLeft:
                #print "eachRevoLeft=",eachRevoLeft;
                revoStr = unicode(eachRevoLeft);
                #print "revoStr=",revoStr;
                if(revoStr.find(u"分类：") > 0):
                    catStr = eachRevoLeft.a.string;
                    #print "catStr=",catStr;
                    catUni = unicode(catStr);
                    #print "catUni=",catUni;
                    break;
    except :
        catUni = "";

    return catUni;

#------------------------------------------------------------------------------
# extract tags info
def extractTags(url, html) :
    tagList = [];
    try :
        #logging.debug("extractTags_html=\n%s", html);

        # <div  class="item-title revoArtlabel">
        # <span class="revoLeft">标签：
         # <a href="http://tag.blog.sohu.com/%C1%BA%C9%BD/" target="_blank">梁山</a>&nbsp;
         # <a href="http://tag.blog.sohu.com/%D0%EC%C4%FE/" target="_blank">徐宁</a>&nbsp;
         # <a href="http://tag.blog.sohu.com/%C1%D6%B3%E5/" target="_blank">林冲</a>&nbsp;
         # <a href="http://tag.blog.sohu.com/%C7%C0%BD%D9/" target="_blank">抢劫</a>&nbsp;
         # <a href="http://tag.blog.sohu.com/%CB%CE%BD%AD/" target="_blank">宋江</a>&nbsp;
        # </span>
        # <span class="revoLeft">分类：
        # <a href="http://tyjzlcl.blog.sohu.com/entry/7076377/">水浒研究</a>
        # </span>
        # <span class="revoRight">2011-12-10 15:47</span>
        # </div>
        soup = getSoupFromUrl(url);
        foundTags = soup.find(attrs={"class":"item-title revoArtlabel"});
        #print "foundTags=",foundTags;
        foundRevoLeft = foundTags.findAll(attrs={"class":"revoLeft"});
        #print "foundRevoLeft=",foundRevoLeft;
        if(foundRevoLeft):
            for eachRevoLeft in foundRevoLeft:
                #print "eachRevoLeft=",eachRevoLeft;
                revoStr = unicode(eachRevoLeft);
                #print "revoStr=",revoStr;
                if(revoStr.find(u"标签：") > 0):
                    aList = eachRevoLeft.findAll("a");
                    #print "aList=",aList;
                    if(aList):
                        for eachA in aList:
                            singleTagStr = eachA.string;
                            #print "singleTagStr=",singleTagStr;
                            if(singleTagStr):
                                tagList.append(singleTagStr);
                    break;
    except :
        logging.debug("Fail to extract tags from url=%s, html=\n%s", url, html);
        tagList = [];

    return tagList;
    
#------------------------------------------------------------------------------
# extract post id from perma link
# 206655492 from http://caochongweiyu.blog.sohu.com/206655492.html
def extractPostId(url):
    postId = "";
    found = re.search("http://\w+\.blog\.sohu\.com/(?P<postId>\d+).html", url);
    if(found):
        postId = found.group("postId");
    return postId;
    
#------------------------------------------------------------------------------
# remove jsonp pref and suf, retain json string
def removeJsonp(jsonpStr):
    jsonStr = "";
    #
    # jsonp1334653968(
    #
    #{xxx}
    #
    #)		
    foundJsonp = re.search("\s*jsonp\d+\(\s*(?P<jsonStr>\{.+?\})\s*\)\s*", jsonpStr, re.S);
    #print "foundJsonp=",foundJsonp;
    if(foundJsonp):
        jsonStr = foundJsonp.group("jsonStr");
    return jsonStr;

#------------------------------------------------------------------------------
# generate the url for get comments
def genGetCmtUrl(xpt, postId, sz, pageNum):
    ids = "blog_" + str(postId) + "_0_" + xpt;
    
    curTimestamp = crifanLib.getCurTimestamp();
    #print "curTimestamp=",curTimestamp;
    jsonp = "jsonp" + str(curTimestamp);
    #http://i.sohu.com/a/app/discuss/indexBlogList.htm?_input_encode=UTF-8&ids=blog_206655492_0_Y2FvY2hvbmd3ZWl5dUBzb2h1LmNvbQ==&page=1&sz=10&callback=jsonp1334652355775
    #http://i.sohu.com/a/app/discuss/indexBlogList.htm?_input_encode=UTF-8&ids=blog_206655492_0_Y2FvY2hvbmd3ZWl5dUBzb2h1LmNvbQ==&page=5&sz=10&callback=jsonp1334652355781
    getCmtUrl = "http://i.sohu.com/a/app/discuss/indexBlogList.htm";
    getCmtUrl += "?_input_encode=" + "UTF-8";
    getCmtUrl += "&ids=" + ids;
    getCmtUrl += "&sz=" + str(sz);
    getCmtUrl += "&page=" + str(pageNum);
    getCmtUrl += "&callback=" + jsonp;

    logging.debug("getCmtUrl=%s", getCmtUrl);
    
    return getCmtUrl;

#------------------------------------------------------------------------------
# fetch comment dict list from comment url
def fetchCmtDictList(getCmtUrl):
    (totalCmtNum, curPageCmtNum, curPageCmtList) = (0, 0, []);
    
    logging.debug("now will get comment from getCmtUrl=%s", getCmtUrl);
    respJsonpStr = crifanLib.getUrlRespHtml(getCmtUrl);
    #logging.debug("getCmtUrl=%s return json string=\n%s", getCmtUrl, respJsonpStr);

    # jsonp1334653968(
    #{"discusscount":121,"spreadcount":0,"code":0,"msg":"获取成功","discusss":[{"content":"我就觉得八荣八耻也不错呀，只是没有蒋公的耐看。","passport":"Y3BjeXNAc29odS5jb20=","id":402223676,"createtime":1331467843000,"unick":"病树前头","uavatar":"http://1851.img.pp.sohu.com.cn/images/blog/2008/12/6/20/7/11eb4c1c5a4g215.jpg","ulink":"http://cpcys.blog.sohu.com/","topassport":"Y2FvY2hvbmd3ZWl5dUBzb2h1LmNvbQ=="},...]}
    # )

    jsonStr = removeJsonp(respJsonpStr);
    #print "jsonStr=",jsonStr;
    cmtInfoDict = json.loads(jsonStr, encoding="GB18030");
    #print "cmtInfoDict=",cmtInfoDict;
    totalCmtNum = cmtInfoDict['discusscount'];
    #print "totalCmtNum=",totalCmtNum;
    
    curPageCmtList = cmtInfoDict['discusss'];
    curPageCmtNum = len(curPageCmtList);
    
    logging.debug("getCmtUrl=%s, feteced comments: totalCmtNum=%d, curPageCmtNum=%d", getCmtUrl, totalCmtNum, curPageCmtNum);
    
    return (totalCmtNum, curPageCmtNum, curPageCmtList);

#------------------------------------------------------------------------------
# parse single source comment soup into dest comment dict 
def parseSingleCmtDict(destCmtDict, srcCmtDict, cmtId):
    global gVal;
    destCmtDict['id'] = cmtId;
    #print "destCmtDict['id']=",destCmtDict['id'];
    
    logging.debug("--- comment[%d] ---", destCmtDict['id']);
    #logging.debug("srcCmtDict=%s", srcCmtDict);

    # {
        # "content": "我就觉得八荣八耻也不错呀，只是没有蒋公的耐看。",
        # "passport": "Y3BjeXNAc29odS5jb20=",
        # "id": 402223676,
        # "createtime": 1331467843000,
        # "unick": "病树前头",
        # "uavatar": "http://1851.img.pp.sohu.com.cn/images/blog/2008/12/6/20/7/11eb4c1c5a4g215.jpg",
        # "ulink": "http://cpcys.blog.sohu.com/",
        # "topassport": "Y2FvY2hvbmd3ZWl5dUBzb2h1LmNvbQ=="
    # }

    #print "srcCmtDict['unick']=",srcCmtDict['unick'];
    destCmtDict['author'] = srcCmtDict['unick'];

    #print "srcCmtDict['ulink']=",srcCmtDict['ulink'];
    destCmtDict['author_url'] = srcCmtDict['ulink'];
    
    createtimeMillisecond = srcCmtDict['createtime'];
    #print "createtimeMillisecond=",createtimeMillisecond;
    createtimeFloat = float(createtimeMillisecond)/1000;
    #print "createtimeFloat=",createtimeFloat;
    localTime = crifanLib.timestampToDatetime(createtimeFloat);
    #print "localTime=",localTime;
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    #print "gmtTime=",gmtTime;
    destCmtDict['date'] = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");
    
    destCmtDict['content'] = srcCmtDict['content'];
    #print "destCmtDict['content']=",destCmtDict['content'];

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
# fetch and parse comments 
# return the parsed dict value
def fetchAndParseComments(url, html):
    parsedCommentsList = [];
    
    try :
        #logging.debug("fetchAndParseComments_html=\n%s", html);
        
        allCmtList = [];
        # var _xpt = 'Y2FvY2hvbmd3ZWl5dUBzb2h1LmNvbQ==';
        # var _upt = 'Y2FvY2hvbmd3ZWl5dUBzb2h1LmNvbQ==';
        foundXpt = re.search(r"var _xpt = '(?P<xpt>.+?)';", html);
        #print "foundXpt=",foundXpt;
        if(foundXpt):
            xpt = foundXpt.group("xpt");
            postId = extractPostId(url);
            #sz = 10;
            sz = 100; # comment number per page, here max allow is 100 !
            pageNum = 1;
            
            getCmtUrl = genGetCmtUrl(xpt, postId, sz, pageNum);
            (totalCmtNum, curPageCmtNum, curPageCmtList) = fetchCmtDictList(getCmtUrl);
            if((totalCmtNum > 0) and (curPageCmtNum > 0)):
                allCmtList.extend(curPageCmtList);
                remainCmtNum = totalCmtNum - curPageCmtNum;
                #print "remainCmtNum=",remainCmtNum;
                if(remainCmtNum >=0):
                    # fetch comments
                    needGetMore = True;
                    while(needGetMore):
                        pageNum += 1;
                        getCmtUrl = genGetCmtUrl(xpt, postId, sz, pageNum);
                        (tmpCmtNum, curPageCmtNum, curPageCmtList) = fetchCmtDictList(getCmtUrl);
                        if(curPageCmtNum > 0):
                            allCmtList.extend(curPageCmtList);
                            remainCmtNum = remainCmtNum - curPageCmtNum;
                            logging.debug("remainCmtNum=%d", remainCmtNum);
                            if(remainCmtNum <= 0):
                                logging.debug("now has got all comments list, so break here");
                                break;
                        else:
                            break;

                parseAllCommentsList(allCmtList, parsedCommentsList);
                
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
    fd5 = picInfoDict['fields']['fd5'];
    fd6 = picInfoDict['fields']['fd6'];

    if ((fd1=='photo') and (fd2=='pic') and (fd3=='sohu') or 
        (fd2=='img') and (fd3=='pp') and (fd4=='sohu')):
        isSelfPic = True;
    else :
        isSelfPic = False;

    logging.debug("isSelfBlogPic: %s", isSelfPic);

    return isSelfPic;

#------------------------------------------------------------------------------
def getProcessPhotoCfg():
    # possible own site pic link:
    # type1:
    # http://caochongweiyu.blog.sohu.com/206655492.html contain:
    # http://photo.pic.sohu.com/images/oldblog/person/2006/4/3/1144077621770_4521.jpg
    # html ->
    #<p><font color="#cccccc"><img style="DISPLAY: block; MARGIN: 0px auto 10px; WIDTH: 398px; ZOOM: 1; HEIGHT: 522px; TEXT-ALIGN: center" height="522" alt="1144077621770_4521.jpg" src="http://photo.pic.sohu.com/images/oldblog/person/2006/4/3/1144077621770_4521.jpg" width="398" border="0"></font></p>
    
    #type2:
    # http://musangdaozhang.blog.sohu.com/206594401.html contain:
    #http://116.img.pp.sohu.com/images/blog/2007/5/24/17/27/11355c13759.jpg
    
    #type3:
    #http://caochongweiyu.blog.sohu.com/206661995.html contain:
    #http://1811.img.pp.sohu.com.cn/images/blog/2012/3/8/18/2/u264889456_136b215d149g214_blog.jpg
    
    # possible othersite pic url:
    
    
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
    #print "blogEntryUrl=",blogEntryUrl;
    
    try:
        logging.debug("blogEntryUrl=%s", blogEntryUrl);
        respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
        logging.debug("extractBlogTitAndDesc_respHtml=\n%s", respHtml);
        
        #<div id="blogDesc">生活中的经济学</div>
        #<div id="blogDesc"></div>
        foundDesc = re.search('<div id="blogDesc">(?P<description>.+?)</div>', respHtml);
        if(foundDesc):
            description = foundDesc.group("description");
            blogDescription = description.decode("GB18030", 'ignore');
            #print "blogDescription=",blogDescription;
        
        #<h1 id="blogTitle"><a href="http://maoyushi.blog.sohu.com/"  id="blogAdmin" onmousedown="CA.q('blog_header_title');">茅于轼</a></h1>
        
        #<h1 id="blogTitle"><a href="http://blog.17173.com" target="_blank"><img src="http://js1.pp.sohu.com.cn/ppp/blog/styles_ppp/images/logo17173_big.gif" alt="17173博客" align="absmiddle" /></a> <a href="http://cosbaby.blog.sohu.com/"  id="blogAdmin" onmousedown="CA.q('blog_header_title');">cosbaby</a></h1>
        
        #foundTitle = re.search('<h1\s+?id="blogTitle"><a\s+?href="[^"]+?"\s+?id="blogAdmin"\s+?onmousedown="[^"^<^>]+?">(?P<title>.+?)</a></h1>', respHtml);
        foundTitle = re.search('<h1\s+?id="blogTitle"><a\s+?href=.+?blog_header_title.\);">(?P<title>.+?)</a></h1>', respHtml);
        if(foundTitle):
            title = foundTitle.group("title");
            blogTitle = title.decode("GB18030", 'ignore');
            #print "blogTitle=",blogTitle;
    except:
        (blogTitle, blogDescription) = ("", "");

    return (blogTitle, blogDescription);

#------------------------------------------------------------------------------
# parse datetime string into (local=GMT+8) datetime value
def parseDatetimeStrToLocalTime(datetimeStr):
    # possible date format:
    # (1) 2008-05-08 18:22
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
if __name__=="BlogSohu":
    print "Imported: %s,\t%s"%( __name__, __VERSION__);