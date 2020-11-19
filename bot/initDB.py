#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3
import sys
import os


def connectToDb():
    try:
        con = sqlite3.connect(os.environ['DB_FILE_NAME'])
        return con
    except sqlite3.OperationalError as e:
        print(f"error while establishing connection to db: {e}")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)


def getCursor(con):
    try:
        return con.cursor()
    except sqlite3.OperationalError as e:
        print(f"error while creating cursor for connection: {e}")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)


def createTables(cur):
    print("creating tables in db")
    try:
        cur.execute('CREATE TABLE chatIds ('
                    'chatId INTEGER PRIMARY KEY '
                    ');')
        cur.execute('CREATE TABLE tweets ('
                    'url VARCHAR(255) PRIMARY KEY,'
                    'teaser VARCHAR(512),'
                    'imageCredits VARCHAR(128),'
                    'image BLOB'
                    ');')
    except sqlite3.OperationalError as e:
        print(f"error while inserting new tables to db: {e}")
        print("exiting")
        print(sys.exc_info())
        sys.exit(1)

    return 0
