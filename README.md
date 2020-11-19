# luhzeTelegramTwitterBot

# Build
```
docker build -t python-bot ./bot
```

# Staging & Deployment
```
cp .env-example .env
cp bot/twitter-example.db bot/twitter.db
docker run -it -v "$(pwd)/bot:/usr/src/app" --rm --env-file .env --name python-bot-running python-bot
```
