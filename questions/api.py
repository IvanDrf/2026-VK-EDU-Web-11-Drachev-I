from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse

from questions.forms import CorrectAnswerForm, VoteForm


def form_response(form: VoteForm | CorrectAnswerForm):
    if form.is_valid():
        try:
            return JsonResponse(form.save())
        except ObjectDoesNotExist:
            return JsonResponse({"error": "Объект не найден."}, status=404)

        except ValidationError as error:
            form.add_error(None, error)
            form.error_status = {"duplicate_vote": 409, "forbidden": 403}.get(error.code or "", 400)

    return JsonResponse({"errors": form.errors.get_json_data()}, status=form.error_status)
