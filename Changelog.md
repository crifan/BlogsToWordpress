# 版本历史

## v18.5 - 20171028
- optmize: change all output files to single output folder

### BlogCsdn
- fixbug: Can not find the first link for http://blog.csdn.net/chdhust

## v18.4
### BlogNetease
- update for find nex post link

## v18.3
### BlogSina
- fixbug -> support sub comments for some post:
http://blog.sina.com.cn/s/blog_89445d4f0101jgen.html

## v18.2
### BlogSina
- fixbug -> support blog author reply comments

## v18.1
### BlogDiandian
- fix post content and next perma link for
  - http://remixmusic.diandian.com
- fix title for post title:
  - BlogsToWordpress.py -f http://remixmusic.diandian.com/?p=669 -l 1
  - BlogsToWordpress.py -f http://remixmusic.diandian.com/?p=316 -l 1
  - BlogsToWordpress.py -f http://remixmusic.diandian.com/?p=18117 -l 1
  - BlogsToWordpress.py -f http://remixmusic.diandian.com/post/2013-05-13/40051897352 -l 1
- fix post content for:
  - BlogsToWordpress.py -f http://remixmusic.diandian.com/post/2013-05-13/40051897352 -l 1

## v17.7
- add note when not designate -s or -f
### BlogNetease
- add emotion into post
eg:
http://blog.163.com/ni_chen/blog/#m=1
-> 心情随笔
- support direct input feeling card url:
  - BlogsToWordpress.py -f http://green-waste.blog.163.com/blog/#m=1
  - BlogsToWordpress.py -f http://blog.163.com/ni_chen/blog/#m=1
### BlogSina
- fix parse sina post comment response json string
http://blog.sina.com.cn/s/blog_4701280b0101854o.html
comment url:
http://blog.sina.com.cn/s/comment_4701280b0101854o_1.html
### BlogDiandian
- fix bug now support http://googleyixia.com/ to find first perma link, next perma link, extract title, tags

## v17.2
### BlogNetease
- update to fix bug: can not find first permanent link

## v17.1
- fix error for extract post title  and nex link for:
http://78391997.qzone.qq.com/

## v17.0
- fix csdn pic download

## v16.9
- update for only support baidu new space

## v16.8
- [BlogBaidu] fix bug for catetory extract, provided by Zhenyu Jiang
- add template BlogXXX.py for add support for more new blog type

## v16.6
### BlogBlogbus
- fix bugs for extract title and date time string
### BlogQQ
- add support for http://84896189.qzone.qq.com, which contain special content & comments & subComments

## v16.2
- csdn: Can not find the first link for http://blog.csdn.net/v_JULY_v, error=Unknown error!
- fix bug: on ubuntu, AttributeError: ‘module’ object has no attribute ‘getwindowsversion’

## v16.0
- add BlogTianya support
- add BlogDiandian support
- fix path combile bug in mac, add logRuntimeInfo

## v13.9
- BlogRenren add captcha for login

## v13.8
- do release include chardet 1.0.1

## v12.8
- BlogBaidu update for support new space

## v11.7
- move blog modules into sub dir
- change pic search pattern to support non-capture match

## v11.5
- support Blogbus
- add unified downloadFile and isFileValid during process pic
- fix pic filter regular pattern to support more type picture, include 3 fields, https, upper suffix
- support use default pic setting
- support new baidu space
- support many template for new baidu space, include:
时间旅程,平行线,边走边看,窗外风景,雕刻时光,粉色佳人,理性格调,清心雅筑,低调优雅,蜕变新生,质感酷黑,经典简洁
- support non-title post for new baidu space

## v9.2
- support modify 163 post via manually input verify code.

## v9.1
- export WXR during processing => whole process speed become a little bit faster !
- change default pic prefix path to http://localhost/wp-content/uploads/pic

## v8.7
- support all type of other site pic for BlogSina

## v8.6
- support other site pic for BlogSina
- support quoted filename check for crifanLib

## v8.4
- support more type pic for BlogQQ

## v8.3
- add Sohu blog support.
- add auto omit invalid/hidden post which returned by extractTitle.
- add remove control char for comment author and content

## v7.0
- add CSDN blog support.

## v6.2
- add RenRen Blog support.
- For title and category, move repUniNumEntToChar and saxutils.escape from different blog providers into main function

## v5.6
- （当评论数据超多的时候，比如sina韩寒博客帖子评论，很多都是2,3万个的）添加日志信息，显示当前已处理多少个评论。