#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------
【版本信息】
版本：     v18.4
作者：     crifan
联系方式： http://www.crifan.com/crifan_released_all/website/python/blogstowordpress/

【详细信息】
BlogsToWordPress：将(新版)百度空间，网易163，新浪Sina，QQ空间，人人网，CSDN，搜狐Sohu，Blogbus博客大巴，天涯博客，点点轻博客等博客搬家到WordPress
http://www.crifan.com/crifan_released_all/website/python/blogstowordpress/

【使用说明】
BlogsToWordPress使用前必读
http://www.crifan.com/crifan_released_all/website/python/blogstowordpress/before_use/

BlogsToWordPress 的用法的举例说明
http://www.crifan.com/crifan_released_all/website/python/blogstowordpress/usage_example/

如何扩展BlogsToWordPress以支持更多类型的博客搬家
http://www.crifan.com/crifan_released_all/website/python/blogstowordpress/extend_blog_type/

BlogsToWordPress – WordPress博客搬家工具 讨论区
http://www.crifan.com/bbs/categories/blogstowordpress

【TODO】
1.增加对于friendOnly类型帖子的支持。
2.支持自定义导出特定类型的帖子为public和private。
3.支持设置导出WXR帖子时的顺序：正序和倒序。

【版本历史】
[v18.4]
[BlogNetease.py]
1. update for find nex post link

[v18.3]
[BlogSina.py]
1.fixbug -> support sub comments for some post:
http://blog.sina.com.cn/s/blog_89445d4f0101jgen.html

[v18.2]
[BlogSina.py]
1.fixbug -> support blog author reply comments

[v18.1]
[BlogDiandian.py]
1. fix post content and next perma link for http://remixmusic.diandian.com
2. fix title for post title:
BlogsToWordpress.py -f http://remixmusic.diandian.com/?p=669 -l 1
BlogsToWordpress.py -f http://remixmusic.diandian.com/?p=316 -l 1
BlogsToWordpress.py -f http://remixmusic.diandian.com/?p=18117 -l 1
BlogsToWordpress.py -f http://remixmusic.diandian.com/post/2013-05-13/40051897352 -l 1
3. fix post content for:
BlogsToWordpress.py -f http://remixmusic.diandian.com/post/2013-05-13/40051897352 -l 1

[v17.7]
1. add note when not designate -s or -f
[BlogNetease.py]
2. add emotion into post
eg:
http://blog.163.com/ni_chen/blog/#m=1
-> 心情随笔
3. support direct input feeling card url:
BlogsToWordpress.py -f http://green-waste.blog.163.com/blog/#m=1
BlogsToWordpress.py -f http://blog.163.com/ni_chen/blog/#m=1
[BlogSina.py]
4. fix parse sina post comment response json string
http://blog.sina.com.cn/s/blog_4701280b0101854o.html
comment url:
http://blog.sina.com.cn/s/comment_4701280b0101854o_1.html
[BlogDiandian.py]
5. fix bug now support http://googleyixia.com/ to find first perma link, next perma link, extract title, tags

[v17.2]
1. [BlogNetease] update to fix bug: can not find first permanent link

[v17.1]
1.fix error for extract post title  and nex link for:
http://78391997.qzone.qq.com/

[v17.0]
1.fix csdn pic download

[v16.9]
1.update for only support baidu new space

[v16.8]
1. [BlogBaidu] fix bug for catetory extract, provided by Zhenyu Jiang
2. add template BlogXXX.py for add support for more new blog type

[v16.6]
1. [BlogBlogbus] fix bugs for extract title and date time string
2. [BlogQQ] add support for http://84896189.qzone.qq.com, which contain special content & comments & subComments

[v16.2]
1. csdn: Can not find the first link for http://blog.csdn.net/v_JULY_v, error=Unknown error!
2. fix bug: on ubuntu, AttributeError: ‘module’ object has no attribute ‘getwindowsversion’

[v16.0]
1. add BlogTianya support
2. add BlogDiandian support
3. fix path combile bug in mac, add logRuntimeInfo

[v13.9]
1. BlogRenren add captcha for login

[v13.8]
1. do release include chardet 1.0.1

[v12.8]
1. BlogBaidu update for support new space

[v11.7]
1.move blog modules into sub dir
2.change pic search pattern to support non-capture match

[v11.5]
1. support Blogbus
2. add unified downloadFile and isFileValid during process pic
3. fix pic filter regular pattern to support more type picture, include 3 fields, https, upper suffix
4. support use default pic setting
5. support new baidu space
6. support many template for new baidu space, include:
时间旅程,平行线,边走边看,窗外风景,雕刻时光,粉色佳人,理性格调,清心雅筑,低调优雅,蜕变新生,质感酷黑,经典简洁
7. support non-title post for new baidu space

[v9.2]
1. support modify 163 post via manually input verify code.

[v9.1]
1. export WXR during processing => whole process speed become a little bit faster !
2. change default pic prefix path to http://localhost/wp-content/uploads/pic

[v8.7]
1. support all type of other site pic for BlogSina

[v8.6]
1. support other site pic for BlogSina
2. support quoted filename check for crifanLib

[v8.4]
1. support more type pic for BlogQQ

[v8.3]
1. add Sohu blog support.
2. add auto omit invalid/hidden post which returned by extractTitle.
3. add remove control char for comment author and content

[v7.0]
1. add CSDN blog support.

[v6.2]
1. add RenRen Blog support.
2. For title and category, move repUniNumEntToChar and saxutils.escape from different blog providers into main function

[v5.6]
1. （当评论数据超多的时候，比如sina韩寒博客帖子评论，很多都是2,3万个的）添加日志信息，显示当前已处理多少个评论。

-------------------------------------------------------------------------------
"""

#---------------------------------import---------------------------------------
import os;
import platform;
import re;
import sys;
sys.path.append("libs/crifan");
sys.path.append("libs/crifan/blogModules");
sys.path.append("libs/thirdparty");
import math;
import time;
import codecs;
import logging;
import urllib;
from datetime import datetime,timedelta;
from optparse import OptionParser;
from string import Template,replace;
import xml;
from xml.sax import saxutils;

import crifanLib;

import BlogNetease;
import BlogBaidu;
import BlogSina;
import BlogQQ;
import BlogRenren;
import BlogCsdn;
import BlogSohu;
import BlogBlogbus;
import BlogTianya;
import BlogDiandian;
#Change Here If Add New Blog Provider Support

#--------------------------------const values-----------------------------------
__VERSION__ = "v18.4 TODO: find and merge v18.3";

gConst = {
    'generator'         : "http://www.crifan.com/crifan_released_all/website/python/blogstowordpress/",
    'tailUni'           : u"""

