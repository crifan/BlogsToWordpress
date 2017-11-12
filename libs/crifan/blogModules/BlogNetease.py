#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

For BlogsToWordpress, this file contains the functions for Netease 163 blog.

[TODO]
1. add support for friendOnly type post detect
2. support modify 163 post

[History]
[v1.8]
1. update for find nex post link

[v1.7]
1. add emotion into post
eg:
http://blog.163.com/ni_chen/blog/#m=1
-> 心情随笔
2.support direct input feeling card url:
BlogsToWordpress.py -f http://green-waste.blog.163.com/blog/#m=1
BlogsToWordpress.py -f http://blog.163.com/ni_chen/blog/#m=1

[v1.5]
1. update to fix bug: can not find first permanent link

[v1.4]
1. change charset from invalid GB18030 to valid UTF-8 when modify post.

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

#from PIL import Image;
import StringIO;


#--------------------------------const values-----------------------------------
__VERSION__ = "v1.7";

gConst = {
    'blogApi163'        : "http://api.blog.163.com",
}

#----------------------------------global values--------------------------------
gVal = {
    'blogUser'      : '',
    'blogEntryUrl'  : '',  # http://againinput4.blog.163.com
    'cj'            : None, # cookiejar, to store cookies for login mode

    'importedPil'   : False,
    'userId'        : '',   # for http://blog.163.com/ni_chen/, its user id is 186541395

    'special': {
        'feelingCard': {
            #'url'      : "http://api.blog.163.com/ni_chen/dwr/call/plaincall/FeelingsBeanNew.getRecentFeelingCards.dwr",
            #'url'      : "http://blog.163.com/ni_chen/blog/FeelingCard",
            #'url'       : "http://blog.163.com",
            'url'       : "",   # need updated after got blogUser, to:
                                #http://blog.163.com/ni_chen/blog/#m=1
                                #http://green-waste.blog.163.com/blog/#m=1
            'processed' : False,
        }
    }
}

################################################################################
# Internal 163 blog Functions
################################################################################

def htmlToSoup(html):
    soup = None;
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
# parse the dwr engine line, return the number of main comments
# possbile input:
# dwr.engine._remoteHandleCallback('1','0',[s0,s1]);
# dwr.engine._remoteHandleCallback('1','0',[]);
# dwr.engine._remoteHandleCallback('1','0',[s0,s1,...,s98,s99]);
def extratMainCmtNum(dwrEngine) :
    mainCmtNum = 0;
    foundSn = re.search(r".*\[(?P<sn>.*)\]", dwrEngine);
    if foundSn and foundSn.group("sn") :
        # parse it
        sList = foundSn.group("sn").split(",");
        mainCmtNum = len(sList);
    else :
        mainCmtNum = 0;
    return mainCmtNum;

def getPlaincallRespDwrStr(c0ScriptName, c0MethodName, c0Param0, c0Param1="", c0Param2=""):
    """
        get FeelingsBeanNew response DWR string
    """

    #sample1:
    # http://api.blog.163.com/againinput4/dwr/call/plaincall/BlogBeanNew.getComments.dwr
    # for: http://againinput4.blog.163.com/blog/static/172799491201010159650483/
    # [paras]
    # callCount=1
    # scriptSessionId=${scriptSessionId}187
    # c0-scriptName=BlogBeanNew
    # c0-methodName=getComments
    # c0-id=0
    # c0-param0=string:fks_094067082083086070082083080095085081083068093095082074085
    # c0-param1=number:1
    # c0-param2=number:0
    # batchId=728048
    #http://api.blog.163.com/againinput4/dwr/call/plaincall/BlogBeanNew.getComments.dwr?&callCount=1&scriptSessionId=${scriptSessionId}187&c0-scriptName=BlogBeanNew&c0-methodName=getComments&c0-id=0&c0-param0=string:fks_094067082083086070082083080095085081083068093095082074085&c0-param1=number:1&c0-param2=number:0&batchId=728048


    #sample2:
    # callCount=1
    # scriptSessionId=${scriptSessionId}187
    # c0-scriptName=FeelingsBeanNew
    # c0-methodName=getRecentFeelingsComment
    # c0-id=0
    # c0-param0=string:134875456
    # c0-param1=number:1
    # c0-param2=number:0
    # batchId=705438

    #sample3:
    # callCount=1
    # scriptSessionId=${scriptSessionId}187
    # c0-scriptName=FeelingsBeanNew
    # c0-methodName=getRecentFeelingCards
    # c0-id=0
    # c0-param0=number:186541395
    # c0-param1=number:0
    # c0-param2=number:20
    # batchId=292545

    #sample4:
    #http://api.blog.163.com/ni_chen/dwr/call/plaincall/BlogBeanNew.getBlogs.dwr
    #callCount=1
    #scriptSessionId=${scriptSessionId}187
    #c0-scriptName=BlogBeanNew
    #c0-methodName=getBlogs
    #c0-id=0
    #c0-param0=number:186541395
    #c0-param1=number:0
    #c0-param2=number:1
    #batchId=494302

    #sample5:
    # http://api.blog.163.com/againinput4/dwr/call/plaincall/BlogBeanNew.getBlogs.dwr
    # callCount=1
    # scriptSessionId=${scriptSessionId}187
    # c0-scriptName=BlogBeanNew
    # c0-methodName=getBlogs
    # c0-id=0
    # c0-param0=number:172799491
    # c0-param1=number:0
    # c0-param2=number:20
    # batchId=955290

    logging.debug("get FeelingsBeanNew reponse DWR string for c0MethodName=%s, c0Param0=%s, c0Param1=%s, c0Param2=%s", c0MethodName, c0Param0, c0Param1, c0Param2);

    postDict = {
        'callCount'     :   '1',
        'scriptSessionId':  '${scriptSessionId}187',
        'c0-scriptName' :   c0ScriptName, #BlogBeanNew/FeelingsBeanNew
        'c0-methodName' :   c0MethodName, #getComments/getRecentFeelingsComment/getRecentFeelingCards
        'c0-id'         :   '0',
        'c0-param0'     :   c0Param0,
        # 'c0-param1'     :   c0Param1,
        # 'c0-param2'     :   c0Param2,
        'batchId'       :   '1', # should random generate number?
    };

    if c0Param1 :
        postDict['c0-param1'] = c0Param1

    if c0Param2 :
        postDict['c0-param2'] = c0Param2

    #http://api.blog.163.com/againinput4/dwr/call/plaincall/BlogBeanNew.getComments.dwr
    #http://api.blog.163.com/ni_chen/dwr/call/plaincall/FeelingsBeanNew.getRecentFeelingsComment.dwr
    #http://api.blog.163.com/ni_chen/dwr/call/plaincall/FeelingsBeanNew.getRecentFeelingCards.dwr
    #http://api.blog.163.com/againinput4/dwr/call/plaincall/BlogBeanNew.getBlogs.dwr
    plaincallDwrUrl = gConst['blogApi163'] + '/' + gVal['blogUser'] + '/' + "dwr/call/plaincall/" + c0ScriptName + "." + c0MethodName + ".dwr";
    logging.debug("plaincallDwrUrl=%s", plaincallDwrUrl);

    #Referer	http://api.blog.163.com/crossdomain.html?t=20100205
    headerDict = {
        'Referer'       :   "http://api.blog.163.com/crossdomain.html?t=20100205",
        'Content-Type'  :   "text/plain",
    };
    plaincallRespDwrStr = crifanLib.getUrlRespHtml(plaincallDwrUrl, postDict=postDict, headerDict=headerDict, postDataDelimiter='\r\n');
    logging.debug("plaincallRespDwrStr=%s", plaincallRespDwrStr);

    return plaincallRespDwrStr;

#------------------------------------------------------------------------------
# replace the character entity references into slash + u + code point
# eg: &#10084; => \u2764 (10084=0x2764)
# more info refer: http://againinput4.blog.163.com/blog/static/1727994912011112295423982/
def replaceChrEntityToSlashU(text):
    unicodeP = re.compile(r'&#\d+;');
    def transToSlashU(match): # translate the matched string to slash unicode
        numStr = match.group(0)[2:-1]; # remove '&#' and ';'
        num = int(numStr);
        hex04x = "%04x" % num;
        slasU = '\\' + 'u' + str(hex04x);
        return slasU;
    return unicodeP.sub(transToSlashU, text);

#------------------------------------------------------------------------------
# replace '&amp;amp;' to '&amp;' in:
# s8.publisherNickname="\u5FE7\u5BDE&amp;amp;\u6CA7\u6851\u72FC";s8.publisherUrl=
# s29.replyToUserNick="\u8001\u9F20\u7687\u5E1D&amp;amp;\u9996\u5E2D\u6751\u5987";s29.shortPublishDateStr
# to makesure string is valid, then following can parse correct
def validateString(text):
    text = text.replace("&amp;amp;", "&amp;");
    return text;

#------------------------------------------------------------------------------
# parse the subComments field, to get the parent idx
def parseSubComments(subComments) :
    # s0.subComments=s2
    equalSplited = subComments.split("=");
    sChild = equalSplited[1]; # s2
    childIdx = int(sChild[1:]); # 2
    return childIdx;

#------------------------------------------------------------------------------
# parse each comment response line string into a dict value
def parseCmtRespStr(line, cmtCurNum) :
    # s0['abstract'] = "\u7528\u817E\u8BAF\u7684QQ\u7535\u8111\u7BA1\u5BB6\u53EF\u4EE5\u67E5\u51FA\u6765";
    # s0.blogId = "fks_094074080084085071086094085095085081083068093095082074085";
    # s0.blogPermalink = "blog/static/1727994912011390245695";
    # s0.blogTitle = "\u3010\u5DF2\u89E3\u51B3\u3011\u7F51\u9875\u65E0\u6CD5\u6253\u5F00\uFF0CIE\u8BCA\u65AD\u7ED3\u679C\u4E3A\uFF1Awindows\u65E0\u6CD5\u4F7F\u7528HTTP HTTPS\u6216\u8005FTP\u8FDE\u63A5\u5230Internet";
    # s0.blogUserId = 172799491;
    # s0.blogUserName = "againinput4";
    # s0.circleId = 0;
    # s0.circleName = null;
    # s0.circleUrlName = null;
    # s0.content = "<P>\u7528\u817E\u8BAF\u7684QQ\u7535\u8111\u7BA1\u5BB6\u53EF\u4EE5\u67E5\u51FA\u6765</P>";
    # s0.id = "fks_081068083085088067084095080095085081083068093095082074085";
    # s0.ip = "175.191.25.231";
    # s0.ipName = "\u5E7F\u4E1C \u6DF1\u5733";
    # s0.lastUpdateTime = 1322129849392;
    # s0.mainComId = "-1";
    # s0.moveFrom = null;
    # s0.popup = false;
    # s0.publishTime = 1322129849397;
    # s0.publishTimeStr = "18:17:29";
    # s0.publisherAvatar = 0;
    # s0.publisherAvatarUrl = "http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";
    # s0.publisherEmail = "";
    # s0.publisherId = 0;
    # s0.publisherName = null;
    # s0.publisherNickname = "\u957F\u5927\u662F\u70E6\u607C";
    # s0.publisherUrl = null;
    # s0.replyComId = "-1";
    # s0.replyToUserId = 172799491;
    # s0.replyToUserName = "againinput4";
    # s0.replyToUserNick = "crifan";
    # s0.shortPublishDateStr = "2011-11-24";
    # s0.spam = 0;
    # s0.subComments = s1;
    # s0.synchMiniBlog = false;
    # s0.valid = 0;

    #s0['abstract']="\u6B22\u8FCE\u6D4F\u89C8\u6211\u7684\u7FFB\u8BD1\u535A\u5BA2\uFF0C\u591A\u591A\u4EA4\u6D41\uFF01";s0.blogId="fks_087067093094084066082084080066072085083069083081080068092";s0.blogPermalink="blog/static/32677678201221810654675";s0.blogTitle="\u642C\u5BB6\u58F0\u660E\uFF1A\u672C\u535A\u5BA2\u5DF2\u642C\u5BB6\u81F3http://www.crifan.com/";s0.blogUserId=32677678;s0.blogUserName="green-waste";s0.circleId=0;s0.circleName=null;s0.circleUrlName=null;s0.content="\u6B22\u8FCE\u6D4F\u89C8\u6211\u7684\u7FFB\u8BD1\u535A\u5BA2\uFF0C<div>\u591A\u591A\u4EA4\u6D41\uFF01<img src=\"http://b.bst.126.net/common/portrait/face/preview/face56.gif\"  ></div>";s0.id="fks_095065092094085068080094080095087084087068083080081075";s0.ip="41.66.64.195";s0.ipName=null;s0.lastUpdateTime=1368197369046;s0.mainComId="-1";s0.moveFrom=null;s0.popup=false;s0.publishTime=1368197369085;s0.publishTimeStr="22:49:29";s0.publisherAvatar=0;s0.publisherAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.publisherEmail="";s0.publisherId=3178579;s0.publisherName="goldyard.vip";s0.publisherNickname="\u516D\u4E00\u513F\u7AE5";s0.publisherUrl=null;s0.replyComId="-1";s0.replyToUserId=32677678;s0.replyToUserName="green-waste";s0.replyToUserNick="green-waste";s0.shortPublishDateStr="2013-5-10";s0.spam=0;s0.subComments=s1;s0.synchMiniBlog=false;s0.valid=0;


    try :
        cmtDict = {};

        # 1. handel special fields,
        # for these field may contain special char and ';',
        # so find and process them firstly
        # (1) handle special ['abstract']
        abstratP = r"s(?P<index>\d+)\['abstract'\]=" + r'"(?P<abstract>.*)' + r'";s[0-9]+\.blogId="';
        foundAbs = re.search(abstratP, line);
        cmtIdx = foundAbs.group("index");
        cmtDict['curCmtIdx'] = int(cmtIdx);
        cmtDict['curCmtNum'] = cmtCurNum;
        cmtDict['parentCmtNum'] = 0; # default to 0, need later update if necessary
        cmtDict['abstract'] = foundAbs.group("abstract");
        line = line[(foundAbs.end("abstract") + 2):]; # 2 means ";
        #logging.info("process comment done for abstract");

        # (2) handle special .blogTitle
        titleP = r'";s' + str(cmtIdx) + "\.blogTitle=" + r'"(.*)' + r'";s' + str(cmtIdx) +'\.blogUserId=';
        foundTitle = re.search(titleP, line);
        cmtDict['blogTitle'] = foundTitle.group(1);
        beforeTitle = line[:(foundTitle.start(0) + 2)]; # include ;"
        afterTitle = line[(foundTitle.end(1) + 2):]; # exclude ";
        line = beforeTitle + afterTitle;
        #logging.info("process comment done for blogTitle");

        # (3) handle special .content
        contentP = r";s" + str(cmtIdx) + "\.content=" + r'"(.*)' + r'";s' + str(cmtIdx) +'\.id="';
        foundContent = re.search(contentP, line);
        cmtDict['content'] = foundContent.group(1);
        beforeContent = line[:(foundContent.start(0) + 1)]; # include ;
        afterContent = line[(foundContent.end(1) + 2):]; # exclude ";
        line = beforeContent + afterContent;
        #logging.info("process comment done for content");

        # TODO: nedd later use following instead of own made ones:
        # htmlentitydefs.entitydefs
        # htmlentitydefs.name2codepoint
        # htmlentitydefs.codepoint2name

        # before use ';' to split, makesure it not contain unicode like char == &#XXX;
        # Note:
        # after test, HTMLParser.unescape can not use here, so use following :
        # replace the &shy; and &#10084; to corresponding \uXXXX

        # (1) replace string entity to number entity:   &shy; -> &#173;
        originalLine = line;

        line = validateString(line);
        afterValidateLine = line;
        #logging.info("afterValidateLine=%s", afterValidateLine);

        line = crifanLib.htmlEntityNameToCodepoint(line);
        afterStrEntToNumLine = line;
        #logging.info("afterStrEntToNumLine=%s", afterStrEntToNumLine);

        # (2) replace number entity into \uXXXX:        &#10084; -> \u2764
        line = replaceChrEntityToSlashU(line);
        afterChrEntToSlashULine = line;
        #logging.info("afterChrEntToSlashULine=%s", afterChrEntToSlashULine);

        # 2. process main fields
        # (1) split
        semiSplited = line.split(";"); # semicolon splited
        #logging.debug("semiSplited=\n%s",semiSplited);
        # (2) remove un-process line
        semiSplited = crifanLib.removeEmptyInList(semiSplited);
        subComments = semiSplited.pop(len(semiSplited) - 3);# remove subComments
        childIdx = parseSubComments(subComments);
        cmtDict['childCmtIdx'] = childIdx;
        #logging.info("process comment done for remove un-process line");

        # (3) remove sN., N=0,1,2,...
        idxLen = len(str(cmtIdx));
        equationList = [];
        for eachLine in semiSplited:
            eachLine = eachLine[(1 + idxLen + 1):]; # omit sN. (N=0,1,2,...)
            equationList.append(eachLine);
        #logging.info("process comment done for sN., N=0,1,2,...");
        # (4) convert to value
        for equation in equationList :
            (key, value) = crifanLib.convertToTupleVal(equation);

            if(not key) :
                # if any error, record log info
                logging.debug("------convert equation string error, the related log info is ------");
                logging.debug("---before process, original line---\n%s", originalLine);
                logging.debug("---after validate ---\n%s", afterValidateLine);
                logging.debug("---after replace string entity to number entity---\n%s", afterStrEntToNumLine);
                logging.debug("---after replace number entity into \uXXXX---\n%s", afterChrEntToSlashULine);
            else :
                # normal, correct one
                cmtDict[key] = value;

        #logging.info("process comment done for convert to value");

        # notes:
        # (1) here not convert unicode-escape for later process
        # (2) most mainComId and replyComId is '-1', but some is:
        # s59.mainComId = "fks_081075082083084068082095094095085084086069083094084065080";
        # s54.replyComId = "fks_081075082080085066086086082095085084086069083094084065080";
    except :
        logging.debug("Fail to parse comment resopnse. Current comment number=%d", cmtCurNum);

    return cmtDict;

