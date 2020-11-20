#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
import pytz
import feedparser
from urllib.request import urlopen
from urllib import error
import requests
import sys
import os
from bs4 import BeautifulSoup
import telegram
import re
import sqlite3
import initDB


def readInFeed():
    print("read in feed")
    NewsFeed = feedparser.parse("https://luhze.de/rss")
    entry = NewsFeed.entries[0]

    #check if date is in last 5 mins
    published = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')

    diff = datetime.utcnow().replace(tzinfo=pytz.utc) - published

    if 1!=1:#diff.seconds > 300 or diff.days > 0:
        print("article is older than 5 minutes, exiting")
        print(sys.exc_info())
        sys.exit(1)
    else:
        resultArray = {'link': entry.link, 'published': published, 'content': entry.content}
        return resultArray


def readInSite(url):
    print("reading in page " + url)
    try:
        text = urlopen(url).read()
    except error.URLError as e:
        print(f"Error reading in " + url + ": {e}")
        print(sys.exc_info())
        sys.exit(1)

    return BeautifulSoup(text, 'html.parser')


def readInTeaser(text):
    print("read in teaser")
    teaserText = text.find("p", {'class': 'descriptionStyle'})
    if teaserText is None:
        print("no teaser text found, exiting")
        print(sys.exc_info())
        sys.exit(1)
    else:
        return teaserText.text


def getPictureCreditsFromContent(text):
    print("get credits from picture")
    match = re.search("<p>Titelfoto:.{1,200}<\/p>", text)
    if match is None:
        print("no credit found")
        return None
    else:
        pictureText = text.split("Titelfoto: ")
        credits = pictureText[1].split("</p>")
        return credits[0]


def getPictureLink(text):
    print("fetch picture link")
    pic = text.find("div", {'class': 'bunnerStyle'})
    if pic is None:
        print("no picture found, exiting")
        print(sys.exc_info())
        sys.exit(1)

    style = pic["style"]
    if len(style) < 0:
        print("could not find picture style information, exiting")
        print(sys.exc_info())
        sys.exit(1)

    url = style.split("('")[1].split("')")[0]

    #remove resolution to get original picture
    return re.sub("-\d{2,5}x\d{2,5}\.jpg$", ".jpg", url)


def downloadPicture(link):
    print("download picture")
    try:
        response = requests.get(link)
        img = sqlite3.Binary(response.content)
        return img
    except requests.exceptions.RequestException as e:
        print(f"error while downloading image: {e}")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)


def craftIntentText(link, teaser, imageCredits):
    print("craft twitter intent text")
    # craft twitter text
    if imageCredits is None:
        twitterText = "https://twitter.com/intent/tweet?text=" + requests.utils.quote(teaser + "\n\n" + u"\u27A1" + " "
                                                                                      + link)
    else:
        twitterText = "https://twitter.com/intent/tweet?text=" + requests.utils.quote(
            teaser + "\n\n" + u"\u27A1" + " " + link + "\n\n" + u"\U0001F4F8" + " " + credits)

    return twitterText


def saveTweetToDb(cur, con, img, imageUrl, imageCredits, link, teaser):
    print("save tweet to db")
    sqlArray = [['INSERT OR IGNORE INTO tweets VALUES (?,?,?,?)', (link, teaser, imageCredits, img)]]
    return insertSQLStatements(cur, con, sqlArray)


def readImageFromDB(cur, link):
    print("read image from db")
    try:
        cur.execute('SELECT image FROM tweets WHERE url=?', (link,))
        return cur.fetchone()[0]
    except sqlite3.OperationalError as e:
        print(f"error while fetching image from db: {e}")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)


def readInNewChatId(cur, con, bot):
    print("read in new chat ids")
    chatIds = bot.get_updates()
    sqlArray = []
    if chatIds is None or len(chatIds) == 0:
        print("no new chat id")
    else:
        for id in chatIds:
            if id.message is None:
                print("no new chat id")
            else:
                print("insert new chat id: " + str(id.message.chat_id))
                sqlArray.append(['INSERT OR IGNORE INTO chatIds VALUES (?)', (int(id.message.chat_id), )])
        insertSQLStatements(cur, con, sqlArray)


def insertSQLStatements(cur, con, sqlArray):
    try:
        for statement in sqlArray:
            print(statement[0])
            print(statement[1])
            cur.execute(statement[0], statement[1])
        con.commit()
        return 0
    except sqlite3.OperationalError as e:
        print(f"error while working with db: {e}")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)


def sendTelegramMessage(bot, link, teaser, imageUrl, credits, chatIds):
    print("send telegram message")

    for id in chatIds:
        bot.send_message(chat_id=id[0], text="--- NEW ARTICLE ---")
        bot.send_photo(chat_id=id[0], photo=imageUrl)
        if credits is None:
            bot.send_message(chat_id=id[0], text="link: \n" + link + "\n\n" + teaser + "\n\ncredits: photo made by author")
        else:
            bot.send_message(chat_id=id[0], text="link: \n" + link + "\n\n" + teaser + "\n\ncredits: " + credits)

    return 0


def initTelegramBot():
    print("initialize telegram bot")
    return telegram.Bot(token=os.environ['TELEGRAM_TOKEN'])


def getChatIdsFromDB(cur):
    print("fetch chat ids from db")
    try:
        cur.execute('SELECT chatId FROM chatIds')
        return cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"error while fetching chat ids: {e}")
        print(sys.exc_info())
        sys.exit(1)


def checkIfDBIsThere(cur):
    print("checking if db has been initialized yet")
    try:
        cur.execute('SELECT chatId FROM chatIds limit 1')
    except sqlite3.OperationalError as e:
        print(f"db has not been initialized yet: {e}")
        initDB.createTables(cur)
    else:
        print("db has been initialized")



def main():
    print("---")
    print("starting bot")
    print("utc time now: " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    bot = initTelegramBot()
    con = initDB.connectToDb()
    cur = initDB.getCursor(con)
    checkIfDBIsThere(cur)
    readInNewChatId(cur, con, bot)
    feedArray = readInFeed()
    if feedArray is not None:
        link = feedArray['link']
        text = readInSite(link)
        teaser = readInTeaser(text)
        imageUrl = getPictureLink(text)
        img = downloadPicture(imageUrl)
        content = feedArray['content'][0]['value']
        pictureCredits = getPictureCreditsFromContent(content)
        saveTweetToDb(cur, con, img, imageUrl, pictureCredits, link, teaser)
        chatIds = getChatIdsFromDB(cur)
        sendTelegramMessage(bot, link, teaser, imageUrl, pictureCredits, chatIds)
    else:
        print("error while fetching and reading rss")
        print(sys.exc_info())
        sys.exit(1)


if __name__ == "__main__":
    main()
