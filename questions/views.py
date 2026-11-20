from django.http import HttpRequest
from django.shortcuts import get_object_or_404, render

from .models import Answer, Question, Tag
from .utils import paginate, render_question_list


def index(request: HttpRequest):
    return render_question_list(request, Question.queries.new(), "questions/index.html", page_title="Вопросы")


def hot(request: HttpRequest):
    return render_question_list(request, Question.queries.best(), "questions/hot.html")


def tag(request: HttpRequest, tag_name: str):
    selected_tag = get_object_or_404(Tag, name=tag_name)
    return render_question_list(request, Question.queries.by_tag(selected_tag), "questions/tag.html", tag_name=selected_tag.name)


def question(request: HttpRequest, question_id: int):
    selected = get_object_or_404(Question.queries.for_display(), pk=question_id)
    page = paginate(Answer.queries.for_question(selected), request)

    return render(request, "questions/question.html", {"question": selected, "answers": page.object_list, "page": page})


def ask(request: HttpRequest):
    return render(request, "questions/ask.html")