#------------------------------------------------------------------------------
# parse something like: s241[0]=s242;s241[1]=s243;
# into {childCommentNumber : parentCommentNumber} info
def extractParentRelation(line) :
    global gVal;

    cmtParentRelation = {};
    equationList = line.split(";");
    equationList = crifanLib.removeEmptyInList(equationList);
    logging.debug("Parsed %s into:", line);
    for equation in equationList:
        match = re.search(r's(\d+)\[(\d+)\]=s(\d+)', equation)
        int1 = int(match.group(1));
        int2 = int(match.group(2));
        int3 = int(match.group(3));
        # here use record its idx, so not +1
        cmtParentRelation[int3] = int1;
        logging.debug("     curIdx=%d, parIdx=%d", int3, int1);
    return cmtParentRelation;

#------------------------------------------------------------------------------
# convert the old {childIdx, parentIdx} to new {childIdx : parentNum}
def updateCmtRelation(oldDict, cmtList) :
    for cmt in cmtList:
        for childIdx in oldDict.keys() :
            if cmt['childCmtIdx'] == oldDict[childIdx] :
                oldDictChildIdx = oldDict[childIdx];
                oldDict[childIdx] = cmt['curCmtNum'];
                # note: here this kind of method, can change the original input oldDict[childIdx]
                logging.debug("Updated comment relation: from %d:%d to %d:%d", childIdx, oldDictChildIdx, childIdx, oldDict[childIdx]);
    return oldDict;

#------------------------------------------------------------------------------
# check whether comment type is normal:
# s10['abstract']="...
def isNormalCmt(line) :
    foundNormal = re.search(r"s\d+\['abstract'\]=.*", line);
    if foundNormal :
        return True;
    else :
        return False;

#------------------------------------------------------------------------------
# parse the returned comments response info
def parseCmtRespInfo(cmtResp, url, startCmtNum):
    retCmtDictList = [];
    mainCmtNum = 0;

    try :
        lines = cmtResp.split("\r\n");
        noBlankLines = crifanLib.removeEmptyInList(lines);
        # remove the 0,1,-1 line
        noBlankLines.pop(0); # //#DWR-INSERT
        noBlankLines.pop(0); # //#DWR-REPLY
        # eg: dwr.engine._remoteHandleCallback('1','0',[s0,s1]);
        dwrEngine = noBlankLines.pop(len(noBlankLines) - 1);
        mainCmtNum = extratMainCmtNum(dwrEngine);

        if noBlankLines :
            # handle first line -> remove var sN=xxx
            beginPos = noBlankLines[0].find("s0['abstract']");
            noBlankLines[0] = noBlankLines[0][beginPos:];

            cmtList = [];
            relationDict = {};
            cmtCurNum = startCmtNum;
            for line in noBlankLines :
                #logging.debug("%s", line);
                if isNormalCmt(line) :
                    singleCmtDict ={};
                    singleCmtDict = parseCmtRespStr(line, cmtCurNum);
                    cmtList.append(singleCmtDict);

                    cmtCurNum += 1;
                else :
                    # something like: s241[0]=s242;s241[1]=s243;
                    parsedRelation = extractParentRelation(line);
                    # add into whole relation dict
                    for childIdx in parsedRelation.keys() :
                        relationDict[childIdx] = parsedRelation[childIdx];
            # update the index relation
            updateCmtRelation(relationDict, cmtList);
            # update parent index info then add to list
            for cmt in cmtList :
                if cmt['curCmtIdx'] in relationDict :
                    cmt['parentCmtNum'] = relationDict[cmt['curCmtIdx']];
                    logging.debug("Updated comment parent info: curNum=%d, parentNum=%d", cmt['curCmtNum'], cmt['parentCmtNum']);
                retCmtDictList.append(cmt);

            logging.debug("Parsed %d comments", cmtCurNum - startCmtNum);
            #logging.debug("-------comment list---------";
            #for cmt in retCmtDictList :
            #    logging.debug("%s", cmt);
        else :
            logging.debug("Parsed result is no comment.");
    except :
        logging.debug("Parse number=%d comment fail for url= %s", cmtCurNum, url);

    return (retCmtDictList, mainCmtNum);

def findFksValue(soup):
    """
        From 163 post html's soup, find the fks value
        eg:
        fks_094067082083086070082083080095085081083068093095082074085
    """
    # extract the fks string
    fskClassInfo = soup.find(attrs={"class":"phide nb-init"});
    textareaJs = fskClassInfo.find(attrs={"name":"js"});
    fksStr = textareaJs.contents[0];
    foundFks = re.search(r"id:'(?P<id>fks_\d+)',", fksStr);
    fksValue = foundFks.group("id");
    logging.debug("fks value %s", fksValue);

    return fksValue;

#------------------------------------------------------------------------------
# get comments for input url of one blog item
# return the converted dict value
def fetchComments(url, soup):
    cmtList = [];

    # init before loop
    needGetMoreCmt = True;
    startCmtIdx = 0;
    startCmtNum = 1;
    onceGetNum = 1000; # get 1000 comments once

    try :
        while needGetMoreCmt :
            # cmtUrl = genReqCmtUrl(soup, startCmtIdx, onceGetNum);
            # cmtRetInfo = crifanLib.getUrlRespHtml(cmtUrl);

            fksValue = findFksValue(soup);

            c0ScriptName = "BlogBeanNew";
            c0MethodName = "getComments";
            c0Param0 = "string:" + str(fksValue);
            c0Param1 = "number:" + str(onceGetNum);
            c0Param2 = "number:" + str(startCmtIdx);
            cmtRetInfo = getPlaincallRespDwrStr(c0ScriptName, c0MethodName, c0Param0, c0Param1, c0Param2)

            #logging.debug("---------got comment original response ------------\n%s", cmtRetInfo);

            (parsedCmtList, mainCmtNum) = parseCmtRespInfo(cmtRetInfo, url, startCmtNum);

            if parsedCmtList :
                # add into ret list
                cmtList.extend(parsedCmtList);
                cmtNum = len(parsedCmtList);
                logging.debug("Currently got %d comments for idx=[%d-%d]", cmtNum, startCmtIdx, startCmtIdx + onceGetNum - 1);
                if mainCmtNum < onceGetNum :
                    # only got less than we want -> already got all comments
                    needGetMoreCmt = False;
                    logging.debug("Now has got all comments.");
                else :
                    needGetMoreCmt = True;
                    startCmtIdx += onceGetNum;
                    startCmtNum += cmtNum;
            else :
                needGetMoreCmt = False;
    except :
        logging.debug("Fail for fetch the comemnts(index=[%d-%d]) for %s ", startCmtIdx, startCmtIdx + onceGetNum - 1, url);

    return cmtList;

def fetchComments_feelingCard():
    """
        Get feeling card items, to use as comments
    """

    totalCmtDictList = [];
    totalMainCmtDictList = [];
    totalSubCmtDictList = [];

    # init before loop
    needGetMore = True;
    startIdx = 0;
    startNum = 1;
    onceGetNum = 1000; # get 1000 items once

    try :
        while needGetMore :
            # get resopnse dwr string

            # callCount=1
            # scriptSessionId=${scriptSessionId}187
            # c0-scriptName=FeelingsBeanNew
            # c0-methodName=getRecentFeelingCards
            # c0-id=0
            # c0-param0=number:186541395
            # c0-param1=number:0
            # c0-param2=number:20
            # batchId=292545
            getRecentFeelingCardsRespDwrStr = getPlaincallRespDwrStr(   "FeelingsBeanNew",
                                                                        "getRecentFeelingCards",
                                                                        "number:" + str(gVal['userId']),
                                                                        "number:" + str(startIdx),
                                                                        "number:" + str(onceGetNum));
            logging.debug("getRecentFeelingCardsRespDwrStr=%s", getRecentFeelingCardsRespDwrStr);
            curMainCmtDictList = parseMainCmtDwrStrToMainCmtDictList(getRecentFeelingCardsRespDwrStr);
            totalMainCmtDictList.extend(curMainCmtDictList);

            curGotMainCmtNum = len(curMainCmtDictList);
            if(curGotMainCmtNum < onceGetNum):
                #has got all comment, so quit
                needGetMore = False;
                logging.debug("Request %d comments, but only response %d comments, so no more comments, has got all comments", onceGetNum, curGotMainCmtNum);

        #add main comment dict list into total comment dict list
        logging.debug("Total got %d main comments dict", len(totalMainCmtDictList));
        totalCmtDictList.extend(totalMainCmtDictList);
        logging.debug("Total comments %d", len(totalCmtDictList));

        #after get all main comment dict, then try to find the sub comments
        for eachMainCmtDict in totalMainCmtDictList:
            #logging.info("eachMainCmtDict=%s", eachMainCmtDict);
            mainCommentCount = eachMainCmtDict['mainCommentCount'];
            #logging.info("mainCommentCount=%s", mainCommentCount);
            mainCommentCountInt = int(mainCommentCount);
            #logging.info("mainCommentCountInt=%d", mainCommentCountInt);
            if(mainCommentCountInt > 0):
                #has sub comment
                logging.debug("[%d] main comment has sub %d comments", eachMainCmtDict['curCmtIdx'], mainCommentCountInt);
                #1. get sub comment dwr string
                subCmtDwrStr = getFeelingCardSubCmtDwrStr(eachMainCmtDict['id']);
                #2. parse sub comment dwr string to sub comment dict
                curSubCmtDictList = parseSubCmtDwrStrToSubCmtDictList(subCmtDwrStr);
                totalSubCmtDictList.extend(curSubCmtDictList);

        #do some update for sub comment
        logging.debug("Total got %d sub comment dict", len(totalSubCmtDictList));
        if(totalSubCmtDictList):
            #update sub comment index
            subCmtStartIdx = len(totalMainCmtDictList);
            logging.debug("subCmtStartIdx=%d", subCmtStartIdx);
            for idx,eachSubCmtDict in enumerate(totalSubCmtDictList):
                eachSubCmtDict['curCmtIdx'] = subCmtStartIdx + idx;
                eachSubCmtDict['curCmtNum'] = eachSubCmtDict['curCmtIdx'] + 1;

            logging.debug("done for update sub comment index");
            #update sub comment's parent relation
            for idx,eachSubCmtDict in enumerate(totalSubCmtDictList):
                subCmtParentId = eachSubCmtDict['cardId'];
                for eachMainCmtDict in totalMainCmtDictList:
                    mainCmtId = eachMainCmtDict['id'];
                    if(subCmtParentId == mainCmtId):
                        logging.debug("sub cmt id=%s 's parent's id=%s, parent curCmtNum=%d", eachSubCmtDict['id'], mainCmtId, eachMainCmtDict['curCmtNum']);
                        eachSubCmtDict['parentCmtNum'] = eachMainCmtDict['curCmtNum'];

                #update sub comment's parent whose within sub comment list
                #s0.replyComId="-1";
                #s3.replyComId="72175292"
                curSubCmtReplyComId = eachSubCmtDict['replyComId']; #
                for singleSubCmtDict in totalSubCmtDictList:
                    subCmtId = singleSubCmtDict['id'];
                    subCmtCurCmtNum = singleSubCmtDict['curCmtNum'];
                    if(curSubCmtReplyComId == subCmtId):
                        logging.debug("sub cmt id=%s 's replyComId=%s, find correspoinding parent (sub) comment, whose curCmtNum=%d", subCmtId, curSubCmtReplyComId, subCmtCurCmtNum);
                        eachSubCmtDict['parentCmtNum'] = subCmtCurCmtNum;

            logging.debug("done for update sub comment's parent relation");
            totalCmtDictList.extend(totalSubCmtDictList);
    except :
        logging.debug("Fail for fetch the feeling card (index=[%d-%d]) for %s ", startIdx, startIdx + onceGetNum - 1, url);

    return totalCmtDictList;

