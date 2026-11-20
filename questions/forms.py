import re

from django import forms
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce

from core.forms import StyledFormMixin

from .models import Answer, AnswerLike, Question, QuestionLike, Tag


class QuestionForm(StyledFormMixin, forms.ModelForm):
    title = forms.CharField(
        label="Название вопроса", max_length=150, widget=forms.TextInput(attrs={"placeholder": "Например: Что лучше Django или FastAPI?"})
    )
    text = forms.CharField(
        label="Текст вопроса", max_length=10000, widget=forms.Textarea(attrs={"rows": 8, "placeholder": "Опишите ситуацию подробно"})
    )
    tags = forms.CharField(
        label="Теги",
        max_length=150,
        required=False,
        help_text="До 5 тегов через запятую.",
        widget=forms.TextInput(attrs={"placeholder": "python, django, fastapi"}),
    )

    class Meta:
        model = Question
        fields = ("title", "text", "tags")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_tags(self):
        names = list(dict.fromkeys(name.strip().casefold() for name in self.cleaned_data["tags"].split(",") if name.strip()))

        if len(names) > 5:
            raise forms.ValidationError("Укажите не больше 5 тегов.")

        if any(len(name) > 80 or not re.fullmatch(r"[\w.+#-]+", name) for name in names):
            raise forms.ValidationError("Тег: до 80 символов, буквы, цифры, _, -, +, # или точка.")
        return names

    @transaction.atomic
    def save(self, commit=True):
        question: Question = super().save(commit=False)
        question.author = self.user

        if commit:
            question.save()
            tags = [Tag.objects.get_or_create(name=name)[0] for name in self.cleaned_data["tags"]]
            question.tags.set(tags)

        return question


class AnswerForm(StyledFormMixin, forms.ModelForm):
    text = forms.CharField(
        label="Текст ответа", max_length=10000, widget=forms.Textarea(attrs={"rows": 6, "placeholder": "Напишите ответ подробно"})
    )

    class Meta:
        model = Answer
        fields = ("text",)

    def __init__(self, *args, user, question, **kwargs):
        super().__init__(*args, **kwargs)
        self.user, self.question = user, question

    def save(self, commit=True):
        answer: Answer = super().save(commit=False)

        answer.author, answer.question = self.user, self.question
        if commit:
            answer.save()

        return answer


class VoteForm(forms.Form):
    like_model: type[QuestionLike] | type[AnswerLike]
    target_field: str
    value = forms.TypedChoiceField(choices=((1, "Лайк"), (-1, "Дизлайк")), coerce=int)
    error_status = 400

    def __init__(self, data=None, *, user, target_id, **kwargs):
        data = data.copy() if data is not None else {}
        data["target"] = target_id
        super().__init__(data, **kwargs)
        self.user = user

    @transaction.atomic
    def save(self):
        target = self.cleaned_data["target"]
        target = type(target).objects.select_for_update().get(pk=target.pk)

        lookup = {self.target_field: target, "user": self.user}
        vote, created = self.like_model.objects.get_or_create(**lookup, defaults={"value": self.cleaned_data["value"]})
        if not created:
            if vote.value == self.cleaned_data["value"]:
                raise forms.ValidationError("Такая оценка уже поставлена.", code="duplicate_vote")

            vote.value = self.cleaned_data["value"]
            vote.save(update_fields=["value"])

        rating = self.like_model.objects.filter(**{self.target_field: target}).aggregate(total=Coalesce(Sum("value"), 0))["total"]

        return {"rating": rating, "user_vote": vote.value}


class QuestionVoteForm(VoteForm):
    target = forms.ModelChoiceField(queryset=Question.objects.all())
    like_model = QuestionLike
    target_field = "question"


class AnswerVoteForm(VoteForm):
    target = forms.ModelChoiceField(queryset=Answer.objects.all())
    like_model = AnswerLike
    target_field = "answer"


class CorrectAnswerForm(forms.Form):
    question = forms.ModelChoiceField(queryset=Question.objects.all())
    answer = forms.ModelChoiceField(queryset=Answer.objects.all())
    is_correct = forms.TypedChoiceField(choices=(("true", "Да"), ("false", "Нет")), coerce=lambda value: value == "true")
    error_status = 400

    def __init__(self, data=None, *, user, question_id, **kwargs):
        data = data.copy() if data is not None else {}
        data["question"] = question_id
        super().__init__(data, **kwargs)
        self.user = user

    def clean(self):
        data = super().clean()
        question, answer = data.get("question"), data.get("answer")

        if question and question.author_id != self.user.pk:
            self.error_status = 403
            raise forms.ValidationError("Только автор вопроса может выбирать правильный ответ.")

        if question and answer and answer.question_id != question.pk:
            raise forms.ValidationError("Этот ответ относится к другому вопросу.")

        return data

    @transaction.atomic
    def save(self):
        question = Question.objects.select_for_update().get(pk=self.cleaned_data["question"].pk)
        if question.author_id != self.user.pk:
            raise forms.ValidationError("Только автор вопроса может выбирать правильный ответ.", code="forbidden")

        answer = Answer.objects.select_for_update().get(pk=self.cleaned_data["answer"].pk, question=question)
        answer.is_correct = self.cleaned_data["is_correct"]
        answer.save(update_fields=["is_correct"])

        return {"question_id": question.pk, "answer_id": answer.pk, "is_correct": answer.is_correct}
