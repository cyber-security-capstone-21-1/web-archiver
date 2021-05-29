import re
import os
import glob
import json
import uuid
import chardet
import argparse
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from urllib.request import urlretrieve, urlopen

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
    with urlopen(url) as response:
        info = response.info()
        return info.get_content_type()


def downloadAsset(uri, dirname):
    tUrl = uri
    o = urlparse(tUrl)
    contentType = ""
    targetDir = os.path.join(CURRENT_DIRECTORY, dirname, '/'.join(o.path.split('/')[1:-1]))

    # javascript, fragment의 경우 다운로드 불필요
    if o.scheme == "javascript" or (o.netloc == '' and o.path == ''):
        return

    if o.scheme == "":
        tUrl = f"https://{uri}"

    try:
        contentType = getContentType(tUrl)
    except Exception:
        try:
            tUrl = f"http://{uri}"
            contentType = getContentType(tUrl)
        except Exception:
            raise Exception("Error during connection")
    else:
        # text/html 무시
        if contentType in mimeTypes[1:]:
            if not os.path.exists(targetDir):
                path = Path(targetDir)
                path.mkdir(parents=True)

            targetFile = os.path.join(targetDir, o.path.split('/')[-1])
            if not os.path.exists(targetFile):
                urlretrieve(uri, targetFile)
                # print(f"[Retrieved] {targetFile}")
        else:
            pass

def archivePage(url, dirname):
    o = urlparse(url)
    try:
        doc = requests.get(url)
    except Exception as e:
        print(type(e).__name__)
    else:
        soup = BeautifulSoup(doc.text, 'lxml')

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
                        downloadAsset(url, ot.path)
                        replaceTo = f"{ot.path}"
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
                                downloadAsset(f"https://{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')}", dirname)
                            except Exception:
                                try:
                                    downloadAsset(f"http://{o.netloc}{o.path.split('/')[:-count]}{ot.path.replace('../', '')}", dirname)
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

        print('\n[Notice] 링크 처리 시작')
        # href, src 속성 처리
        for idx, parseType in enumerate([hrefs, srcs]):
            for data in parseType:
                if idx == 0:
                    tLink = data["href"]
                elif idx == 1:
                    tLink = data["src"]

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
                if idx == 0:
                    data["href"] = f".{ot.path}"
                elif idx == 1:
                    data["src"] = f".{ot.path}"

        # script 콘텐츠 처리
        importRegex = r"@import\s*(url)?\s*\(?([^;]+?)\)?;"
        for script in scripts:
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
        with open(os.path.join(CURRENT_DIRECTORY, dirname, 'index.html'), 'w') as f:
            f.write(str(soup))
    

def parseCSSURLs(url, uid):
    print("[Notice] CSS 내 링크 처리 시작")
    o = urlparse(url)
    files = glob.glob(f"{os.path.join(CURRENT_DIRECTORY, uid)}/**/**")
    styleRegex = 'url\((.*?)\)'
    importRegex = r"@import\s*(url)?\s*\(?([^;]+?)\)?;"

    for file in files:
        basePath = '/'.join(file.split(uid)[-1].split('/')[:-1])
        baseURL = f"{o.scheme}://{o.netloc}{basePath}" 
        filename, extension = os.path.splitext(file)
        if extension == '.css':
            print(f" - {filename.split('/')[-1]}.css 처리 중")

            content_r = open(file, 'rb')
            encoding = chardet.detect(content_r.read())['encoding']
            content_r.close()
            content_r = open(file, 'rt', encoding=encoding)

            removed_comments = re.sub(r'\/\*.*?\*\/', '', content_r.read())

            for regex in [importRegex, styleRegex]:
                for item in re.findall(regex, removed_comments):
                    item = item.strip("'").strip('"')
                    ot = urlparse(item)

                    # javascript, fragment 처리 불필요
                    if ot.scheme == "javascript" or (ot.netloc == '' and ot.path == ''):
                        continue

                    if len(ot.netloc) > 0:
                        # 절대 경로
                        targetFile = url
                        replaceTo = f"{'..' * (len(basePath.split('/')[1:]) + 1)}/{ot.path}"
                    else:
                        # 상대 경로
                        targetFile = ''
                        if ot.path.startswith("./"):
                            targetFile = urljoin(baseURL, ot.path)
                            replaceTo = f"url('{ot.path}')"
                        elif ot.path.startswith("../"):
                            targetFile = urljoin(baseURL, ot.path)
                            replaceTo = f"url('{ot.path}')"
                        elif ot.path.startswith("/"):
                            targetFile = urljoin(baseURL, ot.path)
                            replaceTo = f"url('{'../' * (len(basePath.split('/')[1:]))}{ot.path[1:]}')"
                        elif ot.path[0].isalpha():
                            if 'base64' in ot.path:
                                continue
                            else:
                                targetFile = urljoin(baseURL, '/', ot.path)
                                replaceTo = f"url('{'../' * (len(basePath.split('/')[1:]))}{ot.path[1:]}')"
                        
                        try:
                            downloadAsset(targetFile, uid)
                        except Exception:
                            print(f"[Error] {targetFile} 다운로드 에러")
                    
                    replacement = re.sub(regex, replaceTo, removed_comments)

                    content_w = open(file, 'w', encoding=encoding)
                    content_w.write(replacement)
                    content_w.close()
            
            content_r.close()


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
    args.url = "http://www.ppomppu.co.kr/zboard/view.php?id=issue&page=1&divpage=67&no=359100" # Test URL
    archivePage(args.url, uid)
    parseCSSURLs(args.url, uid)

    print(f"[Complete] Archived into directory - {uid}")
    # Save Meta JSON
    with open(os.path.join(CURRENT_DIRECTORY, uid, "meta.json"), "w") as f:
        json.dump({
            "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }, f)