</channel>
</rss>""",
    'picRootPathInWP'   : "http://localhost/wp-content/uploads/pic",
    'othersiteDirName'  : 'other_site',

    #Change Here If Add New Blog Provider Support
    # for different blog provider
    'blogs' : {
        'Baidu' :   {
            'blogModule'        : BlogBaidu, # module name, should same with above import BlogXXX
            'mandatoryIncStr'   : "hi.baidu.com", # url must contain this
            'descStr'           : "Baidu Space", # Blog description string
        },

        'Netease' : {
            'blogModule'        : BlogNetease,
            'mandatoryIncStr'   : "blog.163.com",
            'descStr'           : "Netease 163 Blog",
        },

        'Sina' : {
            'blogModule'        : BlogSina,
            'mandatoryIncStr'   : "blog.sina.com.cn",
            'descStr'           : "Sina Blog",
        },

        'QQ' :   {
            'blogModule'        : BlogQQ,
            #'mandatoryIncStr'   : "qzone.qq.com",
            # special one http://blog.qq.com/qzone/622007179/1333268691.htm
            'mandatoryIncStr'   : ".qq.com",
            'descStr'           : "QQ Space",
        },

        'Renren' : {
            'blogModule'        : BlogRenren,
            'mandatoryIncStr'   : ".renren.com",
            'descStr'           : "Renren Blog",
        },

        'Csdn' : {
            'blogModule'        : BlogCsdn,
            'mandatoryIncStr'   : "blog.csdn.net",
            'descStr'           : "CSDN Blog",
        },

        'Sohu' : {
            'blogModule'        : BlogSohu,
            'mandatoryIncStr'   : "blog.sohu.com",
            'descStr'           : "Sohu Blog",
        },

        'Blogbus' : {
            'blogModule'        : BlogBlogbus,
            'mandatoryIncStr'   : ".blogbus.com",
            'descStr'           : "Blogbus Blog",
        },

        'BlogTianya' : {
            'blogModule'        : BlogTianya,
            'mandatoryIncStr'   : "blog.tianya.cn",
            'descStr'           : "Tianya Blog",
        },

        'BlogDiandian' : {
            'blogModule'        : BlogDiandian,
            'mandatoryIncStr'   : ".diandian.com",
            'descStr'           : "Diandian Qing Blog",
        },
    } ,
};

#----------------------------------global values--------------------------------
gVal = {
    'blogProvider'          : None,
    'postList'              : [],
    'catNiceDict'           : {}, # store { catName: catNiceName}
    'tagSlugDict'           : {}, # store { tagName: tagSlug}
    'curItem'               : { 'catNiceDict':{},
                                'tagSlugDict':{},
                                },
    'postID'                : 0,
    'curPostUrl'            : "",
    'blogUser'              : '',
    'blogEntryUrl'          : '',
    'processedUrlList'      : [],
    'processedStUrlList'    : [],
    'replacedUrlDict'       : {},
    'outputFileName'        : '',
    'fullHeadInfo'          : '', #  include : header + category + generator
    'statInfoDict'          : {}, # store statistic info
    'errorUrlList'          : [], # store the (pic) url, which error while open
    'postModifyPattern'     : '', # the string, after repalce the pattern, used for each post

    #----------------------------------
    # used to output xml during processing
    'wxrHeaderUni'          : '',
    'wxrHeaderSize'         : 0,

    'generatorUni'          : '',
    'generatorSize'         : 0,

    'tailUni'               : '',
    'tailSize'              : 0,

    'categoriesUni'         : '',
    'categoriesSize'        : 0,

    'tagsUni'               : '',
    'tagsSize'              : 0,

    'itemsUni'              : '',
    'itemsSize'             : 0,

    'curGeneratedUni'       : '',
    'curGeneratedSize'       : 0,

    'wxrValidUsername'      : '',
    'curOutputFileIdx'      : 0,
    'outputFileCreateTime'  : '',

    'nextCatId'        : 1,
    'nextTagId'        : 1,
    #----------------------------------
    'curPicCfgDict'         : {}, # store current/active/real picure config dict
};

#--------------------------configurable values---------------------------------
gCfg ={
# For defalut setting for following config value, please refer parameters.
    # where to save the downloaded pictures
    # Default (in code) set to: gConst['picRootPathInWP']
    'picPathInWP'       : '',
    # Default (in code) set to: gCfg['picPathInWP'] + '/' + gConst['othersiteDirName']
    'otherPicPathInWP'  : '',
    # process pictures or not
    'processPic'        : '',
    # process other site pic or not
    'processOtherPic'   : '',
    # omit process pic, which is similar before errored one
    'omitSimErrUrl'     : '',
    # do translate or not
    'googleTrans'           : '',
    # process comments or not
    'processCmt'        : '',
    # post ID prefix address
    'postPrefAddr'     : '',
    # max/limit size for output XML file
    'maxXmlSize'        : 0,
    # function execute times == max retry number + 1
    # when fail to do something: fetch page/get comment/....)
    'funcTotalExecNum'  : 1,

    'username'          : '',
    'password'          : '',
    'postTypeToProcess' : '',
    'processType'       : '',

    #Change Here If Add New Blog Provider Support
    # for modify post, auto jump over the post of
    # baidu: "文章内容包含不合适内容，请检查", "文章标题包含不合适内容，请检查"
    # other blog : TODO
    'autoJumpSensitivePost' : '',
};

#--------------------------functions--------------------------------------------

#------------------------------------------------------------------------------
# just print whole line
def printDelimiterLine() :
    logging.info("%s", '-'*80);
    return ;

#------------------------------------------------------------------------------
# open output file name in rw mode, return file handler
def openOutputFile():
    global gVal;
    # 'a+': read,write,append
    # 'w' : clear before, then write
    return codecs.open(gVal['outputFileName'], 'a+', 'utf-8');

#------------------------------------------------------------------------------
# init for output file
def initForOutputFile():
    global gVal;
    gVal['curOutputFileIdx'] = 0;
    gVal['outputFileCreateTime'] = datetime.now().strftime('%Y%m%d_%H%M');
    return;

#------------------------------------------------------------------------------
# just create new output file
def createNewOutputFile():
    global gVal;
    gVal['outputFileName'] = "WXR_" + gVal['blogProvider'] + '_[' + gVal['blogUser'] + "]_" + gVal['outputFileCreateTime'] + '-' + str(gVal['curOutputFileIdx']) + '.xml';
    expFile = codecs.open(gVal['outputFileName'], 'w', 'utf-8');
    if expFile:
        logging.info('Created export WXR file: %s', gVal['outputFileName']);
        expFile.close();

        # update
        gVal['curOutputFileIdx'] += 1;
        logging.debug("gVal['curOutputFileIdx']=%d", gVal['curOutputFileIdx']);
    else:
        logging.error("Can not open writable exported WXR file: %s", gVal['outputFileName']);
        sys.exit(2);
    return;

#------------------------------------------------------------------------------
# add CDATA, also validate it for xml
def packageCDATA(info):
    #info = saxutils.escape('<![CDATA[' + info + ']]>');
    info = '<![CDATA[' + info + ']]>';
    return info;

#------------------------------------------------------------------------------
# download file
def defDownloadFile(curPostUrl, picInfoDict, dstPicFile) :
    curUrl = picInfoDict['picUrl'];
    #use common function to download file
    return crifanLib.downloadFile(curUrl, dstPicFile);

#------------------------------------------------------------------------------
#check file validation
def defIsFileValid(picInfoDict):
    curUrl = picInfoDict['picUrl'];
    #use common function to check file validation
    return crifanLib.isFileValid(curUrl);

#------------------------------------------------------------------------------
# generate the file name for other pic
# depend on following picInfoDict definition
def defGenNewOtherPicName(picInfoDict):
    newOtherPicName = "";

    filename = picInfoDict['filename'];
    fd1 = picInfoDict['fields']['fd1'];
    fd2 = picInfoDict['fields']['fd2'];

    newOtherPicName = fd1 + '_' + fd2 + "_" + filename;

    return newOtherPicName;

#------------------------------------------------------------------------------
# check whether is self blog pic
# depend on following picInfoDict definition
# here default to set True: consider all pic is self blog pic
def defIsSelfBlogPic(picInfoDict):
    isSelfPic = True;
    logging.debug("defIsSelfBlogPic: %s", isSelfPic);
    return isSelfPic;

#------------------------------------------------------------------------------
# get the found pic info after re.search
# foundPic is MatchObject
def defGetFoundPicInfo(foundPic):
    # here should corresponding to singlePicUrlPat in curPicCfgDict
    picUrl  = foundPic.group(0);
    fd1     = foundPic.group("fd1"); # blog user's name / img1
    fd2     = foundPic.group("fd2"); # blogbus / blogbuscdn
    fd3     = foundPic.group("fd3"); # com
    fd4     = foundPic.group("fd4"); #
    fd5     = foundPic.group("fd5"); #
    fd6     = foundPic.group("fd6"); #
    filename= foundPic.group("filename");
    suffix  = foundPic.group("suffix");

    #logging.debug("fd:%s,%s,%s,%s,%s,%s, filename=%s, suffix=%s", fd1,fd2,fd3,fd4,fd5,fd6, filename, suffix);

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
        'isSelfBlog'    : False, # value is set by call isSelfBlogPic
    };

    if (suffix.lower() in crifanLib.getPicSufList()) :
        picInfoDict['isSupportedPic'] = True;
        logging.debug("%s is supported pic", picUrl);

    return picInfoDict;

#------------------------------------------------------------------------------
# 1. generate the default picture config dict
# 2. init config dict
def initPicCfgDict():
    global gVal;

    # 1. generate the default picture config dict
    logging.debug("now to generate the default picture config dict");

    picSufChars = crifanLib.getPicSufChars();
    logging.debug("picSufChars=%s", picSufChars);

    # more about the following re pattern corresponding pic url type
    # can refer the detailed comments in each blog's getProcessPhotoCfg function

    defPicCfgDict = {
        #'allPicUrlPat'      : r'(?<=src=")http://\w+?\.\w+?\.?\w+?\.?\w+?\.?\w+?\.?\w+?/[\w%\-=]{0,50}[/]?[\w%\-/=]*/[\w\-\.]{1,100}' + r'\.[' + picSufChars + r']{3,4}(?=")',
        #'singlePicUrlPat'   : r'http://(?P<fd1>\w+?)\.(?P<fd2>\w+?)(\.(?P<fd3>\w+?))?(\.(?P<fd4>\w+?))?(\.(?P<fd5>\w+?))?(\.(?P<fd6>\w+?))?/([\w%\-=]{0,50})[/]?[\w\-/%=]*/(?P<filename>[\w\-\.]{1,100})' + r'\.(?P<suffix>[' + picSufChars + r']{3,4})',

        #'allPicUrlPat'      : r'(?<=src=")http://\w+?\.\w+?\.?\w*?\.?\w*?\.?\w*?\.?\w*?/[\w%\-=]{0,50}[/]?[\w%\-/=]*/[\w\-\.]{1,100}' + r'\.[' + picSufChars + r']{3,4}(?=")',
        #'singlePicUrlPat'   : r'http://(?P<fd1>\w+?)\.(?P<fd2>\w+?)(\.(?P<fd3>\w*?))?(\.(?P<fd4>\w*?))?(\.(?P<fd5>\w*?))?(\.(?P<fd6>\w*?))?/([\w%\-=]{0,50})[/]?[\w\-/%=]*/(?P<filename>[\w\-\.]{1,100})' + r'\.(?P<suffix>[' + picSufChars + r']{3,4})',

        #'allPicUrlPat'      : r'(?<=src=")https?://\w+?\.\w+?\.?\w*?\.?\w*?\.?\w*?\.?\w*?/[\w%\-=]{0,50}[/]?[\w%\-/=]*/[\w\-\.]{1,100}' + r'\.[' + picSufChars + r']{3,4}(?=")',
        #'singlePicUrlPat'   : r'https?://(?P<fd1>\w+?)\.(?P<fd2>\w+?)(\.(?P<fd3>\w*?))?(\.(?P<fd4>\w*?))?(\.(?P<fd5>\w*?))?(\.(?P<fd6>\w*?))?/([\w%\-=]{0,50})[/]?[\w\-/%=]*/(?P<filename>[\w\-\.]{1,100})' + r'\.(?P<suffix>[' + picSufChars + r']{3,4})',

        'allPicUrlPat'      : r'(?<=src=")https?://(?:\w+?)\.(?:\w+?)(?:\.(?:\w*?))?(?:\.(?:\w*?))?(?:\.(?:\w*?))?(?:\.(?:\w*?))?/[\w%\-=]{0,50}[/]?[\w%\-/=]*/[\w\-\.]{1,100}' + r'\.[' + picSufChars + r']{3,4}(?=")',
        'singlePicUrlPat'   : r'https?://(?P<fd1>\w+?)\.(?P<fd2>\w+?)(\.(?P<fd3>\w*?))?(\.(?P<fd4>\w*?))?(\.(?P<fd5>\w*?))?(\.(?P<fd6>\w*?))?/([\w%\-=]{0,50})[/]?[\w\-/%=]*/(?P<filename>[\w\-\.]{1,100})' + r'\.(?P<suffix>[' + picSufChars + r']{3,4})',

        # allPicUrlPat:     search pattern for all pic, should not include '()'
        # singlePicUrlPat:  search pattern for single pic, should inclde '()'
        'getFoundPicInfo'       : defGetFoundPicInfo,   # function to get the found pic info after re.search
        'isSelfBlogPic'         : defIsSelfBlogPic,     # function to func to check whether is self blog pic, otherwise is other site pic
        'genNewOtherPicName'    : defGenNewOtherPicName,# function to generate the new name for other pic
        'isFileValid'           : defIsFileValid,   # function to check the (pic) url/file is valid or not
        'downloadFile'          : defDownloadFile,  # function to download picture, maybe some special blog pic download need special process:
                                                    # 1. QQ: speed is low
                                                    # 2. blogbus: download pic need referer
    };

    logging.debug("defPicCfgDict=%s", defPicCfgDict);

    # 2. init config dict
    gotPicCfgDict = getProcessPhotoCfg();
    logging.debug("gotPicCfgDict=%s", gotPicCfgDict);

    curPicCfgDict = gotPicCfgDict;
    for eachCfg in gotPicCfgDict:
        if(not gotPicCfgDict[eachCfg]):
            # if empty -> use default config
            curPicCfgDict[eachCfg] = defPicCfgDict[eachCfg];

    gVal['curPicCfgDict'] = curPicCfgDict;

    logging.debug("gVal['curPicCfgDict']=%s", gVal['curPicCfgDict']);

    return ;

#------------------------------------------------------------------------------
# 1. extract picture URL from blog content
# 2. process it:
#       remove overlapped
#       remove processed
#       saved into the gVal['processedUrlList']
#       download
#       replace url
def processPhotos(blogContent):
    global gVal;
    global gCfg;
    global gConst;

    if gCfg['processPic'] == 'yes' :
        try :
            crifanLib.calcTimeStart("process_all_picture");
            logging.debug("Begin to process all pictures");

            #logging.debug("before find pic, post Conten=%s", blogContent);

            curPicCfgDict = gVal['curPicCfgDict'];
            allUrlPattern = curPicCfgDict['allPicUrlPat'];
            #print "allUrlPattern=",allUrlPattern;

            # if matched, result for findall() is a list when no () in pattern
            matchedList = re.findall(allUrlPattern, blogContent);
            logging.debug("Len(matchedList)=%d", len(matchedList));
            logging.debug("matchedList=%s", matchedList);
            if matchedList :
                nonOverlapList = crifanLib.uniqueList(matchedList); # remove processed
                # remove processed and got ones that has been processed
                (filteredPicList, existedList) = crifanLib.filterList(nonOverlapList, gVal['processedUrlList']);
                if filteredPicList :
                    logging.debug("Filtered url list to process:\n%s", filteredPicList);
                    picNum = 0;
                    for curUrl in filteredPicList :
                        # to check is similar, only when need check and the list it not empty
                        if ((gCfg['omitSimErrUrl'] == 'yes') and gVal['errorUrlList']):
                            (isSimilar, simSrcUrl) = crifanLib.findSimilarUrl(curUrl, gVal['errorUrlList']);
                            if isSimilar :
                                logging.warning("  Omit process %s for similar with previous error url", curUrl);
                                logging.warning("               %s", simSrcUrl);
                                continue;

                        logging.debug("Now to process %s", curUrl);
                        # no matter:(1) it is pic or not, (2) follow search fail or not
                        # (3) latter fail to fetch pic or not -> still means this url is processed
                        gVal['processedUrlList'].append(curUrl);
                        picNum += 1;

                        # process this url
                        singleUrlPattern = curPicCfgDict['singlePicUrlPat'];
                        #print "singleUrlPattern=",singleUrlPattern;

                        foundPic = re.search(singleUrlPattern, curUrl);
                        if foundPic :
                            #print "foundPic=",foundPic;

                            picInfoDict = {
                                'isSupportedPic': False,
                                'picUrl'        : "", # the current pic url
                                'filename'      : "", # filename of pic
                                'suffix'        : "", # maybe empty for sina pic url
                                'fields'        : {}, # depend on the implemented functions, normal should contains fd1/fd2/fd3/...
                                'isSelfBlog'    : False,#is self blog pic, otherwise is other site pic
                            };

                            picInfoDict = curPicCfgDict['getFoundPicInfo'](foundPic);
                            # print "picInfoDict=",picInfoDict;

                            if picInfoDict['isSupportedPic'] :
                                picUrl  = picInfoDict['picUrl'];
                                filename= picInfoDict['filename'];
                                suffix  = picInfoDict['suffix'];
                                if(not suffix):
                                    # for sina pic url:
                                    # http://s14.sinaimg.cn/middle/3d55a9b7g9522d474a84d&amp;690
                                    # http://s14.sinaimg.cn/middle/3d55a9b7g9522d474a84d&690
                                    # no suf, then set to jpg
                                    suffix = 'jpg';
                                suffix = suffix.lower();

                                #print "filename=",filename;
                                #print "suffix=",suffix
                                #print "picInfoDict['fields']=",picInfoDict['fields'];

                                # check isSelfBlog first to get info for latter isFileValid
                                picInfoDict['isSelfBlog'] = curPicCfgDict['isSelfBlogPic'](picInfoDict);
                                # print "picInfoDict['isSelfBlog']=",picInfoDict['isSelfBlog'];

                                # indeed is pic, process it
                                #(picIsValid, errReason) = curPicCfgDict['isFileValid'](curUrl);
                                (picIsValid, errReason) = curPicCfgDict['isFileValid'](picInfoDict);
                                # print "picIsValid=%s,errReason=%s"%(picIsValid, errReason);
                                if picIsValid :
                                    # 1. prepare info
                                    dstPicFile = ''
                                    nameWithSuf = filename + '.' + suffix;
                                    curPath = os.getcwd();
                                    #dstPathOwnPicOld = curPath + '\\' + gVal['blogUser'] + '\\pic';
                                    dstPathOwnPic = os.path.join(curPath, gVal['blogUser'], 'pic');

                                    # 2. create dir for save pic
                                    if (os.path.isdir(dstPathOwnPic) == False) :
                                        os.makedirs(dstPathOwnPic); # create dir recursively
                                        logging.info("Create dir %s for save downloaded pictures of own site", dstPathOwnPic);
                                    if gCfg['processOtherPic'] == 'yes' :
                                        #dstPathOtherPic = dstPathOwnPic + '\\' + gConst['othersiteDirName'];
                                        dstPathOtherPic = os.path.join(dstPathOwnPic, gConst['othersiteDirName']);
                                        if (os.path.isdir(dstPathOtherPic) == False) :
                                            os.makedirs(dstPathOtherPic); # create dir recursively
                                            logging.info("Create dir %s for save downloaded pictures of other site", dstPathOtherPic);
                                    # 3. prepare info for follow download and save
                                    if(picInfoDict['isSelfBlog']):
                                        #print "++++ yes is self blog pic";
                                        newPicUrl = gCfg['picPathInWP'] + '/' + nameWithSuf;
                                        #dstPicFile = dstPathOwnPic + '\\' + nameWithSuf;
                                        dstPicFile = os.path.join(dstPathOwnPic, nameWithSuf);
                                    else :
                                        # is othersite pic
                                        #print "--- is other pic";
                                        if gCfg['processOtherPic'] == 'yes' :
                                            #newNameWithSuf = fd1 + '_' + fd2 + "_" + nameWithSuf;
                                            newNameWithSuf = curPicCfgDict['genNewOtherPicName'](picInfoDict) + '.' + suffix;
                                            #print "newNameWithSuf=",newNameWithSuf;
                                            newPicUrl = gCfg['otherPicPathInWP'] + '/' + newNameWithSuf;
                                            #dstPicFile = dstPathOtherPic + '\\' + newNameWithSuf;
                                            dstPicFile = os.path.join(dstPathOtherPic, newNameWithSuf);
                                        else :
                                            dstPicFile = ''; # for next not download
                                            #newPicUrl = curUrl

                                    # download pic and replace url
                                    logging.debug("dstPicFile=%s", dstPicFile);

                                    #if dstPicFile and crifanLib.downloadFile(curUrl, dstPicFile) :
                                    #if dstPicFile and curPicCfgDict['downloadFile'](gVal['curPostUrl'], picInfoDict, dstPicFile) :
                                    if dstPicFile != '':
                                        logging.debug("try to download picture %s", picInfoDict['picUrl'])
                                        if curPicCfgDict['downloadFile'](gVal['curPostUrl'], picInfoDict, dstPicFile):
                                            # replace old url with new url
                                            logging.debug("download pic OK, now to replace url");

                                            # http://b306.photo.store.qq.com/psb?/8d8d9a4f-2e9f-4b37-82d4-4559d7ec8472/E8WLK8l*kBjpak.5kg.xPzZ.**38oN517LBfrBNEAaQ!/b/YQN5aLZpBwAAYmuLa7YOBwAA
                                            # will fail for follow line
                                            #blogContent = re.compile(curUrl).sub(newPicUrl, blogContent);
                                            # so use this line
                                            blogContent = blogContent.replace(curUrl, newPicUrl);

                                            # record it
                                            gVal['replacedUrlDict'][curUrl] = newPicUrl;
                                            logging.debug("Replace %s with %s", curUrl, newPicUrl);
                                            #logging.debug("After replac, new blog content:\n%s", blogContent);

                                            logging.info("    Processed picture %3d: %s", picNum, curUrl);
                                        else:
                                            logging.info("    Download failed for picture %3d: %s", picNum, curUrl);
                                    else:
                                        logging.info("    Not process other site pic for processOtherPic=%s", gCfg['processOtherPic']);

                                else :
                                    logging.info("    Invalid picture: %s, reason: %s", curUrl, errReason);
                                    if (gCfg['omitSimErrUrl'] == 'yes'): # take all error pic into record
                                        # when this pic occur error, then add to list
                                        gVal['errorUrlList'].append(curUrl);
                                        #logging.debug("Add invalid %s into global error url list.", curUrl);
                                        logging.info("    Add invalid %s into global error url list.", curUrl);
                            else :
                                logging.debug("Omit unsupported picture %s", curUrl);
                # for that processed url, only replace the address
                if existedList :
                    for processedUrl in existedList:
                        # some pic url maybe is invalid, so not download and replace,
                        # so here only processed that downloaded and replaceed ones
                        if processedUrl in gVal['replacedUrlDict'] :
                            newPicUrl = gVal['replacedUrlDict'][processedUrl];
                            blogContent = re.compile(processedUrl).sub(newPicUrl, blogContent);
                            logging.debug("For processed url %s, not download again, only replace it with %s", processedUrl, newPicUrl);
            logging.debug("Done for process all pictures");
            gVal['statInfoDict']['processPicTime'] += crifanLib.calcTimeEnd("process_all_picture");
            logging.debug("Successfully to process all pictures");
        except :
            logging.warning('  Process picture failed.');

    return blogContent;

#------------------------------------------------------------------------------
# post process blog content:
# 1. download pic and replace pic url
# 2. remove invalid ascii control char
def postProcessContent(blogContent) :
    processedContent = '';
    try :
        blogContent = packageCDATA(blogContent);

        # 1. extract pic url, download pic, replace pic url
        afterProcessPic = processPhotos(blogContent);

        # 2. remove invalid ascii control char
        afterFilter = crifanLib.removeCtlChr(afterProcessPic);

        processedContent = afterFilter;
    except :
        logging.debug("Fail while post process for blog content");

    return processedContent;

#------------------------------------------------------------------------------
# calc the bytes/size of utf-8 string of input unicode
def utf8Bytes(unicodeVal) :
    if (unicodeVal):
        utf8Val = unicodeVal.encode("utf-8");
        bytes = len(utf8Val);
    else:
        bytes = 0;
    return bytes;

#------------------------------------------------------------------------------
# process each feteched post info
def processSinglePost(infoDict) :
    # remove the control char in title:
    # eg;
    # http://green-waste.blog.163.com/blog/static/32677678200879111913911/
    # title contains control char:DC1, BS, DLE, DLE, DLE, DC1
    infoDict['title'] = crifanLib.removeCtlChr(infoDict['title']);

    # do translate here -> avoid in the end,
    # too many translate request to google will cause "HTTPError: HTTP Error 502: Bad Gateway"
    infoDict['titleForPublish'] = generatePostName(infoDict['title']);

    if(gCfg['processType'] == "exportToWxr") :
        # do some post process for blog content
        infoDict['content'] = postProcessContent(infoDict['content']);

        # export single post item if necessary
        #--------------------------- start --------------------------------
        crifanLib.calcTimeStart("export_posts");

        # generate (unicode) strings
        category = infoDict['category'];
        if(not (category in gVal['catNiceDict'])):
            curCatNice = generatePostName(category);
            gVal['curItem']['catNiceDict'][category] = curCatNice;
            # also add to global dict
            gVal['catNiceDict'][category] = curCatNice;

            gVal['nextCatId'] = 1;
            newCategoriesUni = generateCategories(gVal['catNiceDict']);
        else:
            gVal['curItem']['catNiceDict'][category] = gVal['catNiceDict'][category];
            newCategoriesUni = gVal['categoriesUni'];

        # add into global tagSlugDict
        # note: input tags should be unicode type
        if(infoDict['tags']) :
            for eachTag in infoDict['tags'] :
                if eachTag : # maybe is u'', so here should check whether is empty
                    if(eachTag in gVal['tagSlugDict']):
                        gVal['curItem']['tagSlugDict'][eachTag] = gVal['tagSlugDict'][eachTag];
                    else :
                        curTagSlug = generatePostName(eachTag);
                        gVal['curItem']['tagSlugDict'][eachTag] = curTagSlug;
                        gVal['tagSlugDict'][eachTag] = curTagSlug;

        if(gVal['curItem']['tagSlugDict']) :
            newTagsUni = generateTags(gVal['tagSlugDict']);
        else:
            newTagsUni = gVal['tagsUni'];

        itemUni = generateSingleItem(infoDict);
        newItemsUni = gVal['itemsUni'] + itemUni;

        newGeneratedUni  = gVal['wxrHeaderUni']  + newCategoriesUni  + newTagsUni  + gVal['generatorUni']  + newItemsUni  + gVal['tailUni'];
        newGeneratedSize = utf8Bytes(newGeneratedUni);

        logging.debug("newGeneratedSize=%d", newGeneratedSize);
        # check whether size exceed limit
        # Note: 0 means no limit
        if gCfg['maxXmlSize'] and (newGeneratedSize > gCfg['maxXmlSize']) : # if exceed limit
            # create file for output
            createNewOutputFile();

            #write processed ones
            newFile = openOutputFile();
            newFile.write(gVal['curGeneratedUni']);
            newFile.flush();
            newFile.close();

            # update something
            gVal['nextCatId'] = 1;
            itemCategoriyUni = generateCategories(gVal['curItem']['catNiceDict']);
            gVal['categoriesUni'] = itemCategoriyUni;

            if(gVal['curItem']['tagSlugDict']) :
                itemTagsUni = generateTags(gVal['curItem']['tagSlugDict']);
            else:
                itemTagsUni = "";
            gVal['tagsUni'] = itemTagsUni;

            gVal['itemsUni'] = itemUni;

            # reset something
            gVal['tagSlugDict'] = {};
            gVal['catNiceDict'] = {};

        else : # if not exceed limit:
            # update something
            gVal['categoriesUni'] = newCategoriesUni;
            gVal['tagsUni'] = newTagsUni;
            gVal['itemsUni'] = newItemsUni;

        # update something
        gVal['curGeneratedUni']  = gVal['wxrHeaderUni']  + gVal['categoriesUni']  + gVal['tagsUni']  + gVal['generatorUni']  + gVal['itemsUni']  + gVal['tailUni'];
        gVal['curGeneratedSize'] = utf8Bytes(gVal['curGeneratedUni']);
        logging.debug("after process post, gVal['curGeneratedSize']=%d", gVal['curGeneratedSize']);

        # clear something
        gVal['curItem']['catNiceDict'] = {};
        gVal['curItem']['tagSlugDict'] = {};

        gVal['statInfoDict']['exportPostsTime'] += crifanLib.calcTimeEnd("export_posts");
        logging.debug("gVal['statInfoDict']['exportPostsTime']=%f", gVal['statInfoDict']['exportPostsTime']);

        #--------------------------- end --------------------------------

    elif (gCfg['processType'] == "modifyPost") :
        # 1. prepare new content
        newPostContentUni = gVal['postModifyPattern'];

        # replace permanent link in wordpress == title for publish
        newPostContentUni = newPostContentUni.replace("${titleForPublish}", infoDict['titleForPublish']);

        # replace title, infoDict['title'] must non-empty
        newPostContentUni = newPostContentUni.replace("${originalTitle}", unicode(infoDict['title']));

        titleUtf8 = infoDict['title'].encode("UTF-8");
        #quotedTitle = urllib.quote_plus(titleUtf8);
        quotedTitle = urllib.quote(titleUtf8);
        newPostContentUni = newPostContentUni.replace("${quotedTitle}", quotedTitle);

        # replace datetime, infoDict['datetime'] must non-empty
        localTime = parseDatetimeStrToLocalTime(infoDict['datetime']);
        newPostContentUni = newPostContentUni.replace("${postYear}", str.format("{0:4d}", localTime.year));
        newPostContentUni = newPostContentUni.replace("${postMonth}", str.format("{0:02d}", localTime.month));
        newPostContentUni = newPostContentUni.replace("${postDay}", str.format("{0:02d}", localTime.day));

        # replace category
        newPostContentUni = newPostContentUni.replace("${category}", infoDict['category']);

        # replace content
        newPostContentUni = newPostContentUni.replace("${originBlogContent}", infoDict['content']);

        # 2. modify to new content
        (modifyOk, errInfo) = modifySinglePost(newPostContentUni, infoDict, gCfg);
        if(modifyOk) :
            logging.debug("Modify %s successfully.", infoDict['url']);
        else:
            logging.error("Modify %s failed for %s.", infoDict['url'], errInfo);
            sys.exit(2);

#------------------------------------------------------------------------------
#1. open current post item
#2. save related info into post info dict
#3. return post info dict
def fetchSinglePost(url):
    global gVal;
    global gConst;
    global gCfg;

    #update post id
    gVal['postID'] += 1;

    gVal['curPostUrl'] = url;

    logging.debug("----------------------------------------------------------");
    logging.info("[%04d] %s", gVal['postID'], url);

    crifanLib.calcTimeStart("fetch_page");
    # sometime due to network error, fetch page will fail, so here do several try
    for tries in range(gCfg['funcTotalExecNum']) :
        try :
            logging.debug("Begin to get url resp html for %s", url);
            respHtml = crifanLib.getUrlRespHtml(url);
            logging.debug("Response html\n---------------\n%s", respHtml);
            gVal['statInfoDict']['fetchPageTime'] += crifanLib.calcTimeEnd("fetch_page");
            logging.debug("Successfully downloaded: %s", url);
            break # successfully, so break now
        except :
            if tries < (gCfg['funcTotalExecNum'] - 1) :
                logging.warning("Fetch page %s fail, do %d retry", url, (tries + 1));
                continue;
            else : # last try also failed, so exit
                logging.error("Has tried %d times to fetch page: %s, all failed!", gCfg['funcTotalExecNum'], url);
                sys.exit(2);

    infoDict = {
        'omit'          : False,
        'url'           : '',
        'postid'        : 0,
        'title'         : '',
        'nextLink'      : '',
        'type'          : '',
        'content'       : '',
        'datetime'      : '',
        'category'      : '',
        'tags'          : [],
        'comments'      : [], # each one is a dict value
        'respHtml'      : '',
        };

    infoDict['url']     = url;
    infoDict['postid']  = gVal['postID'];
    infoDict['respHtml']= respHtml;

    # extract title
    (needOmit, infoDict['title']) = extractTitle(url, respHtml);
    if(not infoDict['title'] ) :
        logging.error("Can not extract post title for %s !", url);
        sys.exit(2);
    else :
        infoDict['title'] = crifanLib.repUniNumEntToChar(infoDict['title']);
        # for later export to WXR, makesure is xml safe
        infoDict['title'] = saxutils.escape(infoDict['title']);
        logging.debug("Extracted post title: %s", infoDict['title']);

    # extrat next (previously published) blog item link
    # here must extract next link first, for next call to use while omit=True
    #logging.info("Begin to call findNextPermaLink");
    infoDict['nextLink'] = findNextPermaLink(url, respHtml);
    logging.debug("infoDict['nextLink']=%s", infoDict['nextLink']);
    logging.debug("Extracted post's next permanent link: %s", infoDict['nextLink']);

    isPrivate = isPrivatePost(url, respHtml);
    if(isPrivate) :
        infoDict['type'] = 'private';
        logging.debug("Post type is private.");
    else :
        # tmp not consider the "friendOnly" type
        logging.debug("Post type is public.");
        infoDict['type'] = 'publish';

    if(needOmit):
        logging.info("  Omit process current post: %s", infoDict['title']);
        infoDict['omit'] = True;
    elif((gCfg['postTypeToProcess'] == "privateOnly") and (not isPrivate)) :
        logging.info("  Omit process non-private post: %s", infoDict['title']);
        infoDict['omit'] = True;
    elif((gCfg['postTypeToProcess'] == "publicOnly") and isPrivate) :
        infoDict['omit'] = True;
        logging.info("  Omit process private post: %s", infoDict['title']);

    if (infoDict['omit']):
        return infoDict;
    else :
        logging.info("  Title = %s", infoDict['title']);

    # extract datetime
    infoDict['datetime'] = extractDatetime(url, respHtml);
    if(not infoDict['datetime'] ) :
        logging.error("Can not extract post publish datetime for %s !", url);
        sys.exit(2);
    else :
        logging.debug("Extracted post publish datetime: %s", infoDict['datetime']);

    # extract content
    infoDict['content'] = extractContent(url, respHtml);
    if(not infoDict['content'] ) :
        logging.error("Can not extract post content for %s !", url);
        sys.exit(2);
    # else :
        # logging.debug("Extracted post content: %s", infoDict['content']);

    # extract category
    infoDict['category'] = extractCategory(url, respHtml);
    if(infoDict['category']) :
        infoDict['category'] = crifanLib.repUniNumEntToChar(infoDict['category']);
        infoDict['category'] = saxutils.escape(infoDict['category']);
        logging.debug("Extracted post's category: %s", infoDict['category']);
    else :
        # here category must not empty, otherwise last export will faill for
        # keyError for: category_nicename = gVal['catNiceDict'][entry['category']],
        infoDict['category'] = "DefaultCategory";
        logging.debug("Extracted post's category is empty, set to default one: %s", infoDict['category']);

    # if is modify post, no need: tags, comments
    if(gCfg['processType'] == "exportToWxr") :
        # extract tags
        infoDict['tags'] = extractTags(url, respHtml);

        # Note: some list contain [u''], so is not meaningful, remove it here
        # for only [] is empty, [u''] is not empty -> error while exporting to WXR
        infoDict['tags'] = crifanLib.removeEmptyInList(infoDict['tags']);

        for i in range(len(infoDict['tags'])):
            infoDict['tags'][i] = saxutils.escape(infoDict['tags'][i]);

        tags = "";
        for eachTag in infoDict['tags'] :
            tags += "%s, "%(eachTag);
        logging.debug("Extracted %d tags: %s", len(infoDict['tags']), tags);

        # fetch comments
        if gCfg['processCmt'] == 'yes' :
            crifanLib.calcTimeStart("process_comment");
            try :
                infoDict['comments'] = fetchAndParseComments(url, respHtml);
                #logging.info("infoDict['comments']=%s", infoDict['comments']);
                commentLen = len(infoDict['comments']);
                if(commentLen > 0) :
                    logging.info("    Extracted comments: %4d", commentLen);
            except :
                logging.warning("Fail to process comments for %s", url);

            gVal['statInfoDict']['processCmtTime'] += crifanLib.calcTimeEnd("process_comment");

    return infoDict;

#------------------------------------------------------------------------------
# remove invalid character in url(blog's post name and category's nice name)
def removeInvalidCharInUrl(inputString):
    filterd_str = '';
    charNumerP = re.compile(r"[\w|-]");
    for c in inputString :
        if c == ' ' :
            # replace blanksplace with '_'
            filterd_str += '_';
        elif charNumerP.match(c) :
            # retain this char if is a-z,A-Z,0-9,_
            filterd_str += c;
    return filterd_str;

#------------------------------------------------------------------------------
def generateHeader():
    global gConst;
    global gVal;

    #get blog header info
    blogInfoDict = {};
    getBlogHeadInfo(blogInfoDict);

    wxrHeaderT = Template(u"""<?xml version="1.0" encoding="UTF-8"?>
