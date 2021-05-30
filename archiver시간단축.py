import re
import glob
import chardet
import json
import uuid
import requests
import argparse
import os
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from urllib.request import urlretrieve, urlopen, Request, URLopener
import time
CURRENT_DIRECTORY = os.path.dirname(__file__)
get = 0
ret = 0
ret_time = 0

mimeTypes = [
    'text/html',
    'application/xml',
    'application/xhtml+xml',
    'application/pdf',
    'text/css',
    'text/javascript',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'image/webp',
    'audio/midi',
    'audio/mpeg',
    'audio/webm',
    'audio/ogg',
    'audio/wav',
    'video/webm',
    'video/ogg',
    'font/opentype',
    'font/ttf',
    'application/octet-stream',
    'application/font-woff',
    'application/font-sfnt',
    'application/vnd.ms-fontobject',
    'image/svg+xml',
]

def getContent(url) :
    if '.js' in url and '.jsp' not in url:
        return 'text/javascript'
    elif '.png' in url:
        return 'image/png'
    elif '.jpg' in url:
        return 'image/jpeg'
    elif '.css' in url:
        return 'text/css'
    elif '.gif' in url :
        return "image/gif"
    elif '.xml' in url :
        return "text/xml"
    elif '.ico' in url :
        return 'image/x-icon'
    lastText = url.split('/')[-1]
    # 루리웹의 경우 /234135 인 이미지 파일 존재
    if not 'ruliweb' in url :
        if '.' not in lastText or '.com' in lastText or '.co.kr' in lastText:
            return "text/html"
    # 403 방지
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = Request(url, headers=headers)
    # print("==========시작==========")
    try:
        with urlopen(req) as response:
            info = response.info()
            # print(info.get_content_type())
            # print("==========끝==========")
            return info.get_content_type()
    except Exception as e :
        print('get 에러!!', type(e).__name__ , url)

def getContentType(uri):
    tUrl = uri
    o = urlparse(tUrl)

    global get
    get += 1

    if o.scheme == "":
        if uri.startswith("//"):
            tUrl = f"https:{uri}"
        else:
            tUrl = f"https://{uri}"
    try:
        contentType = getContent(tUrl)
        return contentType
    except Exception:
        try:
            if uri.startswith('//'):
                tUrl = f"http:{uri}"
            else:
                tUrl = f"http://{uri}"
            contentType = getContent(tUrl)
            return contentType
        except Exception:
            pass
            # raise Exception("Error during connection")


def downloadAsset(uri, dirname, contentType):
    # if contentType == 'text/javascript':
    #     return
    down = time.time()
    tUrl = uri
    o = urlparse(tUrl)
    targetDir = CURRENT_DIRECTORY + '/' + dirname + '/' + '/'.join(o.path.split('/')[1:-1])

    # javascript, fragment의 경우 다운로드 불필요
    if o.scheme == "javascript" or (o.netloc == '' and o.path == ''):
        return
    global ret_time
    global ret
    ret += 1

    if o.scheme == "":
        if uri.startswith("//"):
            tUrl = f"https:{uri}"
        else:
            tUrl = f"https://{uri}"

    if not uri.startswith('http'):
        if uri.startswith('//'):
            tUrl = f"http:{uri}"
        else:
            tUrl = f"http://{uri}"

    # text/html 무시
    if contentType in mimeTypes[1:]:
        if not os.path.exists(targetDir):
            path = Path(targetDir)
            path.mkdir(parents=True)

        targetFile = targetDir + '/' + o.path.split('/')[-1]
        if not os.path.exists(targetFile):
            try:
                urlretrieve(tUrl, targetFile)
                print(f"[Retrieved] {tUrl}", time.time() - down)
                # print(f"[Retrieved] {targetFile}", time.time() - down)
                ret_time += time.time() - down
            except Exception as e:
                try:
                    print(type(e).__name__ , tUrl)
                    opener = URLopener()
                    opener.addheader('User-Agent', 'Mozilla/5.0')
                    filename, headers = opener.retrieve(tUrl, targetFile)
                    print(f"[Retrieved2] {targetFile}", time.time() - down)
                    ret_time += time.time() - down
                except Exception as e:
                    try:
                        print(type(e).__name__,'헤더 붙여도' , tUrl)
                        tUrl = tUrl.replace('www.', '')
                        tUrl = tUrl.replace('http:', 'https:')
                        opener.retrieve(tUrl, targetFile)
                        print(f"[Retrieved3] {targetFile}", time.time() - down)
                        ret_time += time.time() - down
                    except Exception as e:
                        print(type(e).__name__, 'https:// 에 www 제외', tUrl)
                        if 'bobae' in tUrl : #보배 드림 image 만을 위한 처리 우선은 이렇게 임시방편
                            try :
                                tUrl = tUrl.replace('//', '//image.')
                                opener.retrieve(tUrl, targetFile)
                                print(f"[Retrieved4] 보배드림 image {targetFile}", time.time() - down)
                            except :
                                print(type(e).__name__, 'image 처리도 실패', tUrl)
                                pass
                        return
            finally:
                if contentType == 'text/css':
                    global args
                    parseCSSURLs(targetFile, args.url, dirname)
    else:
        pass


