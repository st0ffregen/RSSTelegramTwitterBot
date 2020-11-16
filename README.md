# luhzeTelegramTwitterBot

# Build
```
docker build -t python-bot ./bot
```

# Staging
```
docker run -it -v "$(pwd)/bot:/usr/src/app" --rm --env telegramToken=YOUR_TOKEN --env telegramChannelId=YOUR_CHANNEL_ID --name python-bot-running python-bot
```

# Deployment
```
docker run -it --rm --env telegramToken=YOUR_TOKEN --env telegramChannelId=YOUR_CHANNEL_ID --name python-bot-running python-bot
```