<!--
    This is a WordPress eXtended RSS file generated by ${generator} as an export of
    your blog. It contains information about your blog's title and description,
    and each post's title, tags, categories, content, publish time and comments.
    You may use this file to transfer that content from one site to another.
    This file can be served as a complete backup of your blog.

    To import this information into a WordPress blog follow these steps:
    1.  Log into your blog as an administrator.
    2.  Go to Manage > Import in the blog's admin.
    3.  Choose "WordPress" from the list of importers.
    4.  Upload this file using the form provided on that page.
    5.  You will first be asked to map the authors in this export file to users
        on the blog. For each author, you may choose to map an existing user on
        the blog or to create a new user.
    6.  WordPress will then import each of the posts' info
        contained in this file onto your blog.
-->

<!-- generator="${generator}" created="${nowTime}"-->
<rss version="2.0"
    xmlns:excerpt="http://wordpress.org/export/1.1/excerpt/"
    xmlns:content="http://purl.org/rss/1.0/modules/content/"
    xmlns:wfw="http://wellformedweb.org/CommentAPI/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:wp="http://wordpress.org/export/1.1/"
>

<channel>
    <title>${blogTitle}</title>
    <!-- ${blogEntryUrl} -->
    <link>http://localhost</link>
    <description>${blogDiscription}</description>
    <pubDate>${blogPubDate}</pubDate>
    <generator>${generator}</generator>
    <language>en</language>
    <wp:wxr_version>1.1</wp:wxr_version>
    <wp:base_site_url>http://localhost</wp:base_site_url>
    <wp:base_blog_url>http://localhost</wp:base_blog_url>

    <wp:author>
        <wp:author_id>1</wp:author_id>
        <wp:author_login>${blogUser}</wp:author_login>
        <wp:author_email></wp:author_email>
        <wp:author_display_name>${authorDisplayName}</wp:author_display_name>
        <wp:author_first_name>${authorFirstName}</wp:author_first_name>
        <wp:author_last_name>${authorLastName}</wp:author_last_name>
    </wp:author>