def getFeelingCardSubCmtDwrStr(subCmtId):
    """
        input sub comment id, return sub comment response dwr string
    """
    # callCount=1
    # scriptSessionId=${scriptSessionId}187
    # c0-scriptName=FeelingsBeanNew
    # c0-methodName=getRecentFeelingsComment
    # c0-id=0
    # c0-param0=string:134875456
    # c0-param1=number:1
    # c0-param2=number:0
    # batchId=705438

    logging.debug("get sub comment for %s", subCmtId);

    getRecentFeelingsCommentRespDwrStr = getPlaincallRespDwrStr(    "FeelingsBeanNew",
                                                                    "getRecentFeelingsComment",
                                                                    "string:" + str(subCmtId),
                                                                    "number:1",
                                                                    "number:0");
    logging.debug("getRecentFeelingsCommentRespDwrStr=%s", getRecentFeelingsCommentRespDwrStr);

    return getRecentFeelingsCommentRespDwrStr;

def parseSingleDwrStrToCmtDict(singleCmtDwrStr):
    """
        parse single comment dwr string, main comment or sub comment, to comment dict
    """
    logging.debug("singleCmtDwrStr=%s", singleCmtDwrStr);

    #init values
    curCmtDict = {};

    singleMainCmtDict = {
        'curCmtIdx'         : 0,
        'curCmtNum'         : 0,
        'parentCmtNum'      : 0,
        'isSubComment'      : False,

        'commentCount'      : "",
        'mainCommentCount'  : "",
        'moodType'          : "",
        'userAvatar'        : "",
        'userAvatarUrl'     : "",
        'userName'          : "",
        'userNickname'      : "",
        #common part
        'content'           : "",
        'id'                : "",
        'moveFrom'          : "",
        'publishTime'       : "",
        'synchMiniBlog'     : "",
        'userId'            : "",
    };

    singleSubCmtDict = {
        'curCmtIdx'         : 0,
        'curCmtNum'         : 0,
        'parentCmtNum'      : 0,
        'isSubComment'      : True,

        'cardId'            : "", # is parent ID
        'ip'                : "",
        'ipName'            : "",
        'lastUpdateTime'    : "",
        'mainComId'         : "",
        'popup'             : "",
        'publisherAvatar'   : "",
        'publisherAvatarUrl': "",
        'publisherId'       : "",
        'publisherName'     : "",
        'publisherNickname' : "",
        'publisherUrl'      : "",
        'replyComId'        : "",
        'replyToUserId'     : "",
        'replyToUserName'   : "",
        'replyToUserNick'   : "",
        'spam'              : "",
        'subComments'       : "",
        'valid'             : "",
        #common part
        'content'           : "",
        'id'                : "",
        'moveFrom'          : "",
        'publishTime'       : "",
        'synchMiniBlog'     : "",
        'userId'            : "",
    };

    #1. check is main comment or sub comment
    #start with sN.cardId=, is sub comment
    foundCardId = re.search("^s\d+\.cardId=", singleCmtDwrStr);
    if(foundCardId):
        curCmtDict = singleSubCmtDict;
        curCmtDict['isSubComment'] = True;
        logging.debug("------- is sub comments");
    else:
        curCmtDict = singleMainCmtDict;
        curCmtDict['isSubComment'] = False;
        logging.debug("======= is main comments");

    #2. process common key and value

    #common key and value

    #fisrt get the comment index
    #main comment:
    #s0.content="\u7EC8\u4E8E\u6709iphone\u7248\u7684\u4E86";s0.id="
    #sub comment:
    #s0.content="\u81EA\u5DF1\u4E70\u70B9\u6C34\u679C\u5403\u3002";s0.id="
    #s0.commentCount=0;s0.content="\u7EC8\u4E8E\u6709iphone\u7248\u7684\u4E86";s0.id="148749270";s0.mainCommentCount=0;s0.moodType=0;s0.moveFrom="iphone";s0.publishTime=1374626867596;s0.synchMiniBlog=-1;s0.userAvatar=0;s0.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.userId=186541395;s0.userName="ni_chen";s0.userNickname="Neysa";

    foundCurCmtIdx = re.search(r's(?P<curCmtIdx>\d+)\.content=".+?";s\1\.id="', singleCmtDwrStr);
    logging.debug("foundCurCmtIdx=%s", foundCurCmtIdx);
    curCmtIdx = foundCurCmtIdx.group("curCmtIdx");
    curCmtIdx = int(curCmtIdx);
    logging.debug("curCmtIdx=%d", curCmtIdx);
    if(not curCmtDict['isSubComment']):
        #only add for main comment
        #later, will update sub comment curCmtIdx and curCmtNum
        curCmtDict['curCmtIdx'] = curCmtIdx;
        curCmtDict['curCmtNum'] = curCmtIdx + 1;

    #init some common values
    strSn = "s" + str(curCmtIdx);

    #content
    #s0.content="\u7EC8\u4E8E\u6709iphone\u7248\u7684\u4E86";s0.id="
    foundContent = re.search(strSn + '\.content=(?P<content>.+?);' + strSn + '\.id="', singleCmtDwrStr);
    content = foundContent.group("content");
    content = content.decode("unicode-escape");
    curCmtDict['content'] = content;
    logging.debug("content=%s", content);

    #id
    #s0.id="148749270";
    foundId = re.search(strSn + '\.id="(?P<id>\d+)";', singleCmtDwrStr);
    id = foundId.group("id");
    curCmtDict['id'] = id;
    logging.debug("id=%s", id);

    #moveFrom
    #s0.moveFrom="iphone";
    #s2.moveFrom=null;
    #s8.moveFrom="wap";
    #s699.moveFrom="";
    foundMoveFrom = re.search(strSn + '\.moveFrom="?(?P<moveFrom>[^"]*?)"?;', singleCmtDwrStr);
    moveFrom = foundMoveFrom.group("moveFrom");
    curCmtDict['moveFrom'] = moveFrom;
    logging.debug("moveFrom=%s", moveFrom);

    #publishTime
    #s0.publishTime=1374626867596;
    foundPublishTime = re.search(strSn + '\.publishTime=(?P<publishTime>\d+);', singleCmtDwrStr);
    publishTime = foundPublishTime.group("publishTime");
    curCmtDict['publishTime'] = publishTime;
    logging.debug("publishTime=%s", publishTime);

    #synchMiniBlog
    #s0.synchMiniBlog=-1;
    #in sub comment:
    #s0.synchMiniBlog=false;
    foundSynchMiniBlog = re.search(strSn + '\.synchMiniBlog=(?P<synchMiniBlog>.+?);', singleCmtDwrStr);
    synchMiniBlog = foundSynchMiniBlog.group("synchMiniBlog");
    curCmtDict['synchMiniBlog'] = synchMiniBlog;
    logging.debug("synchMiniBlog=%s", synchMiniBlog);

    #userId
    #s0.userId=186541395;
    foundUserId = re.search(strSn + '\.userId=(?P<userId>\d+);', singleCmtDwrStr);
    userId = foundUserId.group("userId");
    curCmtDict['userId'] = userId;
    logging.debug("userId=%s", userId);

    #3. process different key and value

    if(curCmtDict['isSubComment']):
        #process sub comment remaing field


        #sub comment dwr string:

        #sample 1: #s0.cardId="134875456";s0.content="\u81EA\u5DF1\u4E70\u70B9\u6C34\u679C\u5403\u3002";s0.id="73300019";s0.ip="203.234.215.66";s0.ipName=null;s0.lastUpdateTime=1351380367156;s0.mainComId="-1";s0.moveFrom=null;s0.popup=false;s0.publishTime=1351380367155;s0.publisherAvatar=0;s0.publisherAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.publisherId=55976067;s0.publisherName="chenlin198412@126";s0.publisherNickname="Lynn";s0.publisherUrl=null;s0.replyComId="-1";s0.replyToUserId=186541395;s0.replyToUserName="ni_chen";s0.replyToUserNick="Neysa";s0.spam=0;s0.subComments=s1;s0.synchMiniBlog=false;s0.userId=186541395;s0.valid=0;

        #sample 2:
        # s0.cardId="133211376";s0.content="\u4ECE\u9AD8\u4E2D\u5C31\u5F00\u59CB\u7684\u5417\uFF1F\u597D\u597D\u53BB\u533B\u9662\u68C0\u67E5\u4E00\u4E0B\u5427\uFF0C\u73B0\u5728\u6709\u75C5\u4E00\u5B9A\u4E0D\u8981\u62D6\u7740\uFF0C\u8981\u4E0D\u5C0F\u75C5\u4E5F\u4F1A\u53D8\u6210\u5927\u75C5\uFF0C\u5230\u65F6\u53EF\u6CA1\u6709\u540E\u6094\u836F\u5403\u3002";s0.id="72192291";s0.ip="115.170.58.191";s0.ipName=null;s0.lastUpdateTime=1348561288469;s0.mainComId="-1";s0.moveFrom=null;s0.popup=false;s0.publishTime=1348468815327;s0.publisherAvatar=0;s0.publisherAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.publisherId=26959367;s0.publisherName="chenyuanyuan0913";s0.publisherNickname="\u6C89\u7F18\u6E90";s0.publisherUrl=null;s0.replyComId="-1";s0.replyToUserId=186541395;s0.replyToUserName="ni_chen";s0.replyToUserNick="Neysa";s0.spam=0;s0.subComments=s1;s0.synchMiniBlog=false;s0.userId=186541395;s0.valid=0;

        # s1[0]=s2;s1[1]=s3;s1[2]=s4;

        # s2.cardId="133211376";s2.content="\u4E00\u76F4\u60F3\u67E5\uFF0C\u4F46\u662F\u6CA1\u6709\u533B\u7597\u4FDD\u9669<img src=\"http://b.bst.126.net/common/portrait/face/preview/face2.gif\"  >\u3002\u6211\u5F97\u5148\u95EE\u6E05\u695A\u4E00\u4E0B";s2.id="72175292";s2.ip="147.46.115.126";s2.ipName=null;s2.lastUpdateTime=0;s2.mainComId="72192291";s2.moveFrom=null;s2.popup=false;s2.publishTime=1348471820683;s2.publisherAvatar=0;s2.publisherAvatarUrl=null;s2.publisherId=186541395;s2.publisherName="ni_chen";s2.publisherNickname="Neysa";s2.publisherUrl=null;s2.replyComId="72192291";s2.replyToUserId=26959367;s2.replyToUserName="chenyuanyuan0913";s2.replyToUserNick="\u6C89\u7F18\u6E90";s2.spam=0;s2.subComments=s5;s2.synchMiniBlog=false;s2.userId=186541395;s2.valid=0;
        #s3.cardId="133211376";s3.content="\u522B\u62D6\u5EF6\uFF0C\u505A\u4E2A\u68C0\u67E5\u82B1\u4E0D\u4E86\u591A\u5C11\u94B1\u7684\uFF0C\u522B\u5230\u65F6\u771F\u751F\u75C5\u4E86\uFF0C\u90A3\u53EF\u82B1\u5F97\u4E0D\u662F\u4E00\u70B9\u534A\u70B9\u7684\u3002\u6709\u65F6\u95F4\u4E86\u5C31\u8D76\u7D27\u53BB\uFF0C\u4E00\u5B9A\u8981\u53BB\u554A\uFF0C\u6CA1\u4EC0\u4E48\u4E8B\u5C31\u653E\u5FC3\u4E86\u3002\u8BB0\u5F97\u6211\u4EEC\u5BBF\u820D\u90A3\u4E2A\u5C0F\u59D1\u5A18\u5417\uFF0C\u90A3\u53EF\u662F\u771F\u5B9E\u7684\u6559\u8BAD\u554A";s3.id="72227357";s3.ip="115.170.26.179";s3.ipName=null;s3.lastUpdateTime=0;s3.mainComId="72192291";s3.moveFrom=null;s3.popup=false;s3.publishTime=1348560697833;s3.publisherAvatar=0;s3.publisherAvatarUrl=null;s3.publisherId=26959367;s3.publisherName="chenyuanyuan0913";s3.publisherNickname="\u6C89\u7F18\u6E90";s3.publisherUrl=null;s3.replyComId="72175292";s3.replyToUserId=186541395;s3.replyToUserName="ni_chen";s3.replyToUserNick="Neysa";s3.spam=0;s3.subComments=s6;s3.synchMiniBlog=false;s3.userId=186541395;s3.valid=0;

        # s4.cardId="133211376";s4.content="\u55EF\uFF0C\u77E5\u9053\u5566<img src=\"http://b.bst.126.net/common/portrait/face/preview/face47.gif\"  >";s4.id="72206314";s4.ip="147.46.115.126";s4.ipName=null;s4.lastUpdateTime=0;s4.mainComId="72192291";s4.moveFrom=null;s4.popup=false;s4.publishTime=1348561288458;s4.publisherAvatar=0;s4.publisherAvatarUrl=null;s4.publisherId=186541395;s4.publisherName="ni_chen";s4.publisherNickname="Neysa";s4.publisherUrl=null;s4.replyComId="72227357";s4.replyToUserId=26959367;s4.replyToUserName="chenyuanyuan0913";s4.replyToUserNick="\u6C89\u7F18\u6E90";s4.spam=0;s4.subComments=s7;s4.synchMiniBlog=false;s4.userId=186541395;s4.valid=0;

        #sample 3:
        #s0.cardId="131435017";s0.content="\u54C8\u54C8\uFF0C\u4FFA\u662F\u7B14\u8FF9\u63A7";s0.id="70788610";s0.ip=null;s0.ipName=null;s0.lastUpdateTime=1344839449690;s0.mainComId="-1";s0.moveFrom="iphone";s0.popup=false;s0.publishTime=1344839449690;s0.publisherAvatar=0;s0.publisherAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.publisherId=186541395;s0.publisherName="ni_chen";s0.publisherNickname="Neysa";s0.publisherUrl=null;s0.replyComId="-1";s0.replyToUserId=0;s0.replyToUserName="";s0.replyToUserNick="";s0.spam=0;s0.subComments=s1;s0.synchMiniBlog=false;s0.userId=186541395;s0.valid=0;

        #sample 4:
        #s0.cardId="131435017";s0.content="\u54C8\u54C8\uFF0C\u4FFA\u662F\u7B14\u8FF9\u63A7";s0.id="70788610";s0.ip=null;s0.ipName=null;s0.lastUpdateTime=1344839449690;s0.mainComId="-1";s0.moveFrom="iphone";s0.popup=false;s0.publishTime=1344839449690;s0.publisherAvatar=0;s0.publisherAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.publisherId=186541395;s0.publisherName="ni_chen";s0.publisherNickname="Neysa";s0.publisherUrl=null;s0.replyComId="-1";s0.replyToUserId=0;s0.replyToUserName="";s0.replyToUserNick="";s0.spam=0;s0.subComments=s1;s0.synchMiniBlog=false;s0.userId=186541395;s0.valid=0;

        #sample 5:
        #s0.cardId="111039854";s0.content="\u65B0\u53D1\u578B\u771F\u5F97\u5F88\u6F02\u4EAE\u554A\u2026\u2026\u53EF\u4EE5\u4F20\u4E00\u7EC4\u7167\u7247\u8BA9\u59D0\u59D0\u770B\u770B\u5417\uFF1F";s0.id="58333672";s0.ip=null;s0.ipName=null;s0.lastUpdateTime=1251121541764;s0.mainComId="-1";s0.moveFrom="";s0.popup=false;s0.publishTime=1251121541764;s0.publisherAvatar=0;s0.publisherAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.publisherId=26959367;s0.publisherName="chenyuanyuan0913";s0.publisherNickname="\u6C89\u7F18\u6E90";s0.publisherUrl=null;s0.replyComId="-1";s0.replyToUserId=0;s0.replyToUserName=null;s0.replyToUserNick=null;s0.spam=0;s0.subComments=s1;s0.synchMiniBlog=false;s0.userId=186541395;s0.valid=0;


        #cardId
        #s0.cardId="134875456";
        foundCardId = re.search(strSn + '\.cardId="?(?P<cardId>.*?)"?;', singleCmtDwrStr);
        cardId = foundCardId.group("cardId");
        curCmtDict['cardId'] = cardId;
        logging.debug("cardId=%s", cardId);

        #ip
        #s0.ip="203.234.215.66";
        #s0.ip=null;
        foundIp = re.search(strSn + '\.ip="?(?P<ip>.*?)"?;', singleCmtDwrStr);
        ip = foundIp.group("ip");
        if(not re.search("\d+\.\d+\.\d+\.\d+", ip)):
            ip = "";
        curCmtDict['ip'] = ip;
        logging.debug("ip=%s", ip);

        #ipName
        #s0.ipName=null;
        foundIpName = re.search(strSn + '\.ipName=(?P<ipName>.+?);', singleCmtDwrStr);
        ipName = foundIpName.group("ipName");
        curCmtDict['ipName'] = ipName;
        logging.debug("ipName=%s", ipName);

        #lastUpdateTime
        #s0.lastUpdateTime=1351380367156;
        foundLastUpdateTime = re.search(strSn + '\.lastUpdateTime=(?P<lastUpdateTime>\d+);', singleCmtDwrStr);
        lastUpdateTime = foundLastUpdateTime.group("lastUpdateTime");
        curCmtDict['lastUpdateTime'] = lastUpdateTime;
        logging.debug("lastUpdateTime=%s", lastUpdateTime);

        #mainComId
        #s0.mainComId="-1";
        foundMainComId = re.search(strSn + '\.mainComId="?(?P<mainComId>.*?)"?;', singleCmtDwrStr);
        mainComId = foundMainComId.group("mainComId");
        curCmtDict['mainComId'] = mainComId;
        logging.debug("mainComId=%s", mainComId);

        #popup
        #s0.popup=false;
        foundPopup = re.search(strSn + '\.popup=(?P<popup>.+?);', singleCmtDwrStr);
        popup = foundPopup.group("popup");
        curCmtDict['popup'] = popup;
        logging.debug("popup=%s", popup);

        #publisherAvatar
        #s0.publisherAvatar=0;
        foundPublisherAvatar = re.search(strSn + '\.publisherAvatar=(?P<publisherAvatar>\d+);', singleCmtDwrStr);
        publisherAvatar = foundPublisherAvatar.group("publisherAvatar");
        curCmtDict['publisherAvatar'] = publisherAvatar;
        logging.debug("publisherAvatar=%s", publisherAvatar);

        #publisherAvatarUrl
        #s0.publisherAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";
        #s2.publisherAvatarUrl=null;
        foundPublisherAvatarUrl = re.search(strSn + '\.publisherAvatarUrl="?(?P<publisherAvatarUrl>.*?)"?;', singleCmtDwrStr);
        publisherAvatarUrl = foundPublisherAvatarUrl.group("publisherAvatarUrl");
        curCmtDict['publisherAvatarUrl'] = publisherAvatarUrl;
        logging.debug("publisherAvatarUrl=%s", publisherAvatarUrl);

        #publisherId
        #s0.publisherId=55976067;
        foundPublisherId = re.search(strSn + '\.publisherId=(?P<publisherId>\d+);', singleCmtDwrStr);
        publisherId = foundPublisherId.group("publisherId");
        curCmtDict['publisherId'] = publisherId;
        logging.debug("publisherId=%s", publisherId);

        #publisherName
        #s0.publisherName="chenlin198412@126";
        foundPublisherName = re.search(strSn + '\.publisherName="?(?P<publisherName>.*?)"?;', singleCmtDwrStr);
        publisherName = foundPublisherName.group("publisherName");
        curCmtDict['publisherName'] = publisherName;
        logging.debug("publisherName=%s", publisherName);

        #publisherNickname
        #s0.publisherNickname="Lynn";
        foundPublisherNickname = re.search(strSn + '\.publisherNickname="?(?P<publisherNickname>.*?)"?;', singleCmtDwrStr);
        publisherNickname = foundPublisherNickname.group("publisherNickname");
        publisherNicknameUni = publisherNickname.decode('unicode-escape');
        curCmtDict['publisherNickname'] = publisherNicknameUni;
        logging.debug("publisherNickname=%s", publisherNickname);

        #publisherUrl
        #s0.publisherUrl=null;
        foundPublisherUrl = re.search(strSn + '\.publisherUrl="?(?P<publisherUrl>.*?)"?;', singleCmtDwrStr);
        publisherUrl = foundPublisherUrl.group("publisherUrl");
        curCmtDict['publisherUrl'] = publisherUrl;
        logging.debug("publisherUrl=%s", publisherUrl);

        #replyComId
        #s0.replyComId="-1";
        foundReplyComId = re.search(strSn + '\.replyComId="?(?P<replyComId>.*?)"?;', singleCmtDwrStr);
        replyComId = foundReplyComId.group("replyComId");
        curCmtDict['replyComId'] = replyComId;
        logging.debug("replyComId=%s", replyComId);

        #replyToUserId
        #s0.replyToUserId=186541395;
        foundReplyToUserId = re.search(strSn + '\.replyToUserId=(?P<replyToUserId>\d+);', singleCmtDwrStr);
        replyToUserId = foundReplyToUserId.group("replyToUserId");
        curCmtDict['replyToUserId'] = replyToUserId;
        logging.debug("replyToUserId=%s", replyToUserId);

        #replyToUserName
        #s0.replyToUserName="ni_chen";
        #s0.replyToUserName="";
        #s0.replyToUserName=null;
        foundReplyToUserName = re.search(strSn + '\.replyToUserName="?(?P<replyToUserName>.*?)"?;', singleCmtDwrStr);
        replyToUserName = foundReplyToUserName.group("replyToUserName");
        curCmtDict['replyToUserName'] = replyToUserName;
        logging.debug("replyToUserName=%s", replyToUserName);

        #replyToUserNick
        #s0.replyToUserNick="Neysa";
        #s0.replyToUserNick=null;
        foundReplyToUserNick = re.search(strSn + '\.replyToUserNick="?(?P<replyToUserNick>.*?)"?;', singleCmtDwrStr);
        replyToUserNick = foundReplyToUserNick.group("replyToUserNick");
        curCmtDict['replyToUserNick'] = replyToUserNick;
        logging.debug("replyToUserNick=%s", replyToUserNick);

        #spam
        #s0.spam=0;
        foundSpam = re.search(strSn + '\.spam=(?P<spam>\d+);', singleCmtDwrStr);
        spam = foundSpam.group("spam");
        curCmtDict['spam'] = spam;
        logging.debug("spam=%s", spam);

        #subComments
        #s0.subComments=s1;
        foundSubComments = re.search(strSn + '\.subComments=(?P<subComments>.+?);', singleCmtDwrStr);
        subComments = foundSubComments.group("subComments");
        curCmtDict['subComments'] = subComments;
        logging.debug("subComments=%s", subComments);

        #valid
        #s0.valid=0;
        foundValid = re.search(strSn + '\.valid=(?P<valid>\d+);', singleCmtDwrStr);
        valid = foundValid.group("valid");
        curCmtDict['valid'] = valid;
        logging.debug("valid=%s", valid);
    else:
        #process main comment remaing field


        #main comment dwr string:
        #s0.commentCount=0;s0.content="\u7EC8\u4E8E\u6709iphone\u7248\u7684\u4E86";s0.id="148749270";s0.mainCommentCount=0;s0.moodType=0;s0.moveFrom="iphone";s0.publishTime=1374626867596;s0.synchMiniBlog=-1;s0.userAvatar=0;s0.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.userId=186541395;s0.userName="ni_chen";s0.userNickname="Neysa";

        #s1.commentCount=1;s1.content="\u4E3B\u9875\u7EC8\u4E8E\u7545\u901A\u4E86\uFF0C\u4FFA\u53C8\u8981\u632A\u7A9D\u4E86[P]\u5FAE\u7B11[/P]";s1.id="134875456";s1.mainCommentCount=1;s1.moodType=1;s1.moveFrom=null;s1.publishTime=1350461318140;s1.synchMiniBlog=-1;s1.userAvatar=0;s1.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s1.userId=186541395;s1.userName="ni_chen";s1.userNickname="Neysa";

        #s2.commentCount=0;s2.content="BK\u529E\u516C\u5BA4\u5927\u5988\u771F\u662F\u540D\u4E0D\u865A\u4F20\uFF0C\u5976\u5976\u7684\u4ECA\u5929\u8FD8\u4E0D\u7ED3\u675F\u6211\u8981\u6297\u8BAE\u4E86";s2.id="134892431";s2.mainCommentCount=0;s2.moodType=1;s2.moveFrom=null;s2.publishTime=1350454487895;s2.synchMiniBlog=-1;s2.userAvatar=0;s2.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s2.userId=186541395;s2.userName="ni_chen";s2.userNickname="Neysa";

        #s3.commentCount=0;s3.content="\u7814\u7A76\u5BA4\u5C0F\u5B69\u8981\u53BB\u89C1IU\uFF0C\u8FD8\u9884\u7EA6\u4E86\u76AE\u80A4\u7BA1\u7406\uFF0C\u4E24\u4E2A\u4EBA\u5728\u90A3\u5600\u5495\u201C\u8FD9\u6837\u62FF\u4E0D\u5230IU\u7B7E\u540D\u7684.....\u201D[P]\u5931\u671B[/P][P]\u5931\u671B[/P]";s3.id="134892313";s3.mainCommentCount=0;s3.moodType=1;s3.moveFrom=null;s3.publishTime=1350443478140;s3.synchMiniBlog=-1;s3.userAvatar=0;s3.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s3.userId=186541395;s3.userName="ni_chen";s3.userNickname="Neysa";


        #commentCount
        #s0.commentCount=0;
        foundCommentCount = re.search(strSn + '\.commentCount=(?P<commentCount>\d+);', singleCmtDwrStr);
        commentCount = foundCommentCount.group("commentCount");
        curCmtDict['commentCount'] = commentCount;
        logging.debug("commentCount=%s", commentCount);


        #mainCommentCount
        #s0.mainCommentCount=0;
        foundMainCommentCount = re.search(strSn + '\.mainCommentCount=(?P<mainCommentCount>\d+);', singleCmtDwrStr);
        mainCommentCount = foundMainCommentCount.group("mainCommentCount");
        curCmtDict['mainCommentCount'] = mainCommentCount;
        logging.debug("mainCommentCount=%s", mainCommentCount);

        #moodType
        #s0.moodType=0;
        foundMoodType = re.search(strSn + '\.moodType=(?P<moodType>\d+);', singleCmtDwrStr);
        moodType = foundMoodType.group("moodType");
        curCmtDict['moodType'] = moodType;
        logging.debug("moodType=%s", moodType);

        #userAvatar
        #s0.userAvatar=0;
        foundUserAvatar = re.search(strSn + '\.userAvatar=(?P<userAvatar>\d+);', singleCmtDwrStr);
        userAvatar = foundUserAvatar.group("userAvatar");
        curCmtDict['userAvatar'] = userAvatar;
        logging.debug("userAvatar=%s", userAvatar);

        #userAvatarUrl
        #s0.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";
        foundUserAvatarUrl = re.search(strSn + '\.userAvatarUrl="?(?P<userAvatarUrl>http://.+?)"?;', singleCmtDwrStr);
        userAvatarUrl = foundUserAvatarUrl.group("userAvatarUrl");
        curCmtDict['userAvatarUrl'] = userAvatarUrl;
        logging.debug("userAvatarUrl=%s", userAvatarUrl);

        #userName
        #s0.userName="ni_chen";
        foundUserName = re.search(strSn + '\.userName="?(?P<userName>.+?)"?;', singleCmtDwrStr);
        userName = foundUserName.group("userName");
        curCmtDict['userName'] = userName;
        logging.debug("userName=%s", userName);

        #userNickname
        #s0.userNickname="Neysa";
        foundUserNickname = re.search(strSn + '\.userNickname="?(?P<userNickname>.+?)"?;', singleCmtDwrStr);
        userNickname = foundUserNickname.group("userNickname");
        curCmtDict['userNickname'] = userNickname;
        logging.debug("userNickname=%s", userNickname);

    return curCmtDict;

