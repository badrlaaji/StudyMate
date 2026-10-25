package io.github.badrlaaji.studymate.core;

import java.time.Instant;

/** One trophy as the interface shows it; obtainedAt is null while it is still locked. */
public record TrophyView(String code, Instant obtainedAt) {
}