""")
#need   nowTime, blogTitle, blogEntryUrl, blogDiscription, blogUser, generator
#       authorDisplayName, authorFirstName, authorLastName, blogPubDate

    # Note: some field value has been set before call this func
    blogInfoDict['authorDisplayName'] = packageCDATA("");
    blogInfoDict['authorFirstName'] = packageCDATA("");
    blogInfoDict['authorLastName'] = packageCDATA("");
    blogInfoDict['blogTitle'] = saxutils.escape(blogInfoDict['blogTitle']);
    blogInfoDict['blogEntryUrl'] = blogInfoDict['blogEntryUrl'];
    blogInfoDict['blogDiscription'] = saxutils.escape(blogInfoDict['blogDiscription']);
    blogInfoDict['generator'] = gConst['generator'];
    wxrHeaderUni = wxrHeaderT.substitute(blogInfoDict);

    gVal['wxrHeaderUni'] = wxrHeaderUni;
    wxrHeaderUtf8 = wxrHeaderUni.encode("utf-8");
    wxrHeaderSize=len(wxrHeaderUtf8);

    gVal['wxrHeaderUni'] = wxrHeaderUni;
    gVal['wxrHeaderSize'] = wxrHeaderSize;

    logging.info("Generate wxr header OK");

    return ;

#------------------------------------------------------------------------------
def generateGenerator():
    global gConst

    generatorT = Template(u"""
    <generator>${generator}</generator>

