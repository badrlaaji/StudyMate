package io.github.badrlaaji.studymate.core;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.stream.Collectors;

/** The 6 trophies, computed from the data only (pure functions, tested at fixed dates). */
final class TrophyRules {

    static final String FIRST_STEPS = "FIRST_STEPS"; // 10 active minutes in total
    static final String GOAL_REACHED = "GOAL_REACHED"; // daily goal reached once
    static final String REGULAR = "REGULAR"; // goal reached 3 days in a row
    static final String PERFECT_WEEK = "PERFECT_WEEK"; // goal reached 7 days in a row
    static final String MARATHON = "MARATHON"; // 10 hours in total
    static final String FLAWLESS = "FLAWLESS"; // a quiz of 5+ questions, all correct, none skipped
    static final List<String> CODES = List.of(FIRST_STEPS, GOAL_REACHED, REGULAR, PERFECT_WEEK, MARATHON, FLAWLESS);

    static final long FIRST_STEPS_SECONDS = 10 * 60;
    static final long MARATHON_SECONDS = 10 * 3600;
    static final int FLAWLESS_MIN_QUESTIONS = 5;

    private TrophyRules() {
    }

    /** Active seconds per local day; a session counts on the day it started (in the goal's zone). */
    static Map<LocalDate, Long> secondsPerDay(List<StudySession> sessions, ZoneId zone) {
        return sessions.stream().collect(Collectors.groupingBy(
                s -> s.getStartedAt().atZone(zone).toLocalDate(), TreeMap::new,
                Collectors.summingLong(StudySession::getActiveSeconds)));
    }

    /** Longest run of consecutive days with the goal reached. */
    static int longestStreak(Map<LocalDate, Long> days, long goalSeconds) {
        int best = 0;
        int run = 0;
        LocalDate previous = null;
        for (LocalDate day : new TreeMap<>(days).keySet()) {
            if (days.get(day) < goalSeconds) {
                run = 0;
            } else {
                run = previous != null && previous.plusDays(1).equals(day) && run > 0 ? run + 1 : 1;
                best = Math.max(best, run);
            }
            previous = day;
        }
        return best;
    }

    /** Days in a row with the goal reached, ending today (or yesterday while today is not reached yet). */
    static int currentStreak(Map<LocalDate, Long> days, long goalSeconds, LocalDate today) {
        LocalDate day = days.getOrDefault(today, 0L) >= goalSeconds ? today : today.minusDays(1);
        int streak = 0;
        while (days.getOrDefault(day, 0L) >= goalSeconds) {
            streak++;
            day = day.minusDays(1);
        }
        return streak;
    }

    /** True if one quiz had at least 5 questions, all correct: a skipped question breaks it. */
    static boolean flawless(List<QuizAnswer> answers) {
        return answers.stream()
                .collect(Collectors.groupingBy(QuizAnswer::getQuizId))
                .values().stream()
                .anyMatch(quiz -> quiz.size() >= FLAWLESS_MIN_QUESTIONS
                        && quiz.stream().allMatch(a -> a.getStatus() == AnswerStatus.CORRECT));
    }

    /** Every trophy the data deserves, in the order of {@link #CODES}. */
    static Set<String> earned(Map<LocalDate, Long> days, int goalMinutes, boolean flawlessQuiz) {
        long total = days.values().stream().mapToLong(Long::longValue).sum();
        int streak = longestStreak(days, goalMinutes * 60L);
        Set<String> codes = new LinkedHashSet<>();
        if (total >= FIRST_STEPS_SECONDS) {
            codes.add(FIRST_STEPS);
        }
        if (streak >= 1) {
            codes.add(GOAL_REACHED);
        }
        if (streak >= 3) {
            codes.add(REGULAR);
        }
        if (streak >= 7) {
            codes.add(PERFECT_WEEK);
        }
        if (total >= MARATHON_SECONDS) {
            codes.add(MARATHON);
        }
        if (flawlessQuiz) {
            codes.add(FLAWLESS);
        }
        return codes;
    }
}
