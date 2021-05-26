import re
import os
import json
import uuid
import argparse
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.request import urlretrieve, urlopen, Request, URLopener

CURRENT_DIRECTORY = os.path.dirname(__file__)

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


def getContentType(url):
    # 403 방지
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = Request(url, headers=headers)
    with urlopen(req) as response:
        info = response.info()
        return info.get_content_type()


def downloadAsset(uri, dirname):
    tUrl = uri
    o = urlparse(tUrl)
    contentType = ""
    # targetDir = os.path.join(CURRENT_DIRECTORY, dirname, '/'.join(o.path.split('/')[1:-1]))
    targetDir = CURRENT_DIRECTORY + '/' + dirname + '/' + '/'.join(o.path.split('/')[1:-1])

    # javascript, fragment의 경우 다운로드 불필요
    if o.scheme == "javascript" or (o.netloc == '' and o.path == ''):
        return

    if o.scheme == "":
        if uri.startswith("//"):
            tUrl = f"https:{uri}"
        else:
            tUrl = f"https://{uri}"

    try:
        contentType = getContentType(tUrl)
    except Exception:
        try:
            if uri.startswith('//'):
                tUrl = f"http:{uri}"
            else:
                tUrl = f"http://{uri}"
            contentType = getContentType(tUrl)
        except Exception:
            pass
            # raise Exception("Error during connection")
    else:
        # text/html 무시
        if contentType in mimeTypes[1:]:
            if not os.path.exists(targetDir):
                path = Path(targetDir)
                path.mkdir(parents=True)

            targetFile = targetDir + '/' + o.path.split('/')[-1]
            if not os.path.exists(targetFile):
                try:
                    urlretrieve(tUrl, targetFile)
                    print(f"[Retrieved] {targetFile}")
                except Exception:
                    try:
                        opener = URLopener()
                        opener.addheader('User-Agent', 'Mozilla/5.0')
                        filename, headers = opener.retrieve(tUrl, targetFile)
                    except Exception:
                        try:
                            tUrl = tUrl.replace('www.', '')
                            tUrl = tUrl.replace('http:', 'https:')
                            filename, headers = opener.retrieve(tUrl, targetFile)
                        except Exception as e:
                            print(str(e))
                            raise Exception

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

                if len(ot.netloc) > 0:
                    # 절대 경로
                    downloadAsset(url, dirname)
                    replaceTo = f"url('.{ot.path}')"
                else:
                    # 상대 경로
                    if ot.path.startswith("./"):
                        if o.scheme == '':
                            try:
                                downloadAsset(f"https://{o.netloc}{o.path}{ot.path.replace('./', '')}", dirname)
                            except Exception:
                                try:
                                    downloadAsset(f"http://{o.netloc}{o.path}{ot.path.replace('./', '')}", dirname)
                                except Exception:
                                    print(f"{o.netloc}{o.path}{ot.path.replace('./', '')} 다운로드 에러")
                        replaceTo = f"url('{ot.path}')"
                    elif ot.path.startswith("../"):
                        count = ot.path.count("../")
                        try:
                            downloadAsset(f"https://{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')}",
                                          dirname)
                        except Exception:
                            try:
                                downloadAsset(
                                    f"http://{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')}",
                                    dirname)
                            except Exception:
                                print(f"{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')} 다운로드 에러")
                        replaceTo = f"url('{o.path.split('/')[:-count]}')"
                    else:
                        try:
                            downloadAsset(f"https://{o.netloc}{ot.path}", dirname)
                        except Exception:
                            try:
                                downloadAsset(f"http://{o.netloc}{ot.path}", dirname)
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
                    if getContentType(tLink) in mimeTypes[4:]:
                        downloadAsset(tLink, dirname)
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
                    if getContentType(tLink) in mimeTypes[4:]:
                        downloadAsset(tLink, dirname)
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
    test_arr = ["https://www.ilbe.com/view/11344603787",  # 0
                "https://www.inven.co.kr/webzine/news/?news=256401",
                "https://www.instiz.net/pt/6978378?happystart=1",  # 2
                "https://hygall.com/385745579",
                "https://www.fmkorea.com/best/3626647809",  # 4
                "https://www.dogdrip.net/326822283",
                "https://gall.dcinside.com/board/view/?id=dcbest&no=6126",  # 6
                "https://www.clien.net/service/board/news/16170716",
                "https://www.bobaedream.co.kr/view?code=best&No=424524&m=1",  # 8
                "https://www.82cook.com/entiz/read.php?num=3225141",  # css 다운받긴 하는데 적용이 안됨
                "https://www.ygosu.com/community/best_article/yeobgi/1825320/?type=daily&sdate=2021-05-25&frombest=Y",
                # 10
                "http://www.todayhumor.co.kr/board/view.php?table=bestofbest&no=440469",
                "https://bbs.ruliweb.com/community/board/300143/read/52187725",  # 12
                "http://www.ppomppu.co.kr/zboard/view.php?id=problem&page=1&divpage=21&no=151609",
                "https://m.pann.nate.com/talk/359978994?currMenu=today",  # 14
                "https://cafe.naver.com/geobuk2/1022437",  # 안됨
                "http://mlbpark.donga.com/mp/b.php?p=1&b=kbotown&id=202105250055338693&select=&query=&user=&site=&reply=&source=&pos=&sig=h4aRSY-1k3HRKfX2h6j9Sg-A6hlq"]  # 16

    args.url = test_arr[16]

    archivePage(args.url, uid)

    print(f"[Complete] Archived into directory - {uid}")
    # Save Meta JSON
    with open(os.path.join(CURRENT_DIRECTORY, uid, "meta.json"), "w") as f:
        json.dump({
            "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }, f)
