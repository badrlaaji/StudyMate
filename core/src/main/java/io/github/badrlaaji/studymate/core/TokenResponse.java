package io.github.badrlaaji.studymate.core;

import java.time.Instant;

/** A signed JWT and who it belongs to. */
public record TokenResponse(String token, Instant expiresAt, Long userId, String email) {
}
