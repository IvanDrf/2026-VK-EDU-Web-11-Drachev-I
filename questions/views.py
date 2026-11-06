from django.http import HttpRequest, HttpResponseNotFound
from django.shortcuts import render

from .utils import ANSWERS, QUESTIONS, paginate

PER_PAGE = 10


def index(request: HttpRequest):
    questions = find_answers_amount(QUESTIONS, ANSWERS)

    page = paginate(questions, request, per_page=PER_PAGE)
    return render(
        request=request,
        template_name="questions/index.html",
        context={
            "questions": page.object_list,
            "page": page,
            "page_title": "Новые вопросы",
            "user_authenticated": True,
        },
    )


def find_answers_amount(questions: list[dict], answers: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for answer in answers:
        counts[answer["question_id"]] = counts.get(answer["question_id"], 0) + 1

    for question in questions:
        question["answers_count"] = counts.get(question["id"], 0)

    return questions


def tag(request: HttpRequest, tag_name: str):
    questions = find_questions_with_tag(QUESTIONS, tag_name)

    page = paginate(questions, request, per_page=PER_PAGE)
    return render(
        request=request,
        template_name="questions/tag.html",
        context={
            "questions": page.object_list,
            "page": page,
            "tag_name": tag_name,
            "user_authenticated": True,
        },
    )


def find_questions_with_tag(questions: list[dict], tag_name: str) -> list[dict]:
    q: list[dict] = []

    for question in questions:
        if tag_name in question["tags"]:
            q.append(question)

    return q


def hot(request: HttpRequest):
    best_questions = sorted(QUESTIONS, key=lambda q: q.get("votes", 0), reverse=True)

    page = paginate(best_questions, request)
    return render(
        request=request,
        template_name="questions/index.html",
        context={
            "questions": page.object_list,
            "page": page,
            "page_title": "Новые вопросы",
            "user_authenticated": True,
        },
    )


def question(request: HttpRequest, question_id: int):
    q, answers = find_question_info(QUESTIONS, ANSWERS, question_id)

    if not q:
        return HttpResponseNotFound(content="вопрос с таким id не найден")

    return render(
        request=request,
        template_name="questions/question.html",
        context={
            "question": q,
            "answers": answers,
            "user_authenticated": True,
        },
    )


def find_question_info(questions: list, answers: list, question_id: int) -> tuple[dict | None, list[dict]]:
    answs = []
    q = None

    for question, answer in zip(questions, answers):
        if question["id"] == question_id:
            q = question

        if answer["question_id"] == question_id:
            answs.append(answer)

    if not q:
        return None, answs

    q["answers_count"] = len(answs)
    return q, answs


def ask(request: HttpRequest):
    return render(
        request=request,
        template_name="questions/ask.html",
        context={
            "user_authenticated": True,
        },
    )
