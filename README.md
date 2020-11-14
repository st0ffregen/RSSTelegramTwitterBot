# luhzeTelegramTwitterBot

# Staging
Inside bot directory run:
```
docker run -it -v "$(pwd):/usr/src/app" --rm --env telegramToken=YOUR_TOKEN --name python-bot-running python-bot
```

# Live
Inside bot directory run:
```
docker run -it --rm --env telegramToken=YOUR_TOKEN --name python-bot-running python-bot
```
