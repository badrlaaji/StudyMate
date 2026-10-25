package io.github.badrlaaji.studymate.core;

import java.time.Instant;
import java.util.List;
import org.springframework.stereotype.Service;

/** Keeps the answer log of each quiz; scores (mastery, FSRS) are recorded apart, by FastAPI. */
@Service
public class QuizService {

    private final QuizAnswerRepository repository;
    private final TrophyService trophies;

    public QuizService(QuizAnswerRepository repository, TrophyService trophies) {
        this.repository = repository;
        this.trophies = trophies;
    }

    /** Save every question of a user's quiz, skipped ones included, and count them. */
    public QuizSummary record(Long userId, QuizResultRequest request) {
        Instant now = Instant.now();
        List<QuizAnswer> answers = request.answers().stream()
                .map(item -> new QuizAnswer(
                        userId, request.quizId(), request.courseId(), item.notionId(), item.status(), now))
                .toList();
        repository.saveAll(answers);
        trophies.award(userId, now); // a flawless quiz unlocks a trophy
        return summarize(answers);
    }

    /** How many questions were right, wrong or skipped. */
    static QuizSummary summarize(List<QuizAnswer> answers) {
        return new QuizSummary(
                answers.size(),
                count(answers, AnswerStatus.CORRECT),
                count(answers, AnswerStatus.INCORRECT),
                count(answers, AnswerStatus.SKIPPED));
    }

    private static int count(List<QuizAnswer> answers, AnswerStatus status) {
        return (int) answers.stream().filter(answer -> answer.getStatus() == status).count();
    }
}
