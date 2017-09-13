#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for Renren Blog.

[TODO]

[History]
v1.1:
1. support captcha while login

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
#from xml.sax import saxutils;
import json; # New in version 2.6.
#import random;
import StringIO;

#--------------------------------const values-----------------------------------
__VERSION__ = "v1.1";

gConst = {
    'spaceDomain'  : 'http://www.renren.com',
    'mode'          : {
        'loginSelf'     : 'loginSelf',  # use password login self renren
        'unloginPage'   : 'unloginPage',# url is something like http://page.renren.com/699092813/note, here also call it page mode 
        'viewFriend'    : 'viewFriend', # (login self then) view friend's renren
    }
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',   # 229351756
    'blogEntryUrl'  : '',   # http://www.renren.com/229351756
    'cj'            : None, # cookiejar, to store cookies for login mode
    'isPageMode'    : False,# 
    'viewFriend'    : False,# login self but view friend
    'curMode'       : '',   # current mode
}

################################################################################
# Internal Functions 
################################################################################

#------------------------------------------------------------------------------
# login self's renren and view self renren blog
def isLoginSelfMode():
    return (gVal['curMode'] == gConst['mode']['loginSelf']);
    
#------------------------------------------------------------------------------
# check whether input url is something like
# http://page.renren.com/699092813/note
# http://page.renren.com/yinyuetaiice/note
# these page can be viewed while not login
def isUnloginPageMode():
    return (gVal['curMode'] == gConst['mode']['unloginPage']);

#------------------------------------------------------------------------------
# login self's renren but view friend renren blog
def isViewFriendMode():
    return (gVal['curMode'] == gConst['mode']['viewFriend']);

#------------------------------------------------------------------------------
def htmlToSoup(html):
    soup = None;
    # Note:
    # (1) after BeautifulSoup process, output html content already is utf-8 encoded
    soup = BeautifulSoup(html, fromEncoding="UTF-8");
    #prettifiedSoup = soup.prettify();
    #logging.debug("Got post html\n---------------\n%s", prettifiedSoup);
    return soup;
    
################################################################################
# Common API Functions 
################################################################################

