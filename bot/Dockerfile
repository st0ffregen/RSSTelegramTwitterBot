FROM python:latest
COPY . /usr/src/app
RUN apt-get update
RUN apt-get install -y python3-pip
RUN pip3 install feedparser
RUN pip3 install python-telegram-bot --upgrade
CMD["python33.7", "/usr/src/app/main.py"]