def parseSubCmtDwrStrToSubCmtDictList(subCmtDwrStr):
    """
        parse sub comment dwr string to sub comment dict list
            split to single sub comment dwr string list
            convert each sub comment dwr string to dict
    """
    subCmtDictList = [];

    # //#DWR-INSERT
    # //#DWR-REPLY
    # var s0={};var s1=[];s0.cardId="134875456";s0.content="\u81EA\u5DF1\u4E70\u70B9\u6C34\u679C\u5403\u3002";s0.id="73300019";s0.ip="203.234.215.66";s0.ipName=null;s0.lastUpdateTime=1351380367156;s0.mainComId="-1";s0.moveFrom=null;s0.popup=false;s0.publishTime=1351380367155;s0.publisherAvatar=0;s0.publisherAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.publisherId=55976067;s0.publisherName="chenlin198412@126";s0.publisherNickname="Lynn";s0.publisherUrl=null;s0.replyComId="-1";s0.replyToUserId=186541395;s0.replyToUserName="ni_chen";s0.replyToUserNick="Neysa";s0.spam=0;s0.subComments=s1;s0.synchMiniBlog=false;s0.userId=186541395;s0.valid=0;
    # dwr.engine._remoteHandleCallback('1','0',[s0]);

    subCmtStrList = re.findall(r's\d+\.cardId=.+?s\d+\.valid=\d+;(?:\s)', subCmtDwrStr);
    #logging.info("subCmtStrList=%s", subCmtStrList);
    logging.debug("len(subCmtStrList)=%d", len(subCmtStrList));

    if(subCmtStrList):
        for singleSubCmtDwrStr in subCmtStrList:
            singleSubCmtDict = parseSingleDwrStrToCmtDict(singleSubCmtDwrStr);
            subCmtDictList.append(singleSubCmtDict);

    return subCmtDictList;

