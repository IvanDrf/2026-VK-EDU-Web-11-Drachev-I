from __future__ import annotations

from typing import cast

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone


def related_count(model: type[models.Model], field: str, **filters):
    counts = model.objects.filter(**{field: OuterRef("pk")}, **filters).order_by().values(field).annotate(n=Count("pk"))

    return Coalesce(Subquery(counts.values("n"), output_field=IntegerField()), 0)


def related_rating(model: type[models.Model], field: str):
    ratings = model.objects.filter(**{field: OuterRef("pk")}).order_by().values(field).annotate(n=Sum("value"))
    return Coalesce(Subquery(ratings.values("n"), output_field=IntegerField()), 0)


def current_vote(model: type[models.Model], field: str, user):
    if user is None or not user.is_authenticated:
        return Value(0, output_field=IntegerField())
    votes = model.objects.filter(**{field: OuterRef("pk")}, user=user).values("value")[:1]
    return Coalesce(Subquery(votes, output_field=IntegerField()), 0)


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
    def for_display(self, user=None) -> QuestionQuerySet:
        return (
            self.select_related("author__profile")
            .prefetch_related("tags")
            .annotate(
                answers_count=related_count(Answer, "question_id"),
                votes=related_rating(QuestionLike, "question_id"),
                user_vote=current_vote(QuestionLike, "question_id", user),
            )
        )

    def new(self, user=None) -> QuestionQuerySet:
        return self.for_display(user).order_by("-created_at", "-pk")

    def best(self, user=None) -> QuestionQuerySet:
        return self.for_display(user).order_by("-votes", "-created_at", "-pk")

    def by_tag(self, tag: Tag, user=None) -> QuestionQuerySet:
        return self.new(user).filter(tags=tag)


class QuestionManager(models.Manager["Question"]):
    _queryset_class = QuestionQuerySet

    def get_queryset(self) -> QuestionQuerySet:
        return cast(QuestionQuerySet, super().get_queryset())

    def for_display(self, user=None) -> QuestionQuerySet:
        return self.get_queryset().for_display(user)

    def new(self, user=None) -> QuestionQuerySet:
        return self.get_queryset().new(user)

    def best(self, user=None) -> QuestionQuerySet:
        return self.get_queryset().best(user)

    def by_tag(self, tag: Tag, user=None) -> QuestionQuerySet:
        return self.get_queryset().by_tag(tag, user)

    def best_authors(self):
        return (
            get_user_model()
            .objects.annotate(points=related_rating(QuestionLike, "question__author_id") + related_rating(AnswerLike, "answer__author_id"))
            .order_by("-points", "username")[:3]
        )


class Question(models.Model):
    author_id: int

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

    def get_vote_url(self):
        return reverse("question_vote", args=[self.pk])


class AnswerQuerySet(models.QuerySet["Answer"]):
    def for_question(self, question: Question, user=None) -> AnswerQuerySet:
        return (
            self.filter(question=question)
            .select_related("author__profile")
            .annotate(votes=related_rating(AnswerLike, "answer_id"), user_vote=current_vote(AnswerLike, "answer_id", user))
            .order_by("created_at", "pk")
        )


class AnswerManager(models.Manager["Answer"]):
    _queryset_class = AnswerQuerySet

    def get_queryset(self) -> AnswerQuerySet:
        return cast(AnswerQuerySet, super().get_queryset())

    def for_question(self, question: Question, user=None) -> AnswerQuerySet:
        return self.get_queryset().for_question(question, user)


PAGE_SIZE = 10


class Answer(models.Model):
    question_id: int
    author_id: int

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
        position = (
            Answer.objects.filter(question_id=self.question_id)
            .filter(Q(created_at__lt=self.created_at) | Q(created_at=self.created_at, pk__lte=self.pk))
            .count()
        )
        page = (position - 1) // PAGE_SIZE + 1
        return f"{reverse('question', args=[self.question_id])}?page={page}#answer-{self.pk}"

    def get_vote_url(self):
        return reverse("answer_vote", args=[self.pk])


class QuestionLike(models.Model):
    user_id: int
    question_id: int

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="question_likes", verbose_name="Пользователь")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="likes", verbose_name="Вопрос")
    created_at = models.DateTimeField("Дата оценки", default=timezone.now)
    value = models.SmallIntegerField("Оценка", choices=((1, "Лайк"), (-1, "Дизлайк")), default=1)

    class Meta:
        verbose_name = "Лайк вопроса"
        verbose_name_plural = "Лайки вопросов"
        unique_together = (("question", "user"),)
        constraints = (models.CheckConstraint(condition=Q(value__in=[-1, 1]), name="question_like_valid_value"),)

    def __str__(self):
        return f"{self.user_id} -> {self.question_id}"


class AnswerLike(models.Model):
    user_id: int
    answer_id: int

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answer_likes", verbose_name="Пользователь")
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="likes", verbose_name="Ответ")
    created_at = models.DateTimeField("Дата оценки", default=timezone.now)
    value = models.SmallIntegerField("Оценка", choices=((1, "Лайк"), (-1, "Дизлайк")), default=1)

    class Meta:
        verbose_name = "Лайк ответа"
        verbose_name_plural = "Лайки ответов"
        unique_together = (("answer", "user"),)
        constraints = (models.CheckConstraint(condition=Q(value__in=[-1, 1]), name="answer_like_valid_value"),)

    def __str__(self):
        return f"{self.user_id} -> {self.answer_id}"