#------------------------------------------------------------------------------
# extract blog user name:
# (1) 229351756 from: 
# http://www.renren.com/229351756
# http://www.renren.com/229351756/
# (2) 229351756
# http://blog.renren.com/blog/229351756/262929661
# http://blog.renren.com/blog/229351756/262929661/
# http://blog.renren.com/blog/229351756/262929661?from=fanyeNew
# (3) 699092813 from
# http://page.renren.com/699092813/note
# http://page.renren.com/699092813/note/817982159
# http://page.renren.com/699092813/note/468796168/
#   yinyuetaiice from
# http://page.renren.com/yinyuetaiice/note
# (4) for login self but view friend
# http://blog.renren.com/blog/253362819/friends
# http://blog.renren.com/blog/253362819/friends/
# http://blog.renren.com/blog/239262292/friends?gal=buh
def extractBlogUser(inputUrl):
    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
    logging.debug("Extracting blog user from url=%s", inputUrl);
    
    try :
        # type1, main url: 
        # http://www.renren.com/229351756
        # http://www.renren.com/229351756/
        foundMainUrl = re.search("http://www\.renren\.com/(?P<username>\d+)/?", inputUrl);
        if(foundMainUrl) :
            extractedBlogUser = foundMainUrl.group("username");
            #generatedBlogEntryUrl = foundMainUrl.group("mainUrl");
            generatedBlogEntryUrl = gConst['spaceDomain'] + "/" + extractedBlogUser;
            extractOk = True;
            gVal['curMode'] = gConst['mode']['loginSelf'];

        # type2, perma link:
        # http://blog.renren.com/blog/229351756/262929661
        # http://blog.renren.com/blog/229351756/262929661/
        # http://blog.renren.com/blog/229351756/262929661?from=fanyeNew
        #
        # for view friend mode, tmp just use following code to detect the blogUser and curMode
        # then later after login will recheck these value
        # http://blog.renren.com/blog/253362819/819181942
        if(not extractOk):
            foundBlog = re.search("http://blog\.renren\.com/blog/(?P<renrenId>\d+)/\d+/?.*", inputUrl);
            if(foundBlog) :
                extractedBlogUser = foundBlog.group("renrenId");
                generatedBlogEntryUrl = "http://blog.renren.com/blog/" + extractedBlogUser;
                extractOk = True;
                gVal['curMode'] = gConst['mode']['loginSelf'];
                
        # type3, fixed page note(=blog):
        # http://page.renren.com/699092813/note
        # http://page.renren.com/yinyuetaiice/note
        # http://page.renren.com/699092813/note/817982159
        # http://page.renren.com/699092813/note/468796168/
        if(not extractOk):
            foundName = re.search("http://page.renren.com/(?P<username>\w+)/note/?.*", inputUrl);
            if(foundName) :
                gVal['isPageMode'] = True;
                logging.debug("Now is page mode: maybe not need input username and password, also can view blog posts");
                extractedBlogUser = foundName.group("username");
                generatedBlogEntryUrl = inputUrl;
                extractOk = True;
                gVal['curMode'] = gConst['mode']['unloginPage'];

        # type4, for login self but view friend:
        # http://blog.renren.com/blog/253362819/friends
        # http://blog.renren.com/blog/253362819/friends/
        # http://blog.renren.com/blog/239262292/friends?gal=buh
        if(not extractOk):
            foundFriend = re.search("http://blog\.renren\.com/blog/(?P<friendId>\d+)/friends/?.*", inputUrl);
            if(foundFriend) :
                extractedBlogUser = foundFriend.group("friendId");
                #http://blog.renren.com/blog/253362819/friends
                generatedBlogEntryUrl = "http://blog.renren.com/blog/" + extractedBlogUser + "/friends";
                extractOk = True;
                gVal['curMode'] = gConst['mode']['viewFriend'];

    except :
        (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
        
    if (extractOk) :
        gVal['blogUser'] = extractedBlogUser;
        gVal['blogEntryUrl'] = generatedBlogEntryUrl;
        logging.info("For RenRen Blog, current detected mode: %s", gVal['curMode']);
        
    return (extractOk, extractedBlogUser, generatedBlogEntryUrl);

#------------------------------------------------------------------------------
# generate the url to get blog posts
def genGetBlogPostUrl(pageIdx):
    blogUrl = "";
    if(isUnloginPageMode()):
        #http://page.renren.com/699092813/note?curpage=4&pid=699092813
        blogUrl = gVal['blogEntryUrl'];
        blogUrl += "?curpage=" + str(pageIdx);
        blogUrl += "&pid=" + gVal['blogUser'];
    elif(isViewFriendMode()) :
        blogUrl = gVal['blogEntryUrl']; #http://blog.renren.com/blog/253362819/friends
        blogUrl += "?curpage=" + str(pageIdx);
        blogUrl += "&year=0";
        blogUrl += "&month=0";
        blogUrl += "&selitem=";
    else:
        # is normal login mode
        #http://blog.renren.com/blog/0?curpage=4&year=0&month=0&selitem=&__view=async-html
        blogUrl = "http://blog.renren.com/blog/0";
        blogUrl += "?curpage=" + str(pageIdx);
        blogUrl += "&year=0";
        blogUrl += "&month=0";
        blogUrl += "&selitem=";
        blogUrl += "&__view=async-html";

    logging.debug("Generated get blog posts url : %s", blogUrl);
    
    return blogUrl;
    
#------------------------------------------------------------------------------
# find the first permanent link = url of the earliset published blog item
def find1stPermalink():
    (isFound, retInfo) = (False, "Unknown error!");
    
    try:
        if(isUnloginPageMode()) :
            blogEntryUrl = gVal['blogEntryUrl'];
            respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
            logging.debug("open %s return html=\n%s", blogEntryUrl, respHtml);
            
        else:
            # normal mode and view friend mode
            pageIdx = 0;
            blogUrl = genGetBlogPostUrl(pageIdx);

            logging.debug("open %s to find blog post", blogUrl);
            respHtml = crifanLib.getUrlRespHtml(blogUrl);
            #logging.debug("%s return html:\n%s", blogUrl, respHtml);
        
        # normalMode: <div class="pager-top"><span>当前显示1-10篇/共448篇</span><ol class="pagerpro"> <!--<a href="#">共条45</a>--><li class="current"><a href="#nogo">1</a></li>
        # pageMode:   <div class="pager-top moretopmargin"><span>当前显示1-20篇/共1720篇</span>
        
        # Note: here both search string and current file is UTF-8 format
        # follow use 1-xxx -> above pageIdx must be 0
        foundPostNum = re.search(r"<span>当前显示1-(?P<numPerPage>\d+)篇/共(?P<totalNum>\d+)篇</span>", respHtml);
        if(foundPostNum) :
            logging.debug("found page number related info");
            numPerPage = foundPostNum.group("numPerPage");
            totalNum = foundPostNum.group("totalNum");
            totalNum = int(totalNum);
            numPerPage = int(numPerPage);
            lastPageIdx = totalNum/numPerPage;
            remain = totalNum % numPerPage;
            #print "remain val=",remain;
            if(remain == 0):
                lastPageIdx = lastPageIdx - 1;
            logging.debug("extracted: numPerPage=%d, totalNum=%d, lastPageIdx=%d", numPerPage, totalNum, lastPageIdx);
            lastPageUrl = genGetBlogPostUrl(lastPageIdx);
            logging.debug("now open %s to find earliest blog post", lastPageUrl);
            respHtml = crifanLib.getUrlRespHtml(lastPageUrl);
            logging.debug("%s return html:\n%s", lastPageUrl, respHtml);
            
            soup = BeautifulSoup(respHtml);

            # <div class="list-blog">
            # <div class="marginleft">
            # <h3 class="title-article">
            # <span class="editarticle"> 
            # <a
            # href="http://blog.renren.com/blog/0/263778573/editBlog">编辑</a> | <a
            # onclick="confirmDelete(this,263778573);return false;"
            # href="http://blog.renren.com/blog/0/263778573/delete">删除</a>
            # </span>
            # <strong><a
            # href="http://blog.renren.com/blog/229351756/263778573?frommyblog">背景歌曲更换记录</a> </strong>
            # <div class="pub-type">
            # <span class="timestamp">2008-01-16 23:31
            # </span>
            # <span class="group">(分类:<a
            # href='http://blog.renren.com/blog/0?categoryId=0'>默认分类</a>)</span></div>
            # </h3>
            # <div class="text-article">

            # 格式：背景音乐更换时间歌手歌曲名链接地址歌曲简评2008.01.16Lene Marlina place nearbyhttp://www.gbabook.com/blog/mymusic/a_place_nearby.wma清新脱俗，舒缓2008.01.14汪峰硬币http://www.wjhtxx.com/kswx/wxxh/tdjs/UploadFil...
            # </div>
            # <div class="full_listfoot"></div>
            # <p class="stat-article bottom-margin">
            # <a
            # href="http://blog.renren.com/blog/229351756/263778573">阅读</a>(1)
            # <span class="pipe">|</span>
            # <a
            # href="http://blog.renren.com/blog/229351756/263778573#comments">评论</a>(0)
            # <span class="pipe">|</span>
            # <a
            # href="http://blog.renren.com/blog/229351756/263778573">分享</a>(0)
            # </p>
            # </div>
            # </div>
            postList = soup.findAll(attrs={"class":"list-blog"});
            logging.debug("last page contain %d posts, whole postList=%s", len(postList), postList);
            if(postList):
                earliestPost = postList[-1];
                logging.debug("earliestPost=%s", earliestPost);
                marginleft = earliestPost.div; # -> <div class="marginleft">
                logging.debug("marginleft=%s", marginleft);
                if(isViewFriendMode()):
                    titleParent = marginleft;
                else:
                    title_article = marginleft.h3;
                    logging.debug("title_article=%s", title_article);
                    titleParent = title_article;
                titleStrong = titleParent.strong;
                logging.debug("titleStrong=%s", titleStrong);
                titleLink = titleStrong.a;
                logging.debug("titleLink=%s", titleLink);
                titleHref = titleLink['href'];
                logging.debug("titleHref=%s", titleHref);
                titleHref = titleHref.replace("?frommyblog", "");
                logging.debug("titleHref=%s", titleHref);
                (isFound, retInfo) = (True, titleHref);
                #titleStr = titleLink.string;
                #print "titleStr=",titleStr;
    except:
        (isFound, retInfo) = (False, "Unknown error!");
    
    return (isFound, retInfo);

#------------------------------------------------------------------------------
# check whether contain special char: 160==0xA0==á
def containSpecialChar(titleStrong):
    (foundSpecial, filteredStr) = (False, "");
    
    #http://blog.renren.com/blog/253362819/819181942 is special
    #->BeautifulSoup will parse error, parse the ' ' to á(==160==0xA0)
    #<strong>濡傛灉褰撲綘鍙戠幇&lt;my聽heart聽will聽go聽on&gt;聽鍜岃€佸勾聽Rose聽閭ｄ釜姊﹀鐨勫叧绯伙紝浣犱篃浼氬儚鎴戜竴鏍疯繛缁袱澶╁湪鐢靛奖闄㈡伕鍝?/strong>
    titleStrongStr = titleStrong.contents[0];
    #titleStrongStr=[u'\u5982\u679c\u5f53\u4f60\u53d1\u73b0&lt;my\xa0heart\xa0will\xa0go\xa0on&gt;\xa0\u548c\u8001\u5e74\xa0Rose\xa0\u90a3\u4e2a\u68a6\u5883\u7684\u5173\u7cfb\uff0c\u4f60\u4e5f\u4f1a\u50cf\u6211\u4e00\u6837\u8fde\u7eed\u4e24\u5929\u5728\u7535\u5f71\u9662\u6078\u54ed']
    logging.debug("titleStrongStr=%s", titleStrongStr);
    
    specialChar = "";

    for c in titleStrongStr :
        asciiVal = ord(c);
        #print "asciiVal=",asciiVal;
        if(asciiVal != 0xa0):
            filteredStr += c;
        else :
            filteredStr += " "; # above missed parsed 0xA0, actually is the space char ' '
            specialChar = c;# 160==0xA0==á
            foundSpecial = True;
    
    logging.debug("specialChar=%s", specialChar);

    return (foundSpecial, filteredStr);

#------------------------------------------------------------------------------
# extract post title
def extractTitle(url, html):
    (needOmit, titleUni) = (False, "");
    try :
        logging.debug("url=%s", url);
        logging.debug("extractTitle:html=%s", html);
        
        soup = htmlToSoup(html);
        
        if(isUnloginPageMode()) :
            #<h3 class="title-article margin-top"><strong>豆丁网创始人林耀成：哈佛MBA打造最大中文文档分享社区</strong>
            foundTitle = soup.find(attrs={"class":"title-article margin-top"});
        else :
            # <h3 class="title-article">
            # <span class="edit"> 
            # <a href="http://blog.renren.com/blog/0/237442520/editBlog">编辑</a>
            # <span class="pipe">|</span> <a onclick="confirmDelete(this);return false;" href="http://blog.renren.com/blog/0/237442520/delete">删除</a>
            # <span class="pipe">|</span>
            # <a href="#nogo" id="copyBlogLink" class="copylink">复制链接</a>
            # <div class="tips-box " id="copyLinkTip" style="display:none">
            # <div class="arrow"></div>
            # <div class="tips-link clearfix">
            # <span>新功能 :</span><a href="javascript:void(0)" onclick="ExternalShareLink.hideTips()" class="x-to-hide"></a>
            # <p>可以和站外好友分享日志了</p>
            # </div>
            # </div>
            # </span>
            # <strong>校内网第一贴</strong>
            # <span class="timestamp">2007-10-13 23:45 <span class="group">(分类:<a
            # href='http://blog.renren.com/blog/0?categoryId=0'>默认分类</a>)</span> </h3>
            foundTitle = soup.find(attrs={"class":"title-article"});

        titleStrong = foundTitle.strong;
        #print "type(titleStrong)=",type(titleStrong);
        #print "titleStrong=",titleStrong;
        
        (foundSpecial, filteredStr) = containSpecialChar(titleStrong);
        #print "(foundSpecial, filteredStr)=",(foundSpecial, filteredStr);
        if(foundSpecial):
            #print "type(filteredStr)=",type(filteredStr);
            #print "filteredStr=",filteredStr;
            titleUni = filteredStr;
        else :
            titleUni = titleStrong.string;
            #print "titleUni=",titleUni;
            titleUni = unicode(titleUni);
            #print "titleUni=",titleUni;
    except : 
        (needOmit, titleUni) = (False, "");
        
    return (needOmit, titleUni);

#------------------------------------------------------------------------------
# find next permanent link of current post
def findNextPermaLink(url, html) :
    nextLinkStr = '';

    try :
        #logging.debug("findNextPermaLink:html=%s", html);
        
        nextPostTitle = "";
        soup = htmlToSoup(html);
        if(isUnloginPageMode()) :
            # <span class="right-line">
            # <a href="http://page.renren.com/699092813/note/468796168?op=next&curTime=1275362924000">上一篇</a> &nbsp;&nbsp;&nbsp;
            # <a href="http://page.renren.com/699092813/note/468796168?op=pre&curTime=1275362924000">下一篇</a>
            # </span>
            foundRightLine = soup.find(attrs={"class":"right-line"});
            if(foundRightLine):
                aVal = foundRightLine.a;
                #print "aVal=",aVal;
                href = aVal['href'];
                #print "href=",href;
                # open href to find the real perma link
                respHtml = crifanLib.getUrlRespHtml(href);
                #XN.page.data.shareData = {"summary":"\u5728\u516d\u4e00\u513f\u7ae5\u8282,\u4e00\u8d77\u6765\u7f05\u6000\u4e00\u4e0b\u5c5e\u4e8e\u516b\u96f6\u540e\u7684\u7ae5\u5e74~\u4e0b\u9762\u8fd9\u4e9b\u63d2\u56fe,\u4f60\u8fd8\u8bb0\u5f97\u591a\u5c11?            \u4e4c\u9e26\u559d\u6c34            \u96ea\u5730\u91cc\u7684\u5c0f\u753b\u5bb6            \u4e0d\u61c2\u5c31\u95ee---\u5b59\u4e2d\u5c71            \u72fc\u7259\u5c71\u4e94\u58ee\u58eb            \u6311\u5c71\u5de5            \u5c06...","fromuniv":"","link":"http:\/\/page.renren.com\/699092813\/note\/468827150?","statID":"page_699092813_2","noteId":4.6882715e8,"pic":"","type":20,"largeurl":"","title":"80\u540e\u7684\u6765\u770b!\u5c0f\u5b66\u8bed\u6587\u8bfe\u672c\u63d2\u56fe\u4f60\u8fd8\u8bb0\u5f97\u591a\u5c11!","level":"2","fromname":"\u8c46\u4e01\u6587\u6863","fromno":699092813,"albumid":"0"};
                #foundShareData = re.search(r"XN\.page\.data\.shareData\s+?=\s+?\{(?P<shareDataJson>.+?)\};$", respHtml, re.S);
                foundShareData = re.search(r"XN\.page\.data\.shareData\s+?=\s+?(?P<shareDataJson>\{.+?\});\s", respHtml, re.S);
                #print "foundShareData=",foundShareData;
                if(foundShareData):
                    shareDataJson = foundShareData.group("shareDataJson");
                    #print "shareDataJson=",shareDataJson;
                    shareDataDict = json.loads(shareDataJson);
                    #print "shareDataDict=",shareDataDict;
                    permaLink = shareDataDict['link'];
                    #print "permaLink=",permaLink;
                    # from : http://page.renren.com/699092813/note/468827150?
                    # to   : http://page.renren.com/699092813/note/468827150
                    permaLink = permaLink.replace("?", "");
                    #print "permaLink=",permaLink;
                    
                    nextLinkStr = permaLink;
                    nextPostTitle = shareDataDict['title'];
        else :
            # method 1:
            # # <div class="pager-top">
            # # <span class="right-line">
            # # <a href="http://blog.renren.com/blog/229351756/262856003?from=fanyeNew" title="好久没来了">较新一篇</a>                            
            # # &#47; 
            # # <a href="http://blog.renren.com/blog/229351756/237442520/preOrNext?time=1192290304000&op=pre" title="没有较旧一篇啦!:::6020169">较旧一篇</a>		  	      
            # # </span>             
            # # </div>
                    
            # foundPagertop = soup.find(attrs={"class":"pager-top"});
            # print "foundPagertop=",foundPagertop;
            # rightLine = foundPagertop.span;
            # fanyeNew = rightLine.a;
            # fanyeNewStr = fanyeNew.string;
            # print "fanyeNewStr=",fanyeNewStr;
            # fanyeNewHref = fanyeNew['href'];
            # print "fanyeNewHref=",fanyeNewHref;
            # foundPermaLink = re.search(r"(?P<permaLink>.+?)\?from=fanyeNew", fanyeNewHref);
            # if(foundPermaLink) :
                # nextLinkStr = foundPermaLink.group("permaLink");
            
            # method 2:
            #<span class="float-left"><a href="http://blog.renren.com/blog/229351756/262856003?from=fanyeNew">较新一篇:好久没来了</a></span>
            foundFloatLeft = soup.find(attrs={"class":"float-left"});
            if(foundFloatLeft):
                aVal = foundFloatLeft.a;
                #print "aVal=",aVal;
                href = aVal['href'];
                #print "href=",href;
                foundPermaLink = re.search(r"(?P<permaLink>.+?)\?from=fanyeNew", href);
                if(foundPermaLink) :
                    nextLinkStr = foundPermaLink.group("permaLink");

                strVal = aVal.string;
                #print "strVal=",strVal;
                nextPostTitle = strVal.replace(u"较新一篇:", "");
                #print 'nextPostTitle=',nextPostTitle;

        logging.debug("Found next permanent link=%s, title=%s", nextLinkStr, nextPostTitle);
    except :
        nextLinkStr = '';
        logging.debug("Can not find next permanent link.");

    return nextLinkStr;

#------------------------------------------------------------------------------
# extract datetime
def extractDatetime(url, html) :
    datetimeStr = '';
    
    try :
        #logging.debug("html=%s", html);
        soup = htmlToSoup(html);
        
        # <span class="timestamp">2007-10-13 23:45 <span class="group">(分类:<a
        # href='http://blog.renren.com/blog/0?categoryId=0'>默认分类</a>)</span> 
        # ---> in the end , lack a </span>
        
        #<span class="timestamp">2010年06月01日 11:28:44</span>
        
        datetime = soup.find(attrs={"class":"timestamp"});
        #print "datetime=",datetime;
        #datetimeStr = datetime.string; # not work here !!!
        #print "datetime.contents=",datetime.contents;
        datetimeStr = datetime.contents[0];
        datetimeStr = datetimeStr.strip();
        #print "type(datetimeStr)=",type(datetimeStr);
        #print "datetimeStr=",datetimeStr;
    except :
        datetimeStr = "";
    
    return datetimeStr;

#------------------------------------------------------------------------------
# extract post content
def extractContent(url, html) :
    contentUni = "";
    
    try :
        soup = htmlToSoup(html);
        
        # normal login mode:
        # <div id="blogContent" class="text-article">
        #
        # <P><FONT size=2>注册有段时间了，还没发过贴呢，呵呵。今天开个头，写个。</FONT></P><P><FONT size=2>顺便记录一个帖子，以备后查：</FONT></P><P><FONT size=2></FONT> </P><P><FONT size=2>对科大感到失望<BR></FONT><a target=_blank href="http://bbs.ustc.edu.cn/cgi/bbscon?bn=GraduateUnion&amp;fn=M47109C02&amp;num=8109"><FONT size=2>http://bbs.ustc.edu.cn/cgi/bbscon?bn=GraduateUnion&amp;fn=M47109C02&amp;num=8109</FONT></A></P>
        # </div>
        
        # page mode:
        # <div class="text-article" id="blogContent">
        # <!-- 动态输出blog内容 -->
        # <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 进入大学以后，我们面临着不断的选择，..........
        # </div>
        
        blogContent = soup.find(id="blogContent");
        mappedContents = map(CData, blogContent.contents);
        #print "type(mappedContents)=",type(mappedContents); #type(mappedContents)= <type 'list'>
        contentUni = ''.join(mappedContents);

        
        #for page mode:, method 2:
        #<div class="text-article" id="blogContent"> ... </div>
        # foundBlogContent = re.search(r'<div class="text-article" id="blogContent">(?P<blogContentUtf8>.+?)</div>\s+', html, re.S);
        # print "foundBlogContent=",foundBlogContent;
        # if(foundBlogContent):
            # blogContentUtf8 = foundBlogContent.group("blogContentUtf8");
            # contentUni = blogContentUtf8.decode("UTF-8");

        #logging.debug("extracted url=%s post content:\n%s", url, contentUni);
    except :
        contentUni = '';
 
    #print "len(contentUni)=",len(contentUni);
    
    return contentUni;

#------------------------------------------------------------------------------
# extract post category
def extractCategory(url, html) :
    catUni = '';
    #logging.debug("in extractCategory, html =\n%s", html);
    
    if(isUnloginPageMode()) :
        # page mode no category
        catUni = "";
    else:   
        soup = htmlToSoup(html);
        
        #<span class="group">(分类:<a href="http://blog.renren.com/blog/0?categoryId=0">默认分类</a>)</span>
        group = soup.find(attrs={"class":"group"});
        
        #print "group=",group;
        aVal = group.a;
        #print "aVal=",aVal;
        href = aVal['href'];
        #print "href=",href;
        aStr = aVal.string;
        #print "aStr=",aStr;
        catUni = unicode(aStr);
    
    return catUni;
    
#------------------------------------------------------------------------------
# extract tags info
def extractTags(url, html) :
    tagList = [];
    # here Renren blog not support tags
    return tagList;

#------------------------------------------------------------------------------
# fill source comments dictionary into destination comments dictionary
def fillComments(destCmtDict, srcCmtDict, cmtId):
    destCmtDict['id'] = cmtId;
    logging.debug("--- comment[%d] ---", destCmtDict['id']);

    logging.debug("srcCmtDict=%s", srcCmtDict);
    
# {
    # "wap": false,
    # "body": "\u6539\u7248\u524d\u662f\u5f88\u597d\u7684\u6539\u7248\u5f8cBUG\u5f88\u591a\u5f88\u591a\u3002\u3002\u3002\u800c\u4e14\u5546\u696d\u5316\u6c23\u5473\u8d8a\u9aee\u6fc3\u70c8",
    # "isVip": false,
    # "likeCount": 0,
    # "ilike": false,
    # "keepUse": false,
    # "id": 4.06012649e8,
    # "author": 222509218,
    # "time": "2008-01-13 10:46",
    # "share": false,
    # "whisper": false,
    # "jf_vip_em": true,
    # "name": "\u5f35\u5b0c\u5b0c",
    # "headUrl": "http:\/\/hd60.xiaonei.com\/photos\/hd60\/20071120\/20\/35\/head_2598k107.jpg"
# }
    
    destCmtDict['author'] = srcCmtDict['name'];
    
    renrenIdUrl = gConst['spaceDomain'] + "/" + str(srcCmtDict['author']);
    #print "renrenIdUrl=",renrenIdUrl;
    destCmtDict['author_url'] = renrenIdUrl;

    #localTime = srcCmtDict['time'].strptime("%Y-%m-%d %H:%M");
    localTime = datetime.strptime(srcCmtDict['time'], "%Y-%m-%d %H:%M");
    #print "localTime=",localTime;
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    #print "gmtTime=",gmtTime;
    destCmtDict['date'] = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");

    destCmtDict['content'] = srcCmtDict['body'];
    
    destCmtDict['author_email'] = "";    
    destCmtDict['author_IP'] = "";
    destCmtDict['approved'] = 1;
    destCmtDict['type'] = '';
    destCmtDict['parent'] = 0;
    destCmtDict['user_id'] = 0;
    
    logging.debug("author       =%s", destCmtDict['author']);
    logging.debug("author_url   =%s", destCmtDict['author_url']);
    logging.debug("date         =%s", destCmtDict['date']);
    logging.debug("date_gmt     =%s", destCmtDict['date_gmt']);
    logging.debug("content      =%s", destCmtDict['content']);
    
    #print "fill comments %d OK"%(destCmtDict['id']);
    
    return;
    
#------------------------------------------------------------------------------
# parse all comments list
def parseAllCommentsList(commentsList, parsedCommentsList):
    #print "total %d comments list to parse"%(len(commentsList));
    for (cmtIdx, srcCmtDict) in enumerate(commentsList) :
        destCmtDict = {};
        cmtId = cmtIdx + 1;
        #print "type(srcCmtDict)=",type(srcCmtDict);
        #print "before fill comment: %d"%(cmtId);
        fillComments(destCmtDict, srcCmtDict, cmtId);
        parsedCommentsList.append(destCmtDict);
    return;

#------------------------------------------------------------------------------
# parse single source comment soup into dest comment dict 
def parseCmtSoup(destCmtDict, srcCmtSoup, cmtId):
    destCmtDict['id'] = cmtId;

    #print "destCmtDict['id']=",destCmtDict['id'];
    logging.debug("--- comment[%d] ---", destCmtDict['id']);
    logging.debug("srcCmtSoup=%s", srcCmtSoup);
    
    # <li id="comment_1498131877">
    # <div class="comment">
    # <div class="picture">
    # <a class="usericon" href="http://www.renren.com/profile.do?id=234648737">	
    # <img alt="234648737" src="http://hd31.xiaonei.com/photos/hd31/20071104/08/27/head_812k171.jpg" /></a></div>
    # <div class="info">
    # <span class="author">
    # <a href="http://www.renren.com/profile.do?id=234648737">李发龙</a>
    # </span>
    # <!-- 管理员具有回复别人日志的功能 -->
    # <!--别人的评论--><span class="timestamp">2010年06月01日 11:29:59 </span><span class="reply-report"><a target="_blank" href="http://admin.renren.com/admin/newuserreport.do?type=23&owner=699092813&contentId=1498131877&userId=234648737&origURL=http://page.renren.com/699092813/note/468796168">举报</a></span>
    # </div><!-- 评论的正文 -->
    # <div class="text-content">
    # 沙发
    # </div>
    # </div>
    # </li>
    
    foundAuthor = srcCmtSoup.find(attrs={"class":"author"});
    #print "foundAuthor=",foundAuthor;
    authorA = foundAuthor.a;
    #print "authorA=",authorA;
    authorUrl = authorA['href'];
    #print "authorUrl=",authorUrl;
    authorName = authorA.string;
    #print "authorName=",authorName;
    
    #print "type(authorName)=",type(authorName);
    
    destCmtDict['author'] = unicode(authorName);
    destCmtDict['author_url'] = authorUrl;
    
    foundTimestamp = srcCmtSoup.find(attrs={"class":"timestamp"});
    #print "foundTimestamp=",foundTimestamp;
    timestamp = foundTimestamp.string.strip();
    #timestamp = unicode(timestamp);
    timestamp = timestamp.encode("UTF-8");
    #print "timestamp=",timestamp;
    localTime = datetime.strptime(timestamp, "%Y年%m月%d日 %H:%M:%S");
    #localTime = datetime.strptime(timestamp, u"%Y年%m月%d日 %H:%M:%S"); #2010年06月01日 11:29:59
    #print "localTime=",localTime;
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    #print "gmtTime=",gmtTime;
    destCmtDict['date'] = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");
    
    foundCmtBody = srcCmtSoup.find(attrs={"class":"text-content"});
    #print "foundCmtBody=",foundCmtBody;
    cmtBody = foundCmtBody.string;
    #print "cmtBody=",cmtBody;
    #cmtBodyUni = cmtBody.decode("UTF-8");
    cmtBodyUni = unicode(cmtBody);
    destCmtDict['content'] = cmtBodyUni;
    #print "destCmtDict['content']=",destCmtDict['content'];
        
    destCmtDict['author_email'] = "";
    destCmtDict['author_IP'] = "";
    destCmtDict['approved'] = 1;
    destCmtDict['type'] = "";
    destCmtDict['parent'] = 0;
    destCmtDict['user_id'] = 0;
    
    logging.debug("author       =%s", destCmtDict['author']);
    logging.debug("author_url   =%s", destCmtDict['author_url']);
    logging.debug("date         =%s", destCmtDict['date']);
    logging.debug("date_gmt     =%s", destCmtDict['date_gmt']);
    logging.debug("content      =%s", destCmtDict['content']);
    
    #print "fill comments %4d OK"%(destCmtDict['id']);
    
    return ;

#------------------------------------------------------------------------------
# extract out the comment <li> soup list from input html
def extractCmtLiSoupList(html):
    cmtSoupList = [];
    
    #print "in extractCmtLiSoupList";
    soup = htmlToSoup(html);
    
    #<div id="comments" class="clearfix"><ol class="commentlist" id="commentlist">
    foundCommentList = soup.find(id="commentlist");
    #print "foundCommentList=",foundCommentList;
    if(foundCommentList):
        cmtSoupList = foundCommentList.findAll("li");
        #print "cmtSoupList=",cmtSoupList;
        #print "len(cmtSoupList)=",len(cmtSoupList);

    return cmtSoupList;

#------------------------------------------------------------------------------
# extract blogId(post id) string from input perma link url
def extractIdFromUrl(url):
    (ownerId, blogId) = ("", "");
    foundId = re.search("http://blog\.renren\.com/blog/(?P<ownerId>\d+)/(?P<blogId>\d+)/?", url);
    if(foundId):
        ownerId = foundId.group("ownerId");
        blogId = foundId.group("blogId");
    logging.debug("Extract out ownerId=%s, blogId=%s from url=%s", ownerId, blogId, url);
    return (ownerId, blogId);

#------------------------------------------------------------------------------
# parse the comments json string
# return the cmtInfoDict
def parseCommentsJson(commentsJson):
    #{"hasMore":false,"code":0,"commentCount":1,"msg":"","comments":[{"wap":false,"body":"\u6539\u7248\u524d\u662f\u5f88\u597d\u7684\u6539\u7248\u5f8cBUG\u5f88\u591a\u5f88\u591a\u3002\u3002\u3002\u800c\u4e14\u5546\u696d\u5316\u6c23\u5473\u8d8a\u9aee\u6fc3\u70c8","isVip":false,"likeCount":0,"ilike":false,"keepUse":false,"id":4.06012649e8,"author":222509218,"time":"2008-01-13 10:46","share":false,"whisper":false,"jf_vip_em":true,"name":"\u5f35\u5b0c\u5b0c","headUrl":"http:\/\/hd60.xiaonei.com\/photos\/hd60\/20071120\/20\/35\/head_2598k107.jpg"}]}
    
    try:
        cmtInfoDict = json.loads(commentsJson);
    except:
        logging.debug("Fail to parse the input commentsJson=\n%s", commentsJson);

    return (hasMore, totalNum, curGotNum);
    
#------------------------------------------------------------------------------
# fetch and parse comments 
# return the parsed dict value
def fetchAndParseComments(url, html):
    parsedCommentsList = [];
        
    try :
        if(isUnloginPageMode()) :
            #logging.debug("fetchAndParseComments:html=%s", html);
            
            soup = htmlToSoup(html);

            #total comments number:
            # <p class="stat-article">
            # 阅读(2974)<span class="pipe">|</span>评论(20)
            # </p>
            
            # <p class="stat-article">
            # 阅读(7410)<span class="pipe">|</span>评论(113)
            # </p>
            
            foundStat = soup.find(attrs={"class":"stat-article"});
            logging.debug("found stat-article=%s", foundStat);
            #print "foundStat.contents=",foundStat.contents;
            #cmtNumStr = foundStat.string;
            cmtNumStr = foundStat.contents[2]; #[u'\n\u9605\u8bfb(7410)', <span class="pipe">|</span>, u'\u8bc4\u8bba(113)\n']
            #print "cmtNumStr=",cmtNumStr;
            cmtNumStrUni = unicode(cmtNumStr);
            #print "cmtNumStrUni=",cmtNumStrUni;
            foundCmtNum = re.search(u"评论\((?P<cmtNum>\d+)\)", cmtNumStrUni);
            #print "foundCmtNum=",foundCmtNum;
            totalCmtNum = foundCmtNum.group("cmtNum");
            #print "totalCmtNum=",totalCmtNum;
            totalCmtNum = int(totalCmtNum);
            #print "totalCmtNum=\t",totalCmtNum;
            
            allCmtSoupList = [];
            
            # got comments in current page
            foundLiList = extractCmtLiSoupList(html);
            allCmtSoupList.extend(foundLiList);
            fetchedCmtNum = len(foundLiList);

            # get more if exist
            maxNumPerPage = 100;
            remainCmtNum = totalCmtNum - fetchedCmtNum;
            logging.debug("totalCmtNum=%d, fetchedCmtNum=%d, remainCmtNum=%d", totalCmtNum, fetchedCmtNum, remainCmtNum);
            cmtPageIdx = 0;
            # get remain comments
            while((fetchedCmtNum >= maxNumPerPage) and (remainCmtNum > 0)) :
                # only fetch more if one page can not show all 100 comments
                # if less than 100, no need to fetch more(
                # even if some page has error, lack several(1/2/...) commments than expected in 评论(xxx)
                
                fetchedCmtList = [];
                
                # get one page comments
                cmtPageIdx += 1;
                
                #http://page.renren.com/699092813/note/468827150?curpage=1
                getCmtUrl = url + "?curpage=" + str(cmtPageIdx);
                logging.debug("open %s to get more comment", getCmtUrl);
                respHtml = crifanLib.getUrlRespHtml(getCmtUrl);
                logging.debug("for extract more comments, got respHtml=\n%s", respHtml);
                
                # extract out
                fetchedCmtList = extractCmtLiSoupList(respHtml);
                fetchedCmtNum = len(fetchedCmtList);
                
                if(fetchedCmtNum > 0):
                    # extend to list
                    allCmtSoupList.extend(fetchedCmtList);
                    
                    # update
                    stillRemainCmtNum = remainCmtNum - fetchedCmtNum;
                    logging.debug("remainCmtNum=%d, fetchedCmtNum=%d, stillRemainCmtNum=%d", remainCmtNum, fetchedCmtNum, stillRemainCmtNum);
                    remainCmtNum = stillRemainCmtNum;
                else :
                    # also some special case: 
                    # http://page.renren.com/699092813/note/468980324 contain 评论(14) comments, but page 0 actually only contains 13 comments
                    # then later call next page, return no more comments here
                    logging.debug("Expected fetch more comments, but return no comments, so break here");
                    break;
            
            #print "len allCmtSoupList= %d"%(len(allCmtSoupList));
            for cmtIdx, srcCmtSoup in enumerate(allCmtSoupList):
                #each comment string:
                
                destCmtDict = {};
                cmtId = cmtIdx + 1;
                #print "type(srcCmtSoup)=",type(srcCmtSoup);
                parseCmtSoup(destCmtDict, srcCmtSoup, cmtId);
                parsedCommentsList.append(destCmtDict);
                #print "len(parsedCommentsList)=",len(parsedCommentsList);
            
            #print "total parsed comments= %d"%(len(parsedCommentsList));
        else:
            logging.debug("fetchAndParseComments:html=%s", html);
            
            #headUrl:"hdn321/20100114/2040/h_head_YLsl_39280000fe1b2f76.jpg", #comments:{"hasMore":false,"code":0,"commentCount":1,"msg":"","comments":[{"wap":false,"body":"\u6539\u7248\u524d\u662f\u5f88\u597d\u7684\u6539\u7248\u5f8cBUG\u5f88\u591a\u5f88\u591a\u3002\u3002\u3002\u800c\u4e14\u5546\u696d\u5316\u6c23\u5473\u8d8a\u9aee\u6fc3\u70c8","isVip":false,"likeCount":0,"ilike":false,"keepUse":false,"id":4.06012649e8,"author":222509218,"time":"2008-01-13 10:46","share":false,"whisper":false,"jf_vip_em":true,"name":"\u5f35\u5b0c\u5b0c","headUrl":"http:\/\/hd60.xiaonei.com\/photos\/hd60\/20071120\/20\/35\/head_2598k107.jpg"}]}
            
            foundCmtJsonStr = re.search(r'headUrl:".+?",\s*?comments:(?P<commentsJson>.+?)\s+?\}\);', html);
            if(foundCmtJsonStr) :
                commentsJson = foundCmtJsonStr.group("commentsJson");
                #print "commentsJson=",commentsJson;
                cmtInfoDict = json.loads(commentsJson);
                #print "cmtInfoDict=",cmtInfoDict;
                
                allCommentsList = [];
                # parse current got comments
                curGotCmtList = cmtInfoDict['comments'];
                allCommentsList.extend(curGotCmtList);

                logging.debug("hasMore=%s, totalCmtNum=%d, curGotCmtNum=%d", cmtInfoDict['hasMore'], cmtInfoDict['commentCount'], len(curGotCmtList));

                # for output info use
                maxNumReportOnce = 200;
                lastRepTime = 0;
                
                if(cmtInfoDict['hasMore']) :
                    # init some value
                    (ownerId, blogId) = extractIdFromUrl(url);
                        
                    #XN = {get_check:'1493138945',get_check_x:'24c07c5b',env:{domain:'renren.com',shortSiteName:'人人',siteName:'人人网'}};
                    foundGetCheckjson = re.search("XN = {get_check:'(?P<get_check>\w+)',get_check_x:'(?P<get_check_x>\w+)',env:", html);
                    getCheck    = foundGetCheckjson.group("get_check");
                    getCheckX   =  foundGetCheckjson.group("get_check_x");
                    
                    # need get more 
                    while(cmtInfoDict['hasMore']):
                        logging.debug("now to get more comments");
                        
                        firstCmt = curGotCmtList[0];
                        #print "firstCmt=",firstCmt;
                        cmtId = firstCmt['id'];
                        #print "cmtId=",cmtId; #cmtId= 1921778984.0
                        cmtId = int(cmtId);
                        #print "cmtId=",cmtId; #cmtId= 1921778984
                        
                        logging.debug("Before get more comments, cmtId=%d, blogId=%s, ownerId=%s, getCheck=%s, getCheckX=%s", 
                            cmtId, blogId, ownerId, getCheck, getCheckX);
                        #cmtId=1921778984&blogId=786201206&owner=253362819&requestToken=1493138945&_rtk=24c07c5b
                        postDict = {
                            'cmtId' : cmtId,
                            'blogId': blogId,
                            'owner' : ownerId,
                            'requestToken': getCheck,
                            '_rtk'  : getCheckX,
                        };
                        # here no need to access http://blog.renren.com/blog/253362819/786201206/comment/list/by-1921778984
                        # for it will auto redirect to that address, then return comments json string
                        reqCmtListUrl = "http://blog.renren.com/AjaxGetBlogCommentList.do";
                        respJson = crifanLib.getUrlRespHtml(reqCmtListUrl, postDict=postDict);
                        
                        #logging.debug("in get more comments, respJson=%s", respJson);
                        cmtInfoDict = json.loads(respJson);
                        curGotCmtList = cmtInfoDict['comments'];
                        
                        allCommentsList.extend(curGotCmtList);
                        logging.debug("after get more comments: hasMore=%s, totalCmtNum=%d, curGotCmtNum=%d, totalHasGotNum=%d", cmtInfoDict['hasMore'], cmtInfoDict['commentCount'], len(curGotCmtList), len(allCommentsList));
                        
                        # report processed comments if exceed certain number
                        processedNum = len(allCommentsList);
                        curRepTime = processedNum/maxNumReportOnce;
                        if(curRepTime != lastRepTime) :
                            # report
                            logging.info("    Has fetched comments: %5d", processedNum);
                            # update
                            lastRepTime = curRepTime;

                parseAllCommentsList(allCommentsList, parsedCommentsList);
            else:
                logging.debug("Can not found comments string from returned htm=\n%s", html);
                logging.warning("Can not found comments string for url=%s", url);
    except:
        logging.warning("Error while fetch and parse comment for %s", url);
    
    logging.debug("len(parsedCommentsList)=%d", len(parsedCommentsList));
    
    return parsedCommentsList;


#------------------------------------------------------------------------------
# extract blog title and description
def extractBlogTitAndDesc(blogEntryUrl) :
    (blogTitle, blogDescription) = ("", "");
    
    #print "input blogEntryUrl=",blogEntryUrl;
    
    try:
        blogTitle = unicode(gVal['blogUser']);
        blogDescription = unicode(gVal['blogUser']);

    except:
        (blogTitle, blogDescription) = ("", "");

    return (blogTitle, blogDescription);

#------------------------------------------------------------------------------
# possible date format
def parseDatetimeStrToLocalTime(datetimeStr):
    parsedLocalTime = None;

    #2007-10-13 23:45
    foundPat1 = re.search(r"(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+) (?P<hour>\d+):(?P<minute>\d+)(:(?P<second>\d+))?", datetimeStr);
    #print "foundPat1=",foundPat1;

    #2010年06月01日 11:28:44
    foundPat2 = re.search(u"(?P<year>\d+)年(?P<month>\d+)月(?P<day>\d+)日 (?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)", datetimeStr);
    #print "foundPat2=",foundPat2;

    if(foundPat1):
        found = foundPat1;
    elif(foundPat2):
        found = foundPat2;
    else:
        found = False;

    if(found) :
        year    = found.group("year");
        month   = found.group("month");
        day     = found.group("day");
        hour    = found.group("hour");
        minute  = found.group("minute");
        second  = found.group("second");
        #print "second=",second;
        if(not second):
            second = "00";
        
        genDatatimeStr = "%s-%s-%s %s:%s:%s"%(year, month, day, hour, minute, second);
        parsedLocalTime = datetime.strptime(genDatatimeStr, "%Y-%m-%d %H:%M:%S"); # here is GMT+8 local time

    logging.debug("Converted datetime string %s to datetime value %s", datetimeStr, parsedLocalTime);
    return parsedLocalTime;

#------------------------------------------------------------------------------
# check whether is self blog pic
# depend on following picInfoDict definition
def isSelfBlogPic(picInfoDict):
    isSelfPic = False;
    
    filename = picInfoDict['filename'];
    fd1 = picInfoDict['fields']['fd1'];
    fd2 = picInfoDict['fields']['fd2'];

    if (fd1=='fmn') and (fd2=='rrimg'):
        isSelfPic = True;
    else :
        isSelfPic = False;
        
    logging.debug("isSelfBlogPic: %s", isSelfPic);

    return isSelfPic;

#------------------------------------------------------------------------------
def getProcessPhotoCfg():
    # possible own site pic link:

    # http://blog.renren.com/blog/229351756/796486456?from=fanyeOld contain:
    # http://fmn.rrimg.com/fmn057/20111227/1525/b_large_76Bv_7a8600004075125b.jpg
    # -> html is:
    #<p> <img src="http://fmn.rrimg.com/fmn057/20111227/1525/b_large_76Bv_7a8600004075125b.jpg" border="0" alt="" /></p>
    # ...<img src="http://s.xnimg.cn//imgpro/emotions/tie/7.gif" border="0" alt="惊恐" />

    # http://page.renren.com/699092813/note/818973150 contain:
    # http://fmn.rrimg.com/fmn059/20120410/1440/b_large_A3t5_7de3000021f51262.jpg

    # http://fmn.rrimg.com/fmn057/20120410/1550/b_large_QHBL_1c8900000a371263.jpg
    # http://page.renren.com/699092813/note/818988007?ref=hotnewsfeed&sfet=2012&fin=2&ff_id=699092813&feed=page_blog&tagid=818988007&statID=page_699092813_2&level=1 contain:

    # http://page.renren.com/600429402/note/818979639?ref=hotnewsfeed&sfet=2012&fin=13&ff_id=600429402&feed=page_blog&tagid=818979639&statID=page_600429402_2&level=1 contain:
    # http://fmn.rrimg.com/fmn061/20120410/1505/b_large_OFx8_3a0700007a7f1261.jpg
    # http://fmn.rrimg.com/fmn059/20120410/1030/b_large_XbH2_188400000b5c1261.jpg

    #http://blog.renren.com/blog/229351756/262929661?from=fanyeNew contain html:
    #需要改进的地方<IMG alt=难过 src="http://static.xiaonei.com/img/editor/emot/emot-11.gif">
    
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

####### Login Mode ######

#------------------------------------------------------------------------------
# check whether login is OK
# if true, return true and homeUrl
# if false, return error info string
# possible input:
#{"catchaCount":2,"code":false,"homeUrl":"http://www.renren.com/SysHome.do?origURL=http%3A%2F%2Fwww.renren.com%2Fhome&catchaCount=2&failCode=4","failDescription":"您的用户名和密码不匹配","failCode":4,"email":"green-waste@163.com"}
#{"catchaCount":3,"code":false,"homeUrl":"http://www.renren.com/SysHome.do?origURL=http%3A%2F%2Fwww.renren.com%2Fhome&catchaCount=3&failCode=4","failDescription":"您的用户名和密码不匹配","failCode":4,"email":"green-waste@163.com"}
#{"catchaCount":3,"code":false,"homeUrl":"http://www.renren.com/SysHome.do?origURL=http%3A%2F%2Fwww.renren.com%2Fhome&catchaCount=3&failCode=512","failDescription":"您输入的验证码不正确","failCode":512,"email":"green-waste@163.com"}
#{"code":true,"homeUrl":"http://www.renren.com/callback.do?t=a951001569377c7c22013b37c39b697a6&origURL=http%3A%2F%2Fwww.renren.com%2Fhome&needNotify=false"}
def isLoginOk(respCodeJson):
    (isOk, homeUrl, failDescription) = (False, "Default: Invalid Home Url", "Default: No Fail Description");
    codeDict = json.loads(respCodeJson);
    logging.debug("parse login return json ok");
    #print "codeDict=",codeDict;
    isOk = codeDict['code'];
    homeUrl = codeDict['homeUrl'];
    logging.debug("isOk=%s, homeUrl=%s", isOk, homeUrl);
    if(not isOk):
        # if login true, then no failDescription
        if('failDescription' in codeDict):
            failDescription = codeDict['failDescription'];

    return (isOk, homeUrl, failDescription);
    
#------------------------------------------------------------------------------
# log in Blog
def loginBlog(username, password) :
    loginOk = False;
    
    gVal['cj'] = cookielib.CookieJar();
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(gVal['cj']));
    urllib2.install_opener(opener);
    
    # 1. fetch get_check_x
    renrenHomeUrl = "http://www.renren.com/";
    respHtml = crifanLib.getUrlRespHtml(renrenHomeUrl);
    #XN = {get_check:'',get_check_x:'c5f17df8',env:{domain:'renren.com',shortSiteName:'人人',siteName:'人人网'}};
    foundGetCheckX = re.search("XN\s.*?=\s.*?\{get_check:'.*?',get_check_x:'(?P<get_check_x>\w+)'.+?\}", respHtml);
    logging.debug("foundGetCheckX=%s", foundGetCheckX);
    if(foundGetCheckX):
        get_check_x = foundGetCheckX.group("get_check_x");
        logging.debug("get_check_x=%s", get_check_x);

    # 2. getcode
    #http://icode.renren.com/getcode.do?t=web_login&rnd=Math.random()
    getcodeUrl = "http://icode.renren.com/getcode.do?t=web_login";
    respHtml = crifanLib.getUrlRespHtml(getcodeUrl);
    #logging.info("respHtml=%s", respHtml);
    logging.debug("now will import PIL module for renren verify code");
    from PIL import Image;
    logging.debug("import PIL module OK");
    img = Image.open(StringIO.StringIO(respHtml));
    # 如果看不到图片，请参考：
    #【已解决】Python中通过Image的open之后，去show结果打不开bmp图片，无法正常显示图片
    #http://www.crifan.com/python_image_show_can_not_open_bmp_image_file/
    img.show();

    hintStr = unicode("请输入所看到的(4个字母的)验证码：", "utf-8");
    icode = raw_input(hintStr.encode("GB18030"));
    logging.info("Your input verify code is %s", icode);

    # 3. show captcha
    getCaptchaUrl = "http://www.renren.com/ajax/ShowCaptcha";
    # email=shidong84%40googlemail.com&
    # password=&
    # icode=&
    # origURL=http%3A%2F%2Fwww.renren.com%2Fhome&
    # domain=renren.com&
    # key_id=1&
    # captcha_type=web_login&
    # _rtk=c5f17df8
    postDict = {
        'email'     : username,
        'password'  : "",
        'icode'     : "",
        'origURL'   : "http://www.renren.com/home",
        'domain'    : "renren.com",
        'key_id'    : "1",
        'captcha_type':"web_login",
        '_rtk'      : get_check_x,
    }
    respHtml = crifanLib.getUrlRespHtml(getCaptchaUrl, postDict);
    logging.debug("getCaptchaUrl=%s, respHtml=%s", getCaptchaUrl, respHtml);
    
    # 4. login
    loginUrl = "http://www.renren.com/ajaxLogin/login";
    postDict = {
        'email'     : username,
        'password'  : password,
        'icode'     : icode,
        'origURL'   : "http://www.renren.com/home",
        'domain'    : "renren.com",
        'key_id'    : "1",
        'captcha_type':"web_login",
        '_rtk'      : get_check_x, #"c60cc3e6", "c5f17df8"
    };

    respJson = crifanLib.getUrlRespHtml(loginUrl, postDict);
    logging.debug('renren login return json:\n%s', respJson);
    
    (loginOk, homeUrl, failDescription) = isLoginOk(respJson);
    logging.debug("loginOk=%s, homeUrl=%s, failDescription=%s", loginOk, homeUrl, failDescription);
    if(loginOk) :
        logging.debug("%s login Renren OK, returned homeUrl=%s", username, homeUrl);
    else :
        logging.error("%s login Renren fail for %s", username, failDescription);
        #之前通过重新在网页登陆人人后，此脚本中，即可消除此验证码错误的问题了
        #但是现在 2012-09-04,好像此方法已失效，登陆时，必须输入验证码
        
        #如果出现验证码错误，请重新运行此脚本

        # foundFailcode = re.search(r"&failCode=(?P<failCode>\d+)", homeUrl);
        # logging.debug("foundFailcode=%s", foundFailcode);
        # if(foundFailcode):
            # failCode = foundFailcode.group("failCode");
            # #failCode=4","failDescription":"您的用户名和密码不匹配"
            # #failCode=512","failDescription":"您输入的验证码不正确"
            # if((failCode=="512") and (failDescription==u"您输入的验证码不正确")):
                # #try re-login, need verify code
                # logging.debug("now will try re-login renren.");
    
    if(loginOk):
        resp = crifanLib.getUrlResponse(homeUrl);
        respInfo = resp.info();
        logging.debug("access %s respInfo=%s", homeUrl, respInfo);
        
        #loginfrom=null; domain=.renren.com; path=/, feedType=229351756_hot; domain=www.renren.com; path=/; expires=Fri, 11-May-2012 02:31:21 GMT, JSESSIONID=abc8_MsdJQoJi6m6ApFAt; path=/
        loginedCookiesStr = respInfo['Set-Cookie'];
        logging.debug("loginedCookiesStr=%s", loginedCookiesStr);
        foundFeedType = re.search(r"feedType=(?P<loginId>\d+)_hot;", loginedCookiesStr);
        logging.debug("foundFeedType=%s", foundFeedType);
        loginId = foundFeedType.group("loginId");
        logging.debug("loginId=%s", loginId);
        if(isLoginSelfMode() and (loginId != gVal['blogUser'])):
            gVal['blogUser'] = loginId;
            gVal['blogEntryUrl'] = "http://blog.renren.com/blog/" + gVal['blogUser'] + "/friends";
            gVal['curMode'] = gConst['mode']['viewFriend'];
            logging.info("After login, change to the real mode: %s", gVal['curMode']);
    
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
if __name__=="BlogQQ":
    print "Imported: %s,\t%s"%( __name__, __VERSION__);