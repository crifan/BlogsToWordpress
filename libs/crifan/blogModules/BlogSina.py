#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for Sina Blog.

[TODO]

【版本历史】
[v1.7]
1.fixbug -> support sub comments for some post:
http://blog.sina.com.cn/s/blog_89445d4f0101jgen.html

[v1.6]
1.fixbug -> support blog author reply comments

[v1.5]
1.fix parse sina post comment response json string
http://blog.sina.com.cn/s/blog_4701280b0101854o.html
comment url:
http://blog.sina.com.cn/s/comment_4701280b0101854o_1.html

[v1.4]
1.支持处理评论数目超多的帖子，比如：
http://blog.sina.com.cn/s/blog_4701280b0101854o.html -> 2万多个评论
http://blog.sina.com.cn/s/blog_4701280b0102e0p3.html -> 3万多个评论
v1.5:
1.添加支持其他网站图片

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
import json;
#from xml.sax import saxutils;

#--------------------------------const values-----------------------------------
__VERSION__ = "v1.6";

gConst = {
    'spaceDomain'  : 'http://blog.sina.com.cn',
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',   # 
    'blogEntryUrl'  : '',   # 
    'cj'            : None, # cookiejar, to store cookies for login mode
}

################################################################################
# Internal Sina Blog Functions 
################################################################################

#------------------------------------------------------------------------------
# pre-process sina post html, then latter the BeautifulSoup can work normally
def beforeCallBeautifulSoup(originalHtml):
    #logging.debug("beforeCallBeautifulSoup originalHtml\n---------------\n%s", originalHtml);

    processedHtml = originalHtml;
    
    # sina post html contain string: "<!–[if lte IE 6]> xxx <![endif]–>"  ->
    # will lead to BeautifulSoup(3.0.4/3.0.6) work abnormally -> 
    # it will parse the input html to single head == 
    # use soup.findAll("head"); will got all content, not the acutual head info ->
    # so follow find(id='xxx') will not work !!!
    # so here repalce them
    processedHtml = processedHtml.replace("<!–[if lte IE 6]>", "");
    processedHtml = processedHtml.replace("<![endif]–>", "");
    
    # handle special case for http://blog.sina.com.cn/s/blog_5058502a01017j3j.html
    processedHtml = processedHtml.replace('<font COLOR="#6D4F19"><font COLOR="#7AAF5A"><font COLOR="#7AAF5A"><font COLOR="#6D4F19"><font COLOR="#7AAF5A"><font COLOR="#7AAF5A">', "");
    processedHtml = processedHtml.replace("</FONT></FONT></FONT></FONT></FONT></FONT>", "");
    
    # processedHtml = processedHtml.replace("<!--$sinatopbar-->", "");
    # processedHtml = processedHtml.replace("<!--$end sinatopbar-->", "");
    
    # processedHtml = processedHtml.replace("<!--第一列start-->", "");
    # processedHtml = processedHtml.replace("<!--$end sinatopbar-->", "");
        
    # # note here both this python file and html should be utf-8
    # processedHtml = processedHtml.replace("<!-- 正文开始 -->", "");
    # processedHtml = processedHtml.replace("<!-- 正文结束 -->", "");
    
    #logging.debug("after beforeCallBeautifulSoup html\n---------------\n%s", processedHtml);
    
    return processedHtml;
    
#------------------------------------------------------------------------------
# convert sina blog post html to soup
def htmlToSoup(html):
    soup = None;
    processedHtml = beforeCallBeautifulSoup(html);
    #logging.debug("after beforeCallBeautifulSoup sina html\n---------------\n%s", processedHtml);
    # Note:
    # (1) after BeautifulSoup process, output html content already is utf-8 encoded
    soup = BeautifulSoup(processedHtml, fromEncoding="UTF-8");
    #soup = BeautifulSoup(processedHtml);
    #prettifiedSoup = soup.prettify();
    #logging.debug("htmlToSoup prettifiedSoup\n---------------\n%s", prettifiedSoup);
    
    return soup;

################################################################################
# Implemented Common Functions 
################################################################################

