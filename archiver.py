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
from urllib.request import urlretrieve

from selenium import webdriver
from time import sleep
from selenium.webdriver.chrome.options import Options

CURRENT_DIRECTORY = os.path.dirname(__file__)

def screenshot(url) :
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--start-maximized')

    # chrome driver 위치
    driver = webdriver.Chrome(r"C:\Users\USER\PycharmProjects\chromedriver.exe", options=chrome_options)
    driver.get(url)
    sleep(1)

    total_height = driver.execute_script("return document.scrollingElement.scrollHeight;")
    driver.set_window_size(1920, total_height)
    sleep(1)
    driver.save_screenshot("Full_screenshot.png")
    driver.quit()


def downloadAsset(uri, dirname):
    print(uri)
    if uri[-1] == '/':
        del uri[-1]

    o = urlparse(uri)

    targetDir = os.path.join(CURRENT_DIRECTORY, dirname, '/'.join(o.path.split('/')[1:-1]))
    if not os.path.exists(targetDir):
        path = Path(targetDir)
        path.mkdir(parents=True)

    urlretrieve(uri, os.path.join(targetDir, o.path.split('/')[-1]))

    # Save assets into S3
    # encoded_string = "something".encode("utf-8")
    # bucket_name = ""
    # file_name = ""
    # s3_path = f"/{file_name}"
    # s3 = boto3.resource("s3")
    # s3.Bucket(bucket_name).put_object(Key=s3_path, Body=encoded_string)

def archivePage(url, dirname):
    o = urlparse(url)
    doc = requests.get(url)
    soup = BeautifulSoup(doc.text, 'lxml')

    srcs = soup.select("[src]")
    styles = soup.select("[style]")
    hrefs = soup.select("[href]")

    # style 속성 처리 
    for style in styles:
        temp = ""
        urls = re.findall('url\((.*?)\)', style["style"])
        if len(urls) > 0: 
            url = urls[0]
            if url[1] == '/':
                if len(url) > 1 and url[2] == '/':
                    pass
                else:
                    url = url.replace('\'', '')
                    downloadAsset(f"{o.scheme}://{o.netloc}{url}", dirname)
                    temp = f"url('.{url}')"
                style["style"] = re.sub('url\((.*?)\)', temp, style["style"])
        else:
            pass

    # href 속성 처리
    for href in hrefs:
        temp = ""
        if href["href"][0] == "/":
            if len(href["href"]) > 1 and href["href"][1] == "/":
                pass
            else:
                temp = f"{o.scheme}://{o.netloc}{href['href']}"
        else:
            temp = href["href"]
        href["href"] = temp

    # src 속성 처리
    for src in srcs:
        temp = ""
        if src["src"][0] == "/":
            if len(src["src"]) > 1 and src["src"][1] == "/":
                pass
            else:
                downloadAsset(f"{o.scheme}://{o.netloc}{src['src']}", dirname)
                temp = f".{src['src']}"
        else:
            temp = src["src"]
        src["src"] = temp

    # Save html File
    with open(os.path.join(CURRENT_DIRECTORY, dirname, 'index.html'), 'w') as f:
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
    archivePage(args.url, uid)


    # Save Meta JSON
    with open(os.path.join(CURRENT_DIRECTORY, uid, "meta.json"), "w") as f:
        json.dump({
            "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }, f)
