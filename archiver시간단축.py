import re
import json
import uuid
import requests
import argparse
import os
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
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
    elif '.php' in url :
        return "text/html"
    elif '.xml' in url :
        return "text/xml"
    elif '.ico' in url :
        return 'image/x-icon'
    lastText = url.split('/')[-1]
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
    if contentType == 'text/javascript':
        return
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
                        filename, headers = opener.retrieve(tUrl, targetFile)
                        print(f"[Retrieved3] {targetFile}", time.time() - down)
                        ret_time += time.time() - down
                    except Exception as e:
                        print(type(e).__name__ ,'https:// 에 www 제외', tUrl)
                        pass

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
                    replaceTo = f"url('.{ot.path}')"
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
                        replaceTo = f"url('{ot.path}')"
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
                        replaceTo = f"url('{o.path.split('/')[:-count]}')"
                    else:
                        try:
                            downloadAsset(f"https://{o.netloc}{ot.path}", dirname, contentType)
                        except Exception:
                            try:
                                downloadAsset(f"http://{o.netloc}{ot.path}", dirname, contentType)
                            except Exception:
                                print(f"{o.netloc}{ot.path} 다운로드 에러")
                        replaceTo = f"url('.{ot.path}')"

                text = re.sub(styleRegex, replaceTo, text)
                if 'style' in style.attrs:
                    style["style"] = text
                elif 'poster' in style.attrs:
                    style["poster"] = text
                # else:
                #     style.string = text

    print('\n[Notice] 링크 처리 시작')
    # href, src 속성 처리
    for idx, parseType in enumerate([hrefs, srcs]):
        for data in parseType:

            if idx == 0:
                tLink = data["href"]
            elif idx == 1:
                tLink = data["src"]

            if idx == 0 and len(data["href"]) == 0:
                continue
            if data.has_attr('data'):
                p = re.compile(r"(http(s)?:\/\/)([a-z0-9\w]+\.*)+[a-z0-9]{2,4}")
                m = p.match(data['data'])
                if m.group(0):
                    tLink = str(data['data'])

            ot = urlparse(tLink)
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
                        downloadAsset(tLink, dirname, contentType)
                except Exception:
                    continue

            ot = urlparse(tLink)
            if idx == 0:
                data["href"] = f".{ot.path}"
            elif idx == 1:
                if 'youtube' in ot.netloc:
                    continue
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


if __name__ == "__main__":
    """
    페이지를 특정 시점에 스냅샷하여 보존합니다.
    Usage:
    python3 [filename].py --url [Page URL]
    """
    parser = argparse.ArgumentParser(description="Web Archiver")
    parser.add_argument('--url', type=str, help="Site URL")

    args = parser.parse_args()

    # Create Unique Archive ID
    uid = str(uuid.uuid4())
    if not os.path.exists(os.path.join(CURRENT_DIRECTORY, uid)):
        os.makedirs(uid)
    else:
        uid = str(uuid.uuid4())

    # Archive Page
    # args.url = "http://www.ppomppu.co.kr/zboard/view.php?id=issue&page=1&divpage=67&no=359100" # Test URL
    # args.url = "https://www.bobaedream.co.kr/view?code=freeb&No=2293907"
    test_arr = ["https://www.ilbe.com/view/11345118798",  # 0 이상없음
                "https://www.inven.co.kr/webzine/news/?news=256401",
                "https://www.instiz.net/name/42841474?page=1&category=1&k=%EC%9D%B8%EB%B2%A4&stype=9",  # 2
                "https://hygall.com/385745579",
                "https://www.fmkorea.com/best/3626647809",  # 4
                "https://www.dogdrip.net/326822283",
                "https://gall.dcinside.com/board/view/?id=dcbest&no=6126",  # 6
                "https://www.clien.net/service/board/news/16170716",
                "https://www.bobaedream.co.kr/view?code=best&No=424524&m=1",  # 8
                "https://www.82cook.com/entiz/read.php?num=3225141",  # css 다운받긴 하는데 적용이 안됨
                "https://www.ygosu.com/community/best_article/yeobgi/1825320/?type=daily&sdate=2021-05-25&frombest=Y", # 10
                "http://www.todayhumor.co.kr/board/view.php?table=bestofbest&no=440469",
                "https://bbs.ruliweb.com/community/board/300143/read/52187725",  # 12
                "http://www.ppomppu.co.kr/zboard/view.php?id=problem&page=1&divpage=21&no=151609",
                "https://m.pann.nate.com/talk/359435076?currMenu=search&page=1&q=%EC%9A%B0%EB%A6%AC%20%EC%95%88%EB%85%95%EC%9E%90%EB%91%90%EC%95%BC",  # 14
                "https://cafe.naver.com/geobuk2/1022437",  # 안됨
                "http://mlbpark.donga.com/mp/b.php?p=1&b=kbotown&id=202105250055338693&select=&query=&user=&site=&reply=&source=&pos=&sig=h4aRSY-1k3HRKfX2h6j9Sg-A6hlq"]  # 16

    args.url = test_arr[1]

    start = time.time()
    archivePage(args.url, uid)

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
