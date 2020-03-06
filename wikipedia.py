import sys
import re
import time
import sqlite3
from collections import deque


class Element:
    def __init__(self, str, parent):
        self.str = str
        self.parent = parent

    def getPath(self):
        if self.parent == 0:
            return [self.str]
        temp = self.parent.getPath()
        temp.append(self.str)
        return temp

def followPath(cursor, link):
    cursor.execute("SELECT _to FROM connections WHERE _from = ?;", (link,));
    res = cursor.fetchone()[0]
    response = [link]
    if res != "None":
        response.extend(followPath(cursor, res))
    return response

def savePath(cursor, elem):
    path = elem.getPath()
    for x in range(len(path)-1):
        # Search if entry already exists
        cursor.execute("SELECT * FROM connections WHERE _from = ?;", (path[x][30:],))
        if len(sys.argv) <= 2:
            if len(cursor.fetchall())==0:
                # Add to Database
                cursor.execute("INSERT INTO connections VALUES (?,?);", (path[x][30:],path[x+1][30:]));

# Search via selenium
def seleniumsearch(start, target):
    from selenium import webdriver
    queue = deque('')
    queue.append(Element(("https://en.wikipedia.org/wiki/" + str(sys.argv[1])), 0))
    r1 = re.compile("^https://en.wikipedia.org/wiki/")
    r2 = re.compile("^https://en.wikipedia.org/wiki/.*#")

    driver = webdriver.Firefox()
    driver.get("https://en.wikipedia.org/wiki/" + str(sys.argv[1]))

    current = queue.popleft()
    while current.str != target:
        print("Navigating to "+current.str)
        driver.get(current.str)

        t = time.time()

        queue.extend(list(
        filter(lambda x: x.str is not None and r1.match(x.str) and not r2.match(x.str),
        map(lambda z:Element(z.get_attribute("href"),current),
        #driver.find_elements_by_partial_link_text("a")
        driver.find_elements_by_tag_name("a")
        ))))

        print("Time: "+str(time.time() - t))

        current = queue.popleft()

    print(current.getPath())
    driver.close()

# Search via bs4 and requests
def bs4search(start, target):
    from bs4 import BeautifulSoup
    from requests import get
    print("\033[92mStarting search for "+target+"\033[0m")

    # Setup
    # Database
    connection = sqlite3.connect("nodes.db")
    cursor = connection.cursor()

    t = time.time()
    queue = deque('')
    queue.append(Element(start, 0))
    scraped_count = 0
    depth = 0
    layer_count = 0
    next_layer_count = 0
    t1 = time.time()
    current = queue.popleft()
    regwiki = re.compile("^/wiki/")
    regfile = re.compile("^/wiki/((Main_Page)|(Template:)|(Category:)|(Portal:)|(Help:)|(Content:)|(File:)|(Wikipedia:)|(Special:))")
    while current.str != target:
        # Get page
        response = get(current.str)
        html_soup = BeautifulSoup(response.text, 'html.parser')
        current.str = response.url

        if layer_count <= 0 or (scraped_count % 20 == 0):
            if layer_count <= 0:
                depth += 1
                layer_count, next_layer_count = next_layer_count, 0
            print("\u001b[36mScraped "+str(scraped_count)+", "+str(len(queue))+" in queue at depth "+str(depth)+", with global velocity "+str(scraped_count/(time.time() - t))+" and local velocity "+str(20/(time.time() - t1))+".\033[0m")
            t1 = time.time()

        print("...Navigating to "+current.str[30:])

        # Search in previous paths
        if len(sys.argv) <= 2:
            cursor.execute("SELECT * FROM connections WHERE _from = ?;", (current.str[30:],))
            res = cursor.fetchall()
            if (len(res) > 0) and current.str[30:] != "Special:Random":
                fina = list(map(lambda z:z[30:],current.getPath()))
                fina.pop()
                fina.extend(followPath(cursor, current.str[30:]))
                print("\033[92mFound Path.")
                print(*fina, sep=' -> ')

                savePath(cursor, current)
                connection.commit()
                print("\033[0m")
                return

        #Find all links on page
        temp = list(map(lambda y:Element("https://en.wikipedia.org" + y.get('href'), current),
                filter(lambda x:not regfile.match(x.get('href')),
                html_soup.findAll('a', attrs={'href':regwiki}))))
        queue.extend(temp)

        scraped_count += 1
        layer_count -= 1
        next_layer_count += len(temp)
        current = queue.popleft()

    print("\033[92m"+"Found Path.")
    savePath(cursor, current)
    connection.commit()
    print(*list(map(lambda z:z[30:],current.getPath())), sep=' -> ')
    print("\033[0m")

def randomScrape(start, target, n):
    x = 1
    while n > 0:
        print("\u001b[33mBeginning Scrape " + str(x) +".\033[0m")
        bs4search(start, target)
        x += 1
        n -= 0 if n < 0 else 1

start = "https://en.wikipedia.org/wiki/" + str(sys.argv[1])
target = "https://en.wikipedia.org/wiki/" + (str(sys.argv[2]) if len(sys.argv) > 2 else "Psychology")

if len(sys.argv) > 1:
    bs4search(start,target)
else:
    randomScrape(10)
