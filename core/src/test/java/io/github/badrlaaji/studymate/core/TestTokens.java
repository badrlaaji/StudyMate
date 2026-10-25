package io.github.badrlaaji.studymate.core;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;

import org.springframework.test.web.servlet.request.RequestPostProcessor;

/** Test-only signing key and a request "signed in as" a user id. */
final class TestTokens {

    /** Not a real secret: used by the tests only (32+ characters, as the service requires). */
    static final String SECRET_PROPERTY = "studymate.jwt.secret=test-only-secret-not-used-anywhere-else";

    private TestTokens() {
    }

    static RequestPostProcessor as(long userId) {
        return jwt().jwt(token -> token.subject(String.valueOf(userId)));
    }
}
