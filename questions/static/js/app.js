(() => {
    const errorBox = document.getElementById("ajax-error");
    const csrfToken = () => document.querySelector('meta[name="csrf-token"]').content;

    const showError = (message) => {
        errorBox.textContent = message;
        errorBox.hidden = false;
        errorBox.focus();
    };

    const post = async (url, values) => {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {"X-CSRFToken": csrfToken(), "X-Requested-With": "XMLHttpRequest"},
            body: new URLSearchParams(values),
        });

        if (response.status === 401) {
            const next = location.pathname + location.search + location.hash;
            location.assign(`/login/?next=${encodeURIComponent(next)}`);
            return null;
        }

        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error("Сервер вернул неожиданный ответ. Обновите страницу и попробуйте ещё раз.");
        }

        if (!response.ok) {
            const errors = Object.values(data.errors || {})
                .flat()
                .map((error) => error.message)
                .join(" ");
            throw new Error(data.error || errors || "Не удалось выполнить действие.");
        }

        errorBox.hidden = true;
        return data;
    };

    const updateVote = (box, value, rating) => {
        box.dataset.userVote = String(value);
        box.querySelector(".vote-count").textContent = rating;

        box.querySelectorAll("[data-vote-value]").forEach((button) => {
            const selected = Number(button.dataset.voteValue) === value;

            button.classList.toggle("active", selected);
            button.setAttribute("aria-pressed", String(selected));
            button.disabled = selected;

            button.title = selected
                ? "Такая оценка уже поставлена"
                : Number(button.dataset.voteValue) === 1
                  ? "Поставить лайк"
                  : "Поставить дизлайк";
        });
    };

    document.addEventListener("click", async (event) => {
        const voteButton = event.target.closest("[data-vote-value]");
        const correctButton = event.target.closest("[data-correct-url]");

        if (voteButton) {
            const box = voteButton.closest("[data-vote-url]");

            if (voteButton.disabled || box.dataset.busy === "true") {
                return;
            }

            box.dataset.busy = "true";
            box.querySelectorAll("button").forEach((button) => {
                button.disabled = true;
            });

            try {
                const data = await post(box.dataset.voteUrl, {value: voteButton.dataset.voteValue});
                if (data) updateVote(box, data.user_vote, data.rating);
            } catch (error) {
                showError(error.message || "Не удалось связаться с сервером.");
            } finally {
                delete box.dataset.busy;

                box.querySelectorAll("[data-vote-value]").forEach((button) => {
                    button.disabled = Number(button.dataset.voteValue) === Number(box.dataset.userVote);
                });
            }
        } else if (correctButton) {
            if (correctButton.disabled) {
                return;
            }

            correctButton.disabled = true;

            try {
                const data = await post(correctButton.dataset.correctUrl, {
                    answer: correctButton.dataset.answerId,
                    is_correct: String(correctButton.getAttribute("aria-checked") !== "true"),
                });

                if (data) {
                    correctButton.classList.toggle("is-correct", data.is_correct);
                    correctButton.setAttribute("aria-checked", String(data.is_correct));
                    correctButton.textContent = data.is_correct ? "✓ Правильный ответ" : "○ Отметить правильным";
                }
            } catch (error) {
                showError(error.message || "Не удалось связаться с сервером.");
            } finally {
                correctButton.disabled = false;
            }
        }
    });

    const avatar = document.querySelector('input[name="avatar"]');
    const preview = document.getElementById("avatar-preview-img");

    if (avatar && preview) {
        let objectUrl;
        avatar.addEventListener("change", () => {
            if (objectUrl) URL.revokeObjectURL(objectUrl);
            const file = avatar.files[0];

            if (file && ["image/png", "image/jpeg"].includes(file.type)) {
                objectUrl = URL.createObjectURL(file);
                preview.src = objectUrl;
            }
        });
    }
})();