""")#need generator

    generatorUni = generatorT.substitute(generator = gConst['generator']);

    gVal['generatorUni'] = generatorUni;
    generatorUtf8 = generatorUni.encode("utf-8");
    generatorSize = len(generatorUtf8);

    gVal['generatorUni'] = generatorUni;
    gVal['generatorSize'] = generatorSize;

    logging.info("Generate generator OK");

    return ;

#------------------------------------------------------------------------------
def generateTail():
    global gVal;

    tailUni = gConst['tailUni'];
    tailUtf8 = tailUni.encode("utf-8");
    tailSize = len(tailUtf8);

    gVal['tailUni'] = tailUni;
    gVal['tailSize'] = tailSize;

    logging.info("Generate tail OK");

    return;

#------------------------------------------------------------------------------
def generateCategories(catNiceDict):
    global gVal

    catT = Template("""
    <wp:category>
        <wp:term_id>${categoryId}</wp:term_id>
        <wp:category_nicename>${catNicename}</wp:category_nicename>
        <wp:category_parent></wp:category_parent>
        <wp:cat_name>${catName}</wp:cat_name>
        <wp:category_description>${catDesc}</wp:category_description>
    </wp:category>
""")#need categoryId, catName, catNicename, catDesc

    categoriesUni = '';
    categoryId = gVal['nextCatId'];
    for cat in catNiceDict.keys():
        categoriesUni += catT.substitute(
            categoryId = categoryId,
            catName = packageCDATA(cat),
            catNicename = catNiceDict[cat],
            catDesc = packageCDATA(""),);
        categoryId += 1;

    gVal['nextCatId'] = categoryId;
    gVal['nextTagId'] = gVal['nextCatId'];

    return categoriesUni;

#------------------------------------------------------------------------------
def generateTags(tagSlugDict):
    global gVal

    tagT = Template("""
    <wp:tag>
        <wp:term_id>${tagNum}</wp:term_id>
        <wp:tag_slug>${tagSlug}</wp:tag_slug>
        <wp:tag_name>${tagName}</wp:tag_name>
    </wp:tag>
""")#need tagNum, tagSlug, tagName

    generatorT = Template("""
    <generator>${generator}</generator>

""")#need generator

    #compose tags string
    tagsUni = '';
    tagTermID = gVal['nextTagId'];
    for tag in tagSlugDict.keys():
        if tag :
            tagsUni += tagT.substitute(
                tagNum = tagTermID,
                tagSlug = tagSlugDict[tag],
                tagName = packageCDATA(tag),);
            tagTermID += 1;

    return tagsUni;


#------------------------------------------------------------------------------
# generate single item (unicode) string
def generateSingleItem(itemDict):
    global gVal;
    global gCfg;

    itemT = Template("""
    <item>
        <title>${itemTitle}</title>
        <!--${originalLink}-->
        <link>${itemUrl}</link>
        <pubDate>${pubDate}</pubDate>
        <dc:creator>${itemAuthor}</dc:creator>
        <guid isPermaLink="false">${itemUrl}</guid>
        <description></description>
        <content:encoded>${itemContent}</content:encoded>
        <excerpt:encoded>${itemExcerpt}</excerpt:encoded>
        <wp:post_id>${postId}</wp:post_id>
        <wp:post_date>${postDate}</wp:post_date>
        <wp:post_date_gmt>${postDateGMT}</wp:post_date_gmt>
        <wp:comment_status>open</wp:comment_status>
        <wp:ping_status>open</wp:ping_status>
        <wp:post_name>${itemPostName}</wp:post_name>
        <wp:status>${postStatus}</wp:status>
        <wp:post_parent>0</wp:post_parent>
        <wp:menu_order>0</wp:menu_order>
        <wp:post_type>post</wp:post_type>
        <wp:post_password></wp:post_password>
        <wp:is_sticky>0</wp:is_sticky>
        <category domain="category" nicename="${category_nicename}">${category}</category>
        ${tags}
        ${comments}
    </item>
"""); #need itemTitle, itemUrl, itemAuthor, category, itemContent,
# itemExcerpt, postId, postDate, itemPostName, postStatus
# originalLink

    tagsT = Template("""
        <category domain="post_tag" nicename="${tagSlug}">${tagName}</category>"""); # tagSlug, tagName

    commentT = Template("""
        <wp:comment>
            <wp:comment_id>${commentId}</wp:comment_id>
            <wp:comment_author>${commentAuthor}</wp:comment_author>
            <wp:comment_author_email>${commentEmail}</wp:comment_author_email>
            <wp:comment_author_url>${commentURL}</wp:comment_author_url>
            <wp:comment_author_IP>${commentAuthorIP}</wp:comment_author_IP>
            <wp:comment_date>${commentDate}</wp:comment_date>
            <wp:comment_date_gmt>${commentDateGMT}</wp:comment_date_gmt>
            <wp:comment_content>${commentContent}</wp:comment_content>
            <wp:comment_approved>1</wp:comment_approved>
            <wp:comment_type></wp:comment_type>
            <wp:comment_parent>${commentParent}</wp:comment_parent>
            <wp:comment_user_id>0</wp:comment_user_id>
        </wp:comment>
