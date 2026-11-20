from collections.abc import Iterator
from datetime import timedelta
from itertools import islice
from random import Random
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.utils import timezone
from faker import Faker

from core.models import Profile
from questions.models import Answer, AnswerLike, Question, QuestionLike, Tag


def generate_like_pairs(target_ids: list[int], user_ids: list[int], count: int, rng: Random) -> Iterator[tuple[int, int]]:
    if not 0 <= count <= len(target_ids) * len(user_ids):
        raise ValueError("Количество лайков превышает число уникальных пар")

    targets = target_ids.copy()
    rng.shuffle(targets)
    remaining = count
    for index, target_id in enumerate(targets):
        targets_left = len(targets) - index

        minimum = max(0, remaining - (targets_left - 1) * len(user_ids))
        average_ceiling = (remaining + targets_left - 1) // targets_left
        maximum = min(len(user_ids), remaining, 2 * average_ceiling)

        target_count = rng.randint(minimum, maximum)
        for user_id in rng.sample(user_ids, target_count):
            yield target_id, user_id

        remaining -= target_count


class Command(BaseCommand):
    help = "Добавить ratio пользователей и тегов, 10x вопросов, 100x ответов, 200x лайков."

    def add_arguments(self, parser):
        parser.add_argument("ratio", type=int)
        parser.add_argument("--batch-size", type=int, default=5000)
        parser.add_argument("--seed", type=int, default=42)

    def create_batches(self, model: models.Model, objects, batch_size):
        iterator = iter(objects)
        ids = []

        while batch := list(islice(iterator, batch_size)):
            created = model.objects.bulk_create(batch, batch_size=batch_size)
            ids.extend(obj.pk for obj in created)

        self.stdout.write(f"{model._meta.verbose_name_plural}: {len(ids)}")

        return ids

    def handle(self, *args, **options):
        ratio, batch_size = options["ratio"], options["batch_size"]
        if ratio < 2:
            raise CommandError("ratio должен быть >= 2: при ratio=1 невозможно создать 200 уникальных лайков.")

        if batch_size < 1:
            raise CommandError("batch-size должен быть положительным.")

        fake = Faker("ru_RU")
        fake.seed_instance(options["seed"])
        rng = Random(options["seed"])
        namespace = uuid4().hex[:12]

        now = timezone.now()
        titles = [fake.sentence(nb_words=8).rstrip(".") for _ in range(512)]
        texts = [fake.paragraph(nb_sentences=3) for _ in range(512)]

        words = [fake.word() for _ in range(512)]
        create = lambda model, objects: self.create_batches(model, objects, batch_size)

        with transaction.atomic():
            User = get_user_model()
            users = create(
                User,
                (
                    User(
                        username=f"demo_{namespace}_{i}",
                        email=f"{namespace}.{i}@example.com",
                        first_name=fake.first_name(),
                        last_name=fake.last_name(),
                        password="!",
                    )
                    for i in range(ratio)
                ),
            )

            create(Profile, (Profile(user_id=user) for user in users))
            tags = create(Tag, (Tag(name=f"{words[i % 512]}-{namespace}-{i}") for i in range(ratio)))
            questions = create(
                Question,
                (
                    Question(
                        title=f"{titles[i % 512]}? №{i + 1}",
                        text=texts[i % 512],
                        author_id=users[i % ratio],
                        created_at=now - timedelta(minutes=ratio * 10 - i),
                    )
                    for i in range(ratio * 10)
                ),
            )

            through = Question.tags.through
            create(
                through,
                (
                    through(question_id=question_id, tag_id=tags[(i + offset) % ratio])
                    for i, question_id in enumerate(questions)
                    for offset in range(min(3, ratio))
                ),
            )

            featured_question = questions[min(34, len(questions) - 1)]
            answers = create(
                Answer,
                (
                    Answer(
                        question_id=featured_question if i < 25 else questions[(i - 25) % len(questions)],
                        author_id=users[(i + 1) % ratio],
                        text=f"{texts[(i + 17) % 512]} ({i + 1})",
                        is_correct=i == 0,
                        created_at=now + timedelta(seconds=i),
                    )
                    for i in range(ratio * 100)
                ),
            )

            question_likes = min(ratio * 100, len(questions) * len(users) // 2)
            create(
                QuestionLike,
                (
                    QuestionLike(question_id=question_id, user_id=user_id, created_at=now)
                    for question_id, user_id in generate_like_pairs(questions, users, question_likes, rng)
                ),
            )
            create(
                AnswerLike,
                (
                    AnswerLike(answer_id=answer_id, user_id=user_id, created_at=now)
                    for answer_id, user_id in generate_like_pairs(answers, users, ratio * 200 - question_likes, rng)
                ),
            )

        self.stdout.write(self.style.SUCCESS("Done"))
