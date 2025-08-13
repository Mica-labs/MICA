from datetime import date
import random

books = {
    "The Time Traveler's Diary": {
        "genre": "Fiction",
        "description": "A man discovers a journal that allows him to revisit moments in history and rewrite fate.",
        "rating": 4.5,
    },
    "Quantum Realities": {
        "genre": "Science",
        "description": "An accessible explanation of quantum physics and its implications for reality.",
        "rating": 4.2,
    },
    "The Dragon's Pact": {
        "genre": "Fantasy",
        "description": "A young mage forms a forbidden alliance with a dragon to save her crumbling kingdom.",
        "rating": 4.7,
    },
    "Deep Work": {
        "genre": "Non-fiction",
        "description": "Guidance on how to focus in a distracted world and achieve meaningful productivity.",
        "rating": 4.6,
    },
    "The Memory Garden": {
        "genre": "Fiction",
        "description": "An elderly woman tends a magical garden where forgotten memories bloom anew.",
        "rating": 4.4,
    },
    "AI and the Future of Thinking": {
        "genre": "Science",
        "description": "Explores how artificial intelligence is transforming the way humans reason and solve problems.",
        "rating": 4.3,
    },
    "The Last Enchanter": {
        "genre": "Fantasy",
        "description": "An orphan discovers he’s the final heir to an ancient magical order and must fight dark forces.",
        "rating": 4.6,
    },
    "Atomic Habits": {
        "genre": "Non-fiction",
        "description": "A proven system for building good habits and breaking bad ones.",
        "rating": 4.9,
    },
    "The Paper City": {
        "genre": "Fiction",
        "description": "In a crumbling metropolis made of paper, a journalist uncovers a conspiracy that could ignite a revolution.",
        "rating": 4.3,
    },
    "The Moonstone Tower": {
        "genre": "Fantasy",
        "description": "A knight seeks a legendary tower that grants wishes—but only at a cost.",
        "rating": 4.1,
    },
}

def get_date():
    today = date.today()
    formatted = today.strftime("%Y-%m-%d")
    return [{"status": "success"},
           {"arg": "today", "value": formatted}]

def query_book_genre(book_name):
    genres = ["Fiction", "Non-fiction", "Fantasy", "Science"]
    genre = random.choice(genres)
    if books.get(book_name):
        genre = books.get(book_name)['genre']
    print(f"The genre is : {genre}")
    return [{"arg": "genre", "value": genre}]

def find_bestsellers(genre = None):
    """If a specific genre is given, the function returns the best-selling book description in that genre; 
    otherwise, it returns the overall best-seller.
    """
    cand = []
    bestseller = {}
    if genre is not None:
        for name, info in books.items():
            if info["genre"].lower() == genre.strip().lower():
                cand.append({"name": name, "info": info})
    else:
        for name, info in books.items():
            cand.append({"name": name, "info": info})
    sorted_cand = sorted(cand, key=lambda x: x["info"]["rating"], reverse=True)
    bestseller = sorted_cand[0]
    print(f"The bestseller is: {bestseller['name']}, the description: {bestseller['info']['description']}")
    return [{"arg": "book_info", "value": bestseller['info']['description']},
           {"arg": "book_name", "value": bestseller["name"]}]
  
def place_order(ordered_book, date):
    return [{"bot": "Okay, your order is all set!"},
           {"arg": "status", "value": True}]