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
import tweepy


def readInFeed():
    print("read in feed")
    NewsFeed = feedparser.parse("https://luhze.de/rss")
    entry = NewsFeed.entries[0]

    # check if date is in last interval seconds
    published = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')

    diff = datetime.utcnow().replace(tzinfo=pytz.utc) - published

    if diff.seconds > int(os.environ['INTERVAL_SECONDS']) or diff.days > int(os.environ['INTERVAL_DAYS']):
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
    blockList = ["Privat"]
    match = re.search("<p>Titelfoto:.{1,200}<\/p>", text)
    if match is None:
        print("no credit found")
        return None
    else:
        pictureText = text.split("Titelfoto: ")
        imageCredits = pictureText[1].split("</p>")
        if imageCredits in blockList:
            return None[0]
        else:
            return imageCredits[0]


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

    # remove resolution to get original picture
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


def getValuesFromDb(cur):
    print("get values from db")
    try:
        cur.execute('SELECT url, teaser, imageCredits FROM tweets')
        lastTweet = cur.fetchone()
        if lastTweet is None:
            return 1
        link = lastTweet[0]
        teaser = lastTweet[1]
        imageCredits = lastTweet[2]
    except sqlite3.OperationalError as e:
        print(f"error while fetching tweet data from db: {e}")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)

    return [link, teaser, imageCredits]


def craftIntentText(cur):
    print("craft twitter intent text")
    # fetch from db
    attributes = getValuesFromDb(cur)
    link = attributes[0]
    teaser = attributes[1]
    imageCredits = attributes[2]

    # craft twitter text
    if imageCredits is None:
        twitterText = "https://twitter.com/intent/tweet?text=" + requests.utils.quote(
           teaser + "\n\n" + u"\u27A1" + " "
            + link)
    else:
        twitterText = "https://twitter.com/intent/tweet?text=" + requests.utils.quote(
            teaser + "\n\n" + u"\u27A1" + " " + link + "\n\n" + u"\U0001F4F8" + " " + imageCredits)

    return twitterText


def saveTweetToDb(cur, con, img, imageUrl, imageCredits, link, teaser):
    print("save tweet to db")
    sqlArray = [['INSERT OR IGNORE INTO tweets VALUES (?,?,?,?)', (link, teaser, imageCredits, img)]]
    return insertSQLStatements(cur, con, sqlArray)


def readImageFromDB(cur):
    print("read image from db")
    try:
        cur.execute('SELECT image FROM tweets')
        res = cur.fetchone()
        if res is not None:
            return res[0]
        else:
            print("no image in tweet db")
            return 1
    except sqlite3.OperationalError as e:
        print(f"error while fetching image from db: {e}")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)


def lookForCommand(cur, bot):
    print("look for publish/intent command")
    updates = bot.get_updates()

    if updates is None or len(updates) == 0:
        print("no new message")
    else:
        for message in updates:
            diff = datetime.utcnow().replace(tzinfo=pytz.utc) - message.message.date

            if diff.seconds > int(os.environ['INTERVAL_SECONDS']) or diff.days > int(os.environ['INTERVAL_DAYS']):
                continue
            if message.message.text == "/publish":
                print("publish last tweet")
                publishTweet(bot, message.message.chat_id, cur)
            if message.message.text == "/sendintent":
                sendIntent(cur, bot, message)
        return 0


def sendIntent(cur, bot, message):
    print("send intent")
    intent = craftIntentText(cur)
    if intent == 1:  # nothing in db
        print("no tweets in db")
        bot.send_message(chat_id=message.message.chat_id,
                         text="the tweet has probably already been published by another person. If that's not the case,"
                              "please contact your administrator")
        print(sys.exc_info())
        sys.exit(1)
    else:
        bot.send_message(chat_id=message.message.chat_id, text=intent)
        print("intent successfully sent")
    return 0


def saveImageTmp(cur):
    file = open("pic.tmp", "wb")
    statusCode = readImageFromDB(cur)
    if statusCode == 1:
        return 1
    file.write(statusCode)
    return 0


def deleteImageTmp():
    file = open("pic.tmp", "w")
    file.write("")
    return 0


