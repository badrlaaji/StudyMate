package io.github.badrlaaji.studymate.core;

import java.time.Instant;
import java.time.ZoneId;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

/** Awards the trophies a user deserves (computed by Spring, never by the client). */
@Service
public class TrophyService {

    private final StudySessionRepository sessions;
    private final StudyGoalRepository goals;
    private final QuizAnswerRepository answers;
    private final TrophyRepository trophies;

    public TrophyService(
            StudySessionRepository sessions, StudyGoalRepository goals,
            QuizAnswerRepository answers, TrophyRepository trophies) {
        this.sessions = sessions;
        this.goals = goals;
        this.answers = answers;
        this.trophies = trophies;
    }

    StudyGoal goal(Long userId) {
        return goals.findById(userId).orElse(new StudyGoal(userId, StudyGoal.DEFAULT_MINUTES, StudyGoal.DEFAULT_ZONE));
    }

    /** Save the trophies newly deserved and return their codes. */
    public List<String> award(Long userId, Instant now) {
        StudyGoal goal = goal(userId);
        var days = TrophyRules.secondsPerDay(sessions.findAllByUserId(userId), ZoneId.of(goal.getTimezone()));
        Set<String> earned = TrophyRules.earned(days, goal.getMinutes(), TrophyRules.flawless(answers.findAllByUserId(userId)));
        Set<String> owned = trophies.findAllByUserId(userId).stream().map(Trophy::getCode).collect(Collectors.toSet());
        List<String> fresh = earned.stream().filter(code -> !owned.contains(code)).toList();
        fresh.forEach(code -> trophies.save(new Trophy(userId, code, now)));
        return fresh;
    }

    /** All 6 trophies, won or not (obtainedAt null when not won yet). */
    public List<TrophyView> list(Long userId) {
        Map<String, Trophy> owned = trophies.findAllByUserId(userId).stream()
                .collect(Collectors.toMap(Trophy::getCode, Function.identity()));
        return TrophyRules.CODES.stream()
                .map(code -> new TrophyView(code, owned.containsKey(code) ? owned.get(code).getObtainedAt() : null))
                .toList();
    }
}
