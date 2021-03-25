import re
import os
import uuid
import argparse
import requests
import webbrowser
from urllib.parse import urlparse
from bs4 import BeautifulSoup

chrome_path = 'open -a /Applications/Google\ Chrome.app %s'

def archivePage(url, dirname):
    o = urlparse(url)
    doc = requests.get(url)
    soup = BeautifulSoup(doc.text, 'lxml')

    # Download all assets
    srcs = soup.select("[src]")

    # Replace all relative paths
    styles = soup.select("[style]")
    hrefs = soup.select("[href]")
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
                    temp = f"url('{o.scheme}://{o.netloc}{url}')"
                style["style"] = re.sub('url\((.*?)\)', temp, style["style"])
        else:
            pass

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

    for src in srcs:
        temp = ""
        if src["src"][0] == "/":
            if len(src["src"]) > 1 and src["src"][1] == "/":
                pass
            else:
                temp = f"{o.scheme}://{o.netloc}{src['src']}"
        else:
            temp = src["src"]
        src["src"] = temp

    # Save html File
    with open(os.path.join(os.path.dirname(__file__), dirname, 'index.html'), 'w') as f:
        f.write(str(soup))
    
    webbrowser.get(chrome_path).open(os.path.join(os.path.dirname(__file__), dirname, 'index.html'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Archiver")
    parser.add_argument('--url', type=str, help="Site URL")

    args = parser.parse_args()

    uid = str(uuid.uuid4())
    if not os.path.exists(os.path.join(os.path.dirname(__file__), uid)):
        os.makedirs(uid)
    else:
        uid = str(uuid.uuid4())
    
    archivePage(args.url, uid)

    print(f"{uid}에 저장되었습니다.")
