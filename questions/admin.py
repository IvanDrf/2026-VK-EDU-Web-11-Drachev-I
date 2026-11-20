from collections.abc import Mapping

from django.contrib import admin
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.contrib.auth.models import User
from django.forms.models import BaseInlineFormSet
from django.urls import reverse

from .models import Answer, AnswerLike, Question, QuestionLike, Tag, related_count


class LikesCountMixin:
    @admin.display(description="Лайки", ordering="_likes_count")
    def likes_count(self, obj):
        return obj._likes_count


class LikesCountAdmin(LikesCountMixin, admin.ModelAdmin):
    like_model: type[QuestionLike] | type[AnswerLike]
    like_field: str

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _likes_count=related_count(self.like_model, self.like_field, value=1)
        )


class CachedAuthorWidget(ForeignKeyRawIdWidget):
    def __init__(self, *args, authors: Mapping[str, User], **kwargs):
        super().__init__(*args, **kwargs)
        self.authors = authors

    def label_and_url_for_value(self, value):
        author = self.authors.get(str(value))
        if author is None:
            return super().label_and_url_for_value(value)
        return str(author), reverse("admin:auth_user_change", args=[author.pk])


class AnswerInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.authors: dict[str, User] = {str(answer.author_id): answer.author for answer in self.get_queryset()}

    def add_fields(self, form, index):
        super().add_fields(form, index)
        original = form.fields["author"].widget
        widget = CachedAuthorWidget(original.rel, original.admin_site, using=original.db, authors=self.authors)
        form.fields["author"].widget = widget


class AnswerInline(LikesCountMixin, admin.TabularInline):
    model = Answer
    fields = ("author", "text", "likes_count", "is_correct", "created_at")
    readonly_fields = ("likes_count",)
    raw_id_fields = ("author",)
    extra = 0
    show_change_link = True
    formset = AnswerInlineFormSet

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("author").annotate(
            _likes_count=related_count(AnswerLike, "answer_id", value=1)
        )


class TagUsageFilter(admin.SimpleListFilter):
    title = "Использование"
    parameter_name = "used"

    def lookups(self, request, model_admin):
        return (("yes", "Есть вопросы"), ("no", "Нет вопросов"))

    def queryset(self, request, queryset):
        if self.value() in {"yes", "no"}:
            return queryset.filter(questions__isnull=self.value() == "no").distinct()
        return queryset


@admin.register(Question)
class QuestionAdmin(LikesCountAdmin):
    like_model = QuestionLike
    like_field = "question_id"
    list_display = ("id", "title", "author", "likes_count", "answers_count", "correct_answers_count", "created_at")
    search_fields = ("title", "text", "author__username", "author__first_name", "author__last_name", "author__email")
    search_help_text = "Поиск по заголовку, тексту, логину, имени, фамилии или email автора."
    list_filter = ("created_at",)
    raw_id_fields = ("author", "tags")
    list_select_related = ("author",)
    inlines = (AnswerInline,)
    show_full_result_count = False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _answers_count=related_count(Answer, "question_id"),
            _correct_answers_count=related_count(Answer, "question_id", is_correct=True),
        )

    @admin.display(description="Количество ответов", ordering="_answers_count")
    def answers_count(self, obj):
        return obj._answers_count

    @admin.display(description="Правильных ответов", ordering="_correct_answers_count")
    def correct_answers_count(self, obj):
        return obj._correct_answers_count


@admin.register(Answer)
class AnswerAdmin(LikesCountAdmin):
    like_model = AnswerLike
    like_field = "answer_id"
    list_display = ("id", "question", "author", "likes_count", "is_correct", "created_at")
    search_fields = ("text", "question__title", "author__username", "author__first_name", "author__last_name", "author__email")
    search_help_text = "Поиск по тексту ответа, заголовку вопроса, логину, имени, фамилии или email автора."
    list_filter = ("is_correct", "created_at")
    list_select_related = ("question", "author")
    raw_id_fields = ("question", "author")
    show_full_result_count = False


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    list_filter = (TagUsageFilter,)


@admin.register(QuestionLike)
class QuestionLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "question", "value", "created_at")
    search_fields = ("user__username", "question__title")
    list_filter = ("value", "created_at")
    list_select_related = ("user", "question")
    raw_id_fields = ("user", "question")
    show_full_result_count = False


@admin.register(AnswerLike)
class AnswerLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "answer", "value", "created_at")
    search_fields = ("user__username", "answer__text")
    list_filter = ("value", "created_at")
    list_select_related = ("user", "answer")
    raw_id_fields = ("user", "answer")
    show_full_result_count = False
