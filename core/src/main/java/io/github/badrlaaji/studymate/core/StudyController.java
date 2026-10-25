package io.github.badrlaaji.studymate.core;

import jakarta.validation.Valid;
import java.time.Instant;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Presence mode: sessions of estimated study time, daily goal, summary and trophies. */
@RestController
@RequestMapping("/api")
public class StudyController {

    private final StudyService study;
    private final TrophyService trophies;

    public StudyController(StudyService study, TrophyService trophies) {
        this.study = study;
        this.trophies = trophies;
    }

    @PostMapping("/study/sessions")
    @ResponseStatus(HttpStatus.CREATED)
    public StudyViews.Session start(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody StudyRequests.Start request) {
        return study.start(CurrentUser.id(jwt), request, Instant.now());
    }

    @PatchMapping("/study/sessions/{id}")
    public StudyViews.Session update(
            @AuthenticationPrincipal Jwt jwt, @PathVariable Long id, @Valid @RequestBody StudyRequests.Update request) {
        return study.update(CurrentUser.id(jwt), id, request.activeSeconds(), Instant.now());
    }

    @PutMapping("/study/goal")
    public StudyRequests.Goal goal(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody StudyRequests.Goal request) {
        StudyGoal saved = study.setGoal(CurrentUser.id(jwt), request);
        return new StudyRequests.Goal(saved.getMinutes(), saved.getTimezone());
    }

    @GetMapping("/study/summary")
    public StudyViews.Summary summary(@AuthenticationPrincipal Jwt jwt) {
        return study.summary(CurrentUser.id(jwt), Instant.now());
    }

    @GetMapping("/trophies")
    public List<TrophyView> trophies(@AuthenticationPrincipal Jwt jwt) {
        return trophies.list(CurrentUser.id(jwt));
    }
}