#------------------------------------------------------------------------------
#extract baidu blog user name, possibility:
# (1) extract crifan2008 from url: 
# http://blog.sina.com.cn/crifan2008
# http://blog.sina.com.cn/crifan2008/
# (2) or given any blog url, such as:
# http://blog.sina.com.cn/s/blog_3d55a9b70100nyl8.html
# http://blog.sina.com.cn/s/blog_5ed55f980102e617.html?tj=1
# http://blog.sina.com.cn/s/blog_67aa18870101dd7i.html
# extract http://blog.sina.com.cn/crifan2008
# from its html code
# (3) extract 2671017827 from:
# http://blog.sina.com.cn/u/2671017827
def extractBlogUser(inputUrl):
    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");

    logging.debug("Extracting blog user from url=%s", inputUrl);
    
    try :
        # type1, main url: 
        #http://blog.sina.com.cn/crifan2008
        #http://blog.sina.com.cn/crifan2008/
        foundMainUrl = re.search("(?P<mainUrl>http://blog\.sina\.com\.cn/(?P<username>\w+))/?$", inputUrl);
        if(foundMainUrl) :
            extractedBlogUser = foundMainUrl.group("username");
            generatedBlogEntryUrl = foundMainUrl.group("mainUrl");
            extractOk = True;
        
        # type2, main url:
        #http://blog.sina.com.cn/u/2671017827
        #http://blog.sina.com.cn/u/2671017827/
        if(not extractOk):
            foundUnumber = re.search("(?P<urlNoSlash>http://blog\.sina\.com\.cn/u/(?P<number>\d+))/?$", inputUrl);
            if(foundUnumber) :
                extractedBlogUser = foundUnumber.group("number");
                generatedBlogEntryUrl = foundUnumber.group("urlNoSlash");
                extractOk = True;

        # type3, some post url:
        #http://blog.sina.com.cn/s/blog_3d55a9b70100nyl8.html
        #http://blog.sina.com.cn/s/blog_5ed55f980102e617.html?tj=1
        if(not extractOk):
            foundPostLink = re.search("(?P<postUrl>http://blog\.sina\.com\.cn/s/blog_\w+\.html).*?", inputUrl);
            if(foundPostLink) :
                postUrl = foundPostLink.group("postUrl");
                respHtml = crifanLib.getUrlRespHtml(postUrl);
                soup = htmlToSoup(respHtml);
                blognameSoup = soup.find(name="h1", id="blogname");
                logging.debug("blognameSoup=%s", blognameSoup);
                if blognameSoup and blognameSoup.a :
                    #http://blog.sina.com.cn/crifan2008
                    #<h1 id="blogname" class="blogtitle"><a href="http://blog.sina.com.cn/crifan2008"><span id="blognamespan">crifan.com</span></a><a onclick="return false;" href="javscript:;" class="CP_a_fuc">[<cite id="modifytitle">编辑</cite>]</a></h1>
                    
                    #http://blog.sina.com.cn/u/1739200647
                    #<h1 id="blogname" class="blogtitle"><a href="http://blog.sina.com.cn/u/1739200647"><span id="blognamespan">小马遇上伪翻译</span></a></h1>
                    href = blognameSoup.a['href'];
                    #logging.info("href=%s", href);
                    extractedMainUrl = href; 
                    generatedBlogEntryUrl = extractedMainUrl;
                    logging.debug("generatedBlogEntryUrl=%s", generatedBlogEntryUrl);

                    # splitedList = extractedMainUrl.split("/");
                    # extractedBlogUser = splitedList[3];
                    blognamespanSoup = blognameSoup.find(name="span", id="blognamespan");
                    if(blognamespanSoup and blognamespanSoup.string):
                        extractedBlogUser = blognamespanSoup.string;
                        logging.debug("extractedBlogUser=%s", extractedBlogUser);
                        extractOk = True;
                    else:
                        logging.debug("Not found: blognamespan for sina blog");
    except :
        (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
        
    if (extractOk) :
        gVal['blogUser'] = extractedBlogUser;
        gVal['blogEntryUrl'] = generatedBlogEntryUrl;
        
    return (extractOk, extractedBlogUser, generatedBlogEntryUrl);

#------------------------------------------------------------------------------
# find the first permanent link = url of the earliset published blog item
def find1stPermalink():
    (isFound, errInfo) = (False, "Unknown error!");
    
    try:
        # 1. open main url
        respHtml = crifanLib.getUrlRespHtml(gVal['blogEntryUrl']);

        # 2. extract:    
        #<span><a  href="http://blog.sina.com.cn/s/articlelist_1029024183_0_1.html">博文目录</a></span>
        # Note: here both sina blog use UTF-8, and here current python file is also UTF-8 => then follow can match
        foundBlogCatalog = re.search('<span><a.+?href="(?P<urlPre>http.+?)1\.html">博文目录</a></span>', respHtml);
        
        #print "foundBlogCatalog=",foundBlogCatalog;
        if(foundBlogCatalog) :
            urlPre = foundBlogCatalog.group("urlPre");
            logging.debug("urlPre=%s", urlPre);
            
            # 3. generate the oldest url:
            # http://blog.sina.com.cn/s/articlelist_1029024183_0_100000.html
            maxPageIdx = 10000;
            oldestPageUrl = urlPre + str(maxPageIdx) + ".html";
            logging.debug("oldestPageUrl=%s", oldestPageUrl);
                        
            # 4. open the last url:
            # http://blog.sina.com.cn/s/blog_3d55a9b70100b0z0.html
            respHtml = crifanLib.getUrlRespHtml(oldestPageUrl);
            #logging.debug("---sina %s html---\n%s", oldestPageUrl, respHtml);
            
            # 5. and extract the earliest url
            
            # eg1:
            #<span class="atc_title">
            #                               <a title="国内常见博客的采集办法(搜狐&nbsp;网易&nbsp;新浪&nbsp;百度空间)，免费写采集规则！" target="_blank" href="http://blog.sina.com.cn/s/blog_40e4b5660100sk8m.html">国内常见博客的采集办法(搜狐&nbsp;网易…</a></span> 
            #                            <span class="atc_ic_b"></span>
            
            #eg2:
            #<span class="atc_title">
            #                                <a title="[转载]钱云会手表视频被编辑的铁证-倒地瞬间闪现奇异" target="_blank" href="http://blog.sina.com.cn/s/blog_3d55a9b70100phmr.html">[转载]钱云会手表视频被编辑的铁证…</a></span> 
            #                            <span class="atc_ic_b"><img class="SG_icon SG_icon18" src="http://simg.sinajs.cn/blog7style/images/common/sg_trans.gif" width="15" height="15" title="此博文包含图片" align="absmiddle" /></span>
            
            soup = htmlToSoup(respHtml);
            foundUrls = soup.findAll(attrs={"class":"atc_title"});
            if(foundUrls and len(foundUrls) > 0 ) :
                lastFoundUrl = foundUrls[-1];
                fristLink = lastFoundUrl.a['href'];

                isFound = True;
                return (isFound, fristLink);
        else :
            isFound = False;
            errInfo = u"Can not found the blog catalog url !";
    except:
        (isFound, errInfo) = (False, "Unknown error!");
    
    return (isFound, errInfo);

#------------------------------------------------------------------------------
# extract title fom url, html
def extractTitle(url, html):
    (needOmit, titleUni) = (False, "");
    try :
        soup = htmlToSoup(html);
        
        #<h2 id="t_3d55a9b70100nyl8" class="titName SG_txta">[转载]学习笔记之三年自然灾害</h2>
        titName = soup.find(attrs={"class":"titName SG_txta"});
        if(titName) :
            titleStr = titName.string;
            titleUni = unicode(titleStr);
    except : 
        (needOmit, titleUni) = (False, "");
        
    return (needOmit, titleUni);

#------------------------------------------------------------------------------
# find next permanent link from url, html
def findNextPermaLink(url, html) :
    nextLinkStr = '';
        
    try :
        #<div><span class="SG_txtb">后一篇：</span><a href="http://blog.sina.com.cn/s/blog_3d55a9b70100iakf.html">缺点</a></div>
        match = re.search('<div><span\s+?class="SG_txtb">后一篇：</span><a href="(?P<href>.+?)">(?P<title>.+?)</a></div>', html);
        nextPostTitle = "";
        if match:
            href = match.group("href");
            nextLinkStr = href;
            
            nextPostTitle = match.group("title");

        logging.debug("Found next permanent link=%s, title=%s", nextLinkStr, nextPostTitle);
    except :
        nextLinkStr = '';
        logging.debug("Can not find next permanent link.");

    return nextLinkStr;

#------------------------------------------------------------------------------
# extract datetime fom url, html
def extractDatetime(url, html) :
    datetimeStr = '';
    try :
        #<span class="time SG_txtc">(2008-10-12 22:14:05)</span>
        match = re.search('<span\s+?class="time SG_txtc">\((?P<datetime>.+?)\)</span>', html);
        if match:
            datetimeStr = match.group("datetime");
    except :
        datetimeStr = "";
        
    return datetimeStr;

#------------------------------------------------------------------------------
# extract blog item content fom url, html
def extractContent(url, html) :
    contentStr = '';
    try :
        #logging.debug("---before extractContent html :\n%s", html);
        soup = htmlToSoup(html);
    
        #prettifiedSoup = soup.prettify();
        #logging.debug("---in extractContent prettifiedSoup :\n%s", prettifiedSoup);
        #foundContent = soup.find(attrs={"class":"articalContent"}); # not work here !!!
        foundContent = soup.find(id="sina_keyword_ad_area2");
        #logging.debug("---soup foundContent:\n%s", foundContent);
        
        # <div id="sina_keyword_ad_area2" class="articalContent  ">
        # ..................
        # </div>

        #method 1
        mappedContents = map(CData, foundContent.contents);
        #print "type(mappedContents)=",type(mappedContents); #type(mappedContents)= <type 'list'>
        contentStr = ''.join(mappedContents);
        
        # #method 2
        # originBlogContent = "";
        # logging.debug("Total %d contents for original blog contents:", len(foundContent.contents));
        # for i, content in enumerate(foundContent.contents):
            # if(content):
                # logging.debug("[%d]=%s", i, content);
                # originBlogContent += unicode(content);
            # else :
                # logging.debug("[%d] is null", i);
        
        #logging.debug("---method 1: map and join---\n%s", contentStr);
        #logging.debug("---method 2: enumerate   ---\n%s", originBlogContent);
    except :
        contentStr = '';

    return contentStr;

#------------------------------------------------------------------------------
# extract category from url, html
def extractCategory(url, html) :
    catUni = '';
    try :
        soup = htmlToSoup(html);
        # <td class="blog_class">
                                # <span class="SG_txtb">分类：</span>
            # <a target="_blank" href="http://blog.sina.com.cn/s/articlelist_1029024183_2_1.html">随写</a>
                            # </td>    

        # when no catagory:
        # <td class="blog_class">
                            # </td>
        foundClass = soup.find(attrs={"class":"blog_class"});
        if(foundClass.a) :
            classStr = foundClass.a.string;
            catUni = unicode(classStr);
    except :
        catUni = "";

    return catUni;

#------------------------------------------------------------------------------
# extract tags info from url, html
def extractTags(url, html) :
    tagList = [];
    try :
        soup = htmlToSoup(html);
        
        # <td class="blog_tag">
        # <script>
        # var $tag='转载';
        # var $tag_code='7d11115e8449fbe2e0bc2d8209f42278';
        # var $r_quote_bligid='450ffd6501000d3y';
        # var $worldcup='0';
        # var $worldcupball='0';
        # </script>
                                # <span class="SG_txtb">标签：</span>
                                                                    # <h3><a href="http://uni.sina.com.cn/c.php?t=blog&k=%D7%AA%D4%D8&ts=bpost&stype=tag" target="_blank">转载</a></h3>
                                                    # </td>
        blogTag = soup.find(attrs={"class":"blog_tag"});
        h3List = blogTag.h3;
        
        for h3 in h3List :
            tagList.append(h3.string);
    except :
        tagList = [];

    return tagList;

#------------------------------------------------------------------------------
# add fake head and tail for latter BeautifulSoup to process
def genFakeHtml(parsedHtml):
    fakeHead = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Fake Title</title>
<body>
""";

    fakeTail = """
</body>
</head>
</html>
    """;

    fakeHtml = fakeHead + parsedHtml + fakeTail;

    return fakeHtml;

#------------------------------------------------------------------------------
# parse to real html
# input is backslash style html string
def parseHtml(backslashDataStr) :
    parsedHtml = backslashDataStr;
    
    parsedHtml = parsedHtml.replace("\\t", "\t");
    parsedHtml = parsedHtml.replace("\\r\\n", "\r\n");
    parsedHtml = parsedHtml.replace("\\/", "/");
    parsedHtml = parsedHtml.replace('\\"', '"');
    #logging.debug("after html parse: \n%s", parsedHtml);

    return parsedHtml;

#process single (main or sub) comment soup
def parseSingleCmtSoup(singleCmtSoup, curCmtId, parentCmdId):
    logging.debug("in parseSingleCmtSoup: curCmtId=%d, parentCmdId=%d", curCmtId, parentCmdId);
    #logging.debug("singleCmtSoup=%s", singleCmtSoup);

    destCmtDict = {};
    
    #main comment
    # <div class="SG_revert_Cont">
        # <p><span class="SG_revert_Tit" id="nick_cmt_2547560"><a href="http://blog.sina.com.cn/u/3149389173" target="_blank">MadCatMKII</a></span><span class="SG_revert_Time" userid="3149389173"><em class="SG_txtc">2013-07-15 01:04:24</em>&nbsp<a id="67aa18870101dd7i_2547560" onclick="comment_report('67aa18870101dd7i_2547560')" href="javascript:;">[\u4e3e\u62a5]</a></span></p>
        # <div class="SG_revert_Inner SG_txtb" id="body_cmt_2547560">\u5355\u8bba\u4e00\u4e2a\u683c\u6597\u6e38\u620f\u7684\u8bdd\uff0c\u5982\u679c\u662f\u8d70Furry\u8def\u7ebf\u8bf4\u4e0d\u5b9a\u6bd4\u8d70PONY\u8def\u7ebf\u66f4\u6709\u8d5a\u5934\uff0c\u6bd5\u7adf\u8bba\u7ec4\u6210\u7684\u8bdd\uff0cFurry\u63a7\u4eec\u4e0d\u6bd4\u9a6c\u8ff7\u5c11\u591a\u5c11\uff0c\u800c\u4e14\u4ed6\u4eec\u80af\u5b9a\u66f4\u559c\u6b22\u683c\u6597\u6e38\u620f\u2026\u2026<br>\u4f46\u662f\u8fd9\u80af\u5b9a\u4e0d\u662f\u9a6c\u8ff7\u60f3\u8981\u770b\u5230\u7684\u3002<br>\u800c\u4e14\u5b69\u4e4b\u5b9d\u4e5f\u5931\u53bb\u4e86\u4e00\u4e2a\u8ba9\u66f4\u591a\u4eba\u559c\u6b22\u5c0f\u9a6c\u7684\u673a\u4f1a\u3002<br><br><br>\u6709\u4e0d\u5c11\u4eba\u90fd\u662f\u56e0\u4e3a\u73a9EFZ\u4e4b\u540e\u624d\u60f3\u8d77\u53bb\u73a9\u90a3\u51e0\u4e2aGALGAME\u7684\u3002<br>\u5982\u679c\u8fd9\u4e2a\u6e38\u620f\u505a\u7684\u8db3\u591f\u4f18\u79c0\u7684\u8bdd\uff0c\u80af\u5b9a\u4e5f\u80fd\u5438\u5f15\u4e00\u5927\u6279\u683c\u6597\u6e38\u620f\u7231\u597d\u8005\u5165\u5751\u3002<br>\u53ef\u60dc\u77ed\u89c6\u7684\u5b69\u4e4b\u5b9d\u5374\u505a\u4e86\u4e0d\u7406\u667a\u7684\u4e3e\u52a8\u3002<br><br></div>

    
    #sub comment
            # <div class="SG_revert_Re SG_j_linedot1" id="reply_2547560" style="display:">
    # <p><span class="SG_revert_Tit">\u535a\u4e3b\u56de\u590d\uff1a</span><span class="SG_revert_Time"><em class="SG_txtc">2013-07-15 01:28:10</em></span></p>
    # <p class="myReInfo wordwrap">Hasbro\u8fd8\u662f\u6709\u5c01\u7684\u7406\u7531\u7684\uff0c\u5426\u5219\u53ef\u80fd\u88ab\u5176\u4ed6\u516c\u53f8\u501f\u673a\u4f5c\u4e3a\u201c\u9ed8\u8bb8\u65d7\u4e0b\u7248\u6743\u89d2\u8272\u88ab\u7b2c\u4e09\u65b9\u5546\u7528\u201d\u7684\u7406\u7531\u62ff\u6765\u4f5c\u4e3a\u76d7\u7248\u7684\u501f\u53e3\uff0c\u9020\u6210\u516c\u53f8\u7684\u635f\u5931\u3002\u8fd9\u4e8b\u548c\u7f8e\u5e1d\u7684\u7248\u6743\u6cd5\u662f\u6709\u5173\u7684\u3002<br><br><br>\u95ee\u9898\u662f\u2026\u2026\u7ed9\u4e2a\u7279\u522b\u6388\u6743\u8fd9\u4e8b\u4e0d\u5c31\u7ed3\u4e86\u4e48\u3002\u7686\u5927\u6b22\u559c\u3002<br><br><br>\u5f53\u7136\uff0c\u4e8e\u6211\u65e0\u6240\u8c13\uff0c\u6211\u66f4\u613f\u610f\u652f\u6301\u6709\u68a6\u60f3\u7684LF\u5927\u795e\u3002</p>
    
    
    # init to null, log it while error
    SG_revert = None;
    SG_revert_Tit = None;
    cmtTitleUrl = "";
    cmtTitle = "";
    decoedCmtTitle = "";
    SG_revert_Time = None;
    datetimeStr = "";
    parsedLocalTime = None;
    gmtTime = None;
    mainOrSubCmtBodySoup = None;
    #mappedContents = None;
    cmtContent = "";
    decodedCmtContent = "";
    
    try:
        destCmtDict['id'] = curCmtId;
        
        logging.debug("--- comment[%d] ---", destCmtDict['id']);
        
        SG_revert = singleCmtSoup.p;
        logging.debug("SG_revert=%s", SG_revert);
        
        SG_revert_Tit = SG_revert.find(attrs={"class":"SG_revert_Tit"});
        #cmtTitleUrl = "";
        if SG_revert_Tit.a :
            SG_revert_Tit_a = SG_revert_Tit.a;
            
            logging.debug("SG_revert_Tit_a=%s", SG_revert_Tit_a);
            
            cmtTitle = SG_revert_Tit_a.string;
            #print "a.string OK, cmtTitle=",cmtTitle;
            
            cmtTitleUrl = SG_revert_Tit_a['href'];
            logging.debug("cmtTitleUrl=%s", cmtTitleUrl);
        else :
            cmtTitle = SG_revert_Tit.string;
        
        logging.debug("cmtTitle=%s", cmtTitle);

        # for special:
        # the 980th in comment http://blog.sina.com.cn/s/blog_4701280b0101854o.html not contain title 
        # => SG_revert_Tit_a.string is empty
        # => follow cmtTitle.decode('unicode-escape') will fail
        # => set a fake title if is empty
        if(not cmtTitle) :
            cmtTitle = "Nobody";

        decoedCmtTitle = cmtTitle.decode('unicode-escape');
        #process special author title to original author
        if(decoedCmtTitle == u"博主回复："):
            decoedCmtTitle = gVal['blogUser'];
            cmtTitleUrl = gVal['blogEntryUrl'];

        destCmtDict['author'] = decoedCmtTitle;
        destCmtDict['author_url'] = cmtTitleUrl;
        
        SG_revert_Time = SG_revert.find(attrs={"class":"SG_revert_Time"});
        logging.debug("SG_revert_Time=%s", SG_revert_Time);
        
        datetimeStr = SG_revert_Time.em.string;
        
        parsedLocalTime = datetime.strptime(datetimeStr, '%Y-%m-%d %H:%M:%S'); #2012-03-29 09:52:17
        gmtTime = crifanLib.convertLocalToGmt(parsedLocalTime);
        destCmtDict['date'] = parsedLocalTime.strftime("%Y-%m-%d %H:%M:%S");
        destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");
        
        bodyCmtSoup = singleCmtSoup.find(name="div", attrs={"class":"SG_revert_Inner SG_txtb", "id":re.compile("body_cmt_\d+")}); #<div class="SG_revert_Inner SG_txtb" id="body_cmt_2547560">
        logging.debug("bodyCmtSoup=%s", bodyCmtSoup);
        
        myReInfoSoup = singleCmtSoup.find(name="p", attrs={"class":re.compile("myReInfo.*?")}); #<p class="myReInfo wordwrap">
        logging.debug("myReInfoSoup=%s", myReInfoSoup);
        if(bodyCmtSoup):
            #first use main comment soup
            mainOrSubCmtBodySoup = bodyCmtSoup;
        elif(myReInfoSoup):
            #if not exist first comment body, then is sub comment
            mainOrSubCmtBodySoup = myReInfoSoup;

        #logging.debug("mainOrSubCmtBodySoup=%s", mainOrSubCmtBodySoup);
        
        cmtContent = crifanLib.soupContentsToUnicode(mainOrSubCmtBodySoup.contents);
        #logging.info("cmtContent=%s", cmtContent);
        
        decodedCmtContent = cmtContent.decode('unicode-escape');
        #logging.info("decodedCmtContent=%s", decodedCmtContent);
        destCmtDict['content'] = decodedCmtContent;

        destCmtDict['author_email'] = "";
        destCmtDict['author_IP'] = "";
        #destCmtDict['approved'] = 1;
        #destCmtDict['type'] = '';
        #destCmtDict['parent'] = 0;
        destCmtDict['parent'] = int(parentCmdId);
        #destCmtDict['user_id'] = 0;
        
        logging.debug("author=%s", destCmtDict['author']);
        logging.debug("author_url=%s", destCmtDict['author_url']);
        logging.debug("date=%s", destCmtDict['date']);
        logging.debug("date_gmt=%s", destCmtDict['date_gmt']);
        logging.debug("content=%s", destCmtDict['content']);
        logging.debug("parent=%d", destCmtDict['parent']);
        
        #print "single comment parse OK: %d"%(curCmtId);
    except:
        logging.debug("Error while parse single comment %d", curCmtId);
        logging.debug("-------- detailed single comment info --------");
        logging.debug("SG_revert=%s", SG_revert);
        logging.debug("SG_revert_Tit=%s", SG_revert_Tit);
        logging.debug("cmtTitleUrl=%s", cmtTitleUrl);
        logging.debug("decoedCmtTitle=%s", decoedCmtTitle);
        logging.debug("SG_revert_Time=%s", SG_revert_Time);
        logging.debug("datetimeStr=%s", datetimeStr);
        logging.debug("parsedLocalTime=%s", parsedLocalTime);
        logging.debug("gmtTime=%s", gmtTime);
        logging.debug("mainOrSubCmtBodySoup=%s", mainOrSubCmtBodySoup);
        #logging.debug("mappedContents=%s", mappedContents);
        logging.debug("cmtContent=%s", cmtContent);
        logging.debug("decodedCmtContent=%s", decodedCmtContent);
        logging.debug("-------- detailed single comment info --------");

    return destCmtDict;

#------------------------------------------------------------------------------
# parse comment 'data' field string to comment dict info
# def parseCmtDataStr(dataStr, startNum):
    # cmtDictList = [];
    
    # #logging.debug("data str in cmt json: \n%s", dataStr);
    # parsedHtml = parseHtml(dataStr);
    # fakeHtml = genFakeHtml(parsedHtml);
    # soup = BeautifulSoup(fakeHtml);
    
    # mainCmtList = soup.findAll(attrs={"class":"SG_revert_Cont"});
    
    # lastCmtId = startNum + 1;
    # logging.debug("lastCmtId=%s", lastCmtId);
    
    # for (mainCmtIdx, singleCmtSoup) in enumerate(mainCmtList) :
        # curMainCmtId = lastCmtId;
        # #process main comment
        # mainDestCmtDict = parseSingleCmtSoup(singleCmtSoup, lastCmtId, 0);
        # logging.debug("lastCmtId=%s", lastCmtId);
        # cmtDictList.append(mainDestCmtDict);
        
        # #check exist sub comment or not, if exist, process them
        # #<div class="SG_revert_Re SG_j_linedot1" id="reply_2547560" style="display:">
        # subCmtSoupList = singleCmtSoup.findAll(name="div", attrs={"class":"SG_revert_Re SG_j_linedot1", "id":re.compile("reply_\d+")});
        # logging.debug("subCmtSoupList=%s", subCmtSoupList);
        # if(subCmtSoupList):
            # for singleSubCmtSoup in subCmtSoupList:
                # logging.info("singleSubCmtSoup=%s", singleSubCmtSoup);
                # #++lastCmtId;
                # lastCmtId = lastCmtId + 1;
                # logging.info("after lastCmtId+1 in sub comment for loop, lastCmtId=%s", lastCmtId);
                # singleSubDestCmtDict = parseSingleCmtSoup(singleSubCmtSoup, lastCmtId, curMainCmtId);
                # cmtDictList.append(singleSubDestCmtDict);
        
        # #++lastCmtId;
        # lastCmtId = lastCmtId + 1;
        # #logging.info("after lastCmtId+1 in main comment for loop, lastCmtId=%s", lastCmtId);

    # return cmtDictList;

# parse data json string into comment dict list
def parseCmtDataStr(postIdStr, dataStr, startNum):
    cmtDictList = [];
	# "data" : {
		# "spam_comment_check" : "bf3678dd0bde3aa355baa8c52cf71e71",
		# "is_comment_close" : "0",
		# "comment_num" : "13",
		# "comment_total_num" : "13",
		# "comment_data" : [{ ...}, {...}, ...]
    dataDict = {};
    try:
        #logging.info("dataStr=%s", dataStr);
        dataDict = json.loads(dataStr);
        #dataDict = json.loads(dataStr, "UTF-8");
        #dataDict = json.loads(dataStr, "GBK");
        #logging.info("dataDict=%s", dataDict);
        if("comment_data" in dataDict):
            commentDataDictList = dataDict['comment_data'];
                #logging.info("commentDataDictList=%s", commentDataDictList);
            lastCmtId = startNum + 1;
            logging.debug("lastCmtId=%s", lastCmtId);
            for singleMainCmtDataDict in commentDataDictList:
                curMainCmtId = lastCmtId;
                logging.debug("curMainCmtId=%s", curMainCmtId);
                #process main comment
                (mainDestCmtDict, subCmtNum) = parseMainOrSubCmtDict(singleMainCmtDataDict, curMainCmtId, 0);
                logging.debug("mainDestCmtDict=%s, subCmtNum=%d", mainDestCmtDict, subCmtNum);
                cmtDictList.append(mainDestCmtDict);
                if(subCmtNum > 0):
                    commentIdStr = singleMainCmtDataDict['id'];
                    logging.debug("commentIdStr=%s", commentIdStr);
                    #has sub comments, need process it
                    (gotValidSubCmtJson, subCmtJsonOrErrMsg) = getSubCmtJson(postIdStr, commentIdStr);
                    logging.debug("gotValidSubCmtJson=%s, subCmtJsonOrErrMsg=%s", gotValidSubCmtJson, subCmtJsonOrErrMsg);
                    subDataDict = json.loads(subCmtJsonOrErrMsg);
                    #logging.info("subDataDict=%s", subDataDict);
                    cmtReDataDictList = subDataDict['comment_reply_data'];
                    #logging.debug("cmtReDataDictList=%s", cmtReDataDictList);
                    for singleSubCmtDict in cmtReDataDictList:
                        logging.debug("singleSubCmtDict=%s", singleSubCmtDict);
                        #++lastCmtId;
                        lastCmtId = lastCmtId + 1;
                        logging.debug("after lastCmtId+1 in sub comment for loop, lastCmtId=%s", lastCmtId);
                        (subCmtDestDict, unuseSubCmtNum) = parseMainOrSubCmtDict(singleSubCmtDict, lastCmtId, curMainCmtId);
                        cmtDictList.append(subCmtDestDict);
                #++lastCmtId;
                lastCmtId = lastCmtId + 1;
                logging.debug("after lastCmtId+1 in main comment for loop, lastCmtId=%s", lastCmtId);
        else:
            #{"spam_comment_check":"081ad68bf5025dc826e2102581e0d060","is_comment_close":"0","comment_num":"0","comment_total_num":"0"}
            logging.debug("Can not found comment_data in data json string=%s", dataStr);
    except:
        logging.warning("Fail for parse resp comment data json string=%s", dataStr);

    return cmtDictList;

#get sub comment
def getSubCmtJson(articleIdStr, commentIdStr):
    (gotValidSubCmtJson, subCmtJsonOrErrMsg) = (False, "");

    #http://control.blog.sina.com.cn/admin/comment_new/cms_usereply_list.php?domain=2
    getSubCmtUrl = "http://control.blog.sina.com.cn/admin/comment_new/cms_usereply_list.php?domain=2";
    # article_id=89445d4f0101jgen&
    # comment_id=3015921&
    # page=1
    postDict = {
        'article_id': articleIdStr,
        'comment_id': commentIdStr,
        'page'      : "1",
        
    };
    subCmtRespHtml = crifanLib.getUrlRespHtml(getSubCmtUrl, postDict);
    logging.debug("subCmtRespHtml=%s", subCmtRespHtml);

    foundTextarea = re.search("<textarea>(?P<respCodeA00006Str>.+)</textarea>$", subCmtRespHtml);
    logging.debug("foundTextarea=%s", foundTextarea);
    if(foundTextarea):
        respCodeA00006Str = foundTextarea.group('respCodeA00006Str');

        # extract returned data field
        (gotValidSubCmtJson, subCmtJsonOrErrMsg) = extractCmtDataJsonStr(respCodeA00006Str);
        logging.debug("gotValidSubCmtJson=%s, subCmtJsonOrErrMsg=%s", gotValidSubCmtJson, subCmtJsonOrErrMsg);
    else:
        logging.debug("Fail to got valid sub comments resp html from getSubCmtUrl=%s", getSubCmtUrl);
        (gotValidSubCmtJson, subCmtJsonOrErrMsg) = (False, "Fail to extract out respCodeA00006Str");

    return (gotValidSubCmtJson, subCmtJsonOrErrMsg);

#parse single main or sub comment dict into dest comment dict
def parseMainOrSubCmtDict(mainOrSubCmtDataDict, curCmtId, parentCmdId):
    logging.debug("in parseMainOrSubCmtDict: curCmtId=%d, parentCmdId=%d", curCmtId, parentCmdId);
    logging.debug("mainOrSubCmtDataDict=%s", mainOrSubCmtDataDict);

    #(1) Main Comment
    # [{
		# "id" : "3015628",
		# "stair_cms_id" : null,
		# "is_first" : true,
		# "comm_uid" : "2445561093",
		# "cms_uid_vinfo" : false,
		# "src_uid" : "2302958927",
		# "cms_reply_num" : "0",
		# "cms_type" : "1",
		# "cms_n" : 1,
		# "fromProduct" : "blog",
		# "uname" : "\u843d\u5c0f\u5b89",
		# "ria_index_url" : "http:\/\/blog.sina.com.cn\/u\/2445561093",
		# "vimg" : null,
		# "user_image" : "http:\/\/portrait6.sinaimg.cn\/2445561093\/blog\/50",
		# "ulink" : "http:\/\/blog.sina.com.cn\/u\/2445561093",
		# "cms_body" : "%E9%98%BF%E6%9D%B0%E5%A7%90%E5%A6%B9%E7%BB%A7%E7%BB%AD%E6%B3%AA%E6%B5%81%E6%BB%A1%E9%9D%A2%E2%80%A6%E2%80%A6%28%2A%5E__%5E%2A%29%26nbsp%3B%E8%BF%99%E7%A7%8D%E8%A1%A8%E8%BE%BE%E5%A5%BD%E5%96%9C%E5%89%A7%E5%93%A6%EF%BC%81%E4%BA%8C%E5%85%AC%E4%B8%BB%E5%A4%A7%E4%BA%BA%E6%88%90%E7%BB%A9%E4%B8%8D%E9%94%99%E5%93%A6%EF%BC%81%E4%B9%88%E4%B9%88%E5%93%92%3Cimg%20src%3D%22http%3A%2F%2Fwww.sinaimg.cn%2Fuc%2Fmyshow%2Fblog%2Fmisc%2Fgif%2FE___0088EN00SIGT.gif%22%20style%3D%22margin%3A1px%3Bcursor%3Apointer%3B%22%20onclick%3D%22window.open%28%27http%3A%2F%2Fblog.sina.com.cn%2Fmyshow2010%27%29%22%20border%3D%220%22%20title%3D%22%E9%A1%B6%22%20%2F%3E",
		# "cms_circle_info" : "",
		# "cms_pubdate" : "2014-03-21 13:02:15"
	# }, {
		# "id" : "3015631",
		# "stair_cms_id" : null,
		# "is_first" : false,
		# "comm_uid" : "1991520912",
		# "cms_uid_vinfo" : false,
		# "src_uid" : "2302958927",
		# "cms_reply_num" : "0",
		# "cms_type" : "1",
		# "cms_n" : 2,
		# "fromProduct" : "blog",
		# "uname" : "Nightscreamer",
		# "ria_index_url" : "http:\/\/blog.sina.com.cn\/u\/1991520912",
		# "vimg" : null,
		# "user_image" : "http:\/\/portrait1.sinaimg.cn\/1991520912\/blog\/50",
		# "ulink" : "http:\/\/blog.sina.com.cn\/u\/1991520912",
		# "cms_body" : "%E5%BE%88%E8%8D%A3%E5%B9%B8%E8%83%BD%E5%8F%82%E5%8A%A0%E8%BF%99%E6%A0%B7%E7%9A%84%E7%BB%9F%E8%AE%A1%E3%80%82%E8%BF%99%E5%85%85%E5%88%86%E8%AF%81%E6%98%8E%E4%BA%86brony%E4%B9%9F%E9%83%BD%E6%98%AF%E6%AD%A3%E5%B8%B8%E4%BA%BA%E3%80%82",
		# "cms_circle_info" : "",
		# "cms_pubdate" : "2014-03-21 13:07:02"
	# }, {
		# "id" : "3015921",
		# "stair_cms_id" : null,
		# "is_first" : false,
		# "comm_uid" : "2895573181",
		# "cms_uid_vinfo" : false,
		# "src_uid" : "2302958927",
		# "cms_reply_num" : "2",
		# "cms_type" : "1",
		# "cms_n" : 3,
		# "fromProduct" : "blog",
		# "uname" : "Lulamoon",
		# "ria_index_url" : "http:\/\/blog.sina.com.cn\/u\/2895573181",
		# "vimg" : null,
		# "user_image" : "http:\/\/portrait6.sinaimg.cn\/2895573181\/blog\/50",
		# "ulink" : "http:\/\/blog.sina.com.cn\/u\/2895573181",
		# "cms_body" : "%E5%8E%9F%E6%9D%A5%E9%82%AA%E8%8C%A7%E8%B7%9FTrixie%E7%9A%84%E4%BA%BA%E6%B0%94%E6%B2%A1%E5%A4%9A%E9%AB%98%E4%B9%88%E2%80%A6%E2%80%A6",
		# "cms_circle_info" : "",
		# "cms_pubdate" : "2014-03-21 18:26:45"
	# },
    
    #(2) Sub Comment
    # [{
        # "id" : "3017611",
        # "stair_cms_id" : "3015921",
        # "reply_cms_id" : "3015921",
        # "comm_uid" : "1591612940",
        # "src_uid" : "2302958927",
        # "source_uid" : "2895573181",
        # "cms_uid_vinfo" : false,
        # "cms_type" : "2",
        # "cms_pubdate" : "2014-03-24 12:13:40",
        # "cms_n" : 1,
        # "fromProduct" : "blog",
        # "uname" : "\u674e\u5c0f\u9f99",
        # "ria_index_url" : "http:\/\/blog.sina.com.cn\/u\/1591612940",
        # "vimg" : null,
        # "user_image" : "http:\/\/portrait5.sinaimg.cn\/1591612940\/blog\/30",
        # "uhost" : "",
        # "ulink" : "http:\/\/blog.sina.com.cn\/u\/1591612940",
        # "source_uname" : "Lulamoon",
        # "source_ria_index_url" : "http:\/\/blog.sina.com.cn\/u\/2895573181",
        # "source_vimg" : null,
        # "cms_body" : "%E5%A6%82%E6%9E%9C%E8%83%BD%E6%94%BE%E5%87%BA%E5%89%8D10%E5%90%8D%E4%BB%A5%E5%A4%96%E7%9A%84%E8%A7%92%E8%89%B2%E4%BA%BA%E6%B0%94%E6%8E%92%E5%90%8D%E7%9A%84%E8%AF%9D%E4%B8%8D%E7%9F%A5%E9%81%93%E5%A5%B9%E4%BB%AC%E4%BC%9A%E5%9C%A8%E5%A4%9A%E5%B0%91%E4%BD%8D%E5%91%A2%E2%80%A6%E2%80%A6",
        # "cms_circle_info" : ""
    # }, {
        # "id" : "3016043",
        # "stair_cms_id" : "3015921",
        # "reply_cms_id" : "3015921",
        # "comm_uid" : "2302958927",
        # "src_uid" : "2302958927",
        # "source_uid" : "2895573181",
        # "cms_uid_vinfo" : false,
        # "cms_type" : "2",
        # "cms_pubdate" : "2014-03-21 21:53:05",
        # "cms_n" : 2,
        # "fromProduct" : "blog",
        # "uname" : "EquestriaCN",
        # "ria_index_url" : "http:\/\/blog.sina.com.cn\/u\/2302958927",
        # "vimg" : null,
        # "user_image" : "http:\/\/portrait8.sinaimg.cn\/2302958927\/blog\/30",
        # "uhost" : "equestriacn",
        # "ulink" : "http:\/\/blog.sina.com.cn\/u\/2302958927",
        # "source_uname" : "Lulamoon",
        # "source_ria_index_url" : "http:\/\/blog.sina.com.cn\/u\/2895573181",
        # "source_vimg" : null,
        # "cms_body" : "%E4%BD%9C%E4%B8%BA%E5%8D%95%E9%A1%B9%E9%80%89%E6%8B%A9%EF%BC%8C%E9%99%A4%E4%BA%86%E9%9C%B2%E5%A8%9C%E5%85%B6%E4%BB%96%E9%B2%9C%E6%9C%89%E8%A7%92%E8%89%B2%E8%83%BD%E8%B7%9F%E5%85%AD%E4%B8%BB%E8%A7%92%E6%AF%94%E3%80%82%E5%A4%9A%E9%80%89%E7%9A%84%E8%AF%9D%E4%B9%9F%E8%AE%B8%E6%83%85%E5%86%B5%E4%BC%9A%E4%B8%8D%E4%B8%80%E6%A0%B7%E3%80%82",
        # "cms_circle_info" : ""
    # }
    
    #special comments
    #http://blog.sina.com.cn/s/blog_89445d4f0100vqa5.html
    # {
        # "id" : "1987844",
        # "stair_cms_id" : null,
        # "is_first" : false,
        # "comm_uid" : "0",
        # "cms_uid_vinfo" : false,
        # "src_uid" : "2302958927",
        # "cms_reply_num" : "0",
        # "cms_type" : "1",
        # "cms_n" : 2,
        # "fromProduct" : "blog",
        # "uname" : "\u65b0\u6d6a\u7f51\u53cb",
        # "user_image" : "http:\/\/blogimg.sinajs.cn\/v5images\/default.gif",
        # "cms_body" : "%E5%8D%9A%E4%B8%BB%E6%9C%80%E5%96%9C%E6%AC%A2%E9%82%A3%E5%8C%B9%E5%B0%8F%E9%A9%AC%E5%91%A2%EF%BC%9F",
        # "cms_circle_info" : "",
        # "cms_pubdate" : "2011-09-02 21:10:29"
    # },

    
    (destCmtDict, subCmtNum) = ({}, 0);
    
    try:
        destCmtDict['id'] = curCmtId;
        logging.debug("--- comment[%d] ---", destCmtDict['id']);

        unameStrUni = mainOrSubCmtDataDict['uname'];
        #logging.info("unameStrUni=%s", unameStrUni);
        #decodedUnameUni = unameStr.decode('unicode-escape');
        #logging.info("decodedUnameUni=%s", decodedUnameUni);
        #destCmtDict['author'] = decodedUnameUni;
        destCmtDict['author'] = unameStrUni;

        if("ulink" in mainOrSubCmtDataDict):
            destCmtDict['author_url'] = mainOrSubCmtDataDict['ulink'];
        else:
            destCmtDict['author_url'] = "";
        #logging.info("destCmtDict['author_url']=%s", destCmtDict['author_url']);

        datetimeStr = mainOrSubCmtDataDict['cms_pubdate'];
        logging.debug("datetimeStr=%s", datetimeStr);
        parsedLocalTime = datetime.strptime(datetimeStr, '%Y-%m-%d %H:%M:%S'); #2012-03-29 09:52:17
        gmtTime = crifanLib.convertLocalToGmt(parsedLocalTime);
        destCmtDict['date'] = parsedLocalTime.strftime("%Y-%m-%d %H:%M:%S");
        destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");

        cmsBodyUni = mainOrSubCmtDataDict['cms_body'];
        #logging.info("cmsBodyUni=%s", cmsBodyUni);
        #curType = type(cmsBodyUni);
        #logging.info("curType=%s", curType);
        cmdBodyStr = str(cmsBodyUni);
        #logging.info("cmdBodyStr=%s", cmdBodyStr);
        #curType = type(cmdBodyStr);
        #logging.info("curType=%s", curType);
        urlunquotedCmsBodyStr = urllib.unquote(cmdBodyStr);
        #logging.info("urlunquotedCmsBodyStr=%s", urlunquotedCmsBodyStr);
        #curType = type(urlunquotedCmsBodyStr);
        #logging.info("curType=%s", curType);
        urlunquotedCmsBodyUni = urlunquotedCmsBodyStr.decode("UTF-8");
        #curType = type(urlunquotedCmsBodyUni);
        #logging.info("curType=%s", curType);
        #logging.info("urlunquotedCmsBodyUni=%s", urlunquotedCmsBodyUni);

        destCmtDict['content'] = urlunquotedCmsBodyUni;

        destCmtDict['author_email'] = "";
        destCmtDict['author_IP'] = "";
        #destCmtDict['approved'] = 1;
        #destCmtDict['type'] = '';
        #destCmtDict['parent'] = 0;
        destCmtDict['parent'] = int(parentCmdId);
        #destCmtDict['user_id'] = 0;

        logging.debug("author=%s", destCmtDict['author']);
        logging.debug("author_url=%s", destCmtDict['author_url']);
        logging.debug("date=%s", destCmtDict['date']);
        logging.debug("date_gmt=%s", destCmtDict['date_gmt']);
        logging.debug("content=%s", destCmtDict['content']);
        logging.debug("parent=%d", destCmtDict['parent']);

        # for main comment
        if("cms_reply_num" in mainOrSubCmtDataDict):
            subCmtNum = mainOrSubCmtDataDict['cms_reply_num'];
            logging.debug("subCmtNum=%s", subCmtNum);
            subCmtNum = int(subCmtNum);

        #print "single comment parse OK: %d"%(curCmtId);
    except:
        logging.warning("Error while parse single main or sub comment dict=%s", mainOrSubCmtDataDict);

    return (destCmtDict, subCmtNum);


#------------------------------------------------------------------------------
# extract post ID
# from :
# http://blog.sina.com.cn/s/blog_56c89b680102dynu.html
# extract the 56c89b680102dynu
def extractPostId(sinaPostUrl):
    postId = "";
    foundPostId = re.search("http://blog\.sina\.com\.cn/s/blog_(?P<postId>\w+)\.html$", sinaPostUrl);
    if(foundPostId) :
        postId = foundPostId.group("postId");
    return postId;

# extract comment data json string
def extractCmtDataJsonStr(respCodeA00006Str):
    (gotValidDataJsonStr, cmtDataJsonOrFailMsg) = (False, "Unknown error");
    #foundCodeA00006 = re.search('{"code":"A00006",data:"(?P<dataJsonStr>.+)"}$', respJson);
    #foundCodeA00006 = re.search('{"code":"A00006","?data"?:"(?P<dataJsonStr>.+)"}$', respJson);
    foundCodeA00006 = re.search('{"code":"A00006","?data"?:(?P<dataJsonStr>\{.+\})}$', respCodeA00006Str);
    logging.debug("foundCodeA00006=%s", foundCodeA00006);

    if (foundCodeA00006) :
        dataJsonStr = foundCodeA00006.group("dataJsonStr");
        logging.debug("dataJsonStr=%s", dataJsonStr);

        # 1. no comments:
        #{"code":"A00006",data:"\u535a\u4e3b\u5df2\u5173\u95ed\u8bc4\u8bba"}
        if(dataJsonStr == "\\u535a\\u4e3b\\u5df2\\u5173\\u95ed\\u8bc4\\u8bba") :
            # 博主已关闭评论
            decodedDataStr = dataJsonStr.decode("unicode-escape");
            (gotValidDataJsonStr, cmtDataJsonOrFailMsg) = (False, decodedDataStr);
        elif (dataJsonStr.find('class=\\"noCommdate\\"') > 0) :
            # 2. no more comment
            #{"code":"A00006",data:"<li><div class=\"noCommdate\">........
            (gotValidDataJsonStr, cmtDataJsonOrFailMsg) = (False, "No more comments");
        else :
            # contain valid comment
            (gotValidDataJsonStr, cmtDataJsonOrFailMsg) = (True, dataJsonStr);
    else:
        logging.debug("Fail extract comment data json string from=%s", respCodeA00006Str);
    
    return (gotValidDataJsonStr, cmtDataJsonOrFailMsg);
    
#------------------------------------------------------------------------------
# get valid data field/string in returned in json string for comment url
def getCmtJson(cmtUrl):
    logging.debug("fetch comment from url %s", cmtUrl);

    (gotOk, cmtDataJsonStr) = (False, "");
    respJson = "";

    # sometime due to network error, fetch comment json string will fail, so here do several try
    maxRetryNum = 3;
    for tries in range(maxRetryNum) :
        try :
            #respJson = crifanLib.getUrlRespHtml(cmtUrl);
            respJson = crifanLib.getUrlRespHtml(cmtUrl, timeout=20); # add timeout to avoid dead(no response for ever) !
            logging.debug("Successfully got comment json string from %s", cmtUrl);
            break # successfully, so break now
        except :
            if tries < (maxRetryNum - 1) :
                logging.warning("    Fail to fetch comment json string from %s, do %d retry", cmtUrl, (tries + 1));
                continue;
            else : # last try also failed, so exit
                logging.warning("    All %d times failed for try to fetch comment json from %s !", maxRetryNum, cmtUrl);
                break;

    if(respJson) :
        #logging.debug("Comment url ret json: \n%s", respJson);
        # extract returned data field
        (gotValidDataJsonStr, cmtDataJsonOrFailMsg) = extractCmtDataJsonStr(respJson);

        if (gotValidDataJsonStr) :
            logging.debug("Got valid comment code json string for cmtUrl=%s", cmtUrl);
            (gotOk, cmtDataJsonStr) = (gotValidDataJsonStr, cmtDataJsonOrFailMsg);
        else:
            logging.debug("Fail to get valid comment code json string for cmtUrl=%s, error message=%s", cmtUrl, cmtDataJsonOrFailMsg);

    return (gotOk, cmtDataJsonStr);

#------------------------------------------------------------------------------
# fetch and parse comments 
# return the parsed dict value
def fetchAndParseComments(url, html):
    parsedCommentsList = [];
   
    # for output info use
    maxNumReportOnce = 200;
    lastRepTime = 0;
    
    try :
        postId = extractPostId(url);
        needGetMore = True;
        cmtPageNum = 1;
        
        while needGetMore :
            # from :
            # http://blog.sina.com.cn/s/blog_56c89b680102dynu.html
            # generate the comment url:
            #http://blog.sina.com.cn/s/comment_56c89b680102dynu_1.html
            #getCommentUrl = "http://blog.sina.com.cn/s/comment_" + postId + "_" + str(cmtPageNum) + ".html";
            #http://blog.sina.com.cn/s/comment_89445d4f0101jgen_1.html?comment_v=articlenew
            getCommentUrl = "http://blog.sina.com.cn/s/comment_" + postId + "_" + str(cmtPageNum) + ".html?comment_v=articlenew";
            logging.debug("getCommentUrl=%s", getCommentUrl);
            (gotOK, cmtDataJsonStr) = getCmtJson(getCommentUrl);
            if(gotOK) :
                cmtIdStartNum = len(parsedCommentsList);
                cmdDictList = parseCmtDataStr(postId, cmtDataJsonStr, cmtIdStartNum);
                if(cmdDictList):
                    for eachCmtDict in cmdDictList :
                        parsedCommentsList.append(eachCmtDict);
                        
                        # report processed comments if exceed certain number
                        parsedCmtLen = len(parsedCommentsList);
                        curRepTime = parsedCmtLen/maxNumReportOnce;
                        if(curRepTime != lastRepTime) :
                            # report
                            logging.info("    Has processed comments: %5d", parsedCmtLen);
                            # update
                            lastRepTime = curRepTime;

                    cmtPageNum += 1;
                else:
                    needGetMore = False;
                    logging.debug("Fail to parse out more comments from %s", cmtDataJsonStr);
            else :
                needGetMore = False;

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

    if (fd2 == "sinaimg") and (fd3 == "cn"):
        isSelfPic = True;
    else :
        isSelfPic = False;

    logging.debug("isSelfBlogPic: %s", isSelfPic);

    return isSelfPic;

#------------------------------------------------------------------------------
# generate the file name for other pic
# depend on following picInfoDict definition
def genNewOtherPicName(picInfoDict):
    newOtherPicName = "";
    
    filename = picInfoDict['filename'];
    fd1 = picInfoDict['fields']['fd1'];
    #fd2 = picInfoDict['fields']['fd2'];
    #fd3 = picInfoDict['fields']['fd3'];
    
    #60xkpa.bay.livefilestore.com
    #newOtherPicName = fd1 + '_' + fd2 + "_" + filename;
    newOtherPicName = fd1 + "_" + filename;
    
    #print "newOtherPicName=",newOtherPicName;

    return newOtherPicName;

#------------------------------------------------------------------------------
# get the found pic info after re.search
# foundPic is MatchObject
def getFoundPicInfo(foundPic):
    #print "In getFoundPicInfo:";
    
    # here should corresponding to singlePicUrlPat in processPicCfgDict
    picUrl  = foundPic.group(0);
    fd1     = foundPic.group("fd1"); # s9/s14/i0/...
    fd2     = foundPic.group("fd2"); # sinaimg
    fd3     = foundPic.group("fd3"); # cn
    fd4     = foundPic.group("fd4"); #
    fd5     = foundPic.group("fd5"); #
    fd6     = foundPic.group("fd6"); #
    filename= foundPic.group("filename");
    suffix  = foundPic.group("suffix");

    #print "suffix=",suffix;
    #y1mo7UWr-T......0ii__WE6l2.......DNpwAbQ/IMG_5214_thumb[1].jpg ->
    #IMG_5214_thumb[1].jpg
    #print "filename=",filename;
    filename = filename.split("/")[-1];
    #print "filename=",filename;
    #try to extract real suffix
    extractedSuffix = filename.split(".")[-1];
    if(extractedSuffix) and (extractedSuffix in crifanLib.getPicSufList()):
        #print "real suffix is",extractedSuffix;
        suffix = extractedSuffix;
        filename = re.compile(r"\.\w+$").sub("", filename);
            
    # handle special sina pic filename
    #3d55a9b7g9522d474a84d&amp;690 -> 3d55a9b7g9522d474a84d
    filename = re.compile(r"&amp;\d+").sub("", filename);
    #y1p_SxhIJn......uua?PARTNER=WRITER -> 
    #y1p_SxhIJn......uua
    filename = filename.replace("?PARTNER=WRITER", "");
    #print "after remove ?PARTNER=WRITER, filename=",filename;
    
    filename = crifanLib.removeNonWordChar(filename);
    #print "valid filename=",filename;
    
    picInfoDict = {
        'isSupportedPic': False,
        'picUrl'        : picUrl,
        'filename'      : filename,
        'suffix'        : suffix,
        'fields'        : 
            {
                'fd1' : fd1,
                'fd2' : fd2,
                'fd3' : fd3,
                'fd4' : fd4,
                'fd5' : fd5,
                'fd6' : fd6,
            },
    };

    # if (suffix in crifanLib.getPicSufList()) :
        # picInfoDict['isSupportedPic'] = True; # other site pic
    # elif(fd2 == "sinaimg") and (fd3 == "cn") :
        # # own siet pic
        # picInfoDict['isSupportedPic'] = True;

    # here always set to True for if it is real_src, then it must be sina pic
    picInfoDict['isSupportedPic'] = True;
    
    return picInfoDict;

#------------------------------------------------------------------------------
def getProcessPhotoCfg():
    # possible own site pic link:
    # type1:
    # http://s13.sinaimg.cn/middle/5058502aga539c8797adc&amp;690 == http://s13.sinaimg.cn/middle/5058502aga539c8797adc&690
    # http://s8.sinaimg.cn/middle/5058502aga539ca24bca7&amp;690
    # type2:
    # http://blog.sina.com.cn/s/blog_48ace2830100aucb.html contain
    # http://s4.sinaimg.cn/bmiddle/48ace283t5925f0b45813
    # type3:
    # http://s9.sinaimg.cn/orignal/6f75ca11tbc32765138a8&690

    # tmp not support:
    # http://i0.sinaimg.cn/ent/v/m/2012-03-29/U6203P28T3D3593517F328DT20120329160927.jpg
    # 
    
    # possible othersite pic url:
    
    
    # <a href="http://photo.blog.sina.com.cn/showpic.html#blogid=3d55a9b70100n8d4&url=http://s14.sinaimg.cn/orignal/3d55a9b7g9522d474a84d" TARGET="_blank"><img src="http://simg.sinajs.cn/blog7style/images/common/sg_trans.gif" real_src ="http://s14.sinaimg.cn/middle/3d55a9b7g9522d474a84d&amp;690"  ALT="【已解决】打开word文档出错&nbsp;<wbr>/&nbsp;<wbr>如何修复损坏的word文档"  TITLE="【已解决】打开word文档出错&nbsp;<wbr>/&nbsp;<wbr>如何修复损坏的word文档" /></A>
    
    #<p ALIGN="center"><img src="http://simg.sinajs.cn/blog7style/images/common/sg_trans.gif" real_src ="http://s9.sinaimg.cn/orignal/6f75ca11tb68f63636ef8&amp;690"  ALT="京城路光影路故宫&nbsp;<wbr>（原创）"  TITLE="京城路光影路故宫&nbsp;<wbr>（原创）" /></P>
    
    #http://blog.sina.com.cn/s/blog_696e50390100ntoi.html contain:
    #<a HREF="https&#58;//60xkpa.bay.livefilestore.com/y1mOcyiIMOvYzOmba2ELKRhpb5D98uIM2UKCCLI9GxqQNgxX1TvvC4WPFTRjxtGQMq_cB7APbXExSn-87K8Qb_vIL3N3OcknHKXG4ucD0RxXnhzZ-FXjGsMDW4zHsLoHeoxYSXUoaLHqgtIqYcnuyIeIA/CACFair_00022[2].jpg" TARGET="_blank"><img TITLE="CACFair_00022" STYLE="border-right&#58;0px;border-top&#58;0px;display&#58;inline;border-left&#58;0px;border-bottom&#58;0px" HEIGHT="462" ALT="CACFair_00022" src="http://simg.sinajs.cn/blog7style/images/common/sg_trans.gif" real_src ="https&#58;//60xkpa.bay.livefilestore.com/y1mVYI3SjAaWIwPe0GXgS9fY3dcym9Ljn1ZZvAZAn2TSX3f-6vgXmgZ6DAQoYBEZfUyb7NqLOYyBwR7gl3dP8aIcsxMUMGEOAtuNE8uuq6e358LQpfOcLiNchLCktKLMHAPBuVe8axwMwQCfry7y8j0MA/CACFair_00022_thumb.jpg" WIDTH="810" BORDER="0" /></A>
    #and :
    #<a HREF="https&#58;//60xkpa.bay.livefilestore.com/y1mzjnfENUIRruWVigbkZoAan8wibeljXM9_yeY-3yO87dXZehRswLJRtK8R2-fvVlrGI_rpEoe-_Pq42D8l3GtviiG81slJyh2Rjahi42Nc-Eg4El6VJlskgPL7jG_AHfRCe-PwOCni5RU_SLsH4ELqQ/IMG_7007ed[2].jpg" TARGET="_blank"><img TITLE="IMG_7007ed" STYLE="border-right&#58;0px;border-top&#58;0px;display&#58;inline;border-left&#58;0px;border-bottom&#58;0px" HEIGHT="540" ALT="IMG_7007ed" src="http://simg.sinajs.cn/blog7style/images/common/sg_trans.gif" real_src ="http://s3.sinaimg.cn/middle/696e5039496c126e73b82&amp;690" WIDTH="810" BORDER="0" /></A>
    # note, after processed, html become:
    #<a href="https://60xkpa.bay.livefilestore.com/y1mzjnfENUIRruWVigbkZoAan8wibeljXM9_yeY-3yO87dXZehRswLJRtK8R2-fvVlrGI_rpEoe-_Pq42D8l3GtviiG81slJyh2Rjahi42Nc-Eg4El6VJlskgPL7jG_AHfRCe-PwOCni5RU_SLsH4ELqQ/IMG_7007ed[2].jpg" target="_blank"><img title="IMG_7007ed" style="border-right:0px;border-top:0px;display:inline;border-left:0px;border-bottom:0px" height="540" alt="IMG_7007ed" src="http://simg.sinajs.cn/blog7style/images/common/sg_trans.gif" real_src="http://s3.sinaimg.cn/middle/696e5039496c126e73b82&amp;690" width="810" border="0" /></a>
    
    
    picSufChars = crifanLib.getPicSufChars();
    processPicCfgDict = {
        # here only extract last pic name contain: char,digit,-,_
        #'allPicUrlPat'      : r'http://\w+\.\w+\.\w+/([\w%\-=]*/)+[\w\-\.&;^"]+'  + r'\.[' + picSufChars + r']{3,4}',
        #                                            field2     field3                                4=filename                     5=suffix
        #'singlePicUrlPat'   : r'http://\w+\.(?P<fd2>\w+)\.(?P<fd3>\w+)(\.(?P<fd4>\w+))?/[\w%\-=]*[/]?[\w\-/%=]*/(?P<filename>[\w\-\.&;]{1,100})' + r'(\.(?P<suffix>[' + picSufChars + r']{3,4}))?',

        # currently only support sina self blog middle type pic
        #'allPicUrlPat'     : r'http://\w+?\.sinaimg\.cn/middle/\w+?&amp;\d+',
        #'allPicUrlPat'     : r'http://\w+?\.sinaimg\.cn/\w*?middle/\w+[&]?[amp;]{0,4}\d{0,3}',
        #'allPicUrlPat'     : r'http://\w+?\.sinaimg\.cn/\w+/\w+[&]?[amp;]{0,4}\d{0,3}',
        #                                      fd1                             filename                
        #'singlePicUrlPat'  : r'http://(?P<fd1>\w+?)\.sinaimg\.cn/middle/(?P<filename>\w+?)&amp;\d+',
        #'singlePicUrlPat'  : r'http://(?P<fd1>\w+?)\.sinaimg\.cn/\w*?middle/(?P<filename>\w+)(&amp;\d+)?',
        #'singlePicUrlPat'  : r'http://(?P<fd1>\w+?)\.sinaimg\.cn/\w+/(?P<filename>\w+)(&amp;\d+)?',

        #Note here url is NOT like this:
        #real_src ="https&#58;//60xkpa.bay.livefilestore.com/xxx/CACFair_00022_thumb.jpg"
        # have been processed, like this:
        #real_src="https://60xkpa.bay.livefilestore.com/xxx/CACFair_00022_thumb.jpg"
        #'allPicUrlPat'      : r'(?<=real_src=")https?://\w+?\.\w+?\.?\w+?\.?\w+?\.?\w+?\.?\w+?/[\w%\-=^"]*/?[\w%\-=/^"]+/[\w^"\-\.&;=\[\]]+(?=")',
        #'singlePicUrlPat'   : r'https?://(?P<fd1>\w+?)\.(?P<fd2>\w+?)(\.(?P<fd3>\w+?))?(\.(?P<fd4>\w+?))?(\.(?P<fd5>\w+?))?(\.(?P<fd6>\w+?))?/.+?/(?P<filename>[\w\[\]&;=\-]+)(\.(?P<suffix>\w{3,4})?)?',
        
        #'allPicUrlPat'      : r'(?<=real_src=")https?://\w+?\.\w+?\.?\w+?\.?\w+?\.?\w+?\.?\w+?/[^"]*/?[^"]+/?[^"]+(?=")',
        #'singlePicUrlPat'   : r'https?://(?P<fd1>\w+?)\.(?P<fd2>\w+?)(\.(?P<fd3>\w+?))?(\.(?P<fd4>\w+?))?(\.(?P<fd5>\w+?))?(\.(?P<fd6>\w+?))?/[^"]*?/?(?P<filename>[^"]+)(\.(?P<suffix>\w{3,4}))?',

        'allPicUrlPat'      : r'(?<=real_src=")https?://\w+?\.\w+?\.?\w*?\.?\w*?\.?\w*?\.?\w*?/[^"]*/?[^"]+/?[^"]+(?=")',
        'singlePicUrlPat'   : r'https?://(?P<fd1>\w+?)\.(?P<fd2>\w+?)(\.(?P<fd3>\w*?))?(\.(?P<fd4>\w*?))?(\.(?P<fd5>\w*?))?(\.(?P<fd6>\w*?))?/[^"]*?/?(?P<filename>[^"]+)(\.(?P<suffix>\w{3,4}))?',

        'getFoundPicInfo'   : getFoundPicInfo,
        'isSelfBlogPic'     : isSelfBlogPic,
        'genNewOtherPicName': genNewOtherPicName,
        'isFileValid'       : None,
        'downloadFile'      : None,
    };
    
    return processPicCfgDict;

#------------------------------------------------------------------------------
# extract blog title and description
def extractBlogTitAndDesc(blogEntryUrl) :
    (blogTitle, blogDescription) = ("", "");
    
    #print "blogEntryUrl=",blogEntryUrl;

    respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
    soup = htmlToSoup(respHtml);
    
    # <div id="blogTitle" class="blogtoparea">
    # <h1 id="blogname" class="blogtitle"><a href="http://blog.sina.com.cn/joyphotography"><span id="blognamespan">.</span></a></h1>
    # <div id="bloglink" class="bloglink"><a href="http://blog.sina.com.cn/joyphotography">http://blog.sina.com.cn/joyphotography</a>  <a onclick="return false;" class="CP_a_fuc" href="#" id="SubscribeNewRss">[<cite>订阅</cite>]</a><a class="CP_a_fuc" href="javascript:void(scope.pa_add.add('1347964970'));">[<cite>手机订阅</cite>]</a></div>
    # </div>
    
    # <div id="blogTitle" class="blogtoparea">
    # <h1 id="blogname" class="blogtitle"><a href="http://blog.sina.com.cn/crifan2008"><span id="blognamespan">crifan.com</span></a></h1>
    # <div id="bloglink" class="bloglink"><a href="http://blog.sina.com.cn/crifan2008">http://blog.sina.com.cn/crifan2008</a>  <a onclick="return false;" class="CP_a_fuc" href="#" id="SubscribeNewRss">[<cite>订阅</cite>]</a><a class="CP_a_fuc" href="javascript:void(scope.pa_add.add('1029024183'));">[<cite>手机订阅</cite>]</a></div>
    # </div>

    try:
        foundTitle = soup.find(attrs={"class":"blogtitle"}); 
        foundTitleA = foundTitle.a;
        foundTitleSpan = foundTitleA.span;
        titStr = foundTitleSpan.string;
        blogTitle = unicode(titStr);
        
        blogDescription = "";
    except:
        (blogTitle, blogDescription) = ("", "");

    return (blogTitle, blogDescription);

#------------------------------------------------------------------------------
# possible date format:
# (1) 2012-03-30 08:32:31
def parseDatetimeStrToLocalTime(datetimeStr):
    parsedLocalTime = datetime.strptime(datetimeStr, '%Y-%m-%d %H:%M:%S') # here is GMT+8 local time
    #print "parsedLocalTime=",parsedLocalTime;
    return parsedLocalTime;


####### Login Mode ######

#------------------------------------------------------------------------------
# log in blog
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
    
    return (modifyOk, errInfo);

#------------------------------------------------------------------------------   
if __name__=="BlogSina":
    print "Imported: %s,\t%s"%( __name__, __VERSION__);