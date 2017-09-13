#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for XXX Blog.


[History]
[v1.0 2012-12-05]
1.initial version

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
__VERSION__ = "v1.0";

gConst = {
    'spaceDomain'   : 'http://www.XXX.com',

    'htmlCharset'   : "UTF-8", #change to the html charset of blog post
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',   # yyy
    'blogEntryUrl'  : '',   # http://yyy.xxx.com
    'blogTitle'     : "",   # title
    'blogDescription':"",   # descrition
    
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
# from 
# to
def extractPostIdPermaLink(url):
    postId = "";

    return postId;

################################################################################
# Implemented Common Functions 
################################################################################

#------------------------------------------------------------------------------
# extract blog user name:
# (1)  from: 
# 
# 
# 
# (2)  from permanent link:
# 
# 
def extractBlogUser(inputUrl):

    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");
    logging.info("Extracting blog user from url=%s", inputUrl);
    
    blogId = "";
    
    try :
        # type1, main url:
        # 
        # 
        foundMainUrl = re.search("http://(?P<blogUser>[\w-]+)\.xxx\.com/?", inputUrl);
        logging.debug("foundMainUrl=%s", foundMainUrl);
        if(foundMainUrl) :
            extractedBlogUser = foundMainUrl.group("blogUser");
            generatedBlogEntryUrl = "http://" + extractedBlogUser + ".xxx.com";
            extractOk = True;
        
        # type2, perma link:
        # 
        # 
        if(not extractOk):
            foundPermalink = re.search("http://(?P<blogUser>[\w-]+)\.xxx\.com/yyyyyyyyyyy/?", inputUrl);
            logging.debug("foundPermalink=%s", foundPermalink);
            if(foundPermalink) :
                extractedBlogUser = foundPermalink.group("blogUser");
                generatedBlogEntryUrl = "http://" + extractedBlogUser + ".xxx.com";
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
        #
        someUrl = gVal['blogEntryUrl'] + "???";
        logging.debug("someUrl=%s", someUrl);
        respHtml = crifanLib.getUrlRespHtml(someUrl);
        logging.debug("respHtml=%s", respHtml);
        
        #TODO: write your own logic to find the first permanent link of post
                    # retInfo = lastHref;
                    # isFound = True;
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
        
        #TODO: write your own logic to extract blog title and description
        
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
        
        #TODO: write your own logic to extract title from url or/and its html
        
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
        
        #TODO: write your own logic to extract next perma link from url or/and its html
        
                    # nextLinkStr = prevPostHref;
                    # foundNext = True;

        logging.debug("Found next permanent link=%s, title=%s", nextLinkStr, nextPostTitle);
    except :
        logging.debug("Fail to extract next perma link from url=%s, html=\n%s", url, html);
        nextLinkStr = '';
        
    return nextLinkStr;

#------------------------------------------------------------------------------
# extract publish datetime string of current post
def extractDatetime(url, html) :
    datetimeStr = '';
    try :
        
        #TODO: write your own logic to extract post publish datatime from url or/and its html
        
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
    
        #TODO: write your own logic to extract content from url or/and its html
        
        #logging.debug("contentUni=%s", contentUni);
    except :
        logging.debug("Fail to extract post content from url=%s, html=\n%s", url, html);
        contentUni = '';
    
    return contentUni;

#------------------------------------------------------------------------------
# extract category
def extractCategory(url, html) :
    catUni = '';
    try :
        #TODO: write your own logic to extract category from url or/and its html
        #catUni = "";
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
                
        #TODO: write your own logic to extract tags from url or/and its html
        
                # if(foundAllTagA):
                    # for eachTagA in foundAllTagA:
                        # logging.debug("eachTagA=%s", eachTagA);
                        # tagAUni = eachTagA.string;
                        # logging.debug("tagAUni=%s", tagAUni);
                        # tagList.append(tagAUni);
                    # foundTag = True;
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
    
    destCmtDict['author'] = srcCmtDict['???'];
    #print "destCmtDict['author']=",destCmtDict['author'];
    
    destCmtDict['author_url'] = ???;
    #print "destCmtDict['author_url']=",destCmtDict['author_url'];
    
    localTime = ???;
    #print "localTime=",localTime;
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    #print "gmtTime=",gmtTime;
    destCmtDict['date']     = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");

    destCmtDict['content'] = ???;
    #print "destCmtDict['content']=",destCmtDict['content']; # some char will raise error for gbk can not show it

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
# fetch and parse comments 
# return the parsed dict value
def fetchAndParseComments(url, html):
    parsedCommentsList = [];
        
    try :
        #logging.debug("fetchAndParseComments_html=\n%s", html);
        
        soup = getSoupFromUrl(url);
        
        #TODO: get all source comment dict list
        
            parseAllCommentsList(allDictList, parsedCommentsList);
            logging.debug("total parsed %d comments", len(parsedCommentsList));
            #print "total parsed comments= %d"%(len(parsedCommentsList));
    except :
        logging.debug("Error while fetch and parse comment for %s", url);

    return parsedCommentsList;

#-------------------------------------------------------------------
# Picture process related functions
#-------------------------------------------------------------------

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

    if ((fd2=='???')and(fd3=='???')and(fd4=='com')):
        isSelfPic = True;
    else :
        isSelfPic = False;

    logging.debug("isSelfBlogPic: %s", isSelfPic);

    return isSelfPic;

#------------------------------------------------------------------------------
def getProcessPhotoCfg():
    # possible own site pic link:
    # type1:
    # ??? contain:
    # ???
    #
    
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
    parsedLocalTime = datetime.strptime(datetimeStr, '???');
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