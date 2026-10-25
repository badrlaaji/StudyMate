package io.github.badrlaaji.studymate.core;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

/** Session updates are checked against real time; goals against real time zones. */
class StudyServiceTest {

    private static final Instant START = Instant.parse("2026-01-01T09:00:00Z");

    private final StudySessionRepository sessions = mock(StudySessionRepository.class);
    private final StudyGoalRepository goals = mock(StudyGoalRepository.class);
    private final TrophyService trophies = mock(TrophyService.class);
    private final StudyService service = new StudyService(sessions, goals, trophies);
    private final StudySession session = new StudySession(7L, "data-science", StudyMode.CAMERA, START);

    StudyServiceTest() {
        when(sessions.findById(1L)).thenReturn(Optional.of(session));
        when(trophies.award(any(), any())).thenReturn(List.of("FIRST_STEPS"));
        when(trophies.goal(any())).thenReturn(new StudyGoal(7L, 30, "Africa/Casablanca"));
    }

    @Test
    void addedTimeCannotExceedTheRealElapsedTime() {
        assertThat(service.update(7L, 1L, 60, START.plusSeconds(60)).newTrophies()).containsExactly("FIRST_STEPS");
        assertThatThrownBy(() -> service.update(7L, 1L, 200, START.plusSeconds(120)))
                .hasMessageContaining("400").hasMessageContaining("only 60 s passed");
        assertThat(service.update(7L, 1L, 122, START.plusSeconds(120)).activeSeconds()).isEqualTo(122); // 2 s slack
    }

    @Test
    void activeTimeCannotGoDown() {
        service.update(7L, 1L, 60, START.plusSeconds(60));
        assertThatThrownBy(() -> service.update(7L, 1L, 30, START.plusSeconds(90))).hasMessageContaining("400");
    }

    @Test
    void anotherUsersSessionIs403() {
        assertThatThrownBy(() -> service.update(8L, 1L, 10, START.plusSeconds(60))).hasMessageContaining("403");
    }

    @Test
    void unknownTimeZoneIs400() {
        assertThatThrownBy(() -> service.setGoal(7L, new StudyRequests.Goal(30, "Mars/Olympus")))
                .hasMessageContaining("400");
    }

    @Test
    void summaryUsesTheGoalsTimeZone() {
        StudySession today = new StudySession(7L, "data-science", StudyMode.MANUAL, Instant.parse("2026-01-05T08:00:00Z"));
        today.update(1800, Instant.parse("2026-01-05T08:40:00Z"));
        when(sessions.findAllByUserId(7L)).thenReturn(List.of(today));
        StudyViews.Summary summary = service.summary(7L, Instant.parse("2026-01-05T20:00:00Z"));
        assertThat(summary.todaySeconds()).isEqualTo(1800);
        assertThat(summary.goalReachedToday()).isTrue();
        assertThat(summary.streakDays()).isEqualTo(1);
        assertThat(summary.week()).hasSize(7);
        assertThat(summary.week().get(6).date()).hasToString("2026-01-05");
    }
}
