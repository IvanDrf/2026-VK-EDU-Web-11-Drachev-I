from django.http import HttpRequest, HttpResponseNotFound
from django.shortcuts import render

from .utils import ANSWERS, QUESTIONS, paginate

PER_PAGE = 10


def index(request: HttpRequest):
    questions = sorted(find_answers_amount(QUESTIONS, ANSWERS), key=lambda q: q["created_at"], reverse=True)

    page = paginate(questions, request, per_page=PER_PAGE)
    return render(
        request=request,
        template_name="questions/index.html",
        context={
            "questions": page.object_list,
            "page": page,
            "page_title": "Вопросы",
            "user_authenticated": False,
        },
    )


def find_answers_amount(questions: list[dict], answers: list[dict]) -> list[dict]:
    counts: dict[int, int] = {}
    for answer in answers:
        counts[answer["question_id"]] = counts.get(answer["question_id"], 0) + 1

    return [{**question, "answers_count": counts.get(question["id"], 0)} for question in questions]


def tag(request: HttpRequest, tag_name: str):
    questions = find_answers_amount(find_questions_with_tag(QUESTIONS, tag_name), ANSWERS)

    page = paginate(questions, request, per_page=PER_PAGE)
    return render(
        request=request,
        template_name="questions/tag.html",
        context={
            "questions": page.object_list,
            "page": page,
            "tag_name": tag_name,
            "user_authenticated": False,
        },
    )


def find_questions_with_tag(questions: list[dict], tag_name: str) -> list[dict]:
    q: list[dict] = []

    for question in questions:
        if tag_name in question["tags"]:
            q.append(question)

    return q


def hot(request: HttpRequest):
    best_questions = sorted(find_answers_amount(QUESTIONS, ANSWERS), key=lambda q: q.get("votes", 0), reverse=True)

    page = paginate(best_questions, request, per_page=PER_PAGE)
    return render(
        request=request,
        template_name="questions/hot.html",
        context={
            "questions": page.object_list,
            "page": page,
            "page_title": "Лучшие вопросы",
            "user_authenticated": False,
        },
    )


def question(request: HttpRequest, question_id: int):
    q, answers = find_question_info(QUESTIONS, ANSWERS, question_id)

    if not q:
        return HttpResponseNotFound(content="вопрос с таким id не найден")

    page = paginate(answers, request, per_page=PER_PAGE)
    return render(
        request=request,
        template_name="questions/question.html",
        context={
            "question": q,
            "answers": page.object_list,
            "page": page,
            "user_authenticated": False,
        },
    )


def find_question_info(questions: list, answers: list, question_id: int) -> tuple[dict | None, list[dict]]:
    q = next((question for question in questions if question["id"] == question_id), None)
    question_answers = [answer for answer in answers if answer["question_id"] == question_id]
    if q is None:
        return None, question_answers

    return {**q, "answers_count": len(question_answers)}, question_answers


def ask(request: HttpRequest):
    return render(
        request=request,
        template_name="questions/ask.html",
        context={
            "user_authenticated": False,
        },
    )
