class TweetObject:
    def __init__(self, teaser, link, imageUrl, imageCredit, pathToImage):
        self.teaser = teaser
        self.link = link
        self.imageUrl = imageUrl
        self.imageCredit = imageCredit
        self.pathToImage = pathToImage

    def __eq__(self, other):
        return self.link == other.link and self.link == other.link and self.imageUrl == other.imageUrl and self.imageCredit == other.imageCredit and self.pathToImage == other.pathToImage