"""); #need commentId, commentAuthor, commentEmail,commentURL, commentDate
     # commentDateGMT, commentContent, commentAuthorIP, commentParent

    #compose tags string
    itemTagsUni = '';
    for tag in itemDict['tags']:
        if tag:
            itemTagsUni += tagsT.substitute(
                tagSlug = gVal['curItem']['tagSlugDict'][tag],
                tagName = packageCDATA(tag),);

    #compose comment string
    itemCommentsUni = "";
    logging.debug("Now will export comments = %d", len(itemDict['comments']));

    # for output info use
    maxNumReportOnce = 500;
    lastRepTime = 0;

    for curCmtNum, comment in enumerate(itemDict['comments']):
        cmtContentNoCtrlChr = crifanLib.removeCtlChr(comment['content']);
        authorNoCtrlChr = crifanLib.removeCtlChr(comment['author']);
        itemCommentsUni += commentT.substitute(
                            commentId = comment['id'],
                            commentAuthor = packageCDATA(authorNoCtrlChr),
                            commentEmail = comment['author_email'],
                            commentURL = comment['author_url'],
                            commentAuthorIP = comment['author_IP'],
                            commentDate = comment['date'],
                            commentDateGMT = comment['date_gmt'],
                            commentContent = packageCDATA(cmtContentNoCtrlChr),
                            commentParent = comment['parent'],);
        # report for each maxNumReportOnce
        curRepTime = curCmtNum/maxNumReportOnce;
        if(curRepTime != lastRepTime) :
            # report
            logging.info("  Has generated comments string: %5d", curCmtNum);
            # update
            lastRepTime = curRepTime;

    # parse datetime string into local time
    parsedLocalTime = parseDatetimeStrToLocalTime(itemDict['datetime']);
    gmtTime = crifanLib.convertLocalToGmt(parsedLocalTime);
    itemDict['pubDate'] = gmtTime.strftime('%a, %d %b %Y %H:%M:%S +0000');
    itemDict['postDate'] = parsedLocalTime.strftime('%Y-%m-%d %H:%M:%S');
    itemDict['postDateGMT'] = gmtTime.strftime('%Y-%m-%d %H:%M:%S');

    itemUni = itemT.substitute(
        itemTitle = itemDict['title'],
        originalLink = itemDict['url'],
        itemUrl = gCfg['postPrefAddr'] + str(itemDict['postid']),
        itemAuthor = gVal['wxrValidUsername'],
        category = packageCDATA(itemDict['category']),
        category_nicename = gVal['curItem']['catNiceDict'][itemDict['category']],
        itemContent = itemDict['content'],
        itemExcerpt = packageCDATA(""),
        postId = itemDict['postid'],
        postDate = itemDict['postDate'],
        postDateGMT = itemDict['postDateGMT'],
        pubDate = itemDict['pubDate'],
        itemPostName = itemDict['titleForPublish'],
        tags = itemTagsUni,
        comments = itemCommentsUni,
        postStatus = itemDict['type'],
        );

    return itemUni;

#------------------------------------------------------------------------------
# get blog header related info
def getBlogHeadInfo(blogInfoDic) :
    global gConst;
    global gVal;

    blogInfoDic['blogEntryUrl'] = gVal['blogEntryUrl'];
    (blogInfoDic['blogTitle'], blogInfoDic['blogDiscription']) = extractBlogTitAndDesc(gVal['blogEntryUrl']);
    logging.debug('Blog title: %s', blogInfoDic['blogTitle']);
    logging.debug('Blog description: %s', blogInfoDic['blogDiscription']);

    # if none, set to a string, avoid fail while latter processing them
    if not blogInfoDic['blogTitle'] :
        blogInfoDic['blogTitle'] = 'NoBlogTitle';
    if not blogInfoDic['blogDiscription'] :
        blogInfoDic['blogDiscription'] = 'NoBlogDescription';
    blogInfoDic['nowTime'] = datetime.now().strftime('%Y-%m-%d %H:%M');
    blogInfoDic['blogUser'] = gVal['wxrValidUsername'];
    blogInfoDic['blogPubDate'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000');

    logging.info("Get blog head info OK");

    return;

#------------------------------------------------------------------------------
# convert the int value total seconds to hour,minute,second type string
def toHourMinuteSecondStr(totalSecondsInt):
    return ("%02d:%02d:%02d")%(totalSecondsInt / 3600, (totalSecondsInt % 3600)/60, totalSecondsInt % 60);

#------------------------------------------------------------------------------
# output statistic info
def outputStatisticInfo() :
    totalTime = int(gVal['statInfoDict']['totalTime']);
    if gCfg['googleTrans'] == 'yes' :
        transNameTime = int(gVal['statInfoDict']['transNameTime']);
    find1stLinkTime = int(gVal['statInfoDict']['find1stLinkTime']);
    processPostsTime = int(gVal['statInfoDict']['processPostsTime']);
    fetchPageTime = int(gVal['statInfoDict']['fetchPageTime']);
    if(gCfg['processType'] == "exportToWxr") :
        exportPostsTime = int(gVal['statInfoDict']['exportPostsTime']);
        if gCfg['processPic'] == 'yes' :
            processPicTime = int(gVal['statInfoDict']['processPicTime']);
        if gCfg['processCmt'] == 'yes' :
            processCmtTime = int(gVal['statInfoDict']['processCmtTime']);

    # output output statistic info
    printDelimiterLine();
    logging.info("Total Processed [%04d] posts, averagely each consume seconds=%.4f", gVal['statInfoDict']['processedPostNum'], gVal['statInfoDict']['itemAverageTime']);
    logging.info("Total Consume Time: %s", toHourMinuteSecondStr(totalTime));
    logging.info("  Find 1stLink: %s", toHourMinuteSecondStr(find1stLinkTime));
    logging.info("  Process Post: %s", toHourMinuteSecondStr(processPostsTime));
    logging.info("      Fetch   Pages     : %s", toHourMinuteSecondStr(fetchPageTime));
    if(gCfg['processType'] == "exportToWxr") :
        logging.info("      Export  Posts     : %s", toHourMinuteSecondStr(exportPostsTime));
        if gCfg['processPic'] == 'yes' :
            logging.info("      Process Pictures  : %s", toHourMinuteSecondStr(processPicTime));
        if gCfg['processCmt'] == 'yes' :
            logging.info("      Process Comments  : %s", toHourMinuteSecondStr(processCmtTime));
    if gCfg['googleTrans'] == 'yes' :
        logging.info("      Translate Name    : %s", toHourMinuteSecondStr(transNameTime));

    return;

#------------------------------------------------------------------------------
# generate the post name for original name
# post name = [translate and ] quote it
# note: input name should be unicode type
def generatePostName(unicodeName) :
    quotedName = '';

    if unicodeName :
        nameUtf8 = unicodeName.encode("utf-8");
        if gCfg['googleTrans'] == 'yes' :
            crifanLib.calcTimeStart("translate_name");
            (transOK, translatedName) = crifanLib.transZhcnToEn(nameUtf8);
            gVal['statInfoDict']['transNameTime'] += crifanLib.calcTimeEnd("translate_name");
            if transOK :
                logging.debug("Has translated [%s] to [%s].", unicodeName, translatedName);
                translatedName = removeInvalidCharInUrl(translatedName);
                logging.debug("After remove invalid char become to %s.", translatedName);
                quotedName = urllib.quote(translatedName);
                logging.debug("After quote become to %s.", quotedName);
            else :
                quotedName = urllib.quote(nameUtf8);
                logging.warning("Translate fail for [%s], roolback to use just quoted string [%s]", nameUtf8, quotedName);
        else :
            #nameUtf8 = removeInvalidCharInUrl(nameUtf8);
            quotedName = urllib.quote(nameUtf8);

    return quotedName;

#------------------------------------------------------------------------------
# if set username and password, then try login first
# if login OK, then will got global cookie for later usage of http request
# Note: makesure has got the extracted blog user: gVal['blogEntryUrl']
def tryLoginBlog() :
    global gCfg

    if gCfg['username'] and gCfg['password'] :
        loginOk = loginBlog(gCfg['username'], gCfg['password']);

        if (loginOk):
            logging.info("%s login successfully.", gCfg['username']);
        else :
            logging.error("%s login failed !", gCfg['username']);
            sys.exit(2);
    else :
        logging.info("Username and/or password is null, now in un-login mode.");

#------------------------------------------------------------------------------
# do some initial work:
# 1. check blog provider
# 2. extract blog user and blog entry url from input url
# 3. also init some related config values
# 4. try login blog
def initialization(inputUrl):
    logging.debug("Extracting blog user from url=%s", inputUrl);

    # 1. check blog provider
    checkBlogProviderFromUrl(inputUrl);

    # 2. extract blog user and blog entry url from input url
    (extractOK, extractedBlogUser, generatedBlogEntryUrl) = extractBlogUser(inputUrl);

    if(extractOK) :
        gVal['blogUser'] = extractedBlogUser;
        gVal['blogEntryUrl'] = generatedBlogEntryUrl;

        logging.info("Extracted Blog user [%s] from %s", gVal['blogUser'], inputUrl);
        logging.info("Blog entry url is %s", gVal['blogEntryUrl']);
    else:
        logging.error("Can not extract blog user form input URL: %s", inputUrl);
        sys.exit(2);

    # 3. also init some related config values
    if(gCfg['processType'] == "exportToWxr") :
        # update some related default value
        if gCfg['picPathInWP'] == '' :
            gCfg['picPathInWP'] = gConst['picRootPathInWP'];
        if gCfg['otherPicPathInWP'] == '' :
            gCfg['otherPicPathInWP'] = gCfg['picPathInWP'] + '/' + gConst['othersiteDirName'];

        logging.debug("Set URL prefix for own   site picture: %s", gCfg['picPathInWP']);
        logging.debug("Set URL prefix for other site picture: %s", gCfg['otherPicPathInWP']);

    # 4. try login blog
    tryLoginBlog();

    return;

#------------------------------------------------------------------------------
# generate the WXR valid username
def generateWxrValidUsername():
    # make sure the username is valid in WXR: not contains non-word(non-char and number, such as '@', '_') character
    gVal['wxrValidUsername'] = crifanLib.removeNonWordChar(gVal['blogUser']);

    # Note:
    # now have found a bug for wordpress importer:
    # if usename in WXR contains underscore, then after imported, that post's username will be omitted, become to default's admin's username
    # eg: if username is green_waste, which is valid, can be recoginzed by wordpress importer,
    # then after imported posts into wordpress, the username of posts imported become to default admin(here is crifan), not we expected : green_waste
    # so here replace the underscore to ''
    gVal['wxrValidUsername'] = gVal['wxrValidUsername'].replace("_", "");
    logging.info("Generated WXR safe username is %s", gVal['wxrValidUsername']);

#------------------------------------------------------------------------------
def logRuntimeInfo():
    logging.info("Current runtime info:");
    logging.info("Paramenters       : %s", sys.argv);
    logging.info("Python version    : %s", sys.version_info);

    # ouput system type and version info
    logging.info("platform.machine()=%s", platform.machine());
    logging.info("platform.node()=%s", platform.node());
    logging.info("platform.platform()=%s", platform.platform());
    logging.info("platform.processor()=%s", platform.processor());
    logging.info("platform.python_build()=%s", platform.python_build());
    logging.info("platform.python_compiler()=%s", platform.python_compiler());
    logging.info("platform.python_branch()=%s", platform.python_branch());
    logging.info("platform.python_implementation()=%s", platform.python_implementation());
    logging.info("platform.python_revision()=%s", platform.python_revision());
    logging.info("platform.python_version()=%s", platform.python_version());
    logging.info("platform.python_version_tuple()=%s", platform.python_version_tuple());
    logging.info("platform.release()=%s", platform.release());
    logging.info("platform.system()=%s", platform.system());
    #logging.info("platform.system_alias()=%s", platform.system_alias());
    logging.info("platform.version()=%s", platform.version());
    logging.info("platform.uname()=%s", platform.uname());

    # logging.info("os.name=%s", os.name);
    # logging.info("sys.platform=%s", sys.platform);
    # if(getattr(sys, "getwindowsversion", None)):
        # logging.info("Windows version   : %s", sys.getwindowsversion());

    logging.info("Default encoding  : %s", sys.getdefaultencoding());
    logging.info("Current path      : %s", sys.prefix);
    return;

#------------------------------------------------------------------------------
def main():
    global gVal
    global gCfg

    logRuntimeInfo();

    # 0. main procedure begin
    parser = OptionParser();
    parser.add_option("-s","--srcUrl",action="store", type="string",dest="srcUrl",help=u"博客入口地址。例如: http://againinput4.blog.163.com, http://hi.baidu.com/recommend_music/。程序会自动找到你的博客的（最早发布的）第一个帖子，然后开始处理。");
    parser.add_option("-f","--startFromUrl",action="store", type="string",dest="startFromUrl",help=u"从哪个帖子（的永久链接地址）开始。例如：http://againinput4.blog.163.com/blog/static/17279949120120824544142/，http://hi.baidu.com/recommend_music/blog/item/c2896794b621ae13d31b70c3.html。如果设置此了参数，那么会自动忽略参数srcUrl");
    parser.add_option("-l","--limit",action="store",type="int",dest="limit",help=u"最多要处理的帖子的个数");
    parser.add_option("-c","--processCmt",action="store",type="string",dest="processCmt",default="yes",help=u"是否处理帖子的评论，yes或no。默认为yes");
    parser.add_option("-u","--username",action="store",type="string",default='',dest="username",help=u"博客登陆用户名");
    parser.add_option("-p","--password",action="store",type="string",default='',dest="password",help=u"博客登陆密码");
    parser.add_option("-i","--firstPostId",action="store",type="int",default=0,dest="firstPostId",help=u"导出到wordpress时候的帖子的起始ID");
    parser.add_option("-b","--processPic",action="store",type="string",default="yes",dest="processPic",help=u"是否处理（帖子内容中，属于本博客的）图片：yes或no。默认为yes。处理图片包括：下载图片，并将原图片地址替换为以wpPicPath参数的设置内容为前缀的新的地址。下载下来的图片存放在当前路径下名为用户名的文件夹中。注意，当将程序生成的WXR文件导入wordpress中之后，为了确保图片可以正确显示，不要忘了把下载下来的图片放到你的wordpress的服务器中相应的位置");
    parser.add_option("-w","--wpPicPath",action="store",type="string",dest="wpPicPath",help=u"wordpress中图片的（即，原图片所被替换的）新地址的前缀。例如：http://www.crifan.com/files/pic/recommend_music，默认设置为：http://localhost/wordpress/wp-content/uploads/BLOG_USER/pic，其中BLOG_USER是你的博客用户名。注意：此选项只有在processPic='yes'的情况下才有效");
    parser.add_option("-o","--processOtherPic",action="store",type="string",default="yes",dest="processOtherPic",help=u"是否处理（帖子内容中）其他（网站的）图片：yes或no。默认为yes。即，下载并替换对应原图片地址为参数wpOtherPicPath所设置的前缀加上原文件名。注意：此选项只有在processPic='yes'的情况下才有效");
    parser.add_option("-r","--wpOtherPicPath",action="store",type="string",dest="wpOtherPicPath",help=u"wordpress中（其他网站的）图片的（即，原其他网站的图片所被替换的）新地址的前缀。默认为 ${wpPicPath}/other_site。此选项只有在processOtherPic='yes'的情况下才有效");
    parser.add_option("-n","--omitSimErrUrl",action="store",type="string",default="yes",dest="omitSimErrUrl",help=u"是否自动忽略处理那些和之前处理过程中出错的图片地址类似的图片：yes或no。默认为yes。即，自动跳过那些图片，其中该图片的地址和之前某些已经在下载过程中出错（比如HTTP Error）的图片地址很类似。注意：此选项只有在processPic='yes'的情况下才有效");
    parser.add_option("-g","--googleTrans",action="store",type="string",default="yes",dest="googleTrans",help=u"是否执行google翻译：yes或no。通过网络调用google的api，将对应的中文翻译为英文。包括：将帖子的标题翻译为英文，用于发布帖子时的固定链接（permanent link）；将帖子的分类，标签等翻译为对应的英文，用于导出到WXR文件中");
    parser.add_option("-a","--postPrefAddr",action="store",type="string",default="http://localhost/?p=",dest="postPrefAddr",help=u"帖子导出到WXR时候的前缀，默认为http://localhost/?p=，例如可设置为：http://www.crifan.com/?p=");
    parser.add_option("-x","--maxXmlSize",action="store",type="int",default=2*1024*1024,dest="maxXmlSize",help=u"导出的单个WXR文件大小的最大值。超出此大小，则会自动分割出对应的多个WXR文件。默认为2097152（2MB=2*1024*1024）。如果设置为0，则表示无限制。");
    parser.add_option("-y","--maxFailRetryNum",action="store",type="int",default=3,dest="maxFailRetryNum",help=u"当获取网页等操作失败时的重试次数。默认为3。设置为0表示当发生错误时，不再重试。");
    parser.add_option("-v","--postTypeToProcess",action="store",type="string",default='publicOnly',dest="postTypeToProcess",help=u"要处理哪些类型的帖子：publicOnly，privateOnly，privateAndPublic。注意：当设置为非publicOnly的时候，是需要提供对应的用户名和密码的，登陆对应的博客才可以执行对应的操作，即获取对应的private等类型帖子的。");
    parser.add_option("-t","--processType",action="store",type="string",default='exportToWxr',dest="processType",help=u"对于相应类型类型的帖子，具体如何处理，即处理的类型：exportToWxr和modifyPost。exportToWxr是将帖子内容导出为WXR；modifyPost是修改帖子内容（并提交，以达到更新帖子的目的），注意需要设置相关的参数：username，password，modifyPostPatFile.");
    parser.add_option("-d","--modifyPostPatFile",action="store",type="string",dest="modifyPostPatFile",help=u"修改帖子的模板，即需要更新的帖子的新的内容。支持相关参数。注意，需要输入的配置文件是UTF-8格式的。支持的格式化参数包括： ${originBlogContent}表示原先帖子的内容；${titleForPublish}表示用于发布的帖子的标题，即翻译并编码后的标题，该标题主要用于wordpress中帖子的永久链接；${originalTitle}表示原先帖子的标题内容；${quotedTitle}表示将原标题编码后的标题；${postYear},${postMonth},${postDay}分别表示帖子发布时间的年月日，均为2位数字；${category}表示帖子的分类。");
    parser.add_option("-j","--autoJumpSensitivePost",action="store",type="string",default='yes',dest="autoJumpSensitivePost",help=u"自动跳过（即不更新处理）那些包含敏感信息的帖子：yes或no。默认为yes。比如如果去修改某些旧版百度空间帖子的话，其会返回 '文章内容包含不合适内容，请检查'，'文章标题包含不合适内容，请检查',等提示，此处则可以自动跳过，不处理此类帖子。");

    logging.info(u"版本信息：%s", __VERSION__);
    logging.info(u"1.如果脚本运行出错，请务必把上述(1)从脚本开始运行到上述所打印出来的系统信息(2)出错时候的相关信息(3)脚本所生成的BlogsToWordpress.log文件，通过复制粘贴、截图、附件等方式");
    logging.info(u"  发送至admin(at)crifan.com或跟帖（下面有地址）回复，否则如果没有足够的错误相关信息，我就是想帮你解决问题，也没法帮啊！");
    logging.info(u"2.如对此脚本使用有任何疑问，请输入-h参数以获得相应的参数说明。");
    logging.info(u"3.关于本程序详细的使用说明和更多相关信息，请参考：");
    #Change Here If Add New Blog Provider Support
    logging.info(u"  BlogsToWordPress：将（新版）百度空间，网易163，新浪Sina，QQ空间，人人网，CSDN，搜狐Sohu，博客大巴Blogbus，天涯博客，点点轻博客等博客搬家到WordPress");
    logging.info(u"  http://www.crifan.com/crifan_released_all/website/python/blogstowordpress/");
    printDelimiterLine();

    (options, args) = parser.parse_args();
    # 1. export all options variables
    for i in dir(options):
        exec(i + " = options." + i);

    # 2. init some settings
    gCfg['processType'] = processType;

    gCfg['username'] = username;
    gCfg['password'] = password;
    gCfg['postTypeToProcess'] = postTypeToProcess;

    if( ((not gCfg['username']) or (not gCfg['password'])) and (gCfg['postTypeToProcess'] != "publicOnly")) :
        logging.error("For no username or password, not support non-publicOnly type of post to process !");
        sys.exit(2);

    if(gCfg['processType'] == "modifyPost") :
        logging.info("Your process type of post is: Modify post.");

        # check parameter validation
        if( (not username) or (not password) ) :
            logging.error("For modify post, username and password, all should not empty !");
            sys.exit(2);

        # init config
        gCfg['autoJumpSensitivePost'] = autoJumpSensitivePost;

        # check parameter validation
        if modifyPostPatFile and os.path.isfile(modifyPostPatFile):
            patternFile = os.open(modifyPostPatFile, os.O_RDONLY);
            gVal['postModifyPattern']  = os.read(patternFile, os.path.getsize(modifyPostPatFile));
            gVal['postModifyPattern'] = unicode(gVal['postModifyPattern'], "utf-8");
            logging.debug("after convert to unicode, modify pattern =%s", gVal['postModifyPattern']);
        else :
            logging.error("For modify post, modifyPostPatFile is null or invalid !");
            sys.exit(2);

    elif(gCfg['processType'] == "exportToWxr") :
        logging.info("Your process type of post is: Export post to WXR(WordPress eXtended Rss).");

        gCfg['processPic'] = processPic;
        if gCfg['processPic'] == 'yes' :
            gCfg['omitSimErrUrl'] = omitSimErrUrl;
            if wpPicPath :
                # remove last slash if user input url if including
                if (wpPicPath[-1] == '/') : wpPicPath = wpPicPath[:-1];
                gCfg['picPathInWP'] = wpPicPath;
            gCfg['processOtherPic'] = processOtherPic;
            if gCfg['processOtherPic'] and wpOtherPicPath :
                # remove last slash if user input url if including
                if (wpOtherPicPath[-1] == '/') : wpOtherPicPath = wpOtherPicPath[:-1];
                gCfg['otherPicPathInWP'] = wpOtherPicPath;

        gCfg['processCmt'] = processCmt;
        gCfg['postPrefAddr'] = postPrefAddr;
        gCfg['maxXmlSize'] = maxXmlSize;

    gCfg['googleTrans'] = googleTrans;
    gCfg['funcTotalExecNum'] = maxFailRetryNum + 1;

    # init some global values

    gVal['postID'] = firstPostId;
    # prepare for statistic
    if(gCfg['processType'] == "exportToWxr") :
        gVal['statInfoDict']['processPicTime']  = 0.0;
        gVal['statInfoDict']['processCmtTime']  = 0.0;
        gVal['statInfoDict']['exportPostsTime'] = 0.0;

    gVal['statInfoDict']['processedPostNum'] = 0; # also include that is omited
    gVal['statInfoDict']['transNameTime']   = 0.0;
    gVal['statInfoDict']['fetchPageTime']   = 0.0;
    gVal['statInfoDict']['find1stLinkTime'] = 0.0;

    crifanLib.initAutoHandleCookies();
    crifanLib.calcTimeStart("total");

    # 3. connect src blog and find first permal link
    if startFromUrl :
        permalink = startFromUrl;
        logging.info("Entry URL: %s", startFromUrl);

        initialization(startFromUrl);
    elif srcUrl:
        logging.info("Source URL: %s", srcUrl);

        initialization(srcUrl);

        crifanLib.calcTimeStart("find_first_perma_link");
        logging.info("Now start to find the permanent link for %s", srcUrl);
        (found, retStr)= find1stPermalink();
        if(found) :
            permalink = retStr;
            logging.info("Found the first link %s", permalink);
        else :
            logging.error("Can not find the first link for %s, error=%s", srcUrl, retStr);
            sys.exit(2);
        gVal['statInfoDict']['find1stLinkTime'] = crifanLib.calcTimeEnd("find_first_perma_link");
    else:
        logging.error("Must designate the entry URL for the first blog item !");
        logging.error(u"解决办法：指定对应的-f或-s参数。详见：");
        logging.error(u"BlogsToWordPress 的用法的举例说明");
        logging.error("http://www.crifan.com/crifan_released_all/website/python/blogstowordpress/usage_example/");
        sys.exit(2);

    # 4. main loop, fetch and process for every post
    crifanLib.calcTimeStart("process_posts");

    #initialize for export post
    if(gCfg['processType'] == "exportToWxr") :
        if gCfg['processPic'] == 'yes' :
            initPicCfgDict();

        initForOutputFile();

        generateWxrValidUsername();

        # generate wxr header info
        logging.info("Generating wxr head info ...");
        generateHeader();

        # generate generator info
        logging.info("Generating generator info ...");
        generateGenerator();

        # generate tail info
        logging.info("Generating tail info ...");
        generateTail();

        # init for current generated
        gVal['curGeneratedUni']  = gVal['wxrHeaderUni']  + gVal['categoriesUni']  + gVal['tagsUni']  + gVal['generatorUni']  + gVal['itemsUni']  + gVal['tailUni'];
        gVal['curGeneratedSize'] = utf8Bytes(gVal['curGeneratedUni']);

    while permalink:
        infoDict = fetchSinglePost(permalink);

        if(not infoDict['omit']) :
            processSinglePost(infoDict);

            gVal['postList'].append(infoDict);

        if 'nextLink' in infoDict :
            permalink = infoDict['nextLink'];
        else :
            break;

        gVal['statInfoDict']['processedPostNum'] += 1;

        if (limit and (gVal['statInfoDict']['processedPostNum'] >= limit)) :
            break;

    gVal['statInfoDict']['processPostsTime'] = crifanLib.calcTimeEnd("process_posts");

    if(gCfg['processType'] == "exportToWxr") :
        logging.info('Exporting items at last ...');
        crifanLib.calcTimeStart("export_posts");
        # output in then end always
        createNewOutputFile();
        newFile = openOutputFile();
        newFile.write(gVal['curGeneratedUni']);
        newFile.flush();
        newFile.close();
        gVal['statInfoDict']['exportPostsTime'] += crifanLib.calcTimeEnd("export_posts");

    logging.info("Process blog %s successfully", gVal['blogEntryUrl']);

    # 7. output statistic info
    gVal['statInfoDict']['totalTime'] = crifanLib.calcTimeEnd("total");
    gVal['statInfoDict']['itemAverageTime'] = gVal['statInfoDict']['totalTime'] / float(gVal['statInfoDict']['processedPostNum']);

    outputStatisticInfo();

############ Different Blog Provider ############
#------------------------------------------------------------------------------
def callBlogFunc(funcToCall, *paraList):
    blogProvider = "";

    funcName = funcToCall.func_name;

    blogProvider = gVal['blogProvider'];
    if(blogProvider in gConst['blogs']):
        blogProviderDict = gConst['blogs'][blogProvider];
        blogModule = blogProviderDict['blogModule'];

        blogDescStr = blogProviderDict['descStr'];
        trueFunc = getattr(blogModule, funcName);
        logging.debug("Now will call %s function: %s", blogDescStr, funcName);
    else:
        logging.error("Invalid blog provider: %s", blogProvider);
        sys.exit(2);
        return;

    paraLen = len(paraList);

    if(paraLen == 0):
        return trueFunc();
    elif(paraLen == 1):
        return trueFunc(paraList[0]);
    elif (paraLen == 2):
        return trueFunc(paraList[0], paraList[1]);
    elif (paraLen == 3):
        return trueFunc(paraList[0], paraList[1], paraList[2]);
    elif (paraLen == 4):
        return trueFunc(paraList[0], paraList[1], paraList[2], paraList[3]);
    elif (paraLen == 5):
        return trueFunc(paraList[0], paraList[1], paraList[2], paraList[3], paraList[4]);
    elif (paraLen == 6):
        return trueFunc(paraList[0], paraList[1], paraList[2], paraList[3], paraList[4], paraList[5]);
    elif (paraLen == 7):
        return trueFunc(paraList[0], paraList[1], paraList[2], paraList[3], paraList[4], paraList[5], paraList[6]);
    elif (paraLen == 8):
        return trueFunc(paraList[0], paraList[1], paraList[2], paraList[3], paraList[4], paraList[5], paraList[6], paraList[7]);
    else :
        logging.error("Not support function parameters exceed 8 !");
        sys.exit(2);
        return;

#------------------------------------------------------------------------------
# check whether is diandian blog url
def checkForBlogDiandian(inputUrl, respHtml) :
    isBlogDiandian = False;

    # some special diandian blog, self domain, not http://xxx.diandian.com
    #http://www.zoushijie.com/
    #http://blog.nuandao.com
    #http://nosta1gie.com
    #http://www.sankin77.com
    #http://www.zoushijie.com/post/2012-09-22/40038845472

    #method 1:
    #<body class="demo_jjl page_1 has_2_pages"><iframe ... id="diandian_controls" ... src="http://www.diandian.com/n/common/toolbar2/zousj"></iframe>
    foundDiandian = re.search('<iframe.+?id="diandian_controls".+?</iframe>', respHtml);
    #method 2:
    #foundDiandian = re.search(u"请不要在 http://www\.diandian\.com 以外的地方输入你的点点密码！".encode("UTF-8"), respHtml);

    logging.debug("foundDiandian=%s", foundDiandian);
    if(foundDiandian):
        isBlogDiandian = True;

    return isBlogDiandian;
#------------------------------------------------------------------------------
# check blog provider from url type
def checkBlogProviderFromUrlType(inputUrl) :
    (foundBlogProvider, blogStr) = (False, "Invalid Blog Provider");

    #try parse url to find reald blog provider
    logging.debug("Inputed url=%s", inputUrl);
    #check whether is DianDian Blog
    respHtml = crifanLib.getUrlRespHtml(inputUrl);
    logging.debug("inputUrl=%s, respHtml=%s", inputUrl, respHtml);
    foundBlogProvider = checkForBlogDiandian(inputUrl, respHtml);
    if(foundBlogProvider):
        (foundBlogProvider, blogStr) = (True, "BlogDiandian");

    # if(not foundBlogProvider):
        # # check for other blog provider

    logging.debug("foundBlogProvider=%s, blogStr=%s", foundBlogProvider, blogStr);

    return (foundBlogProvider, blogStr);
#------------------------------------------------------------------------------
# check the blog provider from input url
def checkBlogProviderFromUrl(inputUrl) :
    foundValidBlog = False;
    for eachBlogStr in gConst['blogs'].keys() :
        eachBlog = gConst['blogs'][eachBlogStr];
        mandatoryStr = eachBlog['mandatoryIncStr'];
        if(inputUrl.find(mandatoryStr) > 0 ):
            blogModule = eachBlog['blogModule'];
            logging.info("Your blog provider : %s.", eachBlog['descStr']);
            gVal['blogProvider'] = eachBlogStr;
            foundValidBlog = True;
            break;

    if(not foundValidBlog) :
        (foundBlogProvider, blogStr) = checkBlogProviderFromUrlType(inputUrl);
        if(foundBlogProvider):
            gVal['blogProvider'] = blogStr;
        else:
            logging.error("Can not find out blog provider from %s", inputUrl);
            sys.exit(2);

################################################################################
# Common Functions for different blog provider: baidu/netease(163)/Sina
# you can implement following functions to support move additional blog provider to wordpress
################################################################################

#------------------------------------------------------------------------------
# extract title fom url, respHtml
def extractTitle(url, respHtml):
    return callBlogFunc(extractTitle, url, respHtml);

#------------------------------------------------------------------------------
# extract datetime fom url, respHtml
def extractDatetime(url, respHtml) :
    return callBlogFunc(extractDatetime, url, respHtml);

#------------------------------------------------------------------------------
# extract blog item content fom url, respHtml
def extractContent(url, respHtml) :
    return callBlogFunc(extractContent, url, respHtml);
#------------------------------------------------------------------------------
# extract category from url, respHtml
def extractCategory(url, respHtml) :
    return callBlogFunc(extractCategory, url, respHtml);

#------------------------------------------------------------------------------
# extract tags info from url, respHtml
def extractTags(url, respHtml) :
    return callBlogFunc(extractTags, url, respHtml);

#------------------------------------------------------------------------------
# fetch and parse comments
def fetchAndParseComments(url, respHtml):
    return callBlogFunc(fetchAndParseComments, url, respHtml);

#------------------------------------------------------------------------------
def findNextPermaLink(url, respHtml):
    return callBlogFunc(findNextPermaLink, url, respHtml);

#------------------------------------------------------------------------------
def parseDatetimeStrToLocalTime(datetimeStr):
    return callBlogFunc(parseDatetimeStrToLocalTime, datetimeStr);

#------------------------------------------------------------------------------
def getProcessPhotoCfg() :
    return callBlogFunc(getProcessPhotoCfg);

#------------------------------------------------------------------------------
# extract blog title and description
def extractBlogTitAndDesc(blogEntryUrl) :
    return callBlogFunc(extractBlogTitAndDesc, blogEntryUrl);

#------------------------------------------------------------------------------
def extractBlogUser(inputUrl):
    return callBlogFunc(extractBlogUser, inputUrl);

#------------------------------------------------------------------------------
def find1stPermalink() :
    return callBlogFunc(find1stPermalink);

####### Login Mode ######
#------------------------------------------------------------------------------
def loginBlog(username, password) :
    return callBlogFunc(loginBlog, username, password);

#------------------------------------------------------------------------------
# check whether this post is private(self only) or not
def isPrivatePost(url, respHtml) :
    return callBlogFunc(isPrivatePost, url, respHtml);

####### Modify post while in Login Mode ######
#------------------------------------------------------------------------------
# modify post content
def modifySinglePost(newPostContentUni, infoDict, inputCfg):
    return callBlogFunc(modifySinglePost, newPostContentUni, infoDict, inputCfg);


###############################################################################
if __name__=="__main__":
    # for : python xxx.py -s yyy    # -> sys.argv[0]=xxx.py
    # for : xxx.py -s yyy           # -> sys.argv[0]=D:\yyy\zzz\xxx.py
    scriptSelfName = crifanLib.extractFilename(sys.argv[0]);

    logging.basicConfig(
                    level    = logging.DEBUG,
                    format   = 'LINE %(lineno)-4d  %(levelname)-8s %(message)s',
                    datefmt  = '%m-%d %H:%M',
                    filename = scriptSelfName + ".log",
                    filemode = 'w');
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler();
    console.setLevel(logging.INFO);
    # set a format which is simpler for console use
    formatter = logging.Formatter('LINE %(lineno)-4d : %(levelname)-8s %(message)s');
    # tell the handler to use this format
    console.setFormatter(formatter);
    logging.getLogger('').addHandler(console);
    try:
        main();
    except:
        logging.exception("Unknown Error !");
        raise;