def parseMainCmtDwrStrToMainCmtDictList(respDwrReplyStr):
    """
        Parse main comment response DWR-REPLY string, into comment dict list
    """
    commentDictList = [];
    #s0.commentCount=0;s0.content="\u7EC8\u4E8E\u6709iphone\u7248\u7684\u4E86";s0.id="148749270";s0.mainCommentCount=0;s0.moodType=0;s0.moveFrom="iphone";s0.publishTime=1374626867596;s0.synchMiniBlog=-1;s0.userAvatar=0;s0.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s0.userId=186541395;s0.userName="ni_chen";s0.userNickname="Neysa";

    #s1.commentCount=1;s1.content="\u4E3B\u9875\u7EC8\u4E8E\u7545\u901A\u4E86\uFF0C\u4FFA\u53C8\u8981\u632A\u7A9D\u4E86[P]\u5FAE\u7B11[/P]";s1.id="134875456";s1.mainCommentCount=1;s1.moodType=1;s1.moveFrom=null;s1.publishTime=1350461318140;s1.synchMiniBlog=-1;s1.userAvatar=0;s1.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s1.userId=186541395;s1.userName="ni_chen";s1.userNickname="Neysa";

    #s2.commentCount=0;s2.content="BK\u529E\u516C\u5BA4\u5927\u5988\u771F\u662F\u540D\u4E0D\u865A\u4F20\uFF0C\u5976\u5976\u7684\u4ECA\u5929\u8FD8\u4E0D\u7ED3\u675F\u6211\u8981\u6297\u8BAE\u4E86";s2.id="134892431";s2.mainCommentCount=0;s2.moodType=1;s2.moveFrom=null;s2.publishTime=1350454487895;s2.synchMiniBlog=-1;s2.userAvatar=0;s2.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s2.userId=186541395;s2.userName="ni_chen";s2.userNickname="Neysa";

    #s3.commentCount=0;s3.content="\u7814\u7A76\u5BA4\u5C0F\u5B69\u8981\u53BB\u89C1IU\uFF0C\u8FD8\u9884\u7EA6\u4E86\u76AE\u80A4\u7BA1\u7406\uFF0C\u4E24\u4E2A\u4EBA\u5728\u90A3\u5600\u5495\u201C\u8FD9\u6837\u62FF\u4E0D\u5230IU\u7B7E\u540D\u7684.....\u201D[P]\u5931\u671B[/P][P]\u5931\u671B[/P]";s3.id="134892313";s3.mainCommentCount=0;s3.moodType=1;s3.moveFrom=null;s3.publishTime=1350443478140;s3.synchMiniBlog=-1;s3.userAvatar=0;s3.userAvatarUrl="http://img.bimg.126.net/photo/hmZoNQaqzZALvVp0rE7faA==/0.jpg";s3.userId=186541395;s3.userName="ni_chen";s3.userNickname="Neysa";

    mainCmtDwrStrList = [];

    #mainCmtDwrStrList = re.findall(r'(?:s\d+)\.commentCount=.+?\1\.userNickname=".+?";', respDwrReplyStr);
    mainCmtDwrStrList = re.findall(r's\d+\.commentCount=.+?s\d+\.userNickname=".+?";(?:\s)', respDwrReplyStr);
    #logging.info("mainCmtDwrStrList=%s", mainCmtDwrStrList);
    logging.debug("len(mainCmtDwrStrList)=%d", len(mainCmtDwrStrList));

    if(mainCmtDwrStrList):
        for eachMainCmtDwrStr in mainCmtDwrStrList:
            #parse each main comment string into comment dict
            singleMainCmtDict = parseSingleDwrStrToCmtDict(eachMainCmtDwrStr);

            #add single comment dict into list
            commentDictList.append(singleMainCmtDict);

    return commentDictList;

#------------------------------------------------------------------------------
def fillComments_fellingCard(destCmtDict, srcCmtDict):
    """
        fill source comments dictionary into destination comments dictionary
            note:
            here srcCmtDict may be is main comment dict or sub comment dict
    """
    logging.debug("--------- source comment: idx=%d, num=%d ---------", srcCmtDict['curCmtIdx'], srcCmtDict['curCmtNum']);
    #for item in srcCmtDict.items() :
    #    logging.debug("%s", item);
    destCmtDict['id'] = srcCmtDict['curCmtNum'];

    if(srcCmtDict['isSubComment']):
        destCmtDict['author'] = srcCmtDict['publisherNickname'];
    else:
        destCmtDict['author'] = srcCmtDict['userNickname'];
    #logging.info("done for author");

    if(srcCmtDict['isSubComment']):
        destCmtDict['author_email'] = srcCmtDict['publisherName'];#s0.publisherName="chenlin198412@126";
    else:
        destCmtDict['author_email'] = "";
    #logging.info("done for author_email");

    if(srcCmtDict['isSubComment']):
        destCmtDict['author_url'] = saxutils.escape(genNeteaseUserUrl(srcCmtDict['publisherName']));
    else:
        destCmtDict['author_url'] = saxutils.escape(gVal['blogEntryUrl']);
    #logging.info("done for author_url");

    if(srcCmtDict['isSubComment']):
        destCmtDict['author_IP'] = srcCmtDict['ip'];
    else:
        destCmtDict['author_IP'] = "";
    #logging.info("done for author_IP");

    # method 1:
    #epoch1000 = srcCmtDict['publishTime']
    #epoch = float(epoch1000) / 1000
    #localTime = time.localtime(epoch)
    #gmtTime = time.gmtime(epoch)
    # method 2:

    #s0.publishTime=1374626867596;
    #s4.publishTime=1348561288458;
    publishTimeStr = srcCmtDict['publishTime'];
    #logging.info("publishTimeStr=%s", publishTimeStr);
    publishTimeStrInt = int(publishTimeStr);
    publishTimeStrIntSec = publishTimeStrInt/1000;
    publishTimeStrIntSecStr = str(publishTimeStrIntSec);
    localTime = crifanLib.timestampToDatetime(publishTimeStrIntSecStr);
    #logging.info("localTime=%s", localTime);
    #pubTimeStr = srcCmtDict['shortPublishDateStr'] + " " + srcCmtDict['publishTimeStr'];
    #localTime = datetime.strptime(pubTimeStr, "%Y-%m-%d %H:%M:%S");
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    destCmtDict['date'] = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");
    #logging.info("done for date and date_gmt");

    # handle some speical condition
    #logging.debug("before decode, coment content:\n%s", srcCmtDict['content']);
    #cmtContent = srcCmtDict['content'].decode('unicode-escape'); # convert from \uXXXX to character
    cmtContent = srcCmtDict['content'];
    #logging.debug("after decode, coment content:\n%s", cmtContent);
    destCmtDict['content'] = cmtContent;
    #logging.info("done for content");

    destCmtDict['approved'] = 1;
    destCmtDict['type'] = '';
    destCmtDict['parent'] = srcCmtDict['parentCmtNum'];
    destCmtDict['user_id'] = 0;

    logging.debug("author=%s", destCmtDict['author']);
    logging.debug("author_email=%s", destCmtDict['author_email']);
    logging.debug("author_IP=%s", destCmtDict['author_IP']);
    logging.debug("author_url=%s", destCmtDict['author_url']);
    logging.debug("date=%s", destCmtDict['date']);
    logging.debug("date_gmt=%s", destCmtDict['date_gmt']);
    logging.debug("content=%s", destCmtDict['content']);
    logging.debug("parent=%s", destCmtDict['parent']);

    return destCmtDict;

#------------------------------------------------------------------------------
# check whether the input 163 blog user is other type user:
# (1) jdidi155@126     in http://blog.163.com/jdidi155@126
# (2) againinput4@yeah in http://blog.163.com/againinput4@yeah/
# note:
# for some extremly special ones:
# hi_ysj -> http://blog.163.com/hi_ysj
def isOtherTypeUser(blogUser) :
    isOthertype = False;
    if blogUser and (len(blogUser) > 4 ) :
        if blogUser[-4:] == '@126' :
            isOthertype = True;
        elif blogUser[-4:] == '@yeah' :
            isOthertype = True;
        else :
            isOthertype = False;
    return isOthertype;

#------------------------------------------------------------------------------
# genarate the 163 blog user url from input user name
# jdidi155@126          -> http://blog.163.com/jdidi155@126
# againinput4@yeah      -> http://blog.163.com/againinput4@yeah/
# miaoyin2008.happy     -> http://miaoyin2008.happy.blog.163.com
# note:
# for some extremly special ones:
# http://blog.163.com/hi_ysj
# the generated is http://hi_ysj.blog.163.com/
# is a workable url but is redirect
def genNeteaseUserUrl(blogUser) :
    global gConst;

    url = '';
    try :
        # http://owecn.blog.163.com/blog/static/862559512011112684224161/
        # whose comments contain 'publisherName'=None
        if blogUser :
            if isOtherTypeUser(blogUser) :
                url = gConst['blogDomain163'] + "/" + blogUser;
            else : # is normal
                url = "http://" + blogUser + ".blog.163.com"
    except :
        logging.debug("Can not generate blog user url for input blog user %s", blogUser);
    return url;

#------------------------------------------------------------------------------
# fill source comments dictionary into destination comments dictionary
def fillComments(destCmtDict, srcCmtDict):
    logging.debug("--------- source comment: idx=%d, num=%d ---------", srcCmtDict['curCmtIdx'], srcCmtDict['curCmtNum']);
    #for item in srcCmtDict.items() :
    #    logging.debug("%s", item);
    destCmtDict['id'] = srcCmtDict['curCmtNum'];

    decodedNickname = srcCmtDict['publisherNickname'].decode('unicode-escape');
    destCmtDict['author'] = decodedNickname;
    destCmtDict['author_email'] = srcCmtDict['publisherEmail'];
    destCmtDict['author_url'] = saxutils.escape(genNeteaseUserUrl(srcCmtDict['publisherName']));
    destCmtDict['author_IP'] = srcCmtDict['ip'];

    # method 1:
    #epoch1000 = srcCmtDict['publishTime']
    #epoch = float(epoch1000) / 1000
    #localTime = time.localtime(epoch)
    #gmtTime = time.gmtime(epoch)
    # method 2:
    pubTimeStr = srcCmtDict['shortPublishDateStr'] + " " + srcCmtDict['publishTimeStr'];
    localTime = datetime.strptime(pubTimeStr, "%Y-%m-%d %H:%M:%S");
    gmtTime = crifanLib.convertLocalToGmt(localTime);
    destCmtDict['date'] = localTime.strftime("%Y-%m-%d %H:%M:%S");
    destCmtDict['date_gmt'] = gmtTime.strftime("%Y-%m-%d %H:%M:%S");

    # handle some speical condition
    #logging.debug("before decode, coment content:\n%s", srcCmtDict['content']);
    cmtContent = srcCmtDict['content'].decode('unicode-escape'); # convert from \uXXXX to character
    #logging.debug("after decode, coment content:\n%s", cmtContent);
    destCmtDict['content'] = cmtContent;

    destCmtDict['approved'] = 1;
    destCmtDict['type'] = '';
    destCmtDict['parent'] = srcCmtDict['parentCmtNum'];
    destCmtDict['user_id'] = 0;

    logging.debug("author=%s", destCmtDict['author']);
    logging.debug("author_email=%s", destCmtDict['author_email']);
    logging.debug("author_IP=%s", destCmtDict['author_IP']);
    logging.debug("author_url=%s", destCmtDict['author_url']);
    logging.debug("date=%s", destCmtDict['date']);
    logging.debug("date_gmt=%s", destCmtDict['date_gmt']);
    logging.debug("content=%s", destCmtDict['content']);
    logging.debug("parent=%s", destCmtDict['parent']);

    return destCmtDict;


