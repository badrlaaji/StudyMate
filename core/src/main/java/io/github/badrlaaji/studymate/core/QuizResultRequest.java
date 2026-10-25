package io.github.badrlaaji.studymate.core;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.List;

/** Body of POST /api/quiz-answers: every question of one quiz with its status. */
public record QuizResultRequest(
        @NotNull @Pattern(regexp = ScoreRequest.COURSE_ID) String courseId,
        @NotNull @Pattern(regexp = "^[a-f0-9-]{8,36}$") String quizId,
        @NotNull @NotEmpty @Size(max = 50) List<@Valid Item> answers) {

    /** One question: its notion and what happened. */
    public record Item(
            @NotNull @Pattern(regexp = ScoreRequest.NOTION_ID) String notionId,
            @NotNull AnswerStatus status) {
    }
}
