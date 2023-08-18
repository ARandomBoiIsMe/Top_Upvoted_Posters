import logging
from utilities import config_util, reddit_util
import prawcore
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-$d %H:%M:%S',
    filename="run.log"
)

config = config_util.load_config()
reddit = reddit_util.initialize_reddit(config)
number_of_posters = int(config['VARS']['NUMBER_OF_POSTERS'])
timeframe = config['VARS']['TIMEFRAME']
timerange = int(config['VARS']['TIMERANGE'])

def main():
    subreddit_name = config['VARS']['SUBREDDIT']
    subreddit = validate_subreddit(reddit, subreddit_name)
    if not subreddit_name:
        logging.error(f"Subreddit does not exist: r/{subreddit_name}.")
        exit()

    # if not subreddit.user_is_moderator:
    #     logging.error(f"You must be a mod in this sub: r/{subreddit_name}.")
    #     exit()

    previous_posts = get_previous_posts(subreddit)

    post_authors = generate_author_karma_count(previous_posts)
    
    create_post(subreddit, post_authors)

    logging.debug(f"Done running. Exiting.")

def validate_subreddit(reddit, subreddit_name):
    if subreddit_name.strip() == '' or subreddit_name is None:
        return None
    
    try:
        return reddit.subreddits.search_by_name(subreddit_name, exact=True)[0]
    except prawcore.exceptions.NotFound:
        return None
    
def get_previous_posts(subreddit):
    print("Getting previous posts...")

    posts = subreddit.new()

    # Generates time range to search for posts
    time_range = None
    if timeframe.lower() == 'w':
        time_range = timedelta(weeks=timerange)
    elif timeframe.lower() == 'm':
        time_range = relativedelta(months=timerange)
    else:
        logging.error("The inputted timeframe is not supported. Please use either weeks or months.")
        exit()
    
    # Filters out posts not in that range
    filtered_posts = []
    for post in posts:
        post_creation_date = datetime.fromtimestamp(post.created_utc)
        if (post_creation_date > (datetime.today() - time_range)):
            filtered_posts.append(post)
        else:
            break
    
    return filtered_posts

def generate_author_karma_count(posts):
    logging.debug("Sorting users based on post karma count.")
    
    author_karma_count = {}

    # Get authors of all posts
    for post in posts:
        if post.author is None:
            continue

        # Map karma values to authors, increasing values for cases of posts with the same author
        if post.author in author_karma_count:
            author_karma_count[post.author] += post.score
        else:
            author_karma_count[post.author] = 0
    
    # Sort author karma counts from highest to lowest
    return sorted(author_karma_count.items(), key=lambda x: x[1], reverse=True)

def create_post(subreddit, post_authors):
    global number_of_posters

    # Ensures that the actual number of posters is used, to avoid errors
    if (number_of_posters > len(post_authors)):
        number_of_posters = len(post_authors)

    title = None
    if timeframe.lower() == 'w':
        if timerange == 1:
            title = f"Top {number_of_posters} Posters of the past week."
        else:
            title = f"Top {number_of_posters} Posters of the past {timerange} weeks."
    elif timeframe.lower() == 'm':
        if timerange == 1:
            title = f"Top {number_of_posters} Posters of the past month."
        else:
            title = f"Top {number_of_posters} Posters of the past {timerange} months."

    # Builds the post body with the top N posters
    body = ""
    i = 1
    for author in post_authors:
        if i > number_of_posters:
            break

        body += f"{i}. {author[0]} - {author[1]} upvotes.\n"
        i += 1

    subreddit.submit(
        title=title,
        selftext=body
    )

if __name__ == "__main__":
    main()