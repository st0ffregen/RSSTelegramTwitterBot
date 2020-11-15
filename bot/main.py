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


def getFotoCreditsFromContent(text):
    fotoText = text.split("Foto: ")
    if len(fotoText) > 1:
        credits = fotoText[1].split("</p>")
        return credits[0]
    else:
        fotoText = text.split("Titelfoto: ")
        if len(fotoText) > 1:
            credits = fotoText[1].split("</p>")
            return credits[0]
        else:
            print("no credit found")
    return None


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
    return url


def sendTelegramMessage(link, teaser, imageUrl, credits):
    print("send telegram message")
    bot = telegram.Bot(token=os.environ['telegramToken'])
    chatIds = bot.get_updates()

    #craft twitter text
    if credits is None:
        twitterText = "https://twitter.com/intent/tweet?text=" + requests.utils.quote(teaser + "\n\n" + u"\u27A1" + " "
                                                                                      + link)
    else:
        twitterText = "https://twitter.com/intent/tweet?text=" + requests.utils.quote(
            teaser + "\n\n" + u"\u27A1" + " " + link + "\n\n" + u"\U0001F4F8" + " " + credits)

    for id in chatIds:
        bot.send_message(chart_id=id.message.chat_id, text="---")
        bot.send_message(chat_id=id.message.chat_id, text=twitterText)
        bot.send_message(chat_id=id.message.chat_id, text="title image: " + imageUrl)


def main():
    print("---")
    print("starting bot")
    print("utc time now: " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    feedArray = readInFeed()
    if feedArray is not None:
        link = feedArray['link']
        text = readInSite(link)
        teaser = readInTeaser(text)
        imageUrl = getPicture(text)
        content = feedArray['content'][0]['value']
        fotoCredits = getFotoCreditsFromContent(content)
        sendTelegramMessage(link, teaser, imageUrl, fotoCredits)
    else:
        print("error while fetching and reading rss")
        print(sys.exc_info())
        sys.exit(1)


if __name__ == "__main__":
    main()