#------------------------------------------------------------------------------
# extract the 'permaSerial' filed from the single response blog string
def extractPermaSerial(singleBlogStr):
    permaSerial = '';
    foundPerma = re.search(r's[0-9]{1,10}\.permaSerial="(?P<permaSerial>[0-9]{1,100})";', singleBlogStr);
    permaSerial = foundPerma.group("permaSerial");
    logging.debug("Extracted permaSerial=%s", permaSerial);
    return permaSerial;

#------------------------------------------------------------------------------
# find prev permanent link from soup
def findPrevPermaLink(soup) :
    prevLinkStr = False;
    try :
        foundPrevLink = soup.find(attrs={"class":"pleft thide"});
        prevLinkStr = foundPrevLink.a['href'];
        #prevLinkTitleStr = foundPrevLink.a.string.strip();
        logging.debug("Found previous permanent link %s", prevLinkStr);
        foundPrev = True;
    except :
        foundPrev = False;
        prevLinkStr = "";
        logging.debug("Can not find previous permanent link");

    return prevLinkStr;

#------------------------------------------------------------------------------
# find the real end of previous link == earliest permanent link
# Why do this:
# for some blog, if stiky some blog, which is earliest than the lastFoundPermaSerial
# then should check whether it has more previuous link or not
# if has, then find the end of previous link
# eg: http://cqyoume.blog.163.com/blog
def findRealFirstPermaLink(blogEntryUrl, permaSerial) :
    endOfPrevLink = '';
    try :
        curLink = blogEntryUrl + "/blog/static/" + permaSerial;
        logging.debug("Start find real first permanent link from %s", curLink);

        lastLink = curLink;

        while curLink :
            # save before
            lastLink = curLink;

            # open it
            respHtml = crifanLib.getUrlRespHtml(curLink);
            soup = BeautifulSoup(respHtml);

            # find previous link util the end
            curLink = findPrevPermaLink(soup);

        endOfPrevLink = lastLink;
        logging.debug("Found the earliest link %s", endOfPrevLink);
    except:
        logging.debug("Can not find the earliest link for %s", permaSerial);

    return endOfPrevLink;

################################################################################
# Implemented Common Functions
################################################################################

#------------------------------------------------------------------------------
# extract title fom url, html
def extractTitle(url, html):
    (needOmit, titleUni) = (False, "");
    try :
        if(url == gVal['special']['feelingCard']['url']):
            titleUni = unicode(gVal['blogUser']) + u"的心情随笔";
        else:
            soup = htmlToSoup(html);
            foundTitle = soup.find(attrs={"class":"tcnt"});

            # foundTitle should not empty
            # foundTitle.string is unicode type here
            titleStr = foundTitle.string.strip();
            titleUni = unicode(titleStr);
        logging.debug("Extrated title=%s", titleUni);
    except :
        (needOmit, titleUni) = (False, "");

    return (needOmit, titleUni);

#------------------------------------------------------------------------------
# extract datetime fom url, html
def extractDatetime(url, html) :
    datetimeStr = '';
    try :
        if(url == gVal['special']['feelingCard']['url']):
            currentDatetime = datetime.now();
            logging.debug("currentDatetime=%s", currentDatetime);
            datetimeStr = currentDatetime.strftime('%Y-%m-%d %H:%M:%S');
            logging.debug("datetimeStr=%s", datetimeStr);
        else:
            soup = htmlToSoup(html);
            foundDatetime = soup.find(attrs={"class":"blogsep"});
            datetimeStr = foundDatetime.string.strip(); #2010-11-15 09:44:12
    except :
        datetimeStr = "";

    return datetimeStr

#------------------------------------------------------------------------------
# extract blog item content fom url, html
def extractContent(url, html) :
    contentStr = '';
    try :
        if(url == gVal['special']['feelingCard']['url']):
            contentStr = u"当前帖子是专门为心情随笔新建，内容为空。所有的心情随笔的内容，都在此帖子的评论中。";
        else:
            soup = htmlToSoup(html);
            foundContent = soup.find(attrs={"class":"bct fc05 fc11 nbw-blog ztag"});

            # note:
            # here must use BeautifulSoup-3.0.6.py
            # for CData in BeautifulSoup-3.0.4.py has bug :
            # process some kind of string will fail when use CData
            # eg: http://benbenwo1091.blog.163.com/blog/static/26634402200842202442518/
            # CData for foundContent.contents[11] will fail
            mappedContents = map(CData, foundContent.contents);
            contentStr = ''.join(mappedContents);
    except :
        contentStr = '';

    return contentStr;

#------------------------------------------------------------------------------
# extract category from url, html
def extractCategory(url, html) :
    catUni = '';
    try :
        if(url == gVal['special']['feelingCard']['url']):
            catUni = "";
        else:
            soup = htmlToSoup(html);
            foundCat = soup.find(attrs={"class":"fc03 m2a"});
            catStr = foundCat.string.strip();
            catUni = unicode(catStr);
    except :
        catUni = "";

    return catUni;

#------------------------------------------------------------------------------
# extract tags info from url, html
def extractTags(url, html) :
    tagList = [];
    try :
        if(url == gVal['special']['feelingCard']['url']):
            tagList = [];
        else:
            soup = htmlToSoup(html);

            # extract tags from following string:
            # blogTag:'wordpress,importer,无法识别作者,author',

            # blogUrl:'blog/static/1727994912012040341700',
            nbInit = soup.find(attrs={"class":"phide nb-init"});
            nbInitUni = unicode(nbInit);
            #nbInitStr = str(nbInit)
            blogTagP = re.compile(r"blogTag:'(?P<blogTag>.*)',\s+blogUrl:'");
            searched = blogTagP.search(nbInitUni);
            #searched = blogTagP.search(nbInitStr)
            tags = searched.group("blogTag");
            tagList = tags.split(',');
    except :
        tagList = [];

    return tagList;

#------------------------------------------------------------------------------
# fetch and parse comments
# return the parsed dict value
def fetchAndParseComments(url, html):
    cmtRespDictList = [];
    parsedCommentsList = [];

    if(url == gVal['special']['feelingCard']['url']):
        cmtRespDictList = fetchComments_feelingCard();
        if(cmtRespDictList) :
            # got valid comments, now proess it
            for cmtDict in cmtRespDictList :
                comment = {};
                #fill all comment field
                comment = fillComments_fellingCard(comment, cmtDict);
                parsedCommentsList.append(comment);
    else:
        #extract comments if exist
        soup = htmlToSoup(html);
        cmtRespDictList = fetchComments(url, soup);
        #logging.info("cmtRespDictList=%s", cmtRespDictList);
        if(cmtRespDictList) :
            # got valid comments, now proess it
            for cmtDict in cmtRespDictList :
                comment = {};
                #fill all comment field
                comment = fillComments(comment, cmtDict);
                parsedCommentsList.append(comment);

    return parsedCommentsList;

#------------------------------------------------------------------------------
# find next permanent link from url, html
def findNextPermaLink(url, html) :
    nextLinkStr = '';
    try :
        if(url == gVal['special']['feelingCard']['url']):
            #Special feeling card is the last post, so next is null
            nextLinkStr = "";
            gVal['special']['feelingCard']['processed'] = True;
        else:
            #logging.info("url=%s, html=%s", url, html);


            # this.p={  m:2,
                      # b:2,
                      # loftPermalink:'',
                      # id:'fks_087070082087081071087094082095080086088070092080083064',
                      # blogTitle:'»Ã',
                      # ...
                      # blogUrl:'blog/static/409586532005710312550',
                      # isPublished:1,
                      # istop:false,
                      # type:2,
                      # modifyTime:1123657975000,
                      # publishTime:1123657975000,
                      # permalink:'blog/static/409586532005710312550',
                      # ...
                    # }
            foundPublishTime = re.search(r"publishTime:(?P<publishTime>\d{5,20}),", html);
            logging.debug("foundPublishTime=%s", foundPublishTime);
            if foundPublishTime :
                publishTime = foundPublishTime.group("publishTime");
                logging.debug("publishTime=%s", publishTime);

                # http://api.blog.163.com/yangzaitime/dwr/call/plaincall/BlogBeanNew.getNewerAndOlderBlog.dwr
                #
                # callCount=1
                # scriptSessionId=${scriptSessionId}187
                # c0-scriptName=BlogBeanNew
                # c0-methodName=getNewerAndOlderBlog
                # c0-id=0
                # c0-param0=number:1123657975000
                # batchId=279839
                #
                # //#DWR-INSERT
                # //#DWR-REPLY
                # dwr.engine._remoteHandleCallback('279839','0',{nextBlogTitle:"\u4E0E\u6218\u53CB\u59B9\u59B9\u7684\u4E00\u6B21\u7A81\u56F4",preBlogPermalink:null,nextBlogPermalink:"blog/static/40958653200571031680",preBlogTitle:null});

                c0ScriptName = "BlogBeanNew";
                c0MethodName = "getNewerAndOlderBlog";
                c0Param0 = "number:" + str(publishTime);
                # c0Param1 = "number:" + str(0);
                # c0Param2 = "number:" + str(1);
                blogsDwrRespHtml = getPlaincallRespDwrStr(c0ScriptName, c0MethodName, c0Param0)
                logging.debug("blogsDwrRespHtml=%s", blogsDwrRespHtml);

                # //#DWR-REPLY
                # dwr.engine._remoteHandleCallback('1','0',{nextBlogTitle:"\u4E0E\u6218\u53CB\u59B9\u59B9\u7684\u4E00\u6B21\u7A81\u56F4",preBlogPermalink:null,nextBlogPermalink:"blog/static/40958653200571031680",preBlogTitle:null});

                foundNextBlogPermalink = re.search(r",nextBlogPermalink:\"(?P<nextBlogPermalink>blog/static/\d+)\",", blogsDwrRespHtml);
                logging.debug("foundNextBlogPermalink=%s", foundNextBlogPermalink);
                if foundNextBlogPermalink :
                    nextBlogPermalink = foundNextBlogPermalink.group("nextBlogPermalink");
                    logging.debug("nextBlogPermalink=%s", nextBlogPermalink);

                    nextLinkStr = gVal['blogEntryUrl'] + "/" + nextBlogPermalink
                    logging.debug("nextLinkStr=%s", nextLinkStr);

            # soup = htmlToSoup(html);
            # #logging.info("htmlToSoup,soup=%s", soup);
            # foundNextLink = soup.find(attrs={"class":"pright thide"});
            # logging.debug("foundNextLink=%s", foundNextLink);
            # if(foundNextLink):
            #     nextLinkStr = foundNextLink.a['href'];

            if((not nextLinkStr) and (not gVal['special']['feelingCard']['processed'])):
                #here when last one,
                #return the special url of FeelingCard
                logging.debug("Next perma link is empty, so in last, take special process.");
                nextLinkStr = gVal['special']['feelingCard']['url'];

                gVal['special']['feelingCard']['processed'] = True;

        if(nextLinkStr):
            logging.debug("Found next permanent link %s", nextLinkStr);
        else:
            logging.debug("Not found next permanent link");
    except :
        nextLinkStr = '';
        logging.debug("Can not find next permanent link.");

    return nextLinkStr;

#------------------------------------------------------------------------------
# possible date format:
# (1) 2011-12-26 08:46:03
def parseDatetimeStrToLocalTime(datetimeStr):
    parsedLocalTime = datetime.strptime(datetimeStr, '%Y-%m-%d %H:%M:%S') # here is GMT+8 local time
    return parsedLocalTime;

#------------------------------------------------------------------------------
# check whether is self blog pic
def isSelfBlogPic(picInfoDict):
    isSelfPic = False;

    filename = picInfoDict['filename'];
    fd1 = picInfoDict['fields']['fd1'];
    fd2 = picInfoDict['fields']['fd2'];
    fd3 = picInfoDict['fields']['fd3'];

    #if ((fd1=='ph') or (fd1=='bimg')) and (fd2=='126') and (fd3=='net') :
    if ((fd2=='126') and (fd3=='net')) or (fd2=='blog' and fd3=='163'):
        #print "isSelfBlogPic: yes";

        # is 163 pic
        # http://imgAAA.BBB.126.net/CCC/DDD.EEE
        # AAA=None/1/3/6/7/182/..., BBB=ph/bimg, CCC=gA402SeBEI_fgrOs8HjFZA==/uCnmEQiWL40RrkIJnXKjsA==, DDD=2844867589615022702/667940119751497876, EEE=jpg
        #
        # http://img.blog.163.com/photo/sDClDadN7qfbzi0CcW9GXA==/580401401977762343.jpg
        # http://img.blog.163.com/photo/ZZqr_fc0wkU262FTCJZlYA==/291608075872538448.jpg

        isSelfPic = True;
    else :
        #print "isSelfBlogPic: no";
        isSelfPic = False;

    return isSelfPic;

