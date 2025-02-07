import requests
import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

url = "https://www.xiaohongshu.com/explore"  # Rednote Website
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    print("Success!") #Content stored in response.text
else:
    print(f"Failed with status：{response.status_code}")


soup = BeautifulSoup(response.text, "lxml")  #Use lxml to analyze HTML

# 示例：提取所有的标题 <h1> 标签
titles = soup.find_all("h1")
for title in titles:
    print(title.text)

'''
# Get All links
links = soup.find_all("a")
for link in links:
    print(link.get("href"))
'''

