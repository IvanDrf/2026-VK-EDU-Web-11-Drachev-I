from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("tag/<str:tag_name>/", views.tag, name="tag"),
    path("question/<int:question_id>/", views.question, name="question"),
    path("ask/", views.ask, name="ask"),
    path("hot/", views.hot, name="hot"),
    path("api/questions/<int:question_id>/vote/", views.question_vote, name="question_vote"),
    path("api/answers/<int:answer_id>/vote/", views.answer_vote, name="answer_vote"),
    path("api/questions/<int:question_id>/correct-answer/", views.correct_answer, name="correct_answer"),
]
