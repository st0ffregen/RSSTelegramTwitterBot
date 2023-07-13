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
import re
import tweepy
import traceback
import logging
from dotenv import load_dotenv
from bot.FeedObject import FeedObject
from bot.TweetObject import TweetObject
import time
import shutil
import sqlite3

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

def filterAlreadyTweetedArticles(cur, feedList):
    notAlreadyTweetedArticlesList = []

    for article in feedList:
        if not isLinkAlreadyTweeted(cur, article.link):
            notAlreadyTweetedArticlesList.append(article)

    return notAlreadyTweetedArticlesList


def isLinkAlreadyTweeted(cur, link):
    # get tweets from db
    rows = cur.execute('SELECT * FROM tweets where url = ?', (link,)).fetchall()

    if len(rows) > 0:
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


def publishTweets(api, client, tweetObjectList, logger):

    for tweet in tweetObjectList:
        media = api.media_upload(tweet.pathToImage)

        if tweet.imageCredit is None:
            tweet = tweet.teaser + "\n\n" + u"\u27A1" + " " + tweet.link
        else:
            tweet = tweet.teaser + "\n\n" + u"\u27A1" + " " + tweet.link + "\n\n" + u"\U0001F4F8" + " " + tweet.imageCredit

        logger.info('tweet ' + tweet.replace('\n', ''))
        response = client.create_tweet(text=tweet, media_ids=[media.media_id])
        logger.info(f"published tweet id: {response.data['id']}")



def getTwitterAccess():
    auth = tweepy.OAuth1UserHandler(os.environ['TWITTER_API_KEY'], os.environ['TWITTER_API_SECRET_KEY'], os.environ['TWITTER_ACCESS_TOKEN'], os.environ['TWITTER_ACCESS_TOKEN_SECRET'])
    api = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=os.environ['TWITTER_API_KEY'],
        consumer_secret=os.environ['TWITTER_API_SECRET_KEY'],
        access_token=os.environ['TWITTER_ACCESS_TOKEN'],
        access_token_secret=os.environ['TWITTER_ACCESS_TOKEN_SECRET'])
    return api, client


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

        conn = sqlite3.connect('tweets.db')
        cur = conn.cursor()

        notTweetedArticles = filterAlreadyTweetedArticles(cur, onlyNewArticlesFeedList)

        tweetObjectList = craftTweetObjectList(notTweetedArticles, logger)

        logger.info('init twitter bot')
        api, client = getTwitterAccess()

        publishTweets(api, client, tweetObjectList, logger)

        # write published tweets to db
        for article in notTweetedArticles:
            cur.execute('INSERT INTO tweets VALUES (?, ?)', (article.link, datetime.utcnow()))
        conn.commit()

        logger.info('delete images')
        deleteAllImages()

        cur.close()
        conn.close()

    except Exception as e:
        logger.critical(f"something went wrong: {e}")
        logger.critical(traceback.format_exception(*sys.exc_info()))
        return 1
    finally:
        logger.info('stop bot')


if __name__ == "__main__":
    main()
