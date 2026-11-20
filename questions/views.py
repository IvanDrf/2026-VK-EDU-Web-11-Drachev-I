from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.decorators import json_endpoint, login_required_for_post

from .api import form_response
from .forms import AnswerForm, AnswerVoteForm, CorrectAnswerForm, QuestionForm, QuestionVoteForm
from .models import PAGE_SIZE, Answer, Question, Tag
from .utils import paginate, render_question_list


def index(request: HttpRequest):
    return render_question_list(request, Question.queries.new(request.user), "questions/index.html", page_title="Вопросы")


def hot(request: HttpRequest):
    return render_question_list(request, Question.queries.best(request.user), "questions/hot.html")


def tag(request: HttpRequest, tag_name: str):
    selected_tag = get_object_or_404(Tag, name=tag_name)
    return render_question_list(
        request, Question.queries.by_tag(selected_tag, request.user), "questions/tag.html", tag_name=selected_tag.name
    )


@login_required_for_post
@require_http_methods(["GET", "POST"])
def question(request: HttpRequest, question_id: int):
    selected = get_object_or_404(Question.queries.for_display(request.user), pk=question_id)
    form = AnswerForm(
        request.POST if request.method == "POST" else None,
        user=request.user,
        question=selected,
    )

    if request.method == "POST" and form.is_valid():
        return redirect(form.save().get_absolute_url())

    page = paginate(Answer.queries.for_question(selected, request.user), request, PAGE_SIZE)
    return render(request, "questions/question.html", {"question": selected, "answers": page.object_list, "page": page, "form": form})


@login_required
@require_http_methods(["GET", "POST"])
def ask(request: HttpRequest):
    form = QuestionForm(request.POST if request.method == "POST" else None, user=request.user)
    if request.method == "POST" and form.is_valid():
        return redirect(form.save())
    return render(request, "questions/ask.html", {"form": form})


@json_endpoint
def question_vote(request: HttpRequest, question_id: int):
    return form_response(QuestionVoteForm(request.POST, user=request.user, target_id=question_id))


@json_endpoint
def answer_vote(request: HttpRequest, answer_id: int):
    return form_response(AnswerVoteForm(request.POST, user=request.user, target_id=answer_id))


@json_endpoint
def correct_answer(request: HttpRequest, question_id: int):
    return form_response(CorrectAnswerForm(request.POST, user=request.user, question_id=question_id))
