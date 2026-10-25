package io.github.badrlaaji.studymate.core;

import java.time.Instant;

/** Public view of an account (never the password hash). */
public record Account(Long id, String email, Instant createdAt) {

    static Account of(AppUser user) {
        return new Account(user.getId(), user.getEmail(), user.getCreatedAt());
    }
}
