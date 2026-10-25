package io.github.badrlaaji.studymate.core;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

/** Body of POST /api/scores, validated before it reaches the service. */
public record ScoreRequest(
        @NotNull @Pattern(regexp = COURSE_ID) String courseId,
        @NotNull @Pattern(regexp = NOTION_ID) String notionId,
        @NotNull Source source,
        @NotNull @Min(0) @Max(5) Integer score) {

    /** Course ids of course/courses.json, e.g. "data-science". */
    public static final String COURSE_ID = "^[a-z0-9]+(-[a-z0-9]+)*$";

    /** Notion ids of the catalogues, e.g. "k_means_clustering". */
    public static final String NOTION_ID = "^[a-z0-9]+(_[a-z0-9]+)*$";
}