#------------------------------------------------------------------------------
def getProcessPhotoCfg():

    # possible own 163 pic link:
    # http://img1.bimg.126.net/photo/4OhNd7YZHKcWBijDhH_xkw==/4545539398901511141.jpg
    # http://img7.bimg.126.net/photo/6Sr67VS8U_RjyPLm5DDomw==/2315976108376294877.jpg
    # http://img.ph.126.net/L1z4EBxPAMwKj1WNRn6YTw==/3388114294667569667.jpg
    # http://img3.ph.126.net/vnCN6SMX6Kx6qM1BuEwEdg==/2837549240237180773.jpg
    # http://img5.ph.126.net/xR2T_SFlDqkzMRv2-Hwv6A==/3088061969509771535.jpg
    # http://img6.ph.126.net/mSalyXJwPfy-1agdRYLWBA==/667940119751497876.jpg
    # http://img7.ph.126.net/gA402SeBEI_fgrOs8HjFZA==/2521171366414523437.jpg
    # http://img157.ph.126.net/CrAyvqUxAjL58T1ks-n42Q==/1470988228291290473.jpg
    # http://img842.ph.126.net/kHXUQVumsubuU_-u49bC9A==/868350303154275443.jpg
    # http://img699.ph.126.net/uCnmEQiWL40RrkIJnXKjsA==/2844867589615022702.jpg
    # http://imgcdn.ph.126.net/Q0B-u3-uRIsEtozkdfTDZw==/2831356790749646754.jpg

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

    respHtml = crifanLib.getUrlRespHtml(blogEntryUrl);
    soup = htmlToSoup(respHtml);

    try:
        titleAndDesc = soup.findAll(attrs={"class":"ztag pre"});
        blogTitle = titleAndDesc[0].string;
        blogDescription = titleAndDesc[1].string;
    except:
        (blogTitle, blogDescription) = ("", "");

    return (blogTitle, blogDescription);

#------------------------------------------------------------------------------
#extract 163 blog user name
# eg:
# (1) againinput4       in http://againinput4.blog.163.com/xxxxxx
#     zhao.geyu         in http://zhao.geyu.blog.163.com/xxx
# (2) jdidi155@126      in http://blog.163.com/jdidi155@126/xxx
#     againinput4@yeah  in http://blog.163.com/againinput4@yeah/xxx
# (3) hi_ysj            in http://blog.163.com/hi_ysj/
def extractBlogUser(inputUrl):
    #print "inputUrl=",inputUrl;

    crifanLib.initAutoHandleCookies("localTempCookieFile.txt");

    (extractOk, extractedBlogUser, generatedBlogEntryUrl) = (False, "", "");

    try :
        blog163com = ".blog.163.com";
        lenBlog163com = len(blog163com);

        blog163Str = "http://blog.163.com/";
        lenBlog163 = len(blog163Str);
        compEnd = lenBlog163 - 1; # compare end

        slashList = inputUrl.split("/");
        mainStr = slashList[2]; # againinput4.blog.163.com or blog.163.com

        if inputUrl[0 : compEnd] == blog163Str[0: compEnd] :
            # is http://blog.163.com/jdidi155@126/...
            extractedBlogUser = slashList[3]; # jdidi155@126
            generatedBlogEntryUrl = blog163Str + extractedBlogUser;

            extractOk = True;
        elif mainStr[(-(lenBlog163com)):] == blog163com :
            # is http://zhao.geyu.blog.163.com/...
            extractedBlogUser = mainStr[0:(-(lenBlog163com))]; # zhao.geyu
            generatedBlogEntryUrl = "http://" + extractedBlogUser + blog163com;

            extractOk = True;
        else :
            extractOk = False;
    except :
        extractOk = False;

    if (extractOk) :
        gVal['blogUser'] = extractedBlogUser;
        gVal['blogEntryUrl'] = generatedBlogEntryUrl;

        #generate feeling card url
        #http://blog.163.com/ni_chen/blog/#m=1
        #http://green-waste.blog.163.com/blog/#m=1
        gVal['special']['feelingCard']['url'] = gVal['blogEntryUrl'] + "/blog/#m=1";
        logging.info("Generated netease 163 feeling card sepeical url=%s", gVal['special']['feelingCard']['url']);

        respHtml = crifanLib.getUrlRespHtml(gVal['blogEntryUrl']);
        # extract userId
        #UD.host = {
        #  userId:39515918
        # ,userName:'zhuchao-2006'
        # ,...........
        # };

        #logging.debug("respHtml=%s", respHtml)

        udHost = re.search(r"UD\.host\s*=\s*\{\s*userId:(?P<userId>[0-9]{1,20})\s*,", respHtml);
        userId = udHost.group("userId");
        logging.info("Extracted blog useId=%s", userId);
        gVal['userId'] = userId;

    return (extractOk, extractedBlogUser, generatedBlogEntryUrl);

#------------------------------------------------------------------------------
# find the first permanent link = url of the earliset published blog item
def find1stPermalink():
    global gVal;

    (isFound, errInfo) = (False, "Unknown error!");
    blogEntryUrl = gVal['blogEntryUrl'];

    firstPermaLink = '';
    try :
        # 1. generate and open main blog url
        # blogEntryUrl = blogEntryUrl + "/blog"
        logging.debug("Begin to find the first permanent link from %s", blogEntryUrl)
        logging.debug("Begin to open %s", blogEntryUrl)

        respHtml = crifanLib.getUrlRespHtml(blogEntryUrl)

        logging.debug("Connect successfully, now begin to find the first blog item")

        # # 1. extract last page number
        # """
        # <div class="ui-1582983425 noselect js-zfrg-6541" style="display: block;">
        #   <span class="pgi pgb iblock fc03 bgc9 bdc0 js-znpg-097">上一页</span>
        #   <span class="pgi zpg1 iblock fc03 bgc9 bdc0 js-zslt-987 fc05">1</span>
        #   <span class="frg fgp fc06">...</span>
        #   <span class="pgi zpg2 iblock fc03 bgc9 bdc0">2</span>
        #   <span class="pgi zpg3 iblock fc03 bgc9 bdc0">3</span>
        #   <span class="pgi zpg4 iblock fc03 bgc9 bdc0">4</span>
        #   <span class="pgi zpg5 iblock fc03 bgc9 bdc0">5</span>
        #   <span class="pgi zpg6 iblock fc03 bgc9 bdc0">6</span>
        #   <span class="pgi zpg7 iblock fc03 bgc9 bdc0">7</span>
        #   <span class="pgi zpg8 iblock fc03 bgc9 bdc0">8</span>
        #   <span class="frg fgn fc06">...</span>
        #   <span class="pgi zpg9 iblock fc03 bgc9 bdc0">58</span>
        #   <span class="pgi pgb iblock fc03 bgc9 bdc0">下一页</span>
        # </div>
        # """
        # soup = htmlToSoup(respHtml)
        # pageClassPattern = re.compile("pgi zpg\d+ iblock fc03 bgc9 bdc0")
        # logging.debug("pageClassPattern=%s", pageClassPattern)
        # allPageNodeList = soup.findAll(attrs={"class" : pageClassPattern})
        # logging.debug("allPageNodeList=%s", allPageNodeList)
        # if allPageNodeList :
        #     lastPageNumNode = allPageNodeList[-1]
        #     logging.debug("lastPageNumNode=%s", lastPageNumNode)
        #     lastPageNumStr = lastPageNumNode.string.strip()
        #     logging.debug("lastPageNumStr=%s", lastPageNumStr)
        #     lastPageNum = int(lastPageNumStr)
        #     logging.debug("lastPageNum=%s", lastPageNum)


        # 2. init

        # # extract userId
        # #UD.host = {
        # #  userId:39515918
        # # ,userName:'zhuchao-2006'
        # # ,...........
        # # };
        # udHost = re.search(r"UD\.host\s*=\s*\{\s*userId:(?P<userId>[0-9]{1,20})\s*,", respHtml);
        # userId = udHost.group("userId");
        # logging.debug("Extracted blog useId=%s", userId);
        userId = gVal['userId'];

        # 3. get blogs and parse it
        needGetMoreBlogs = True;
        lastFoundPermaSerial = '';
        startBlogIdx = 0;
        onceGetNum = 400 # note: for get 163 blogs, one time request more than 500 will fail

        while needGetMoreBlogs :
            logging.debug("Start to get blogs: startBlogIdx=%d, onceGetNum=%d", startBlogIdx, onceGetNum);

            #blogsDwrRespHtml = getBlogsDwrRespHtml(userId, startBlogIdx, onceGetNum);
            c0ScriptName = "BlogBeanNew";
            c0MethodName = "getBlogs";
            c0Param0 = "number:" + str(userId);
            c0Param1 = "number:" + str(startBlogIdx);
            c0Param2 = "number:" + str(onceGetNum);
            blogsDwrRespHtml = getPlaincallRespDwrStr(c0ScriptName, c0MethodName, c0Param0, c0Param1, c0Param2)

            logging.debug("blogsDwrRespHtml=%s", blogsDwrRespHtml);

            # parse it
            lines = blogsDwrRespHtml.split("\r\n");
            logging.debug("lines=%s", lines);
            noBlankLines = crifanLib.removeEmptyInList(lines);

            # remove the 0,1,-1 line
            noBlankLines.pop(0); # //#DWR-INSERT
            noBlankLines.pop(0); # //#DWR-REPLY
            # eg: dwr.engine._remoteHandleCallback('1','0',[s0,s1]);
            dwrEngine = noBlankLines.pop(len(noBlankLines) - 1);
            mainBlogsNum = extratMainCmtNum(dwrEngine);

            if (mainBlogsNum > 0)  and noBlankLines :
                # if not once get max num,
                # then last line of the response is not contain permaSerial, like this:
                # s32[0]=8412120;s32[1]=8596165;............;s32[8]=8223049;
                while noBlankLines :
                    curLastBlogStr = noBlankLines.pop(-1);
                    if re.search(r'\.permaSerial', curLastBlogStr) :
                        # only contain '.permaSerial', then goto extract it
                        lastFoundPermaSerial = extractPermaSerial(curLastBlogStr);
                        break; # exit while

                if mainBlogsNum < onceGetNum :
                    needGetMoreBlogs = False;
                    logging.debug("Has got all blogs");
                else :
                    needGetMoreBlogs = True;
                    startBlogIdx += onceGetNum;
            else :
                needGetMoreBlogs = False;
        # out of while loop, set value
        if lastFoundPermaSerial :
            firstPermaLink = findRealFirstPermaLink(blogEntryUrl, lastFoundPermaSerial)
            isFound = True
        else :
            errInfo = "Can not extract real first permanent link !"
            isFound = False

    except :
        isFound = False

    if(isFound) :
        return (isFound, firstPermaLink)
    else :
        return (isFound, errInfo)

####### Login Mode ######

#------------------------------------------------------------------------------
# login 163
# extract necessary info
# username = againinput4@163.com
def loginBlog(username, password) :
    loginOk = False;

    # 1. http://againinput4.blog.163.com
    gVal['cj'] = cookielib.CookieJar();
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(gVal['cj']));
    urllib2.install_opener(opener);
    resp = urllib2.urlopen(gVal['blogEntryUrl']);

    # for index, cookie in enumerate(gVal['cj']):
        # logging.debug('[%s]:', index);
        # logging.debug("name=%s", cookie.name);
        # # cookie.__class__,cookie.__dict__,dir(cookie);
        # logging.debug("value=%s", cookie.value);
        # logging.debug("domain=%s", cookie.domain);

    # 2. https://reg.163.com/logins.jsp
    # againinput4
    usernameNoSuf = username;
    atIdx = username.find("@");
    if( atIdx > 0) :
        usernameNoSuf = username[:atIdx];

    #http://blog.163.com/loginGate.do?username=againinput4&target=http%3A%2F%2Fagaininput4.blog.163.com%2F&blogActivation=true
    loginGateUrl = "http://blog.163.com/loginGate.do?";
    loginGateUrl += "username=" + usernameNoSuf;
    loginGateUrl += "&target=" + urllib.quote(gVal['blogEntryUrl']);
    loginGateUrl += "&blogActivation=" + "true";
    logging.debug("loginGateUrl=%s", loginGateUrl);

    loginUrl = "https://reg.163.com/logins.jsp";
    postDict = {
        'username'  : username,
        'password'  : password,
        'savelogin' : 'blog',
        'type'      : '1',
        'savelogin' : '0',
        'url'       : loginGateUrl,
        };
    resp = crifanLib.getUrlResponse(loginUrl, postDict);

    respInfo = resp.info();
    # for key in respInfo.__dict__.keys() :
        # logging.debug("[%s]=%s", key, respInfo.__dict__[key]);

    # logging.debug("--------after loginUrl -----");
    # for key in respInfo.__dict__['headers'] :
        # logging.debug(key);

    cookieNameList = ["NTES_SESS", "S_INFO", "P_INFO", "SID", "JSESSIONID"];
    loginOk = crifanLib.checkAllCookiesExist(cookieNameList, gVal['cj']);
    if (not loginOk) :
        logging.error("Login fail for not all expected cookies exist !");
        return loginOk;

    respHtml = crifanLib.getUrlRespHtml(gVal['blogEntryUrl']);
    #soup = BeautifulSoup(respHtml, fromEncoding="GB18030");
    #prettifiedSoup = soup.prettify();
    #logging.debug("--------after login, main url -----\n%s", prettifiedSoup);
    #logging.debug("--------after login, main url -----\n%s", respHtml);

    # UD.host = {
        # userId: 32677678,
        # userName: 'green-waste',
        # nickName: 'green-waste',
        # imageUpdateTime: 1258015689716,
        # baseUrl: 'http://green-waste.blog.163.com/',
        # gender: '他',
        # email: 'green-waste@163.com',
        # photo163Name: 'green-waste',
        # photo163HostName: 'green-waste',
        # TOKEN_HTMLMODULE: 'b0bda791b43853d241bb0dc738b8f971',
        # isMultiUserBlog: false,
        # isWumiUser: true,
        # sRank: -100
    # };
    # UD.visitor = {
        # userId: 32677678,
        # userName: 'green-waste',
        # nickName: 'green-waste',
        # imageUpdateTime: 1258015689716,
        # userType: [12, 26],
        # baseUrl: 'http://green-waste.blog.163.com/',
        # email: 'green-waste@163.com',
        # photo163Name: 'green-waste',
        # photo163VisitorName: 'green-waste',
        # isOnwer: true,
        # isMultiUserMember: false,
        # multiUserVisitorRank: 10000,
        # isShowFaXianTip: false,
        # isShowGuanggaoTip: false,
        # isLofterInviteTip: false,
        # isVIP: false,
        # isShowYXP: false
    # };

      # window.UD = {};
      # UD.host = {
          # userId:167169970
         # ,userName:'fgsink'
         # ,nickName:'Neo'
         # ,imageUpdateTime:1278587392293
         # ,baseUrl:'http://fgsink.blog.163.com/'
         # ,gender:'他'
         # ,email:'fgsink@163.com'
         # ,photo163Name:'fgsink'
         # ,photo163HostName:'fgsink'
         # ,TOKEN_HTMLMODULE:''
         # ,isMultiUserBlog:false
         # ,isWumiUser:true
         # ,sRank:-100
      # };
      # UD.visitor = {
         # userId:32677678,
         # userName:'green-waste',
         # nickName:'green-waste',
         # imageUpdateTime:1258015689716,
         # userType:[12,26],
         # baseUrl:'http://green-waste.blog.163.com/',
         # email:'green-waste@163.com'
         # ,photo163Name:'green-waste'
         # ,photo163VisitorName:'green-waste'
         # ,isOnwer:false
         # ,isMultiUserMember:false
         # ,multiUserVisitorRank:0
         # ,isShowFaXianTip:false
         # ,isShowGuanggaoTip:false
         # ,isLofterInviteTip:false
         # ,isVIP:false
         # ,isShowYXP:false
      # };

    matched = re.search(r"UD\.host\s*?=\s*?\{.+?email\:'(?P<email>.+?)'.+?isOnwer:(?P<isBlogOwner>\w+)\s*?,", respHtml);
    #print "matched=",matched;
    if( matched ) :
        hostMail = matched.group("email");
        if(hostMail == username) :
            logging.debug("Extrat out blog host email equal with the username = %s", username);
            loginOk = True;
            isBlogOwner = matched.group("isBlogOwner");
            if(isBlogOwner.lower() == "true") :
                loginOk = True;
                logging.debug("Indeed is blog owner.");
            else :
                loginOk = False;
                logging.error("Host email equal, but you are not blog owner !");
        else :
            logging.error("Extrat out blog host email is %s, not equal with the username %s => your are not this blog's owner !", hostMail, username);
            loginOk = False;
    else :
        logging.error("Fail to extract out blog host email => do not know whether you are the host of this blog.");
        loginOk = False;

    if (not loginOk) :
        return loginOk;

    # # 3. http://blog.163.com/loginGate.do?username=againinput4&target=http%3A%2F%2Fagaininput4.blog.163.com%2F&blogActivation=true
    # resp = crifanLib.getUrlResponse(gVal['blogEntryUrl']);
    # respSoup = BeautifulSoup(resp, fromEncoding="GB18030");
    # prettifiedSoup = respSoup.prettify();
    # logging.debug("163 blog entry returned html:\r\n%s", prettifiedSoup);

    return loginOk;

