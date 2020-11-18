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

    if diff.seconds > 300 or diff.days > 0:
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
    teaserText = text.find("p", {'class': 'descriptionStyle'})
    if teaserText is None:
        print("no teaser text found, exiting")
        print(sys.exc_info())
        sys.exit(1)
    else:
        return teaserText.text


def getPictureCreditsFromContent(text):
    match = re.search("<p>Titelfoto:.{1,200}<\/p>", text)
    if match is None:
        print("no credit found")
        return None
    else:
        pictureText = text.split("Titelfoto: ")
        credits = pictureText[1].split("</p>")
        return credits[0]


def getPicture(text):
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


def readInNewChatId(cur, con, bot):
    chatIds = bot.get_updates()
    if chatIds is None:
        print("no new chat id")
    else:
        for id in chatIds:
            if id.message is None:
                print("no new chat id")
            else:
                print("insert new chat id: " + str(id.message.chat_id))
                cur.execute('INSERT OR IGNORE INTO chatIds VALUES (?)', (int(id.message.chat_id), ))

    con.commit()


def sendTelegramMessage(bot, link, teaser, imageUrl, credits):
    print("send telegram message")

    #craft twitter text
    if credits is None:
        twitterText = "https://twitter.com/intent/tweet?text=" + requests.utils.quote(teaser + "\n\n" + u"\u27A1" + " "
                                                                                      + link)
    else:
        twitterText = "https://twitter.com/intent/tweet?text=" + requests.utils.quote(
            teaser + "\n\n" + u"\u27A1" + " " + link + "\n\n" + u"\U0001F4F8" + " " + credits)



    # send message to channel
    bot.send_message(chat_id=os.environ['TELEGRAM_CHANNEL_ID'], text=imageUrl)
    bot.send_message(chat_id=os.environ['TELEGRAM_CHANNEL_ID'], text=twitterText)


def initTelegramBot():
    return telegram.Bot(token=os.environ['TELEGRAM_TOKEN'])


def checkIfDBIsThere(cur):
    print("checking if db has been initialized yet")
    try:
        cur.execute('SELECT chatId FROM chatIds limit 1')
    except sqlite3.OperationalError as e:
        print(f"db has not been initialized yet: {e}")
        initDB.initDb()
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
    #feedArray = readInFeed()
    feedArray = None
    if feedArray is not None:
        link = feedArray['link']
        text = readInSite(link)
        teaser = readInTeaser(text)
        imageUrl = getPicture(text)
        content = feedArray['content'][0]['value']
        pictureCredits = getPictureCreditsFromContent(content)
        sendTelegramMessage(bot, link, teaser, imageUrl, pictureCredits)
    else:
        print("error while fetching and reading rss")
        print(sys.exc_info())
        sys.exit(1)


if __name__ == "__main__":
    main()
