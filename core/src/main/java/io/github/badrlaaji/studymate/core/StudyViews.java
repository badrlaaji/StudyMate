package io.github.badrlaaji.studymate.core;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

/** What the study routes return. */
final class StudyViews {

    private StudyViews() {
    }

    /** A session after an update, with the trophies it just unlocked. */
    record Session(Long id, String courseId, StudyMode mode, Instant startedAt, long activeSeconds,
            List<String> newTrophies) {

        static Session of(StudySession s, List<String> newTrophies) {
            return new Session(s.getId(), s.getCourseId(), s.getMode(), s.getStartedAt(), s.getActiveSeconds(),
                    newTrophies);
        }
    }

    /** Estimated study time of one local day. */
    record Day(LocalDate date, long seconds, boolean reached) {
    }

    /** Today, the goal, the streak and the last 7 days. */
    record Summary(int goalMinutes, String timezone, long todaySeconds, boolean goalReachedToday,
            int streakDays, long totalSeconds, List<Day> week) {
    }
}
