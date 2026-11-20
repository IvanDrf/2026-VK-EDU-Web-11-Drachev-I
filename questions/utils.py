from django.core.paginator import EmptyPage, Page, PageNotAnInteger, Paginator
from django.http import HttpRequest
from django.shortcuts import render

from .models import Question, Tag


def render_question_list(request: HttpRequest, queryset, template, **context):
    page = paginate(queryset, request)
    return render(request, template, {"questions": page.object_list, "page": page, **context})


def pagination_pages(page: Page) -> list[int | str]:
    last = page.paginator.num_pages
    if last <= 10:
        return list(range(1, last + 1))

    start = max(2, min(page.number - 4, last - 8))
    stop = start + 8

    numbers: list[int | str] = [1]
    if start > 2:
        numbers.append("…")
    numbers.extend(range(start, stop))

    if stop < last:
        numbers.append("…")

    numbers.append(last)
    return numbers


class PaginationPage(Page):
    @property
    def page_numbers(self) -> list[int | str]:
        return pagination_pages(self)


def paginate(objects_list, request: HttpRequest, per_page=10) -> PaginationPage:
    paginator = Paginator(objects_list, per_page)
    try:
        page = paginator.page(request.GET.get("page", 1))
    except (PageNotAnInteger, EmptyPage):
        page = paginator.page(1)

    return PaginationPage(page.object_list, page.number, paginator)


def count_most_popular_tags(request: HttpRequest):
    return {"popular_tags": Tag.queries.popular(), "best_members": Question.queries.best_authors()}
