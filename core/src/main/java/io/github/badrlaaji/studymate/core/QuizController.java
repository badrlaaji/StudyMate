package io.github.badrlaaji.studymate.core;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Quiz answer log (correct, incorrect or skipped); its only client is FastAPI. */
@RestController
@RequestMapping("/api")
public class QuizController {

    private final QuizService service;

    public QuizController(QuizService service) {
        this.service = service;
    }

    /** Record every question of one quiz. */
    @PostMapping("/quiz-answers")
    @ResponseStatus(HttpStatus.CREATED)
    public QuizSummary record(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody QuizResultRequest request) {
        return service.record(CurrentUser.id(jwt), request);
    }
}
