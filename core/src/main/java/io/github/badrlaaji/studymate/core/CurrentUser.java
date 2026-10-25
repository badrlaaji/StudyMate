package io.github.badrlaaji.studymate.core;

import org.springframework.http.HttpStatus;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.server.ResponseStatusException;

/** The user behind a verified token, and the "own data only" rule. */
final class CurrentUser {

    private CurrentUser() {
    }

    static Long id(Jwt jwt) {
        return Long.valueOf(jwt.getSubject());
    }

    /** 403 when a token asks for another user's data. */
    static void requireOwner(Jwt jwt, Long ownerId) {
        if (!id(jwt).equals(ownerId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "This belongs to another user.");
        }
    }
}
