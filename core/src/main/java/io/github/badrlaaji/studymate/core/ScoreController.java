package io.github.badrlaaji.studymate.core;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Mastery API; its only client is the FastAPI service.
 * Parameter constraints are checked by Spring MVC itself (400 on violation). */
@RestController
@RequestMapping("/api")
public class ScoreController {

    private final MasteryService service;

    public ScoreController(MasteryService service) {
        this.service = service;
    }

    /** Record one 0-5 score (FEYNMAN or QUIZ). */
    @PostMapping("/scores")
    @ResponseStatus(HttpStatus.CREATED)
    public NotionMastery addScore(@Valid @RequestBody ScoreRequest request) {
        service.record(request);
        return service.mastery().stream()
                .filter(m -> m.notionId().equals(request.notionId()))
                .findFirst()
                .orElseThrow();
    }

    /** Weak notions (average of the last 3 scores below 3), weakest first. */
    @GetMapping("/notions/weak")
    public List<NotionMastery> weak(@RequestParam(defaultValue = "5") @Min(1) @Max(25) int limit) {
        return service.weak(limit);
    }

    /** Mastery of every scored notion. */
    @GetMapping("/mastery")
    public List<NotionMastery> mastery() {
        return service.mastery();
    }
}
