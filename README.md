# luhzeTelegramTwitterBot

This bot automatically publishes a tweet when a new article is added on website XY.  
To tweet the bot aggregate information specifically useful for luhze.de. That can be edited.  
You can specify an interval in which the user can stop the publishing pipeline via her telegram.  
The bot uses RSS. If you want it to work for your site you need RSS with the same structure as luhze.de/rss.


# Build
```
docker build -t luhze-telegram-twitter-bot ./bot
```

# Run
Copy ```.env.example``` to ```.env``` and fill out the variables.
```
docker run -it -v "$(pwd)/bot:/usr/src/bot" --rm --env-file .env --name luhze-telegram-twitter-bot-running luhze-telegram-twitter-bot
```

# Telegram Bot Commands
```
/stop - Stops the publishing pipeline
```