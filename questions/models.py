from __future__ import annotations

from typing import cast

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone


def related_count(model: type[models.Model], field: str, **filters):
    counts = model.objects.filter(**{field: OuterRef("pk")}, **filters).order_by().values(field).annotate(n=Count("pk"))

    return Coalesce(Subquery(counts.values("n"), output_field=IntegerField()), 0)


class TagQuerySet(models.QuerySet["Tag"]):
    def popular(self) -> TagQuerySet:
        return self.annotate(count=Count("questions")).order_by("-count", "name")[:10]


class TagManager(models.Manager["Tag"]):
    _queryset_class = TagQuerySet

    def get_queryset(self) -> TagQuerySet:
        return cast(TagQuerySet, super().get_queryset())

    def popular(self) -> TagQuerySet:
        return self.get_queryset().popular()


class Tag(models.Model):
    name = models.CharField("Название", max_length=80, unique=True)
    objects = models.Manager()
    queries: TagManager = TagManager()

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ("name",)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tag", args=[self.name])


class QuestionQuerySet(models.QuerySet["Question"]):
    def for_display(self) -> QuestionQuerySet:
        return (
            self.select_related("author__profile")
            .prefetch_related("tags")
            .annotate(
                answers_count=related_count(Answer, "question_id"),
                votes=related_count(QuestionLike, "question_id"),
            )
        )

    def new(self) -> QuestionQuerySet:
        return self.for_display().order_by("-created_at", "-pk")

    def best(self) -> QuestionQuerySet:
        return self.for_display().order_by("-votes", "-created_at", "-pk")

    def by_tag(self, tag: Tag) -> QuestionQuerySet:
        return self.new().filter(tags=tag)


class QuestionManager(models.Manager["Question"]):
    _queryset_class = QuestionQuerySet

    def get_queryset(self) -> QuestionQuerySet:
        return cast(QuestionQuerySet, super().get_queryset())

    def for_display(self) -> QuestionQuerySet:
        return self.get_queryset().for_display()

    def new(self) -> QuestionQuerySet:
        return self.get_queryset().new()

    def best(self) -> QuestionQuerySet:
        return self.get_queryset().best()

    def by_tag(self, tag: Tag) -> QuestionQuerySet:
        return self.get_queryset().by_tag(tag)

    def best_authors(self):
        return get_user_model().objects.annotate(
            points=related_count(QuestionLike, "question__author_id")
            + related_count(AnswerLike, "answer__author_id")
        ).order_by("-points", "username")[:3]


class Question(models.Model):
    title = models.CharField("Заголовок", max_length=255)
    text = models.TextField("Текст")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questions", verbose_name="Автор")
    tags = models.ManyToManyField(Tag, related_name="questions", verbose_name="Теги", blank=True)
    created_at = models.DateTimeField("Дата создания", default=timezone.now)
    objects = models.Manager()
    queries: QuestionManager = QuestionManager()

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        ordering = ("-created_at", "-pk")
        indexes = (models.Index(fields=["-created_at", "-id"]),)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("question", args=[self.pk])


class AnswerQuerySet(models.QuerySet["Answer"]):
    def for_question(self, question: Question) -> AnswerQuerySet:
        return (
            self.filter(question=question)
            .select_related("author__profile")
            .annotate(votes=related_count(AnswerLike, "answer_id"))
            .order_by("created_at", "pk")
        )


class AnswerManager(models.Manager["Answer"]):
    _queryset_class = AnswerQuerySet

    def get_queryset(self) -> AnswerQuerySet:
        return cast(AnswerQuerySet, super().get_queryset())

    def for_question(self, question: Question) -> AnswerQuerySet:
        return self.get_queryset().for_question(question)


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers", verbose_name="Вопрос")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answers", verbose_name="Автор")
    text = models.TextField("Текст")
    created_at = models.DateTimeField("Дата создания", default=timezone.now)
    is_correct = models.BooleanField("Правильный ответ", default=False)
    objects = models.Manager()
    queries: AnswerManager = AnswerManager()

    class Meta:
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"
        ordering = ("created_at", "pk")
        indexes = (models.Index(fields=["question", "created_at", "id"]),)

    def __str__(self):
        return self.text[:80]

    def get_absolute_url(self):
        return self.question.get_absolute_url() + "#answers"


class QuestionLike(models.Model):
    user_id: int
    question_id: int

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="question_likes", verbose_name="Пользователь")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="likes", verbose_name="Вопрос")
    created_at = models.DateTimeField("Дата оценки", default=timezone.now)

    class Meta:
        verbose_name = "Лайк вопроса"
        verbose_name_plural = "Лайки вопросов"
        unique_together = (("question", "user"),)

    def __str__(self):
        return f"{self.user_id} -> {self.question_id}"


class AnswerLike(models.Model):
    user_id: int
    answer_id: int

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answer_likes", verbose_name="Пользователь")
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="likes", verbose_name="Ответ")
    created_at = models.DateTimeField("Дата оценки", default=timezone.now)

    class Meta:
        verbose_name = "Лайк ответа"
        verbose_name_plural = "Лайки ответов"
        unique_together = (("answer", "user"),)

    def __str__(self):
        return f"{self.user_id} -> {self.answer_id}"