#------------------------------------------------------------------------------
# check whether this post is private(self only) or not
# if error while check, consider it to non-private
def isPrivatePost(url, html) :
    isPrivate = False;

    # private posts:
    #<h3 class="title pre fs1"><span class="tcnt">private 帖子2 测试</span>&nbsp;&nbsp;<span class="bgc0 fc07 fw0 fs0">私人日志</span></h3>
    #<h3 class="title pre fs1"><span class="tcnt">private post test</span>&nbsp;&nbsp;<span class="bgc0 fc07 fw0 fs0">私人日志</span></h3>

    # public posts:
    #<h3 class="title pre fs1"><span class="tcnt">公开 帖子 测试</span>&nbsp;&nbsp;<span class="bgc0 fc07 fw0 fs0"></span></h3>
    try :
        if(url == gVal['special']['feelingCard']['url']):
            isPrivate = False;
        else:
            soup = htmlToSoup(html);
            foundBgc0 = soup.find(attrs={"class":"bgc0 fc07 fw0 fs0"});
            if foundBgc0 and foundBgc0.contents :
                for i, content in enumerate(foundBgc0.contents) :
                    curStr = content;
                    # here: type(curStr)= <class 'BeautifulSoup.NavigableString'>
                    curStr = unicode(curStr);
                    if(curStr == u"私人日志"):
                        isPrivate = True;
                        break;
    except :
        isPrivate = False;
        logging.debug("Error while check whether post is private");

    return isPrivate;

####### Modify post while in Login Mode ######

#------------------------------------------------------------------------------
# modify post content
# note:
# (1) infoDict['title'] should be unicode
def modifySinglePost(newPostContentUni, infoDict, inputCfg):
    (modifyOk, errInfo) = (False, "Unknown error!");

    postRespHtml = infoDict['respHtml'];
    title = infoDict['title'];

    # upload new blog content
    #logging.debug("New blog content to upload=\r\n%s", newPostContentUni);

    # extract cls
    #<a class="fc03 m2a" href="http://againinput4.blog.163.com/blog/#m=0&t=1&c=fks_084066086082087074083094084095085081083068093095082074085" title="tmp_todo">tmp_todo</a>

    # extract bid
    #id:'fks_081075087094087075093094087095085081083068093095082074085',
    foundBid = re.search(r"id:'(?P<bid>fks_\d+)',", postRespHtml);
    if(foundBid) :
        bid = foundBid.group("bid");
        logging.debug("bid=%s", bid);
    else :
        modifyOk = False;
        errInfo = "Can't extract bid from post response html.";
        return (modifyOk, errInfo);

    #<a class="fc03 m2a" href="http://againinput4.blog.163.com/blog/#m=0&amp;t=1&amp;c=fks_084066086082085064082082085095085081083068093095082074085" title=
    #hrefP = r'class="fc03 m2a" href="http://\w+\.blog\.163\.com/blog/.+?c=(?P<classId>fks_\d+)" title=';
    hrefP = r'class="fc03 m2a" href="http://.*?blog\.163\.com.+?c=(?P<classId>fks_\d+)" title=';
    foundClassid = re.search(hrefP, postRespHtml);
    if(foundClassid) :
        classId = foundClassid.group("classId");
        logging.debug("classId=%s", classId);
    else :
        modifyOk = False;
        errInfo = "Can't extract classId from post response html.";
        return (modifyOk, errInfo);

    #extract:
    #<span class="sep fc07">|</span><a class="noul m2a" href="http://againinput4.blog.163.com/blog/getBlog.do?bid=fks_087067093080081074087081085074072087086065083095095071093087">编辑</a>
    #from html
    foundGetblog = re.search(r'class="noul m2a" href="(?P<getBlogUrl>http://\w+?\.blog\.163\.com/blog/getBlog\.do\?bid=fks_\d+)"', postRespHtml);
    if(foundGetblog) :
        getBlogUrl = foundGetblog.group("getBlogUrl");
        logging.debug("getBlogUrl=%s", getBlogUrl);
    else :
        modifyOk = False;
        errInfo = "Can't extract getBlogUrl from post response html.";
        return (modifyOk, errInfo);

    #access:
    #http://againinput4.blog.163.com/blog/getBlog.do?bid=fks_087067093080081074087081085074072087086065083095095071093087
    #to get :
    # <input class="ytag" type="hidden" name="NETEASE_BLOG_TOKEN_EDITBLOG" value="18a51c507a2407ca8a6ee920c8f46d26"/>
    getBlogRespHtml = crifanLib.getUrlRespHtml(getBlogUrl);
    foundEditBlogToken = re.search(r'name="NETEASE_BLOG_TOKEN_EDITBLOG" value="(?P<editBlogToken>\w+)"', getBlogRespHtml);
    if(foundEditBlogToken) :
        editBlogToken = foundEditBlogToken.group("editBlogToken");
        logging.debug("editBlogToken=%s", editBlogToken);
    else :
        modifyOk = False;
        errInfo = "Can't extract NETEASE_BLOG_TOKEN_EDITBLOG from getBlogUrl response html.";
        return (modifyOk, errInfo);

    #  location.vcd = 'http://api.blog.163.com/cap/captcha.jpgx?parentId=172799491&r=';
    foundCaptcha = re.search(r"location\.vcd\s+?=\s+?'(?P<captchaUrl>.+?)';", getBlogRespHtml);
    if(foundCaptcha) :
        captchaUrl = foundCaptcha.group("captchaUrl");

        # following is emulation of goto
        retryNum = 5;
        for tries in range(retryNum) :
            logging.debug("begin do %d times verify code", tries);
            # do what you want normally do here

            verifyCode = "";

            # process verify code == captcha
            # url is:
            #http://api.blog.163.com/cap/captcha.jpgx?parentId=172799491&r=581079
            #captchaUrl = "http://api.blog.163.com/cap/captcha.jpgx";
            #captchaUrl += "?parentId=" + parentId;

            # add 6 digit random value
            captchaUrl += str(crifanLib.randDigitsStr(6));
            logging.debug("captchaUrl=%s", captchaUrl);
            respHtml = crifanLib.getUrlRespHtml(captchaUrl);

            # captchaDir = "captcha";
            # #captchaPicFile = "returned_captcha.jpg";
            # captchaPicFile = datetime.now().strftime('%Y%m%d_%H%M%S') + "_captcha.jpg";

            # saveToFile = captchaDir + "/" + captchaPicFile;
            # crifanLib.saveBinDataToFile(respHtml, saveToFile);
            # print "save verify code pic OK, saveToFile=",saveToFile;

            # openedImg = Image.open(saveToFile);
            # print "openedImg=",openedImg;
            # openedImg.show();
            # print "openedImg OK";

            #jpgData = respHtml;
            #newImg = Image.new("RGB", (60,24));
            #img = newImg.fromstring(jpgData);
            #img.show();

            if(gVal['importedPil'] == False):
                logging.debug("now will import PIL module");
                from PIL import Image;
                logging.debug("import PIL module OK");
                gVal['importedPil'] = True;
            img = Image.open(StringIO.StringIO(respHtml));
            # 如果看不到图片，请参考：
            #【已解决】Python中通过Image的open之后，去show结果打不开bmp图片，无法正常显示图片
            #http://www.crifan.com/python_image_show_can_not_open_bmp_image_file/
            img.show();

            hintStr = unicode("请输入所看到的(4个字母的)验证码：", "utf-8");
            verifyCode = raw_input(hintStr.encode("GB18030"));
            #logging.info(u"您所输入的验证码为：%s", verifyCode);

            # captchaCode = crifanLib.parseCaptchaFromPicFile(saveToFile);
            # print "captchaCode=",captchaCode;

            # cccccccccccc

            # now to modify post

            #http://api.blog.163.com/againinput4/editBlogNew.do?p=1&n=0
            modifyPostUrl = "http://api.blog.163.com/" + gVal['blogUser'] + "/editBlogNew.do?p=1&n=0";
            logging.debug("modifyPostUrl=%s", modifyPostUrl);

            validCharsetForSubmit = "UTF-8"; # if here use "GB18030" -> after submit, the chinese char is messy code !!!
            newPostContentGb18030 = newPostContentUni.encode(validCharsetForSubmit);
            titleGb18030 = title.encode(validCharsetForSubmit);

            postDict = {
                "tag"           : "", #should find original blog tags,
                "cls"           : classId, # 新的分类 的 id, fks_084066086082085064082082085095085081083068093095082074085
                "allowview"     : "-100",
                "refurl"        : "",
                "abstract"      : "",
                "bid"           : bid, #fks_081075087094087074084084086095085081083068093095082074085
                "origClassId"   : classId, # 原先的分类的id
                "origPublishState": "1",
                "oldtitle"      : titleGb18030, #test%E6%9B%B4%E6%96%B0%E5%B8%96%E5%AD%90%E6%B5%8B%E8%AF%952
                "todayPublishedCount": "0",
                #"todayPublishedCount": "1",
                "NETEASE_BLOG_TOKEN_EDITBLOG" : editBlogToken, #e6a5766d73b0daf359a37e9361e11e46
                "title"         : titleGb18030,
                "HEContent"     : newPostContentGb18030,
                "copyPhotos"    : "",
                "suggestedSortedIds": "",
                "suggestedRecomCnt": "",
                "suggestedStyle": "0",
                "isSuggestedEachOther": "0",
                "photoBookImgUrl": "",
                "miniBlogCard"  : "0",
                'valcodeKey'    : verifyCode,
                "p"             : "1",
            };

            resp = crifanLib.getUrlResponse(modifyPostUrl, postDict);

            #soup = BeautifulSoup(resp, fromEncoding="GB18030");
            #prettifiedSoup = soup.prettify();
            #logging.debug("Modify blog url resp json\n---------------\n%s", prettifiedSoup);
            modifyPostRespHtml = crifanLib.getUrlRespHtml(modifyPostUrl, postDict);
            logging.debug("modify post response html=%s", modifyPostRespHtml);

            RET_OK              = "1";
            RET_ERR_REFERER     = "-1";
            RET_ERR_TOKEN       = "-2";
            RET_ERR_VERIFY_CODE = "-3";

            #return json:
            #modify OK:
            #{r:1,id:’1067120792′,sfx:’blog/static/17279949120120102415384/’}
            #modify fail when need captcha(verify code):
            #{r:-3,id:'',sfx:'/'}
            foundModifyResult = re.search(r"\{r:(?P<retVal>[\-\+\d]+?),id:'(?P<id>\d*?)',sfx:'(?P<sfx>.+?)'\}", modifyPostRespHtml);
            if(foundModifyResult) :
                retVal = foundModifyResult.group("retVal");

                if(retVal == RET_OK) :
                    modifyOk = True;
                elif(retVal == RET_ERR_VERIFY_CODE) :
                    modifyOk = False;
                    errInfo = u"验证码错误！"; # captcha
                elif(retVal == RET_ERR_TOKEN) :
                    modifyOk = False;
                    errInfo = u"Token错误！";
                elif(retVal == RET_ERR_REFERER) :
                    modifyOk = False;
                    errInfo = u"Referer错误！";
                else:
                    modifyOk = False;
                    errInfo = u"暂时无法保存日志，请稍后再试！";

                id = foundModifyResult.group("id");

                sfx = foundModifyResult.group("sfx");
            else :
                modifyOk = False;
                errInfo = "Can't parse the returned result of modify post.";

            if(tries < (retryNum - 1)):
                if(retVal == RET_ERR_VERIFY_CODE):
                    logging.info("verify code fail, do %d retry", tries + 1)
                    continue # do retry
                else :
                    break # quit here

    return (modifyOk, errInfo);

#------------------------------------------------------------------------------
if __name__=="BlogNetease":
    print "Imported: %s,\t%s"%( __name__, __VERSION__);
