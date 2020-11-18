# luhzeTelegramTwitterBot

# Build
```
docker build -t python-bot ./bot
```

# Staging & Deployment
```
docker run -it -v "$(pwd)/bot:/usr/src/app" --rm --env-file .env --name python-bot-running python-bot
```
