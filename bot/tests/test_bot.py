#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime, timezone, timedelta
from unittest import TestCase, mock
from dotenv import load_dotenv
from bot import main
from bot.FeedObject import FeedObject
from bot.TweetObject import TweetObject
import os
import time

load_dotenv()

telegramUpdatesMock = [
    {'message': {'text': 'foo', 'date': time.time(), 'chat': {'id': 1}}},
    {'message': {'text': '/stop Third Culture Kids', 'date': time.time(), 'chat': {'id': 1}}},
    {'message': {'text': '/stop', 'date': time.time(), 'chat': {'id': 1}}},
    {'message': {'text': 'bar', 'date': time.time(), 'chat': {'id': 2}}},
    {'message': {'text': '/stop Third Culture Kids', 'date': time.time(), 'chat': {'id': 2}}},
    {'message': {'text': '/stop', 'date': time.time(), 'chat': {'id': 3}}},
    {'message': {'text': 'abc', 'date': time.time(), 'chat': {'id': 4}}},
]


class TestBot(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        return

    def test_split_updates_for_chat_ids(self):
        telegramUpdatesMock = [
            {'message': {'text': 'foo', 'chat': {'id': 1}}},
            {'message': {'text': '/stop Third Culture Kids', 'chat': {'id': 1}}},
            {'message': {'text': '/stop', 'chat': {'id': 1}}},
            {'message': {'text': 'bar', 'chat': {'id': 2}}},
            {'message': {'text': '/stop', 'chat': {'id': 3}}},
        ]

        chatIdsWithUpdatesDict = {
            1: [{'chat': {'id': 1}, 'text': 'foo'},
                {'chat': {'id': 1}, 'text': '/stop Third Culture Kids'},
                {'chat': {'id': 1}, 'text': '/stop'}],
            2: [{'chat': {'id': 2}, 'text': 'bar'}],
            3: [{'chat': {'id': 3}, 'text': '/stop'}]
        }

        self.assertEqual(main.splitUpdatesForChatIds(telegramUpdatesMock), chatIdsWithUpdatesDict)

    @mock.patch.dict(os.environ, {'TELEGRAM_AUTHOR_NAMES': '[abc, def]'})
    @mock.patch.dict(os.environ, {'TELEGRAM_CHAT_IDS': '[1,2]'})
    def test_resolveChat_id_by_author_name(self):
        self.assertEqual(main.resolveChatIdByAuthorName('abc'), 1)

    @mock.patch.dict(os.environ, {'TELEGRAM_AUTHOR_NAMES': '[a, b, c, d]'})
    @mock.patch.dict(os.environ, {'TELEGRAM_CHAT_IDS': '[1,2,3,4]'})
    @mock.patch('bot.main.logging')
    @mock.patch('bot.main.telegram')
    def test_is_there_stop_command(self, telegram_mock, logging_mock):
        telegram_mock.bot.get_updates.return_value = telegramUpdatesMock

        # stops because same author and correct keywords
        self.assertTrue(main.isThereStopCommand(telegram_mock.bot, 'a', 'abc Third Culture Kids abc', logging_mock))
        # stops because same author and uses general /stop to stop all
        self.assertTrue(main.isThereStopCommand(telegram_mock.bot, 'c', 'abc Third Culture Kids abc', logging_mock))
        # stops because same author and uses general /stop to stop all
        self.assertTrue(main.isThereStopCommand(telegram_mock.bot, 'c', None, logging_mock))
        # does not stop because specific stop keywords but no matching article
        self.assertFalse(main.isThereStopCommand(telegram_mock.bot, 'b', 'abc some other text abc', logging_mock))
        # does not stop because no stop used
        self.assertFalse(main.isThereStopCommand(telegram_mock.bot, 'd', 'abc some other text abc', logging_mock))
        # does not stop because no stop used
        self.assertFalse(main.isThereStopCommand(telegram_mock.bot, 'd', None, logging_mock))

    @mock.patch.dict(os.environ, {'TELEGRAM_AUTHOR_NAMES': '[a, b, c, d]'})
    @mock.patch.dict(os.environ, {'TELEGRAM_CHAT_IDS': '[1,2,3,4]'})
    @mock.patch('bot.main.logging')
    @mock.patch('bot.main.telegram')
    def test_filter_stopped_articles(self, telegram_mock, logging_mock):
        telegram_mock.bot.get_updates.return_value = telegramUpdatesMock

        feedListSeveralArticles = [
            FeedObject('https://www.luhze.de/2021/10/18/vorschau-auf-das-64-dok-leipzig/',
                       datetime(2021, 10, 18, 9, 2, 49, tzinfo=timezone.utc), 'a',
                       '<p>Zum 64. Mal präsentiert das Dok Leipzig jene Dokumentar- und Animationsfilme, die es aus insgesamt 2.800 gesichteten Filmen in die engere Auswahl geschafft haben. Es werden 162 Streifen aus 51 Ländern in acht Leipziger Spielstätten gezeigt. Im Dok Stream können die Filme auch nach dem Festival bis zum 14. November angesehen werden. Das Festival wird von einem umfangreichen Rahmenprogramm begleitet.</p>\n<p>Fotos: Susann Jehnichen</p>'),
            FeedObject('https://www.luhze.de/2021/10/18/guenther-grass-und-das-klima/',
                       datetime(2021, 10, 18, 8, 19, 41, tzinfo=timezone.utc), 'a',
                       '<p>„Noah hat von jedem Tier zwei mit auf die Arche genommen. Von den unreinen nur eins. Nur die Ratten, hat er nicht mitnehmen wollen – und doch haben sie die Sintflut überlebt“, erzählt die Rättin (Teresa Schergaut). Auch den Ultemosch, eine nicht näher beschriebene Katastrophe, haben die Ratten überdauert.</p>\n<p>Foto: Rolf Arnold</p>'),
            FeedObject('https://www.luhze.de/2021/10/17/aus-dem-leben-eines-third-culture-kids/',
                       datetime(2021, 10, 17, 18, 12, 4, tzinfo=timezone.utc), 'b',
                       '<p>Stell dir vor, deine Mutter kommt aus Uganda und aus Belgien, ist aber in Kanada aufgewachsen. Dein Vater kommt aus der Schweiz. Du selber hast in den USA, in Uganda, Zimbabwe und in Kanada gelebt. Wo ist dann deine Heimat? Der Begriff der Herkunft und der Heimat wird unpassend und abstrus angesichts solcher Lebensläufe. In einem Versuch der Selbstdefinition nennen sich solche Menschen „Third Culture Kids“. Sie wachsen eben nicht in ihrer eigenen Kultur oder in der ihrer Eltern auf, sondern in einer gänzlich Dritten. Meistens auch Vierten und Fünften. In einem weiteren Versuch der Selbstdefinition sehe ich mich als gemäßigtes Third Culture Kid. Zwar bin auch ich mehrere Jahre im Ausland aufgewachsen, aber anders als die vollblütigen Third Culture Kids, bin ich immer wieder zum selben Ort zurück geboomerangt.</p></p>\n<p>&nbsp;</p>\n<p>&nbsp;</p>'),
            FeedObject('https://www.luhze.de/2021/10/15/harmonische-schreibtischarbeit/',
                       datetime(2021, 10, 15, 7, 6, 46, tzinfo=timezone.utc), 'b',
                       '<p>Als ich das Gelände des Tapetenwerks in Leipzig Lindenau betrete und das Gemeinschaftsbüro Raumstation im zweiten Obergeschoss aufsuchen möchte, macht die Chefin, Martina Ecklebe, gerade Mittagspause in der Cafeteria nebenan. Ich solle doch schonmal ins Büro gehen und dort auf sie warten. Das erste, was mir dort ins Auge fällt, ist der Schriftzug Raumstation, der, zusammen mit einer einäugigen Katze und zwei vier\xadfingrigen Marsmännchen, die Wand gegenüber dem Eingang ziert. Ich lasse mich an einer der sechs Arbeitsplatzinseln, bestehend aus jeweils zwei oder drei blauweißen Schreibtischen, nieder.</p>'),
            FeedObject('https://www.luhze.de/2021/10/14/integration-verstehen/',
                       datetime(2021, 10, 14, 16, 21, 24, tzinfo=timezone.utc), 'b',
                       '<p>Im April feierte das Willkommenszentrum Leipzig (WZL) dreijähriges Jubiläum. Seit seiner Eröffnung 2018 haben Menschen mit Migrationsgeschichte die Chance, sich im Zentrum in der Otto-Schill-Straße umfassend beraten zu lassen. Die Mitarbeiter*innen der Stadt sa\xadgen, sie würden vor allem auf die Menschen zugehen wollen.</p>'),
            FeedObject('https://www.luhze.de/2021/10/13/ewig-wird-er-weiterleben-2/',
                       datetime(2021, 10, 13, 6, 33, 54, tzinfo=timezone.utc), 'b',
                       '<p>Wie weit müssen wir Menschen laufen, wenn uns die eigene Rache treibt?</p>\n<p>Fotos: Maria Obermeier</p>'),
            FeedObject('https://www.luhze.de/2021/10/10/koennen-wir-auf-dauer-funktionieren/',
                       datetime(2021, 10, 10, 13, 41, 59, tzinfo=timezone.utc), 'c',
                       '<p>Vor einigen Wochen, nachdem ich mich von meiner Freundin hatte updaten lassen, wie der knapp 2000 Kilometer entfernte, deutsche Sommer während meiner Reisen weitergelaufen war, stellte sie mir am Telefon eine Frage. Unser Gespräch war fast vorbei, als sie sagte: „Noch eine Frage. Kann man eine glückliche Beziehung führen, wenn man grundsätzlich verschieden ist, unterschiedliche Grundwerte vertritt, aber man im Alltag unglaublich gut harmoniert?\xa0Kann man einfach die Zweisamkeit genießen, ohne sich Gedanken darüber machen zu müssen, ob der Mensch wirklich grad alle Ansprüche erfüllt?“.</p>'),
            FeedObject('https://www.luhze.de/2021/10/08/filmfestivals-sind-gatekeeper/',
                       datetime(2021, 10, 8, 11, 32, 36, tzinfo=timezone.utc), 'a',
                       '<p>Vom 25. bis 31. Oktober 2021 findet das Dokumentar- und Animationsfilmfestival Dok Leipzig statt. <em>luhze</em>-Redakteurin Anna Seikel hat mit der neuen Programmkoordinatorin im Wettbewerb, Marie-Thérèse Antony, über Filmauswahl, Verantwortung und Diversität beim Festival gesprochen.</p>\n<p>Foto: Susann Jehnichen</p>')
        ]

        feedListOneArticleFromAuthorA = [FeedObject('https://www.luhze.de/2021/10/18/vorschau-auf-das-64-dok-leipzig/',
                                                    datetime(2021, 10, 18, 9, 2, 49, tzinfo=timezone.utc), 'a',
                                                    '<p>Zum 64. Mal präsentiert das Dok Leipzig jene Dokumentar- und Animationsfilme, die es aus insgesamt 2.800 gesichteten Filmen in die engere Auswahl geschafft haben. Es werden 162 Streifen aus 51 Ländern in acht Leipziger Spielstätten gezeigt. Im Dok Stream können die Filme auch nach dem Festival bis zum 14. November angesehen werden. Das Festival wird von einem umfangreichen Rahmenprogramm begleitet.</p>\n<p>Fotos: Susann Jehnichen</p>')]

        feedListOneArticleFromAuthorD = [FeedObject('https://www.luhze.de/2021/10/18/vorschau-auf-das-64-dok-leipzig/',
                                                    datetime(2021, 10, 18, 9, 2, 49, tzinfo=timezone.utc), 'd',
                                                    '<p>Zum 64. Mal präsentiert das Dok Leipzig jene Dokumentar- und Animationsfilme, die es aus insgesamt 2.800 gesichteten Filmen in die engere Auswahl geschafft haben. Es werden 162 Streifen aus 51 Ländern in acht Leipziger Spielstätten gezeigt. Im Dok Stream können die Filme auch nach dem Festival bis zum 14. November angesehen werden. Das Festival wird von einem umfangreichen Rahmenprogramm begleitet.</p>\n<p>Fotos: Susann Jehnichen</p>')]

        feedListWithoutStoppedArticles = [
            FeedObject('https://www.luhze.de/2021/10/15/harmonische-schreibtischarbeit/',
                       datetime(2021, 10, 15, 7, 6, 46, tzinfo=timezone.utc), 'b',
                       '<p>Als ich das Gelände des Tapetenwerks in Leipzig Lindenau betrete und das Gemeinschaftsbüro Raumstation im zweiten Obergeschoss aufsuchen möchte, macht die Chefin, Martina Ecklebe, gerade Mittagspause in der Cafeteria nebenan. Ich solle doch schonmal ins Büro gehen und dort auf sie warten. Das erste, was mir dort ins Auge fällt, ist der Schriftzug Raumstation, der, zusammen mit einer einäugigen Katze und zwei vier\xadfingrigen Marsmännchen, die Wand gegenüber dem Eingang ziert. Ich lasse mich an einer der sechs Arbeitsplatzinseln, bestehend aus jeweils zwei oder drei blauweißen Schreibtischen, nieder.</p>'),
            FeedObject('https://www.luhze.de/2021/10/14/integration-verstehen/',
                       datetime(2021, 10, 14, 16, 21, 24, tzinfo=timezone.utc), 'b',
                       '<p>Im April feierte das Willkommenszentrum Leipzig (WZL) dreijähriges Jubiläum. Seit seiner Eröffnung 2018 haben Menschen mit Migrationsgeschichte die Chance, sich im Zentrum in der Otto-Schill-Straße umfassend beraten zu lassen. Die Mitarbeiter*innen der Stadt sa\xadgen, sie würden vor allem auf die Menschen zugehen wollen.</p>'),
            FeedObject('https://www.luhze.de/2021/10/13/ewig-wird-er-weiterleben-2/',
                       datetime(2021, 10, 13, 6, 33, 54, tzinfo=timezone.utc), 'b',
                       '<p>Wie weit müssen wir Menschen laufen, wenn uns die eigene Rache treibt?</p>\n<p>Fotos: Maria Obermeier</p>')
        ]

        # returns empty list because authors gives /stop signal
        self.assertEqual(main.filterStoppedArticles(telegram_mock.bot, feedListOneArticleFromAuthorA, logging_mock), [])
        # returns feed array because there is no stop command
        self.assertEqual(main.filterStoppedArticles(telegram_mock.bot, feedListOneArticleFromAuthorD, logging_mock),
                         feedListOneArticleFromAuthorD)
        # returns filtered list
        self.assertEqual(main.filterStoppedArticles(telegram_mock.bot, feedListSeveralArticles, logging_mock),
                         feedListWithoutStoppedArticles)

    @mock.patch.dict(os.environ, {'INTERVAL_SECONDS': '1860'})
    @mock.patch('bot.main.logging')
    @mock.patch('bot.main.tweepy')
    def test_is_link_already_tweeted(self, tweepy_mock, logging_mock):
        class StatusMock:
            def __init__(self, created_at, id_str, entities, in_reply_to_status_id):
                self.created_at = created_at
                self.id_str = id_str
                self.entities = entities
                self.in_reply_to_status_id = in_reply_to_status_id

        tweepy_mock.user_timeline.return_value = [
            StatusMock(datetime.utcnow(), '1450703342284517381',
                       {'urls': [{'expanded_url': 'https://steadyhq.com/de/luhzeleipzig'}]}, None),
            StatusMock(datetime.utcnow(), '1438478887646863360', {
                'urls': [{'expanded_url': 'https://www.luhze.de/2021/09/16/langer-weg-zur-gruenen-universitaet/'}]},
                       None),
            StatusMock(datetime.utcnow() - timedelta(seconds=1870), '1438478887646863360',
                       {'urls': [{'expanded_url': 'https://www.luhze.de/2021/10/19/was-bleibt-wenn-wir-gehen/'}]}, None)
        ]

        self.assertTrue(main.isLinkAlreadyTweeted(tweepy_mock,
                                                  'https://www.luhze.de/2021/09/16/langer-weg-zur-gruenen-universitaet/',
                                                  logging_mock))
        self.assertFalse(main.isLinkAlreadyTweeted(tweepy_mock, 'https://www.abc.de', logging_mock))
        # tweet is too old to stop publishing
        self.assertFalse(
            main.isLinkAlreadyTweeted(tweepy_mock, 'https://www.luhze.de/2021/10/19/was-bleibt-wenn-wir-gehen/',
                                      logging_mock))

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

        expectedTweetObject = TweetObject('Im Schauspiel Leipzig läuft derzeit das Theaterstück „Die Rättin“ inszeniert von Claudia Bauer. In bunten Kleidern und Masken erzählen weibliche Ratten vom Untergang der Menschheit.', 'https://www.luhze.de/2021/10/18/guenther-grass-und-das-klima/', 'Rolf Arnold', 'https://www.luhze.de/wp-content/uploads/2021/10/die-Raettinen_Rolf-Arnold-scaled-e1634544908467-1024x384.jpg', '123')

        self.assertEqual(main.craftTweetObjectList(feedArray, logging_mock), [expectedTweetObject])

