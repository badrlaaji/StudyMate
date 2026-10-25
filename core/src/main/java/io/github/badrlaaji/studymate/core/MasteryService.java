package io.github.badrlaaji.studymate.core;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/** Mastery rules: weak = average of the last 3 scores below 3, mastered = 4 or more. */
@Service
public class MasteryService {

    static final int LAST_SCORES = 3;
    static final double WEAK_BELOW = 3.0;
    static final double MASTERED_FROM = 4.0;

    private final ScoreRepository repository;

    public MasteryService(ScoreRepository repository) {
        this.repository = repository;
    }

    /** Save one validated score of a user with the current time. */
    public Score record(Long userId, ScoreRequest request) {
        Score score = new Score(
                userId, request.courseId(), request.notionId(), request.source(), request.score(), Instant.now());
        return repository.save(score);
    }

    /** Mastery of every notion a user scored in a course, weakest first. */
    public List<NotionMastery> mastery(Long userId, String courseId) {
        return summarizeAll(repository.findAllByUserIdAndCourseIdOrderByCreatedAtDescIdDesc(userId, courseId));
    }

    /** Every score of a user in a course with its time, oldest first. */
    public List<ScoreHistory> history(Long userId, String courseId) {
        return repository.findAllByUserIdAndCourseIdOrderByCreatedAtAscIdAsc(userId, courseId).stream()
                .map(ScoreHistory::of)
                .toList();
    }

    /** A user's weak notions of a course only, weakest first, at most {@code limit}. */
    public List<NotionMastery> weak(Long userId, String courseId, int limit) {
        return mastery(userId, courseId).stream().filter(m -> m.level().equals("WEAK")).limit(limit).toList();
    }

    /** Group scores (newest first) by notion and summarize each group. */
    static List<NotionMastery> summarizeAll(List<Score> newestFirst) {
        Map<String, List<Integer>> byNotion = new LinkedHashMap<>();
        for (Score score : newestFirst) {
            byNotion.computeIfAbsent(score.getNotionId(), id -> new ArrayList<>()).add(score.getScore());
        }
        return byNotion.entrySet().stream()
                .map(entry -> summarize(entry.getKey(), entry.getValue()))
                .sorted(Comparator.comparingDouble(NotionMastery::average))
                .toList();
    }

    /** Average of the last 3 scores (newest first), rounded to 2 decimals, and its level. */
    static NotionMastery summarize(String notionId, List<Integer> newestFirst) {
        List<Integer> last = newestFirst.subList(0, Math.min(LAST_SCORES, newestFirst.size()));
        double average = last.stream().mapToInt(Integer::intValue).average().orElse(0);
        double rounded = Math.round(average * 100) / 100.0;
        return new NotionMastery(notionId, rounded, newestFirst.size(), level(rounded));
    }

    /** WEAK below 3, MASTERED from 4, LEARNING in between. */
    static String level(double average) {
        if (average < WEAK_BELOW) {
            return "WEAK";
        }
        return average >= MASTERED_FROM ? "MASTERED" : "LEARNING";
    }
}