def archivePage(url, dirname):
    o = urlparse(url)
    doc = requests.get(url, allow_redirects=False, headers={'User-Agent': 'Mozilla/5.0'})
    if 'bobae' in url:
        doc.encoding = 'utf-8'
        soup = BeautifulSoup(doc.text, 'html.parser', from_encoding='utf-8')
    else:
        soup = BeautifulSoup(doc.text, 'html.parser')

    srcs = soup.select("[src]")
    # srcsets = soup.select("[srcset]")
    styleTags = soup.select("style")
    styleAttrs = soup.select("[style]")
    posterAttrs = soup.select("[poster]")
    hrefs = soup.select("[href]")
    scripts = soup.select("script:not([src])")

    # 스타일 속성 / 스타일 태그 처리
    print('\n[Notice] 스타일 처리 시작')
    styleRegex = 'url\((.*?)\)'
    for parseType in [styleTags, styleAttrs, posterAttrs]:
        for style in parseType:
            if 'style' in style.attrs:
                text = style["style"]
            elif 'poster' in style.attrs:
                text = style["poster"]
            else:
                text = style.string

            for url in re.finditer(styleRegex, text):
                url = url.group(0)[4:-1].strip('"').strip("'")
                ot = urlparse(url)

                # javascript, fragment 처리 불필요
                if ot.scheme == "javascript" or (ot.netloc == '' and ot.path == ''):
                    continue

                try :
                    contentType = getContentType(url)
                except :
                    continue

                if len(ot.netloc) > 0:
                    # 절대 경로
                    downloadAsset(url, dirname, contentType)
                    replaceTo = f".{ot.path}"
                else:
                    # 상대 경로
                    if ot.path.startswith("./"):
                        if o.scheme == '':
                            try:
                                contentType = getContentType(url)
                                downloadAsset(f"https://{o.netloc}{o.path}{ot.path.replace('./', '')}", dirname, contentType)
                            except Exception:
                                try:
                                    downloadAsset(f"http://{o.netloc}{o.path}{ot.path.replace('./', '')}", dirname, contentType)
                                except Exception:
                                    print(f"{o.netloc}{o.path}{ot.path.replace('./', '')} 다운로드 에러")
                        replaceTo = f"{ot.path}"
                    elif ot.path.startswith("../"):
                        count = ot.path.count("../")
                        try:
                            downloadAsset(f"https://{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')}",
                                          dirname, contentType)
                        except Exception:
                            try:
                                downloadAsset(
                                    f"http://{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')}",
                                    dirname, contentType)
                            except Exception:
                                print(f"{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')} 다운로드 에러")
                        replaceTo = f"{o.path.split('/')[:-count]}"
                    else:
                        try:
                            downloadAsset(f"https://{o.netloc}{ot.path}", dirname, contentType)
                        except Exception:
                            try:
                                downloadAsset(f"http://{o.netloc}{ot.path}", dirname, contentType)
                            except Exception:
                                print(f"{o.netloc}{ot.path} 다운로드 에러")
                        replaceTo = f".{ot.path}"

                text = text.replace(url, replaceTo)
                if 'style' in style.attrs:
                    style["style"] = text
                elif 'poster' in style.attrs:
                    style["poster"] = text
                else:
                    style.string = text

    print('\n[Notice] 링크 처리 시작')
    # href, src 속성 처리
    for idx, parseType in enumerate([hrefs, srcs]):
        for data in parseType:
            if idx == 0:
                tLink = data["href"]
            elif idx == 1:
                tLink = data["src"]
            if data.name == 'iframe' :
                continue
            if idx == 0 and len(data["href"]) == 0:
                continue
            if data.has_attr('data'):
                p = re.compile(r"(http(s)?:\/\/)([a-z0-9\w]+\.*)+[a-z0-9]{2,4}")
                m = p.match(data['data'])
                if m.group(0):
                    tLink = str(data['data'])

            ot = urlparse(tLink)
            if 'img/family' in tLink:
                print("sdf")
            # android-app, javascript 등의 프로토콜은 생략
            if ot.scheme in ["http", "https", ""]:
                if len(ot.netloc) == 0:
                    if tLink.startswith("#") or ot.fragment:
                        continue
                    elif ot.path.startswith("./"):
                        tLink = f"{o.netloc}/{ot.path.replace('./', '')}"
                        if not tLink.startswith('www'):
                            tLink = f"www.{tLink}"
                    elif ot.path.startswith("../"):
                        count = ot.path.count('../')
                        splitted = o.path.split('/')[:-count]
                        if splitted[0] == '' :
                            tLink = f"{o.netloc}/{ot.path.replace('../', '')}"
                        else :
                            tLink = f"{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')}"

                    elif ot.path.startswith("/"):
                        tLink = f"{o.netloc}{ot.path}"
                    elif len(ot.path) == 0:
                        pass
                    elif ot.path[0].isalpha():
                        tLink = f"{o.netloc}/{''.join(o.path.split('/')[:-1])}/{ot.path}"

                if ot.scheme == "":
                    if ot.query and len(ot.path) == 0:
                        tLink = f"http://{o.netloc}?{ot.query}"
                    elif tLink.startswith('//'):
                        tLink = f"http:{tLink}"
                    else:
                        tLink = f"http://{tLink}"

                try:
                    # idx 4부터 해당하는 mimeTypes만 허용
                    contentType = getContentType(tLink)
                    if contentType in mimeTypes[4:]:
                        if '.css' in ot.path and ot.__getattribute__('query') :
                            tLink = f"tLink?{ot.__getattribute__('query')}"
                            downloadAsset(tLink, dirname, contentType)
                        else:
                            downloadAsset(tLink, dirname, contentType)
                except Exception as e:
                    print(type(e).__name__)
                    pass

            ot = urlparse(tLink)

            #네이트판 src
            tmp = ot.path
            while 'https://' in tmp :
                tmp = tmp.split('https://')[-1]

            if idx == 0:
                if '.css' in ot.path and ot.__getattribute__('query') :
                    data["href"] = f".{ot.path}?{ot.query}"
                else :
                    data["href"] = f".{ot.path}"
            elif idx == 1:
                if 'youtube' in ot.netloc:
                    continue
                if ot.path != tmp :
                    data["src"] = f"./{'/'.join(tmp.split('/')[1:])}"
                else :
                    data["src"] = f".{ot.path}"

    # script 콘텐츠 처리
    print('\n[Notice] 스크립트 처리 시작')
    importRegex = r"@import\s*(url)?\s*\(?([^;]+?)\)?;"
    for script in scripts:
        if script.string == None:
            continue
        for url in re.findall(importRegex, script.string):
            tLink = url[-1]

            ot = urlparse(tLink)
            # android-app, javascript 등의 프로토콜은 생략
            if ot.scheme in ["http", "https", ""]:
                if len(ot.netloc) == 0:
                    if tLink.startswith("#") or ot.fragment:
                        continue
                    elif ot.path.startswith("./"):
                        tLink = f"{ot.path.replace('./', '')}"
                    elif ot.path.startswith("../"):
                        count = ot.path.count('../')
                        tLink = f"{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')}"
                    elif ot.path.startswith("/"):
                        tLink = f"{o.netloc}{ot.path}"
                    elif ot.path[0].isalpha():
                        tLink = f"{o.netloc}/{ot.path}"

                if ot.scheme == "":
                    tLink = f"http://{tLink}"

                try:
                    # idx 4부터 해당하는 mimeTypes만 허용
                    contentType = getContentType(tLink)
                    if contentType in mimeTypes[4:]:
                        downloadAsset(tLink, dirname, contentType)
                except Exception:
                    continue

            ot = urlparse(tLink)
            tLink = f".{ot.path}"
            script = re.sub(importRegex, tLink, script)

    # Save html File
    with open(os.path.join(CURRENT_DIRECTORY, dirname, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(str(soup))


# def parseCSSURLs(file, url, uid):
#     print("CSS URL ", file)
#     o = urlparse(url)
#     styleRegex = 'url\((.*?)\)'
#     importRegex = r"@import\s*(url)?\s*\(?([^;]+?)\)?;"
#
#     basePath = '/'.join(file.split(uid)[-1].split('/')[:-1])
#     baseURL = f"{o.scheme}://{o.netloc}{basePath}"
#     filename, extension = os.path.splitext(file)
#     if extension == '.css':
#         content_r = open(file, 'rb')
#         encoding = chardet.detect(content_r.read())['encoding']
#         content_r.close()
#         content_r = open(file, 'rt', encoding=encoding)
#
#
#         removed_comments = re.sub(r'\/\*.*?\*\/', '', content_r.read())
#
#         for regex in [importRegex, styleRegex]:
#             for item in re.findall(regex, removed_comments):
#                 try :
#                     item = item.strip("'").strip('"')
#                 except Exception as e :
#                     print(e)
#                 ot = urlparse(item)
#
#                 # javascript, fragment 처리 불필요
#                 if ot.scheme == "javascript" or (ot.netloc == '' and ot.path == ''):
#                     continue
#
#                 if len(ot.netloc) > 0:
#                     # 절대 경로
#                     targetFile = url
#                     replaceTo = f"url('{'../' * (len(basePath.split('/')[1:]))}{ot.path[1:]}')"
#                 else:
#                     # 상대 경로
#                     targetFile = ''
#                     if ot.path.startswith("./"):
#                         parsed = ot.path.split('/')
#                         parsed = '/'.join(parsed[1:])
#                         targetFile = f"{baseURL}/{parsed}"
#                         replaceTo = f"url('{ot.path}')"
#                     elif ot.path.startswith("../"):
#                         url2 = baseURL[::-1]
#                         idx = url2.index('/')
#                         targetFile = baseURL[:len(baseURL) - idx] + ot.path.replace('../', '')
#                         replaceTo = f"url('{ot.path}')"
#                     elif ot.path.startswith("/"):
#                         targetFile = urljoin(baseURL, ot.path)
#                         replaceTo = f"url('{'../' * (len(basePath.split('/')[1:]))}{ot.path[1:]}')"
#                     elif ot.path[0].isalpha():
#                         if 'base64' in ot.path:
#                             continue
#                         else:
#                             targetFile = urljoin(baseURL, '/', ot.path)
#                             replaceTo = f"url('{'../' * (len(basePath.split('/')[1:]))}{ot.path[1:]}')"
#
#                     try:
#                         contentType = getContentType(targetFile)
#                         downloadAsset(targetFile, uid, contentType)
#                     except Exception:
#                         print("down error")
#                         continue
#
#                 print('이거를 : ',item)
#                 print('이걸로 바꿔 : ',replaceTo)
#                 replacement = re.sub(item, replaceTo, removed_comments)
#
#                 content_w = open(file, 'w', encoding=encoding)
#                 content_w.write(replacement)
#                 content_w.close()
#
#             content_r.close()


def parseCSSURLs(file, url, uid):
    print("CSS URL ", file)
    o = urlparse(url)
    file = file.replace('//', '/')
    styleRegex = 'url\((.*?)\)'
    importRegex = r"@import\s*(url)?\s*\(?([^;]+?)\)?;"

    basePath = '/'.join(file.split(uid)[-1].split('/')[:-1])
    baseURL = f"{o.scheme}://{o.netloc}{basePath}"
    filename, extension = os.path.splitext(file)
    if extension == '.css':
        content_r = open(file, 'rb')
        encoding = chardet.detect(content_r.read())['encoding']
        content_r.close()
        content_r = open(file, 'rt', encoding=encoding)
        removed_comments = re.sub(r'\/\*.*?\*\/', '', content_r.read())
        content_r.close()

        for regex in [importRegex, styleRegex]:
            for item in re.findall(regex, removed_comments):
                try :
                    item = item.strip("'").strip('"')
                except Exception as e :
                    print(e)
                    continue
                ot = urlparse(item)

                # javascript, fragment 처리 불필요
                if ot.scheme == "javascript" or (ot.netloc == '' and ot.path == ''):
                    continue
                if len(ot.netloc) > 0:
                    # 절대 경로
                    # 인벤 처리
                    # if 'static' in item and not 'http' in item:
                    #     replaceTo = "https:" + item
                    # else:
                    #     replaceTo = item


                    replaceTo = f"{'../' * (len(basePath.split('/')[1:]))}{ot.path[1:]}"
                    targetFile = item
                    try:
                        contentType = getContentType(targetFile)
                        downloadAsset(targetFile, uid, contentType)
                    except Exception:
                        if 'static' in item and not 'http' in item:
                            replaceTo = "https:" + item
                        else:
                            replaceTo = item
                        pass
                else:
                    # 상대 경로
                    targetFile = ''
                    if ot.path.startswith("./"):
                        parsed = ot.path.split('/')
                        parsed = '/'.join(parsed[1:])
                        targetFile = f"{baseURL}/{parsed}"
                        replaceTo = f"{ot.path}"
                    elif ot.path.startswith("../"):
                        url2 = baseURL[::-1]
                        idx = url2.index('/')
                        targetFile = baseURL[:len(baseURL) - idx] + ot.path.replace('../', '')
                        replaceTo = f"{ot.path}"
                    elif ot.path.startswith("//"):
                        targetFile = ot.path
                        replaceTo = f""
                    elif ot.path.startswith("/"):
                        print(ot.path)
                        targetFile = urljoin(baseURL, ot.path)
                        replaceTo = f"{'../' * (len(basePath.split('/')[1:]))}{ot.path[1:]}"
                    elif ot.path[0].isalpha():
                        if 'base64' in ot.path:
                            continue
                        else:
                            targetFile = baseURL + ot.path
                            splitted = file.split(uid)[-1]
                            splitted = splitted.split('/')
                            count = len(splitted)-1
                            # replaceTo = f"{'../' * (len(basePath.split('/')[1:]))}{ot.path}"
                            if count :
                                replaceTo = f"{'../' * (count)}{ot.path}"
                            else :
                                replaceTo = f"./{ot.path}"


                    try:
                        contentType = getContentType(targetFile)
                        downloadAsset(targetFile, uid, contentType)
                    except Exception:
                        print("down error")
                        pass

                # removed_comments = re.sub(item, replaceTo, removed_comments)
                removed_comments = removed_comments.replace(item, replaceTo)

            content_w = open(file, 'w', encoding=encoding)
            content_w.write(removed_comments)
            content_w.close()

if __name__ == "__main__":
    """
    페이지를 특정 시점에 스냅샷하여 보존합니다.
    Usage:
    python3 [filename].py --url [Page URL]
    """
    parser = argparse.ArgumentParser(description="Web Archiver")
    parser.add_argument('--url', type=str, help="Site URL")

    args = parser.parse_args()

    # Archive Page
    test_arr = ["https://www.ilbe.com/view/11345118798",  # 0 이상없음
                "https://www.inven.co.kr/webzine/news/?news=256401",
                "https://www.instiz.net/name/42841474?page=1&category=1&k=%EC%9D%B8%EB%B2%A4&stype=9",  # 2
                "https://hygall.com/385745579", # 잘됨
                "https://www.fmkorea.com/best/3626647809",  # 4 ip 차단 테스트 불가능##########################
                "https://www.dogdrip.net/326822283", #왜 검은색이지
                "https://gall.dcinside.com/board/view/?id=dcbest&no=6126",  # 6 댓글제외 잘나옴###############
                "https://www.clien.net/service/board/news/16170716",  # css에서 백그라운드 색 블랙으로 돼있음####
                "https://www.bobaedream.co.kr/view?code=best&No=424524&m=1",  # 8 image. 으로 시작하는 url들 다운로드 처리  잘됨. ######
                "https://www.82cook.com/entiz/read.php?num=3225141",  # 9 다 잘되는데 깨지는 iframe이 들어옴 ###
                "https://www.ygosu.com/community/best_article/yeobgi/1825320/?type=daily&sdate=2021-05-25&frombest=Y", # 10 댓글제외 잘됨
                "http://www.todayhumor.co.kr/board/view.php?table=bestofbest&no=440469", # 11 댓글제외 잘나옴 #
                "https://bbs.ruliweb.com/community/board/300143/read/52187725",  # 12 화면 까맣게 나옴
                "http://www.ppomppu.co.kr/zboard/view.php?id=issue&page=1&divpage=67&no=359100", # 잘됨
                "https://m.pann.nate.com/talk/359435076?currMenu=search&page=1&q=%EC%9A%B0%EB%A6%AC%20%EC%95%88%EB%85%95%EC%9E%90%EB%91%90%EC%95%BC",  # 14 잘됨
                "http://mlbpark.donga.com/mp/b.php?p=1&b=kbotown&id=202105250055338693&select=&query=&user=&site=&reply=&source=&pos=&sig=h4aRSY-1k3HRKfX2h6j9Sg-A6hlq",  # 15 잘됨
                "https://www.instiz.net/pt/6978378", # 16
                "https://www.bobaedream.co.kr/view?code=freeb&No=2293907"] # 17

    args.url = test_arr[12]

    start = time.time()
    uid = str(uuid.uuid4())
    if not os.path.exists(os.path.join(CURRENT_DIRECTORY, uid)):
        os.makedirs(uid)
    else:
        uid = str(uuid.uuid4())

    archivePage(args.url, uid)

    # for i in test_arr :
    #
    #     # Create Unique Archive ID
    #     uid = str(uuid.uuid4())
    #     if not os.path.exists(os.path.join(CURRENT_DIRECTORY, uid)):
    #         os.makedirs(uid)
    #     else:
    #         uid = str(uuid.uuid4())
    #
    #     args.url = i
    #     archivePage(args.url, uid)

    j = open('memo.txt', 'a', encoding='UTF-8')
    j.write(f'\n{args.url}')
    j.write(f'\ntotal : {time.time() - start} seconds / download : {ret_time} seconds')
    j.write(f'\nget content: {get} / retrive: {ret}')
    j.write('\n------------------')
    j.close()
    print('걸린시간 : ', time.time() - start, '다운로드 걸린 시간 : ', ret_time)
    print('get content :' , get, 'retrive : ', ret)

    print(f"[Complete] Archived into directory - {uid}")
    # Save Meta JSON
    with open(os.path.join(CURRENT_DIRECTORY, uid, "meta.json"), "w") as f:
        json.dump({
            "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }, f)
