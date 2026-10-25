package io.github.badrlaaji.studymate.core;

import java.time.DateTimeException;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import java.util.stream.IntStream;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

/** Study sessions (estimated active time), the daily goal and the summary. */
@Service
public class StudyService {

    static final long SLACK_SECONDS = 2; // network delay between the browser clock and ours

    private final StudySessionRepository sessions;
    private final StudyGoalRepository goals;
    private final TrophyService trophies;

    public StudyService(StudySessionRepository sessions, StudyGoalRepository goals, TrophyService trophies) {
        this.sessions = sessions;
        this.goals = goals;
        this.trophies = trophies;
    }

    public StudyViews.Session start(Long userId, StudyRequests.Start request, Instant now) {
        StudySession session = sessions.save(new StudySession(userId, request.courseId(), request.mode(), now));
        return StudyViews.Session.of(session, List.of());
    }

    /** New total of active seconds: 403 if not yours, 400 if it goes down or grows faster than real time. */
    public StudyViews.Session update(Long userId, Long sessionId, long activeSeconds, Instant now) {
        StudySession session = sessions.findById(sessionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such session."));
        if (!session.getUserId().equals(userId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "This session belongs to another user.");
        }
        long added = activeSeconds - session.getActiveSeconds();
        long elapsed = Duration.between(session.getEndedAt(), now).toSeconds();
        if (added < 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Active time cannot go down.");
        }
        if (added > elapsed + SLACK_SECONDS) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "Added " + added + " s but only " + elapsed + " s passed since the last update.");
        }
        session.update(activeSeconds, now);
        sessions.save(session);
        return StudyViews.Session.of(session, trophies.award(userId, now));
    }

    /** Save the daily goal; 400 for an unknown time zone. */
    public StudyGoal setGoal(Long userId, StudyRequests.Goal request) {
        try {
            ZoneId.of(request.timezone());
        } catch (DateTimeException error) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unknown time zone: " + request.timezone());
        }
        return goals.save(new StudyGoal(userId, request.minutes(), request.timezone()));
    }

    /** Today in the user's time zone, the current streak, the total and the last 7 days. */
    public StudyViews.Summary summary(Long userId, Instant now) {
        StudyGoal goal = trophies.goal(userId);
        ZoneId zone = ZoneId.of(goal.getTimezone());
        var days = TrophyRules.secondsPerDay(sessions.findAllByUserId(userId), zone);
        long goalSeconds = goal.getMinutes() * 60L;
        LocalDate today = now.atZone(zone).toLocalDate();
        long todaySeconds = days.getOrDefault(today, 0L);
        List<StudyViews.Day> week = IntStream.rangeClosed(0, 6)
                .mapToObj(i -> today.minusDays(6 - i))
                .map(day -> new StudyViews.Day(day, days.getOrDefault(day, 0L), days.getOrDefault(day, 0L) >= goalSeconds))
                .toList();
        long total = days.values().stream().mapToLong(Long::longValue).sum();
        return new StudyViews.Summary(goal.getMinutes(), goal.getTimezone(), todaySeconds, todaySeconds >= goalSeconds,
                TrophyRules.currentStreak(days, goalSeconds, today), total, week);
    }
}
