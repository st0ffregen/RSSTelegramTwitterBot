#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3
import sys
import os


def connectToDb():
    con = sqlite3.connect(os.environ['DB_FILE_NAME'])
    return con


def getCursor(con):
    return con.cursor()


def createTables(cur):
    cur.execute('CREATE TABLE chatIds ('
                'chatId INTEGER PRIMARY KEY '
                ');')
    return 0


def initDb():
    print("init db with tables")
    try:
        con = connectToDb()
        cur = getCursor(con)
        createTables(cur)
        con.commit()
        con.close()
        print("db initialized")
    except sqlite3.Error as e:
        print(f"Error while working with db: {e}")
        sys.exit(1)


if __name__ == "__main__":
    initDb()
