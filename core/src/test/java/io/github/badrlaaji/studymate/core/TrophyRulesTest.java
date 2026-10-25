package io.github.badrlaaji.studymate.core;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.junit.jupiter.api.Test;

/** The 6 trophies at fixed dates. */
class TrophyRulesTest {

    private static final LocalDate D1 = LocalDate.of(2026, 1, 1);
    private static final long GOAL = 30 * 60; // 30 minutes

    private static StudySession session(String start, long seconds) {
        StudySession session = new StudySession(7L, "data-science", StudyMode.MANUAL, Instant.parse(start));
        session.update(seconds, Instant.parse(start).plusSeconds(seconds));
        return session;
    }

    /** Seconds per day starting on 1 January: one value per day. */
    private static Map<LocalDate, Long> days(long... seconds) {
        Map<LocalDate, Long> days = new TreeMap<>();
        for (int i = 0; i < seconds.length; i++) {
            days.put(D1.plusDays(i), seconds[i]);
        }
        return days;
    }

    private static QuizAnswer answer(String quiz, AnswerStatus status) {
        return new QuizAnswer(7L, quiz, "data-science", "k_means", status, Instant.EPOCH);
    }

    @Test
    void aSessionCountsOnTheLocalDayItStarted() {
        // 23:30 UTC on 1 January is already 2 January in Tokyo (UTC+9).
        List<StudySession> sessions = List.of(session("2026-01-01T23:30:00Z", 600), session("2026-01-01T10:00:00Z", 300));
        assertThat(TrophyRules.secondsPerDay(sessions, ZoneId.of("UTC"))).containsEntry(D1, 900L);
        assertThat(TrophyRules.secondsPerDay(sessions, ZoneId.of("Asia/Tokyo")))
                .containsEntry(D1, 300L).containsEntry(D1.plusDays(1), 600L);
    }

    @Test
    void streaksNeedConsecutiveDaysAtTheGoal() {
        assertThat(TrophyRules.longestStreak(days(GOAL, GOAL, GOAL - 1, GOAL, GOAL, GOAL, GOAL), GOAL)).isEqualTo(4);
        Map<LocalDate, Long> gap = new TreeMap<>(Map.of(D1, GOAL, D1.plusDays(2), GOAL)); // 2 January missing
        assertThat(TrophyRules.longestStreak(gap, GOAL)).isEqualTo(1);
    }

    @Test
    void currentStreakEndsTodayOrYesterday() {
        Map<LocalDate, Long> three = days(GOAL, GOAL, GOAL); // 1, 2, 3 January
        assertThat(TrophyRules.currentStreak(three, GOAL, D1.plusDays(2))).isEqualTo(3);
        assertThat(TrophyRules.currentStreak(three, GOAL, D1.plusDays(3))).isEqualTo(3); // today not done yet
        assertThat(TrophyRules.currentStreak(three, GOAL, D1.plusDays(4))).isEqualTo(0); // a day was missed
    }

    @Test
    void flawlessNeedsFiveCorrectAndNoSkip() {
        List<QuizAnswer> five = List.of(answer("a", AnswerStatus.CORRECT), answer("a", AnswerStatus.CORRECT),
                answer("a", AnswerStatus.CORRECT), answer("a", AnswerStatus.CORRECT), answer("a", AnswerStatus.CORRECT));
        assertThat(TrophyRules.flawless(five)).isTrue();
        assertThat(TrophyRules.flawless(five.subList(0, 4))).isFalse(); // only 4 questions
        List<QuizAnswer> skipped = new java.util.ArrayList<>(five.subList(0, 4));
        skipped.add(answer("a", AnswerStatus.SKIPPED));
        assertThat(TrophyRules.flawless(skipped)).isFalse(); // a skipped question breaks it
        List<QuizAnswer> twoQuizzes = new java.util.ArrayList<>(five.subList(0, 3));
        twoQuizzes.addAll(List.of(answer("b", AnswerStatus.CORRECT), answer("b", AnswerStatus.CORRECT)));
        assertThat(TrophyRules.flawless(twoQuizzes)).isFalse(); // 3 + 2, not one quiz of 5
    }

    @Test
    void thresholds() {
        assertThat(TrophyRules.earned(days(599), 30, false)).isEmpty();
        assertThat(TrophyRules.earned(days(600), 30, false)).containsExactly(TrophyRules.FIRST_STEPS);
        assertThat(TrophyRules.earned(days(GOAL), 30, false))
                .containsExactly(TrophyRules.FIRST_STEPS, TrophyRules.GOAL_REACHED);
        assertThat(TrophyRules.earned(days(GOAL, GOAL, GOAL), 30, false)).contains(TrophyRules.REGULAR)
                .doesNotContain(TrophyRules.PERFECT_WEEK);
        assertThat(TrophyRules.earned(days(GOAL, GOAL, GOAL, GOAL, GOAL, GOAL, GOAL), 30, false))
                .contains(TrophyRules.PERFECT_WEEK);
        assertThat(TrophyRules.earned(days(36_000), 480, false)).contains(TrophyRules.MARATHON);
        assertThat(TrophyRules.earned(days(35_999), 600, false)).doesNotContain(TrophyRules.MARATHON);
        assertThat(TrophyRules.earned(days(), 30, true)).containsExactly(TrophyRules.FLAWLESS);
    }
}
