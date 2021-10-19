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
import tweepy
import traceback
import logging
from dotenv import load_dotenv

load_dotenv()

pathToLogFile = 'logs/rssTelegramTwitterBot.log'


def configureLogger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

    file_handler = logging.FileHandler(pathToLogFile)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def getLinksFromRSS():
    print("read in feed")
    NewsFeed = feedparser.parse("https://luhze.de/rss")
    entries = NewsFeed.entries

    linkArray = []

    for entry in entries:
        linkArray.append(entry.link.strip())

    return linkArray


def isLinkOld(entry):
    published = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
    diff = datetime.utcnow().replace(tzinfo=pytz.utc) - published
    intervalSeconds = int(os.environ['INTERVAL_SECONDS'])

    #if diff.seconds > intervalSeconds or diff.days > 0:
    if True:
        return False

    return False


def generateListWithoutOldLinks(listWithOldLinks):
    listWithoutOldLinks = []

    for entry in listWithOldLinks:
        if not isLinkOld(entry):
            listWithoutOldLinks.append({'link': entry.link, 'published': datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z'), 'author': entry.author, 'content': entry.content})
    return listWithoutOldLinks


def readInFeed():
    rssFeed = feedparser.parse(os.environ['RSS_URL'])

    if rssFeed.bozo > 0:
        raise rssFeed.bozo_exception

    return generateListWithoutOldLinks(rssFeed.entries)





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
        if imageCredits[0] in blockList:
            print("image credit in blocklist")
            return None
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
    #return re.sub("-\d{2,5}x\d{2,5}\.jpg$", ".jpg", url)

    return url

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


def generateListWithArticlesToPublish(bot, feedArray):

    if len(feedArray) < 2:  # only one article published
        authorName = feedArray[0]['author']
        if isThereStopCommand(bot, authorName, None):
            return []
        else:
            return feedArray
    else:  # several articles published
        authorsWithArticlesDict = {}
        feedArrayWithArticlesToPublish = []

        for article in feedArray:
            if article['author'] in authorsWithArticlesDict:
                authorsWithArticlesDict[article['author']].append(article)
            else:
                authorsWithArticlesDict[article['author']] = [article]

        for author in authorsWithArticlesDict:
            #if len(authorsWithArticlesDict[author]) > 1:  # more that one article from author so keywords must be given to distinguish what to stop
            for article in authorsWithArticlesDict[author]:
                if not isThereStopCommand(bot, author, article['content']):
                    feedArrayWithArticlesToPublish.append(article)
            #else:
             #   if not isThereStopCommand(bot, author, None):  # only one article from author so /stop is sufficient
              #      feedArrayWithArticlesToPublish.append(authorsWithArticlesDict[author][0])

        return feedArrayWithArticlesToPublish


def splitUpdatesForChatIds(updateArray):
    chatIdsWithUpdatesDict = {}

    for update in updateArray:
        chatId = update['message']['chat']['id']
        if chatId in chatIdsWithUpdatesDict:
            chatIdsWithUpdatesDict[chatId].append(update['message'])
        else:
            chatIdsWithUpdatesDict[chatId] = [update['message']]

    return chatIdsWithUpdatesDict


def resolveChatIdByAuthorName(authorName):
    authorNames = [authorName.strip() for authorName in os.environ['TELEGRAM_AUTHOR_NAMES'][1:-1].split(',')]
    authorIds = [authorId.strip() for authorId in os.environ['TELEGRAM_CHAT_IDS'][1:-1].split(',')]

    return int(authorIds[authorNames.index(authorName)])


def isThereStopCommand(bot, authorName, articleContent):
    updates = bot.get_updates(timeout=120)

    if updates is None or len(updates) == 0:
        return False

    chatIdsWithUpdatesDict = splitUpdatesForChatIds(updates)
    authorChatId = resolveChatIdByAuthorName(authorName)

    for author in chatIdsWithUpdatesDict:

        if authorChatId != author:
            continue

        for message in chatIdsWithUpdatesDict[author]:
            timeDiff = datetime.now() - datetime.fromtimestamp(message['date'])

            if timeDiff.seconds > int(os.environ['INTERVAL_SECONDS']) or timeDiff.days > 0:
                continue

            if '/stop' == message['text'].strip():
                return True
            if '/stop' in message['text'].strip() and message['text'].replace('/stop', '').strip() in articleContent:
                return True

    return False


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
    print("publish new tweet")
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
        print(f"something went wrong while publishing the tweet twitter: {e}")
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



def sendTelegramMessage(bot, link, teaser, imageUrl, credits, chatIds, published):
    print("send telegram message")

    for id in chatIds:
        bot.send_message(chat_id=id[0], text="--- NEW ARTICLE " + published.strftime('%Y-%m-%d %H:%M:%S') + " ---")
        bot.send_photo(chat_id=id[0], photo=imageUrl)
        if credits is None:
            bot.send_message(chat_id=id[0],
                             text="link: \n" + link + "\n\n" + teaser + "\n\nwon't show any credits")
        else:
            bot.send_message(chat_id=id[0], text="link: \n" + link + "\n\n" + teaser + "\n\ncredits: " + credits)

    return 0


def initTelegramBot():
    return telegram.Bot(token=os.environ['TELEGRAM_TOKEN'])


def authorizeToTwitter():
    auth = tweepy.OAuthHandler(os.environ['TWITTER_API_KEY'], os.environ['TWITTER_API_SECRET_KEY'])
    auth.set_access_token(os.environ['TWITTER_ACCESS_TOKEN'], os.environ['TWITTER_ACCESS_TOKEN_SECRET'])
    return auth


def main():
    telegramToken = os.environ['TELEGRAM_TOKEN']
    chatIdArray = os.environ['TELEGRAM_CHAT_IDS']
    telegramAdminChatId = os.environ['TELEGRAM_ADMIN_CHAT_ID']

    # was passiert wenn mehrere artikel hochgeladen wurden555 -> signalwort aus dem content
    # was passiert wenn abwehcselnd franz und funmi in dieser stunde was hochladen5 -> wird strikt nach autor:in gesplittet
    # am ende noch autor:in benachrichtigen

    logger = configureLogger()
    logger.info('start bot')

    try:
        logger.debug('read in feed')
        feedArray = readInFeed()

        if len(feedArray) == 0:
            logger.info('no new articles uploaded in the last ' + os.environ['INTERVAL_SECONDS'] + ' seconds')
            return

        logger.debug('init telegram bot')
        telegramBot = initTelegramBot()

        generateListWithArticlesToPublish(telegramBot, feedArray)

        logger.debug('init twitter bot')
        #twitterAuth = authorizeToTwitter()
    except Exception as e:
        logger.critical(f"something went wrong: {e}")
        logger.critical(traceback.format_exception(*sys.exc_info()))
        return 1


    # try:
    #     lookForCommand(cur, bot)
    #
    #     if feedArray is not None:
    #         link = feedArray['link']
    #         text = readInSite(link)
    #         teaser = readInTeaser(text)
    #         imageUrl = getPictureLink(text)
    #         img = downloadPicture(imageUrl)
    #         content = feedArray['content'][0]['value']
    #         pictureCredits = getPictureCreditsFromContent(content)
    #         saveTweetToDb(cur, con, img, imageUrl, pictureCredits, link, teaser)
    #         chatIds = getChatIdsFromDB(cur)
    #         sendTelegramMessage(bot, link, teaser, imageUrl, pictureCredits, chatIds, feedArray['published'])
    #         cur.close()
    #         con.close()
    #     else:
    #         print("error while fetching and reading rss")
    #         print(sys.exc_info())
    #         sys.exit(1)
    # except telegram.TelegramError as e:
    #     print(f"error while working with telegram api: {e}")
    #     traceback.print_exc()
    #     print("exiting")
    #     print(sys.exc_info())
    #     sys.exit(1)


if __name__ == "__main__":
    main()
