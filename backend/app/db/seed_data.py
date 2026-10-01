"""Small curated development fixture, not a claim about an actual library's holdings."""

CATEGORIES = {
    "Programming": "Software design, programming languages and practical development.",
    "Artificial Intelligence": "Intelligent systems, reasoning and AI applications.",
    "Machine Learning": "Learning from data, supervised learning and statistical models.",
    "History": "People, societies and historical change, including Kazakhstan.",
    "Fiction": "Novels and stories exploring human experience.",
    "Psychology": "Human behavior, decisions, learning and habits.",
    "Business": "Entrepreneurship, organizations and management.",
    "Science": "Scientific methods, discoveries and explanations of nature.",
    "Philosophy": "Ethics, knowledge and reflection on life.",
    "Biography": "The lives and experiences of notable people.",
}

# Edition-specific ISBN/page counts are deliberately absent, not invented.
BOOKS = [
    (
        "Абай жолы",
        "Мұхтар Әуезов",
        "kk",
        1942,
        ("Fiction", "History"),
        "Абайдың өмірі мен қазақ қоғамының өзгерістерін суреттейтін тарихи роман.",
    ),
    (
        "Clean Code",
        "Robert C. Martin",
        "en",
        2008,
        ("Programming",),
        "Practical discussion of readable code, small functions, testing and software maintenance.",
    ),
    (
        "Python Crash Course",
        "Eric Matthes",
        "en",
        2015,
        ("Programming",),
        "An introduction to Python syntax and programming through practical projects.",
    ),
    (
        "Deep Learning with Python",
        "François Chollet",
        "en",
        2017,
        ("Artificial Intelligence", "Machine Learning", "Programming"),
        "Introduces neural networks, model training and practical deep learning with Python.",
    ),
    (
        "Қара сөздер",
        "Абай Құнанбайұлы",
        "kk",
        None,
        ("Philosophy",),
        "Білім, еңбек, мінез және адамгершілік туралы ойлар жинағы.",
    ),
    (
        "Война и мир",
        "Лев Толстой",
        "ru",
        1869,
        ("Fiction", "History"),
        "Роман о семьях, войне и общественных переменах в России начала XIX века.",
    ),
    (
        "Преступление и наказание",
        "Фёдор Достоевский",
        "ru",
        1866,
        ("Fiction", "Psychology"),
        "Роман об ответственности, нравственном выборе и последствиях преступления.",
    ),
    (
        "Atomic Habits",
        "James Clear",
        "en",
        2018,
        ("Psychology",),
        "Explores how small repeated actions and the surrounding environment influence habits.",
    ),
    (
        "The Lean Startup",
        "Eric Ries",
        "en",
        2011,
        ("Business",),
        (
            "Discusses testing business assumptions, customer feedback and "
            "iterative product development."
        ),
    ),
    (
        "A Brief History of Time",
        "Stephen Hawking",
        "en",
        1988,
        ("Science",),
        "An accessible introduction to cosmology, space, time and black holes.",
    ),
    (
        "The Republic",
        "Plato",
        "en",
        None,
        ("Philosophy",),
        "A philosophical dialogue about justice, education and the organization of society.",
    ),
    (
        "Steve Jobs",
        "Walter Isaacson",
        "en",
        2011,
        ("Biography", "Business"),
        "A biography examining the life, creative work and management of Steve Jobs.",
    ),
]
