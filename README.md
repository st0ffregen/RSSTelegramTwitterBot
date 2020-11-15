# luhzeTelegramTwitterBot

# Build
Inside bot directpry run:
```
docker build -t python-bot .
```

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
