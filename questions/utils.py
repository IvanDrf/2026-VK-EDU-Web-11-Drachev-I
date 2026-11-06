from random import randint

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpRequest


def paginate(objects_list, request: HttpRequest, per_page=10):
    paginator = Paginator(objects_list, per_page)
    page_number = request.GET.get("page", 1)

    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    return page


AUTHORS = ["IvanDrf", "Vanek1", "Vanek2", "Vanek3", "Vanek4"]
TAGS_POOL = ["python", "django", "fastapi", "backend", "docker", "postgresql", "html", "css", "git"]


def count_most_popular_tags(request: HttpRequest):
    tags: dict[str, int] = {}
    for question in QUESTIONS:
        for tag in question["tags"]:
            tags[tag] = tags.get(tag, 0) + 1

    return {"popular_tags": [{"name": name, "count": count} for name, count in tags.items()]}


def generate_questions(count: int) -> list[dict]:
    questions: list[dict] = []

    for i in range(1, count + 1):
        questions.append(
            {
                "id": i,
                "title": f"Заголовок вопроса #{i}",
                "text": (
                    f"Текст вопроса #{i}. Lorem ipsum dolor sit amet, consectetur "
                    f"adipiscing elit, sed do eiusmod tempor incididunt ut labore."
                ),
                "author": AUTHORS[i % len(AUTHORS)],
                "votes": (i * 3) % 20 + 1,
                "tags": TAGS_POOL[: (i % 3) + 1],
                "created_at": f"{10 + i % 12} окт 2026, {10 + i % 12}:{i % 60:02d}",
            }
        )

    return questions


def generate_answers(count: int) -> list[dict]:
    answers: list[dict] = []

    for i in range(1, count + 1):
        answers.append(
            {
                "id": i,
                "question_id": randint(1, count),
                "text": (f"Ответ #{i}. Lorem Ipsum is simply dummy text of the printing and typesetting industry."),
                "author": ["MariaK", "PavelDev", "AnnaS"][i % 3],
                "votes": (i * 4) % 15 + 1,
                "created_at": f"11 окт 2026, {15 + i}:10",
            }
        )

    return answers


QUESTIONS = generate_questions(30)
ANSWERS = generate_answers(30)
