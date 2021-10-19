# RSSTelegramTwitterBot

This bot automatically publishes a tweet when a new article is added on website XY.  
You can specify an interval in which the user can stop the publishing pipeline via her telegram.  
The bot uses RSS. If you want it to work for your site you need RSS with the same structure as luhze.de/rss.


# Build
```
docker build -t rss-telegram-twitter-bot ./bot
```

# Run
Copy ```.env.example``` to ```.env``` and fill out the variables.
```
docker run -it -v "$(pwd)/bot:/usr/src/app" --rm --env-file .env --name rss-telegram-twitter-bot-running rss-telegram-twitter-bot
```

# Telegram Bot Commands
```
/stop - Stops the publishing pipeline
```