# luhzeTelegramTwitterBot

# Build
```
docker build -t python-bot ./bot
```

# Staging
```
docker run -it -v "$(pwd)/bot:/usr/src/app" --rm --env-file .env --name python-bot-running python-bot
```

# Deployment
```
docker run -it --rm --env-file .env --name python-bot-running python-bot
```
