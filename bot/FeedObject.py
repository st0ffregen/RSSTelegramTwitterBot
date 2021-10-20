class FeedObject:
    def __init__(self, link, published, author, content):
        self.link = link
        self.published = published
        self.author = author
        self.content = content

    def __eq__(self, other):
        return self.link == other.link and self.published == other.published and self.author == other.author and self.content == other.content
