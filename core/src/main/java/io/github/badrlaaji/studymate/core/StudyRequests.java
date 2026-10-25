package io.github.badrlaaji.studymate.core;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** Bodies of the study routes, validated before they reach the service. */
final class StudyRequests {

    private StudyRequests() {
    }

    /** POST /api/study/sessions. */
    record Start(@NotNull @Pattern(regexp = ScoreRequest.COURSE_ID) String courseId, @NotNull StudyMode mode) {
    }

    /** PATCH /api/study/sessions/{id}: the new total of active seconds (never an image). */
    record Update(@NotNull @Min(0) @Max(86_400) Long activeSeconds) {
    }

    /** PUT /api/study/goal: 5 to 480 minutes a day, in an IANA time zone such as "Africa/Casablanca". */
    record Goal(@NotNull @Min(5) @Max(480) Integer minutes, @NotBlank @Size(max = 64) String timezone) {
    }
}
