#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime, timezone, timedelta
from unittest import TestCase, mock
from dotenv import load_dotenv
from bot import main
from bot.FeedObject import FeedObject
from bot.TweetObject import TweetObject
import sqlite3

load_dotenv()

class TestBot(TestCase):

    def setUp(self):
        # Create a temporary in-memory SQLite database for testing
        self.con = sqlite3.connect(':memory:')
        self.cur = self.con.cursor()

        self.cur.execute(
            'CREATE TABLE tweets ( "id" INTEGER, "url" TEXT NOT NULL UNIQUE, "published_at" TEXT NOT NULL, PRIMARY KEY("id" AUTOINCREMENT))')
        self.con.commit()


    def tearDown(self):
        self.cur.close()
        self.con.close()


    def test_is_link_already_tweeted(self):

        self.cur.execute('insert into tweets (url, published_at) values (?, ?)', ('https://www.luhze.de/2021/09/16/langer-weg-zur-gruenen-universitaet/', 'test'))
        self.con.commit()

        self.assertTrue(main.isLinkAlreadyTweeted(self.cur, 'https://www.luhze.de/2021/09/16/langer-weg-zur-gruenen-universitaet/'))
        self.assertFalse(main.isLinkAlreadyTweeted(self.cur, 'not_tweeted_test'))

    def test_get_picture_credit(self):
        contentFotosPlural = '<p>some content here</p><p>Fotos: abc</p>'
        contentFotosSingular = '<p>some content here</p><p>Foto: abc</p>'
        contentTitelfoto = '<p>some content here</p><p>Titelfoto: abc</p>'

        self.assertEqual(main.getPictureCredit(contentFotosPlural), 'abc')
        self.assertEqual(main.getPictureCredit(contentFotosSingular), 'abc')
        self.assertEqual(main.getPictureCredit(contentTitelfoto), 'abc')

    @mock.patch('bot.main.logging')
    @mock.patch('bot.main.downloadImage')
    @mock.patch('bot.main.urlopen')
    def test_craft_tweet_object_list(self, urlopen_mock, downloadImage_mock, logging_mock):
        class UrlOpenMock:
            def __init__(self, sourceCode):
                self.sourceCode = sourceCode

            def read(self):
                return self.sourceCode

        urlopen_mock.return_value = UrlOpenMock('<!DOCTYPE html><html lang="de"><head></head><body><div class="bunnerStyle" style="background-image:url(\'https://www.luhze.de/wp-content/uploads/2021/10/die-Raettinen_Rolf-Arnold-scaled-e1634544908467-1024x384.jpg\');"></div><p class="descriptionStyle">Im Schauspiel Leipzig läuft derzeit das Theaterstück „Die Rättin“ inszeniert von Claudia Bauer. In bunten Kleidern und Masken erzählen weibliche Ratten vom Untergang der Menschheit. </p><p>Foto: Rolf Arnold</p></body>')
        downloadImage_mock.return_value = '123'

        feedArray = [FeedObject('https://www.luhze.de/2021/10/18/guenther-grass-und-das-klima/',
                   datetime(2021, 10, 18, 9, 2, 49, tzinfo=timezone.utc), 'a',
                   '<p>Die Ratten und Rättinen aber würden dies überleben.</p> <p>„Die Rättin“ läuft derzeit auf der Großen Bühne des Schauspiel Leipzigs. Weitere Spieltermine: 21.10, 30.10, 14.11. Tickets für Studierende ab 12 Euro.</p> <p>Foto: Rolf Arnold</p>')]

        expectedTweetObject = TweetObject('Im Schauspiel Leipzig läuft derzeit das Theaterstück „Die Rättin“ inszeniert von Claudia Bauer. In bunten Kleidern und Masken erzählen weibliche Ratten vom Untergang der Menschheit.', 'https://www.luhze.de/2021/10/18/guenther-grass-und-das-klima/', 'https://www.luhze.de/wp-content/uploads/2021/10/die-Raettinen_Rolf-Arnold-scaled-e1634544908467-1024x384.jpg', 'Rolf Arnold', '123')

        self.assertEqual(main.craftTweetObjectList(feedArray, logging_mock), [expectedTweetObject])

