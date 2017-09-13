#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for Tianya Blog.

[TODO]

"""

import os;
import re;
import sys;
import time;
import math;
#import urllib;
#import urllib2;
from datetime import datetime,timedelta;
from BeautifulSoup import BeautifulSoup,Tag,CData;
import logging;
import crifanLib;
#import cookielib;
#from xml.sax import saxutils;
#import json; # New in version 2.6.
#import random;

#--------------------------------const values-----------------------------------
__VERSION__ = "v1.0";

gConst = {
    'spaceDomain'   : 'http://blog.tianya.cn',

    # html show GBK, actually is GB18030
    # if use "GBK" -> title will messy code
    'htmlCharset'   : "GB18030",
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',   # susu7788, from input url http://susu7788.blog.tianya.cn
    'blogId'        : '',   # 2723898
    'blogEntryUrl'  : '',   # http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898
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
# extract post id from perma link
# 41963783 from http://blog.tianya.cn/blogger/post_read.asp?BlogID=3210723&PostID=41963783
def extractPostIdFromPermaLink(url):
    postId = "";
    #http://blog.tianya.cn/blogger/post_read.asp?BlogID=3210723&PostID=41963783
    foundPostId = re.search(r"http://blog\.tianya\.cn/blogger/post_read\.asp\?BlogID=\d+&PostID=(?P<postId>\d+)/?", url);
    if(foundPostId) :
        postId = foundPostId.group("postId");
        logging.debug("postId=%s", postId);
        #postId = int(postId);
    return postId;

#------------------------------------------------------------------------------
# generate entry url from blog ID
# from 2723898 generate http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898
def genEntryUrl(blogId):
    return "http://blog.tianya.cn/blogger/blog_main.asp?BlogID=" + blogId;

#------------------------------------------------------------------------------
# generate post list url from blogId and categoryID
# 2723898,0     -> http://blog.tianya.cn/blogger/post_list.asp?BlogID=2723898&CategoryID=0
# 2723898,0,7   -> http://blog.tianya.cn/blogger/post_list.asp?BlogID=2723898&CategoryID=0&page=7
def genPostListUrl(blogId, categoryId, page=""):
    postListUrl = "";
    if(page):
        postListUrl = "http://blog.tianya.cn/blogger/post_list.asp?BlogID=" + str(blogId) + "&CategoryID=" + str(categoryId) + "&page=" + str(page);
    else:
        postListUrl = "http://blog.tianya.cn/blogger/post_list.asp?BlogID=" + str(blogId) + "&CategoryID=" + str(categoryId);
    return postListUrl;

#------------------------------------------------------------------------------
# generate post read url from blogId, postId, page
# 3210723,41963783,2    ->  http://blog.tianya.cn/blogger/post_read.asp?BlogID=3210723&PostID=41963783&page=2
def genPostReadUrl(blogId, postId, page=""):
    postReadUrl = "";
    if(page):
        #http://blog.tianya.cn/blogger/post_read.asp?BlogID=3210723&PostID=41963783&page=2
        postReadUrl = "http://blog.tianya.cn/blogger/post_read.asp?BlogID=" + str(blogId) + "&PostID=" + str(postId) + "&page=" + str(page);
    else:
        postReadUrl = "http://blog.tianya.cn/blogger/post_read.asp?BlogID=" + str(blogId) + "&PostID=" + str(postId);
    return postReadUrl;

#------------------------------------------------------------------------------
# extract blogUser from blog ID
# susu7788 from 2723898
def extractBlogUserFromBlogId(blogId):
    blogUser = "";
    
    #http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898
    blogEntryUrl = genEntryUrl(str(blogId));
    
    #extract blogUser
    #<div class="blog-header-rul"><a href="http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898">http://susu7788.blog.tianya.cn</a> <a href="rss.asp?BlogID=2723898" target="_blank">[RSS订阅]</a></div>
    respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
    foundBlogHeaderRurl = re.search('<div\s+class="blog-header-rul"><a\s+href="http://blog\.tianya\.cn/blogger/blog_main\.asp\?BlogID=' + blogId + '">http://(?P<blogUser>\w+).blog.tianya.cn</a>', respHtml);
    logging.debug("foundBlogHeaderRurl=%s", foundBlogHeaderRurl);
    if(foundBlogHeaderRurl):
        blogUser = foundBlogHeaderRurl.group("blogUser");
        logging.debug("Extracted blog user %s from entry url %s", blogUser, blogEntryUrl);
    else:
        blogUser = "";
    return blogUser;
    
################################################################################
# Implemented Common Functions 
################################################################################

#------------------------------------------------------------------------------
# extract blog user name:
# (1) susu7788 from: 
# http://susu7788.blog.tianya.cn
# http://susu7788.blog.tianya.cn/
# (2) susu7788 (blog id is 2723898) from:
# http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898
# http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898/
# (3) susu7788 from permanent link:
# http://blog.tianya.cn/blogger/post_read.asp?BlogID=2723898&PostID=23024897
# http://blog.tianya.cn/blogger/post_read.asp?BlogID=2723898&PostID=23024897/
def extractBlogUser(inputUrl):
    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
    logging.debug("Extracting blog user from url=%s", inputUrl);
    
    blogId = "";
    
    try :
        #http://blog.tianya.cn/blogger/post_show.asp?idWriter=0&Key=0&BlogID=71314&PostID=47683615
        #currentNotSupportBlogUrl = "http://blog.tianya.cn/blogger/post_show.asp?BlogID=71314&PostID=47745859";
        oldStyleTianyaBlogExample = "http://ufowm.blog.tianya.cn/";
        logging.info("Note: currently not support old style of tianya blog, such as: %s", oldStyleTianyaBlogExample);

        # type1, main url with blogUser: 
        # http://susu7788.blog.tianya.cn
        # http://susu7788.blog.tianya.cn/
        foundMainUrl = re.search("http://(?P<blogUser>\w+)\.blog\.tianya\.cn/?", inputUrl);
        logging.debug("foundMainUrl=%s", foundMainUrl);
        if(foundMainUrl) :
            extractedBlogUser = foundMainUrl.group("blogUser");
            resp = crifanLib.getUrlResponse(inputUrl);
            realUrl = resp.geturl();
            logging.debug("realUrl=%s", realUrl);
            generatedBlogEntryUrl = realUrl;
            foundBlogIdMainUrl = re.search("http://blog\.tianya\.cn/blogger/blog_main\.asp\?BlogID=(?P<blogId>\d+)/?", generatedBlogEntryUrl);
            logging.debug("foundBlogIdMainUrl=%s", foundBlogIdMainUrl);
            if(foundBlogIdMainUrl):
                blogId = foundBlogIdMainUrl.group("blogId");
                extractOk = True;
            else:
                (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
        
        # type2, main url with blogId, perma link:
        # http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898
        # http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898/
        if(not extractOk):
            foundMainUrlWithBlogId = re.search("(?P<blogIdMainUrl>http://blog\.tianya\.cn/blogger/blog_main\.asp\?BlogID=(?P<blogId>\d+))/?", inputUrl);
            logging.debug("foundMainUrlWithBlogId=%s", foundMainUrlWithBlogId);
            if(foundMainUrlWithBlogId) :
                blogId = foundMainUrlWithBlogId.group("blogId");
                generatedBlogEntryUrl = genEntryUrl(blogId);
                extractedBlogUser = extractBlogUserFromBlogId(blogId);
                if(extractedBlogUser):
                    extractOk = True;
                    
        # type3, perma link:
        # http://blog.tianya.cn/blogger/post_read.asp?BlogID=2723898&PostID=23024897
        # http://blog.tianya.cn/blogger/post_read.asp?BlogID=2723898&PostID=23024897/
        if(not extractOk):
            # note, if input:
            # BlogsToWordpress.py -f http://blog.tianya.cn/blogger/post_read.asp?BlogID=2723898&PostID=23024897
            # in windows cmd, actually only got:
            # BlogsToWordpress.py -f http://blog.tianya.cn/blogger/post_read.asp?BlogID=2723898
            # you need do like this:
            # BlogsToWordpress.py -f http://blog.tianya.cn/blogger/post_read.asp?BlogID=2723898^&PostID=23024897
            # then you can get the normal parameter:
            # -f == http://blog.tianya.cn/blogger/post_read.asp?BlogID=2723898&PostID=23024897
            foundPermaLink = re.search("http://blog\.tianya\.cn/blogger/post_read\.asp\?BlogID=(?P<blogId>\d+)&PostID=(?P<postId>\d+)/?", inputUrl);
            logging.debug("foundPermaLink=%s", foundPermaLink);
            if(foundPermaLink):
                postId = foundPermaLink.group("postId");
                blogId = foundPermaLink.group("blogId");
                generatedBlogEntryUrl = genEntryUrl(blogId);
                extractedBlogUser = extractBlogUserFromBlogId(blogId);
                if(extractedBlogUser):
                    extractOk = True;
    except :
        (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
        
    if (extractOk) :
        gVal['blogUser']    = extractedBlogUser;
        gVal['blogId']      = blogId;
        gVal['blogEntryUrl']= generatedBlogEntryUrl;
    
    logging.debug("extractOk=%s, gVal['blogId']=%s, gVal['blogUser']=%s, gVal['blogEntryUrl']=%s", extractOk, gVal['blogId'], gVal['blogUser'], gVal['blogEntryUrl']);

    return (extractOk, extractedBlogUser, generatedBlogEntryUrl);

#------------------------------------------------------------------------------
# find the first permanent link = url of the earliset published blog item
def find1stPermalink():
    (isFound, retInfo) = (False, "Unknown error!");
    
    try:
        #http://blog.tianya.cn/blogger/post_list.asp?BlogID=2723898&CategoryID=0
        allPostCategoryId = 0;
        allCategoryUrl = genPostListUrl(gVal['blogId'], allPostCategoryId);
        
        respHtml = crifanLib.getUrlRespHtml(allCategoryUrl);
        logging.debug("allCategoryUrl=%s resp respHtml=%s", allCategoryUrl, respHtml);
        # <div class="pages pos-relative">
        # 页码：1/7 << <a href="/blogger/post_list.asp?BlogID=2723898&CategoryID=0&page=1" class="here">1</a> <a href="/blogger/post_list.asp?BlogID=2723898&CategoryID=0&page=2" class="">2</a> <a href="/blogger/post_list.asp?BlogID=2723898&CategoryID=0&page=3" class="">3</a> <a href="/blogger/post_list.asp?BlogID=2723898&CategoryID=0&page=4" class="">4</a> <a href="/blogger/post_list.asp?BlogID=2723898&CategoryID=0&page=5" class="">5</a> <a href="/blogger/post_list.asp?BlogID=2723898&CategoryID=0&page=6" title=下5页>></a> <a href="/blogger/post_list.asp?BlogID=2723898&CategoryID=0&page=7" title=尾页>>></a> 
            # <span class="pos-right gototop"><a href="#">返回顶部</a></span>
        # </div>
        #foundPagesPos = re.search('<div\s+class="pages pos-relative">.+?1/(?P<totalPageNum>\d+)', respHtml, re.S);
        #foundPagesPos = re.search('<div\s+class="pages pos-relative">\s+...1/(?P<totalPageNum>\d+)', respHtml);
        foundPagesPos = re.search('<div\s+class="pages pos-relative">\s+(?P<yemaStr>.+)1/(?P<totalPageNum>\d+)', respHtml);
        foundPagesPos = re.search('<div\s+class="pages pos-relative">\s+.+1/(?P<totalPageNum>\d+)', respHtml);
        logging.debug("foundPagesPos=%s", foundPagesPos);
        if(foundPagesPos):
            #yemaStr = foundPagesPos.group("yemaStr");
            #logging.info("yemaStr=%s", yemaStr);
            totalPageNum = foundPagesPos.group("totalPageNum");
            logging.debug("totalPageNum=%s", totalPageNum);
            totalPageNumInt = int(totalPageNum);
            if(totalPageNumInt == 1):
                lastPageHtml = respHtml;
            else:
                #http://blog.tianya.cn/blogger/post_list.asp?BlogID=2723898&CategoryID=0&page=7
                lastPageUrl = genPostListUrl(gVal['blogId'], 0, totalPageNumInt);
                logging.debug("lastPageUrl=%s", lastPageUrl);
                lastPageHtml = crifanLib.getUrlRespHtml(lastPageUrl);
                
                # special:
                #http://blog.tianya.cn/blogger/post_list.asp?BlogID=4338249&CategoryID=0&page=26
                # contain no post, so here calc prev page
                lastButOneInt = totalPageNumInt - 1;
                lastButOnePageUrl = genPostListUrl(gVal['blogId'], 0, lastButOneInt);
                logging.debug("lastButOnePageUrl=%s", lastButOnePageUrl);
                lastButOnePageHtml = crifanLib.getUrlRespHtml(lastButOnePageUrl);
        #<li class="articlecell cf"><p class="ptit"><a href="/blogger/post_read.asp?BlogID=2723898&PostID=47717072" target="_blank">再见过去，我们的足迹</a></p><p class="ptime">2012-10-27 08:13</p><p class="pcomments">3</p></li>
        soup = htmlToSoup(lastPageHtml);
        foundArticleCellCf = soup.findAll(attrs={"class":"articlecell cf"});
        if(not foundArticleCellCf):
            # for special:
            #http://blog.tianya.cn/blogger/post_list.asp?BlogID=4338249&CategoryID=0&page=26
            soup = htmlToSoup(lastButOnePageHtml);
            foundArticleCellCf = soup.findAll(attrs={"class":"articlecell cf"});
        logging.debug("foundArticleCellCf=%s", foundArticleCellCf);
        articleCellCfLen = len(foundArticleCellCf);
        logging.debug("articleCellCfLen=%s", articleCellCfLen);
        lastPostSoup = foundArticleCellCf[-1];
        logging.debug("lastPostSoup=%s", lastPostSoup);
        logging.debug("lastPostSoup.contents=%s", lastPostSoup.contents);
        #p0 = lastPostSoup.p[0];
        p0 = lastPostSoup.contents[0];
        logging.debug("p0=%s", p0);
        p0a = p0.a;
        logging.debug("p0a=%s", p0a);
        href = p0a['href'];
        logging.debug("href=%s", href);
        lastPostUrl = gConst['spaceDomain'] + href;
        logging.debug("lastPostUrl=%s", lastPostUrl);
        if(lastPostUrl):
            retInfo = lastPostUrl;
            isFound = True;
    except:
        (isFound, retInfo) = (False, "Unknown error!");
    
    return (isFound, retInfo);

#------------------------------------------------------------------------------
# extract blog title and description
def extractBlogTitAndDesc(blogEntryUrl) :
    (blogTitle, blogDescription) = ("", "");

    try:
        logging.debug("Now extract blog title and description from blogEntryUrl=%s", blogEntryUrl);
        respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
        #logging.debug("url=%s return html=\n%s", blogEntryUrl, respHtml);
        
        # <div class="headerinner">
            # <h1><a href="http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898">素颜素语</a><img src="/images/mb2.gif" style="margin-left:15px" align="absmiddle"></h1>
            # <div class="blog-header-rul"><a href="http://blog.tianya.cn/blogger/blog_main.asp?BlogID=2723898">http://susu7788.blog.tianya.cn</a> <a href="rss.asp?BlogID=2723898" target="_blank">[RSS订阅]</a></div>
            # <div class="blogsign">真诚待人，用心写文。</div>
        # </div>

        soup = htmlToSoup(respHtml);

        foundHeaderInner = soup.find(attrs={"class":"headerinner"});
        logging.debug("foundHeaderInner=%s", foundHeaderInner);
        h1 = foundHeaderInner.h1;
        h1a = h1.a;
        logging.debug("h1a=%s", h1a);
        h1aStr = h1a.string;
        logging.debug("h1aStr=%s", h1aStr);
        blogTitle = h1aStr;
        logging.debug("blogTitle=%s", blogTitle);
        
        foundBlogsign = foundHeaderInner.find(attrs={"class":"blogsign"});
        logging.debug("foundBlogsign=%s", foundBlogsign);
        blogDescription = foundBlogsign.string;
        logging.debug("blogDescription=%s", blogDescription);
    except:
        (blogTitle, blogDescription) = ("", "");
    
    return (blogTitle, blogDescription);

#------------------------------------------------------------------------------
# extract title
def extractTitle(url, html):
    (needOmit, titleUni) = (False, "");

    try :
        logging.debug("in extractTitle, url=%s", url);
        
        # <div class="article">
            # <h2><a href="/blogger/post_read.asp?BlogID=2723898&PostID=23024897" class="">兄弟，再见</a></h2>
        
        #http://blog.tianya.cn/blogger/post_read.asp?BlogID=231650&PostID=2929614
        # <div class="article">
            # <h2><a href="/blogger/post_read.asp?BlogID=231650&PostID=2929614" class="">能让爱远离我吗<b></b><big></big></a></h2>

        soup = getSoupFromUrl(url);
        foundArticle = soup.find(attrs={"class":"article"});
        #logging.debug("foundArticle=%s", foundArticle);
        h2 = foundArticle.h2;
        #logging.debug("h2=%s", h2);
        h2a = h2.a;
        #logging.debug("h2a=%s", h2a);
        h2aContents = h2a.contents;
        #logging.debug("h2aContents=%s", h2aContents);
        h2aContents0Str = h2aContents[0].string;
        #logging.debug("h2aContents0Str=%s", h2aContents0Str);
        
        #h2aStr = h2a.string;
        #logging.debug("h2aStr=%s", h2aStr);
        #titleUni = h2aStr;
        
        titleUni = h2aContents0Str;
        logging.debug("titleUni=%s", titleUni);
    except : 
        logging.debug("Fail to extract tiltle from url=%s, html=\n%s", url, html);
        (needOmit, titleUni) = (False, "");
    
    return (needOmit, titleUni);

#------------------------------------------------------------------------------
# find next permanent link of current post
def findNextPermaLink(url, html) :
    nextLinkStr = '';
    nextPostTitle = "";

    try :
        # <div class="prearticle">上一篇：<a href="/blogger/post_read.asp?BlogID=2723898&PostID=23078527">初识</a></div>
        # <div class="nextarticle"></div>

        # <div class="prearticle">上一篇：<a href="/blogger/post_read.asp?BlogID=4493710&PostID=47715394">那些年，我们追的女孩：都做妈妈了</a></div>
        # <div class="nextarticle">下一篇：<a href="/blogger/post_read.asp?BlogID=4493710&PostID=47363021">弱肉强食：道德的缺失是价值观的扭曲</a></div>
        
        # <div class="prearticle"></div>
        # <div class="nextarticle">下一篇：<a href="/blogger/post_read.asp?BlogID=4493710&PostID=47493241">生存压力：喝咖啡和吃红薯的都难过</a></div>
        
        soup = getSoupFromUrl(url);
        foundPrearticle = soup.find(attrs={"class":"prearticle"});
        logging.debug("foundPrearticle=%s", foundPrearticle);
        #if(foundPrearticle.string):
        preArticleA = foundPrearticle.a;
        logging.debug("preArticleA=%s", preArticleA);
        if(preArticleA):
            aHref = preArticleA['href'];
            logging.debug("aHref=%s", aHref);
            nextLinkStr = gConst['spaceDomain'] + aHref;

            nextPostTitle = preArticleA.string;
        
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
        #<span class="pos-right gray6">2010-04-11 22:00 星期日 晴</span>
        soup = getSoupFromUrl(url);
        foundPostRightGray6 = soup.find(attrs={"class":"pos-right gray6"});
        if(foundPostRightGray6):
            wholeDatetimeStr = foundPostRightGray6.string;
            logging.debug("wholeDatetimeStr=%s", wholeDatetimeStr);
            foundDatatimePart = re.search("(?P<datetimeOnlyStr>\d{4}-\d{2}-\d{2} \d{2}:\d{2})", wholeDatetimeStr);
            logging.debug("foundDatatimePart=%s", foundDatatimePart);
            if(foundDatatimePart):
                datetimeOnlyStr = foundDatatimePart.group("datetimeOnlyStr");
                datetimeStr = datetimeOnlyStr;
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
        #<div class="article-summary articletext">...</div>
        soup = getSoupFromUrl(url);
        foundContent = soup.find(attrs={"class":"article-summary articletext"});
        #logging.debug("---soup foundContent:\n%s", foundContent);

        #method 1
        mappedContents = map(CData, foundContent.contents);
        #print "type(mappedContents)=",type(mappedContents); #type(mappedContents)= <type 'list'>
        contentUni = ''.join(mappedContents);
        logging.debug("type(contentUni)=%s", type(contentUni));
        #logging.info("contentUni=%s", contentUni);
    except :
        logging.debug("Fail to extract post content from url=%s, html=\n%s", url, html);
        contentUni = '';

    return contentUni;

#------------------------------------------------------------------------------
# extract category
def extractCategory(url, html) :
    catUni = '';
    try :
        #<div class="article-categories pos-relative">分类：<span class="gray6"><a href="/blogger/post_list.asp?BlogID=309977&CategoryID=" target="_blank">未分类</a></span>
        #<div class="article-categories pos-relative">分类：<span class="gray6"><a href="/blogger/post_list.asp?BlogID=2723898&CategoryID=1546431" target="_blank">【那时光】</a></span>
        foundCategory = re.search('<div class="article-categories pos-relative">.+?<span class="gray6"><a href="/blogger/post_list\.asp\?BlogID=\d+&CategoryID=(?P<categoryId>\d*)" target="_blank">(?P<categoryName>.+?)</a></span>', html);
        logging.debug("foundCategory=%s", foundCategory);
        categoryId = foundCategory.group("categoryId");
        categoryName = foundCategory.group("categoryName");
        logging.debug("categoryId=%s, categoryName=%s", categoryId, categoryName);
        categoryNameUni = categoryName.decode(gConst['htmlCharset']);
        logging.debug("categoryNameUni=%s", categoryNameUni);
        catUni = categoryNameUni;
    except :
        catUni = "";

    return catUni;

#------------------------------------------------------------------------------
# extract tags info
def extractTags(url, html) :
    tagList = [];
    try :
        #<div class="article-tag pos-relative cf">作者:<a href="http://blog.tianya.cn/myblog/blog.asp?UserID=34481178" target="_blank">素素素素素素素素</a>&nbsp;&nbsp; 标签：<a href="http://blog.tianya.cn/blogger/Search_KeyWord.asp?KeyWord=生活&condition=3" target="_blank">生活</a><span class="pos-right gray6">
        #<div class="article-tag pos-relative cf">作者:<a href="http://blog.tianya.cn/myblog/blog.asp?UserID=5911663" target="_blank">crifan</a>&nbsp;&nbsp; <span class="pos-right gray6">
        soup = getSoupFromUrl(url);
        foundArticleTag = soup.find(attrs={"class":"article-tag pos-relative cf"});
        logging.debug("foundArticleTag=%s", foundArticleTag);
        foundArticleTagUni = unicode(foundArticleTag);
        logging.debug("foundArticleTagUni=%s", foundArticleTagUni);
        foundTagsStr = re.search(u'标签：(?P<tagsStr>.+?)<span class="pos-right gray6">', foundArticleTagUni);
        logging.debug("foundTagsStr=%s", foundTagsStr);
        if(foundTagsStr):
            tagsStr = foundTagsStr.group("tagsStr");
            logging.debug("tagsStr=%s", tagsStr);
            #<a href="http://blog.tianya.cn/blogger/Search_KeyWord.asp?KeyWord=生活&amp;condition=3" target="_blank">生活</a>
            foundAllTag = re.findall('<a href="http://blog\.tianya\.cn/blogger/Search_KeyWord\.asp\?KeyWord=.+?" target="_blank">.+?</a>', tagsStr);
            logging.debug("foundAllTag=%s", foundAllTag);
            if(foundAllTag):
                for eachTagString in foundAllTag:
                    logging.debug("eachTagString=%s", eachTagString);
                    foundTagUni = re.search('<a href="http://blog\.tianya\.cn/blogger/Search_KeyWord\.asp\?KeyWord=.+?" target="_blank">(?P<tagUni>.+?)</a>', eachTagString);
                    logging.debug("foundTagUni=%s", foundTagUni);
                    if(foundTagUni):
                        tagUni = foundTagUni.group("tagUni");
                        logging.debug("tagUni=%s", tagUni);
                        tagList.append(tagUni);
    except :
        logging.debug("Fail to extract tags from url=%s, html=\n%s", url, html);
        tagList = [];
    
    return tagList;

#------------------------------------------------------------------------------
# parse single src comment dict into dest comment dict
def parseCmtDict(destCmtDict, srcCmtDict, cmtId):
    global gVal;
    
    destCmtDict['id'] = cmtId;
    #print "destCmtDict['id']=",destCmtDict['id'];
    
    logging.debug("--- comment[%d] ---", destCmtDict['id']);
    logging.debug("srcCmtDict=%s", srcCmtDict);
    
    # singleCmtCellDict = {
        # 'userUrl'   : "",
        # 'username'  : "",
        # 'time'      : "",
        # 'content'   : "",
    # };
    
    destCmtDict['author'] = srcCmtDict['username'];
    #print "destCmtDict['author']=",destCmtDict['author'];
    destCmtDict['author_url'] = srcCmtDict['userUrl'];
    #print "destCmtDict['author_url']=",destCmtDict['author_url'];
    
    #2012-05-15 11:03
    localTime = datetime.strptime(srcCmtDict['time'], "%Y-%m-%d %H:%M");
    #print "localTime=",localTime;
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    #print "gmtTime=",gmtTime;
    destCmtDict['date']     = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");

    destCmtDict['content'] = srcCmtDict['content'];
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
    
    #print "fill comments %4d OK"%(destCmtDict['id']);

    return ;
    
#------------------------------------------------------------------------------
# parse source all comment dict list into dest comment dict list
def parseAllCommentsList(allCmtDictList, parsedCommentsList):
    cmtListLen = len(allCmtDictList);
    logging.debug("Now to parse total %d comment dict list", cmtListLen);
    
    for cmtIdx, srcCmtDict in enumerate(allCmtDictList):
        destCmtDict = {};
        cmtId = cmtIdx + 1;
        parseCmtDict(destCmtDict, srcCmtDict, cmtId);
        parsedCommentsList.append(destCmtDict);

    logging.debug("after parse, got %d comments", len(parsedCommentsList));
    return;

#------------------------------------------------------------------------------
# extract comment cell dict list from html
def extractCmtCellDictList(html):
    extractedCmtCellDictList = [];
    
    parseAllOk = True;

    soup = htmlToSoup(html);

    # <div class="articlecomments-list">
        # <div class="tit pos-relative" id="allcomments"><strong>网友评论:</strong><span class="pos-right"><a href="#postcomments">我要评论</a></span></div>
        # <div class="articlecomments-cell"><div class="pos-relative comments-infor"><a href="http://blog.tianya.cn/myblog/blog.asp?UserID=13892197" target="_blank">静水流深1015</a><span class="gray6 pos-right">2010-04-11 22:11</span></div><div class="comments-content">沙发顶一个~！素素，晚安~！</div></div><div class="articlecomments-cell"><div class="pos-relative comments-infor"><a href="http://blog.tianya.cn/myblog/blog.asp?UserID=23322396" target="_blank">香圣</a><span class="gray6 pos-right">2010-04-11 22:24</span></div><div class="comments-content">板凳顶一个~！素素，晚安~！</div></div>
    # </div>
        
    foundAllCmtCell = soup.findAll(attrs={"class":"articlecomments-cell"});
    logging.debug("foundAllCmtCell=%s", foundAllCmtCell);
    allCmtLen = len(foundAllCmtCell);
    logging.debug("allCmtLen=%s", allCmtLen);
    for eachCmtCellSoup in foundAllCmtCell:
        singleCmtCellDict = {
            'userUrl'       : "",
            'username'  : "",
            'time'      : "",
            'content'   : "",
        };

        # <div class="articlecomments-cell">
            # <div class="pos-relative comments-infor">
                # <a href="http://blog.tianya.cn/myblog/blog.asp?UserID=8276759" target="_blank">官窑次品</a>
                # <span class="gray6 pos-right">2012-05-14 10:27</span>
            # </div>
            # <div class="comments-content">顶是必须要顶的</div>
        # </div>
        
        #<div class="articlecomments-cell"><div class="pos-relative comments-infor"><a href="http://blog.tianya.cn/myblog/blog.asp?UserID=8276759" target="_blank">官窑次品</a><span class="gray6 pos-right">2012-05-14 10:27</span></div><div class="comments-content">顶是必须要顶的</div></div>
        
        #<div class="articlecomments-cell"><div class="pos-relative comments-infor"><a href="http://byeryiyuankq.blog.tianya.cn/" target="_blank">不知名的名字</a><span class="gray6 pos-right">2012-10-12 14:37</span></div><div class="comments-content">中国现在的贪官是历代中国和平年代里最腐败最无耻的</div></div>
        
        foundCmtInfo = eachCmtCellSoup.find(attrs={"class":"pos-relative comments-infor"});
        #logging.debug("foundCmtInfo=%s", foundCmtInfo);
        if(foundCmtInfo):
            singleCmtCellDict['userUrl'] = foundCmtInfo.a['href'];
            #logging.debug("singleCmtCellDict['userUrl']=%s", singleCmtCellDict['userUrl']);
            singleCmtCellDict['username'] = foundCmtInfo.a.string;
            logging.debug("singleCmtCellDict['username']=%s", singleCmtCellDict['username']);
            singleCmtCellDict['time'] = foundCmtInfo.span.string;
            #logging.debug("singleCmtCellDict['time']=%s", singleCmtCellDict['time']);
            
            foundCmtContent = eachCmtCellSoup.find(attrs={"class":"comments-content"});
            #logging.debug("foundCmtContent=%s", foundCmtContent);
            if(foundCmtContent):
                singleCmtCellDict['content'] = crifanLib.soupContentsToUnicode(foundCmtContent);
                #logging.debug("singleCmtCellDict['content']=%s", singleCmtCellDict['content']);
                
                #logging.debug("singleCmtCellDict=%s", singleCmtCellDict);
                
                extractedCmtCellDictList.append(singleCmtCellDict);
            else:
                logging.error("Cannot parse comment content from %s", unicode(eachCmtCellSoup));
                parseAllOk = False;
                break;
        else:
            logging.error("Cannot parse comment info from %s", unicode(eachCmtCellSoup));
            parseAllOk = False;
            break;
        #print "-----------------------";
        
    logging.debug("Parse all comment cell string to dict is %s", parseAllOk);
    
    return extractedCmtCellDictList;

#------------------------------------------------------------------------------
# fetch and parse comments 
# return the parsed dict value
def fetchAndParseComments(url, html):
    parsedCommentsList = [];
    
    try :
        #logging.debug("fetchAndParseComments_html=\n%s", html);
        
        soup = getSoupFromUrl(url);

        #<a href="#allcomments">评论:235</a>
        #foundAllCmtNum = soup.find(attrs={"href":"#allcomments"});
        foundAllCmtNum = re.search('<a href="#allcomments">.+?(?P<allCmtNum>\d+)</a>', html);
        logging.debug("foundAllCmtNum=%s", foundAllCmtNum);
        if(foundAllCmtNum):
            allCmtNum = foundAllCmtNum.group("allCmtNum");
            logging.debug("allCmtNum=%s", allCmtNum);
            allCmtNumInt = int(allCmtNum);
            logging.debug("allCmtNumInt=%s", allCmtNumInt);
            logging.debug("total comment number=%d", allCmtNumInt);
            if(allCmtNumInt > 0):
                allCmtCellDictList = [];
                
                # calc total comment page num
                maxCmtNumPerPage = 50;
                toalCmtPageNum = math.ceil(float(allCmtNumInt)/float(50));
                toalCmtPageNum = int(toalCmtPageNum);
                logging.debug("toalCmtPageNum=%d", toalCmtPageNum);

                # get all comment cell dict list
                if(toalCmtPageNum <= 1):
                    allCmtCellDictList = extractCmtCellDictList(html);
                else:
                    postId = extractPostIdFromPermaLink(url);
                    # for each comment page get html and extract comment cell string list
                    for eachPageIdx in range(toalCmtPageNum):
                        eachPageNum = eachPageIdx + 1;
                        #genrate comment url for each page
                        #http://blog.tianya.cn/blogger/post_read.asp?BlogID=3210723&PostID=41963783&page=2
                        postReadUrl = genPostReadUrl(gVal['blogId'], postId, eachPageNum);
                        respHtml = crifanLib.getUrlRespHtml(postReadUrl);
                        singlePageCmtCellStrList = extractCmtCellDictList(respHtml);
                        logging.debug("len(singlePageCmtCellStrList)=%s", len(singlePageCmtCellStrList));
                        allCmtCellDictList.extend(singlePageCmtCellStrList);
                
                logging.debug("len(allCmtCellDictList)=%s", len(allCmtCellDictList));
                # parse each comment cell string into dest comment dict
                parseAllCommentsList(allCmtCellDictList, parsedCommentsList);
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
    fd2 = picInfoDict['fields']['fd2'];
    fd3 = picInfoDict['fields']['fd3'];

    if (((fd2=='laibafile') or (fd2=='tianya')) and (fd3=='cn')):
        isSelfPic = True;
    else :
        isSelfPic = False;

    logging.debug("isSelfBlogPic: %s", isSelfPic);

    return isSelfPic;

#------------------------------------------------------------------------------
#check file validation for tianya blog pic
def isFileValid(picInfoDict):
    curUrl = picInfoDict['picUrl'];
    if(picInfoDict['isSelfBlog']):
        # here should use post url as referer to check pic validation, currently just set to true for simplicity
        (picIsValid, errReason) = (True, "");
    else:
        (picIsValid, errReason) = crifanLib.isFileValid(curUrl);
    return (picIsValid, errReason);
 
#------------------------------------------------------------------------------
# download file
def downloadFile(curPostUrl, picInfoDict, dstPicFile) :
    curUrl = picInfoDict['picUrl'];
    
    if(picInfoDict['isSelfBlog']):
        logging.debug("curPostUrl=%s, curUrl=%s, dstPicFile=%s", curPostUrl, curUrl, dstPicFile);
        # must use post url as referer, otherwise will get HTTP Error 403: Forbidden
        headerDict = {
            'Referer' : curPostUrl,
        };
        return crifanLib.manuallyDownloadFile(curUrl, dstPicFile, headerDict);
    else:
        return crifanLib.downloadFile(curUrl, dstPicFile);

#------------------------------------------------------------------------------
def getProcessPhotoCfg():
    # possible own site pic link:
    # type1:
    # http://blog.tianya.cn/blogger/post_read.asp?BlogID=309977&PostID=47772706 contain:
    # http://img3.laibafile.cn/p/m/122282130.jpg
    # http://img3.laibafile.cn/p/m/122282156.jpg
    # html ->
    # <img class="img-insert" title="全选 右键 delete.jpg" src="http://img3.laibafile.cn/p/m/122282130.jpg" />
    # <img class="img-insert" title="点击 对应页面的叉号 remove this page.jpg" src="http://img3.laibafile.cn/p/m/122282156.jpg" />
    #
    # http://blog.tianya.cn/blogger/post_read.asp?BlogID=4493710&PostID=47493241 contain:
    # http://img3.laibafile.cn/p/m/120994510.jpg
    # html ->
    # <img class="img-insert" title="22 .jpg" src="http://img3.laibafile.cn/p/m/120994510.jpg" />
    
    # type2:
    # http://blog.tianya.cn/blogger/post_read.asp?BlogID=2723898&PostID=24989103 contain:
    # http://img13.tianya.cn/photo/2010/7/4/24358385_34481178.jpg
    # html ->
    # <br><img src=http://img13.tianya.cn/photo/2010/7/4/24358385_34481178.jpg  style="DISPLAY: block; MARGIN: 0px auto 5px; TEXT-ALIGN: center;" border="0"><br>
    
    # possible othersite pic url:
        
    processPicCfgDict = {
        # here only extract last pic name contain: char,digit,-,_
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