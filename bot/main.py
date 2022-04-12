#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime, timezone
import pytz
import feedparser
from urllib.request import urlopen
import requests
import sys
import os
from bs4 import BeautifulSoup
import telegram
import re
import tweepy
import traceback
import logging
from dotenv import load_dotenv
from bot.FeedObject import FeedObject
from bot.TweetObject import TweetObject
import time
import shutil

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


def isLinkOld(entry, upperTimeBound):
    diff = upperTimeBound.replace(tzinfo=pytz.utc) - entry.published

    if diff.seconds > int(os.environ['INTERVAL_SECONDS']) or diff.days > 0:
        return True

    return False


def generateListWithoutOldLinks(feedList, upperTimeBound, logger):
    feedListWithoutOldLinks = []

    for entry in feedList:
        if not isLinkOld(entry, upperTimeBound):
            logger.info('new article ' + entry.link)
            feedListWithoutOldLinks.append(entry)

    return feedListWithoutOldLinks


def readInFeed(logger):
    rssFeed = feedparser.parse(os.environ['RSS_URL'])

    if rssFeed.bozo > 0:
        raise rssFeed.bozo_exception

    feedList = []

    for entry in rssFeed.entries:
        logger.info('found article ' + entry.link)
        feedList.append(FeedObject(entry.link, datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z'), entry.author, entry.content[0]['value']))

    return feedList


def filterStoppedArticles(bot, feedList, upperTimeBound, logger):

    if len(feedList) < 2:  # only one article published
        authorName = feedList[0].author
        if isThereStopCommand(bot, authorName, feedList[0].content, upperTimeBound, logger):
            return []
        else:
            return feedList
    else:  # several articles published
        authorsWithArticlesDict = {}
        feedListWithArticlesToPublish = []

        for article in feedList:
            if article.author in authorsWithArticlesDict:
                authorsWithArticlesDict[article.author].append(article)
            else:
                authorsWithArticlesDict[article.author] = [article]

        for author in authorsWithArticlesDict:
            for article in authorsWithArticlesDict[author]:
                if not isThereStopCommand(bot, author, article.content, upperTimeBound, logger):
                    feedListWithArticlesToPublish.append(article)

        return feedListWithArticlesToPublish


def splitUpdatesForChatIds(updateArray):
    chatIdsWithUpdatesDict = {}

    try:
        for update in updateArray:
            chatId = update['message']['chat']['id']
            if chatId in chatIdsWithUpdatesDict:
                chatIdsWithUpdatesDict[chatId].append(update['message'])
            else:
                chatIdsWithUpdatesDict[chatId] = [update['message']]
    except TypeError:
        raise Exception('TypeError: \'NoneType\' object is not subscriptable. Messages: ' + updateArray)

    return chatIdsWithUpdatesDict


def resolveChatIdByAuthorName(authorName):
    authorNames = [authorName.strip() for authorName in os.environ['TELEGRAM_AUTHOR_NAMES'][1:-1].split(',')]
    authorIds = [authorId.strip() for authorId in os.environ['TELEGRAM_CHAT_IDS'][1:-1].split(',')]

    return int(authorIds[authorNames.index(authorName)])


def isThereStopCommand(bot, authorName, articleContent, upperTimeBound, logger):
    updates = bot.get_updates(timeout=120)

    if updates is None or len(updates) == 0:
        return False

    chatIdsWithUpdatesDict = splitUpdatesForChatIds(updates)
    authorChatId = resolveChatIdByAuthorName(authorName)

    for author in chatIdsWithUpdatesDict:

        if authorChatId != author:
            continue

        for message in chatIdsWithUpdatesDict[author]:
            timeDiff = upperTimeBound - datetime.fromtimestamp(message['date'])

            if timeDiff.seconds > int(os.environ['INTERVAL_SECONDS']) or timeDiff.days > 0:
                continue

            if '/stop' == message['text'].strip():
                logger.info('article was stopped by keyword ' + message['text'].strip())
                return True

            if '/stop' in message['text'].strip() and message['text'].replace('/stop', '').strip() in articleContent:
                logger.info('article was stopped by keyword ' + message['text'].strip())
                return True

    return False


def filterAlreadyTweetedArticles(twitterApi, feedList, upperTimeBound, logger):
    notAlreadyTweetedArticlesList = []

    for article in feedList:
        if not isLinkAlreadyTweeted(twitterApi, article.link, upperTimeBound, logger):
            notAlreadyTweetedArticlesList.append(article)

    return notAlreadyTweetedArticlesList


def isLinkAlreadyTweeted(twitterApi, link, upperTimeBound, logger):
    tweetList = twitterApi.user_timeline(id="luhze_leipzig", count=5, tweet_mode='extended')

    for tweet in tweetList:
        if not (upperTimeBound - tweet.created_at).seconds <= int(os.environ['INTERVAL_SECONDS']):
            logger.info('tweet ' + tweet.id_str + ' older than ' + os.environ['INTERVAL_SECONDS'] + ' seconds')
            continue

        if not (upperTimeBound - tweet.created_at).days <= 0:
            logger.info('tweet ' + tweet.id_str + ' older than 0 days')
            continue

        if tweet.in_reply_to_status_id is not None:
            logger.info('tweet ' + tweet.id_str + ' is a reply')
            continue

        if tweet.entities['urls'][0]['expanded_url'].strip() != link:
            logger.info('no link to a recent luhze article in tweet ' + tweet.id_str)
            continue

        logger.info('tweet ' + tweet.id_str + ' blocks publishing')
        return True

    return False


def deleteAllImages():
    directoryList = os.listdir('.')
    for file in directoryList:
        if file.endswith('.jpg'):
            os.remove(file)


def downloadImage(url):
    response = requests.get(url, stream=True)
    response.raw.decode_content = True
    filename = str(time.time()) + '.jpg'

    with open(filename, 'wb') as file:
        shutil.copyfileobj(response.raw, file)

    return filename


def getImageUrl(sourceCode):
    imageDiv = sourceCode.find('div', {'class': 'bunnerStyle'})
    style = imageDiv['style']
    return style.split("('")[1].split("')")[0]


def readInSite(link):
    return BeautifulSoup(urlopen(link).read(), 'html.parser')


def getTeaserText(sourceCode):
    return sourceCode.find("p", {'class': 'descriptionStyle'}).text.strip()


def getPictureCredit(content):
    blockList = ['privat']
    match = re.search('<p>(Grafik|Titelfoto|Foto(s)?):.{1,200}<\/p>', content)
    if match is not None:
        matchString = match.group()
        imageCredit = matchString.replace('</p>', '').split(':')[1].strip()
        if imageCredit.lower() not in blockList:
            return imageCredit

    return None


def craftTweetObjectList(feedList, logger):
    tweetObjectList = []

    for article in feedList:
        sourceCode = readInSite(article.link)
        teaserText = getTeaserText(sourceCode)
        imageUrl = getImageUrl(sourceCode)
        imageCredit = getPictureCredit(article.content)
        pathToImage = downloadImage(imageUrl)

        logger.info('article ' + article.link + ' with image url ' + imageUrl)
        tweetObjectList.append(TweetObject(teaserText, article.link, imageUrl, imageCredit, pathToImage))

    return tweetObjectList


def publishTweets(twitterApi, tweetObjectList, logger):

    for tweet in tweetObjectList:
        media = twitterApi.media_upload(tweet.pathToImage)

        if tweet.imageCredit is None:
            tweet = tweet.teaser + "\n\n" + u"\u27A1" + " " + tweet.link
        else:
            tweet = tweet.teaser + "\n\n" + u"\u27A1" + " " + tweet.link + "\n\n" + u"\U0001F4F8" + " " + tweet.imageCredit

        logger.info('tweet ' + tweet.replace('\n', ''))
        response = twitterApi.update_status(status=tweet, media_ids=[media.media_id])
        logger.info(response.entities['urls'][0]['expanded_url'])


def initTelegramBot():
    return telegram.Bot(token=os.environ['TELEGRAM_TOKEN'])


def getTwitterApi():
    auth = tweepy.OAuthHandler(os.environ['TWITTER_API_KEY'], os.environ['TWITTER_API_SECRET_KEY'])
    auth.set_access_token(os.environ['TWITTER_ACCESS_TOKEN'], os.environ['TWITTER_ACCESS_TOKEN_SECRET'])
    return tweepy.API(auth)


def main():
    startingTime = datetime.utcnow()

    logger = configureLogger()
    logger.info('start bot')

    try:
        logger.info('read in feed')
        feedList = readInFeed(logger)

        onlyNewArticlesFeedList = generateListWithoutOldLinks(feedList, startingTime, logger)

        if len(onlyNewArticlesFeedList) == 0:
            logger.info('no new articles uploaded in the last ' + os.environ['INTERVAL_SECONDS'] + ' seconds')
            return

        logger.info('init telegram bot')
        telegramBot = initTelegramBot()

        notStoppedArticles = filterStoppedArticles(telegramBot, onlyNewArticlesFeedList, startingTime, logger)

        logger.info('init twitter bot')
        twitterApi = getTwitterApi()

        notTweetedArticles = filterAlreadyTweetedArticles(twitterApi, notStoppedArticles, startingTime, logger)

        tweetObjectList = craftTweetObjectList(notTweetedArticles, logger)

        publishTweets(twitterApi, tweetObjectList, logger)

        logger.info('delete images')
        deleteAllImages()

    except Exception as e:
        logger.critical(f"something went wrong: {e}")
        logger.critical(traceback.format_exception(*sys.exc_info()))
        return 1
    finally:
        logger.info('stop bot')


if __name__ == "__main__":
    main()