def publishTweet(bot, id, cur):
    oauth = OAuth()
    if oauth == 1:
        bot.send_message(chat_id=id,
                         text="something went wrong while authenticating to twitter, please contact your administrator")
    try:
        api = tweepy.API(oauth)
        statusCode = saveImageTmp(cur)
        if statusCode == 1:
            bot.send_message(chat_id=id,
                             text="something went wrong while fetching data from the database, please contact your administrator")
            print("exiting")
            print(sys.exc_info())
            sys.exit(1)

        media = api.media_upload("pic.tmp")
        deleteImageTmp()
        attributes = getValuesFromDb(cur)
        link = attributes[0]
        teaser = attributes[1]
        imageCredits = attributes[2]
        if imageCredits is None:
            tweet = teaser + "\n\n" + u"\u27A1" + " " + link
        else:
            tweet = teaser + "\n\n" + u"\u27A1" + " " + link + "\n\n" + u"\U0001F4F8" + " " + imageCredits

        post_result = api.update_status(status=tweet, media_ids=[media.media_id])
    except tweepy.error.TweepError as e:
        print(f"something went wrong while authenticating to twitter: {e}")
        bot.send_message(chat_id=id,
                         text="something went wrong while publishing the tweet, please contact your administrator")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)

    statusCode = deleteAllTweetsFromDB(cur)
    if statusCode == 1:
        print("something went wrong while deleting all tweets from db")
        bot.send_message(chat_id=id,
                         text="the tweet has probably already been published by another person. If that's not the case,"
                              "please contact your administrator")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)

    print("new tweet successfully published")
    bot.send_message(chat_id=id,
                     text="new tweet has been successfully published")
    return 0


def deleteAllTweetsFromDB(cur):
    print("delete all tweets from db")
    try:
        cur.execute('DELETE FROM tweets')
        return 0
    except sqlite3.OperationalError as e:
        print(f"error deleting all tweets: {e}")
        print("exiting")
        print(sys.exc_info())
        return 1


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
                sqlArray.append(['INSERT OR IGNORE INTO chatIds VALUES (?)', (int(id.message.chat_id),)])
        insertSQLStatements(cur, con, sqlArray)


def insertSQLStatements(cur, con, sqlArray):
    try:
        for statement in sqlArray:
            cur.execute(statement[0], statement[1])
        con.commit()
        return 0
    except sqlite3.OperationalError as e:
        print(f"error while working with db: {e}")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)


def sendTelegramMessage(bot, link, teaser, imageUrl, credits, chatIds, published):
    print("send telegram message")

    for id in chatIds:
        bot.send_message(chat_id=id[0], text="--- NEW ARTICLE " + published.strftime('%Y-%m-%d %H:%M:%S') + " ---")
        bot.send_photo(chat_id=id[0], photo=imageUrl)
        if credits is None:
            bot.send_message(chat_id=id[0],
                             text="link: \n" + link + "\n\n" + teaser + "\n\ncredits: photo made by author")
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
        return 0


def OAuth():
    try:
        auth = tweepy.OAuthHandler(os.environ['TWITTER_API_KEY'], os.environ['TWITTER_API_SECRET_KEY'])
        auth.set_access_token(os.environ['TWITTER_ACCESS_TOKEN'], os.environ['TWITTER_ACCESS_TOKEN_SECRET'])
        return auth
    except tweepy.error.TweepError as e:
        print(f"something went wrong while authenticating to twitter: {e}")
        return 1


def main():
    print("---")
    print("starting bot")
    print("utc time now: " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    bot = initTelegramBot()
    con = initDB.connectToDb()
    cur = initDB.getCursor(con)
    checkIfDBIsThere(cur)
    readInNewChatId(cur, con, bot)
    lookForCommand(cur, bot)
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
        sendTelegramMessage(bot, link, teaser, imageUrl, pictureCredits, chatIds, feedArray['published'])
        cur.close()
        con.close()
    else:
        print("error while fetching and reading rss")
        print(sys.exc_info())
        sys.exit(1)


if __name__ == "__main__":
    main()
