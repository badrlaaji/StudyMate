package io.github.badrlaaji.studymate.core;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.lang.reflect.Field;
import java.time.Instant;
import java.util.Optional;
import javax.crypto.SecretKey;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.web.server.ResponseStatusException;

/** Sign-up, login and the token round trip with the real encoder and decoder. */
class AccountServiceTest {

    private final SecurityConfig config = new SecurityConfig();
    private final SecretKey key = config.jwtKey("test-only-secret-not-used-anywhere-else");
    private final JwtDecoder decoder = config.jwtDecoder(key);
    private final BCryptPasswordEncoder passwords = new BCryptPasswordEncoder();
    private final UserRepository users = mock(UserRepository.class);
    private final AccountService accounts = new AccountService(users, passwords, config.jwtEncoder(key));

    private static AppUser saved(long id, String email, String hash) throws Exception {
        AppUser user = new AppUser(email, hash, Instant.parse("2026-01-01T09:00:00Z"));
        Field field = AppUser.class.getDeclaredField("id"); // set by the database in real use
        field.setAccessible(true);
        field.set(user, id);
        return user;
    }

    @Test
    void registerStoresAHashNeverThePassword() throws Exception {
        when(users.existsByEmail("ada@example.org")).thenReturn(false);
        when(users.save(any(AppUser.class))).thenAnswer(call -> {
            AppUser user = call.getArgument(0);
            assertThat(user.getPasswordHash()).isNotEqualTo("correct horse").startsWith("$2");
            assertThat(passwords.matches("correct horse", user.getPasswordHash())).isTrue();
            return saved(1, user.getEmail(), user.getPasswordHash());
        });
        Account account = accounts.register(new AuthRequest("  Ada@Example.org ", "correct horse"));
        assertThat(account.email()).isEqualTo("ada@example.org"); // trimmed, lower case
    }

    @Test
    void registerTwiceIs409() {
        when(users.existsByEmail("ada@example.org")).thenReturn(true);
        assertThatThrownBy(() -> accounts.register(new AuthRequest("ada@example.org", "correct horse")))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("409");
    }

    @Test
    void loginIssuesATokenTheDecoderAccepts() throws Exception {
        AppUser ada = saved(42, "ada@example.org", passwords.encode("correct horse"));
        when(users.findByEmail("ada@example.org")).thenReturn(Optional.of(ada));
        TokenResponse response = accounts.login(new AuthRequest("ada@example.org", "correct horse"));
        Jwt jwt = decoder.decode(response.token());
        assertThat(jwt.getSubject()).isEqualTo("42");
        assertThat(jwt.getClaimAsString("email")).isEqualTo("ada@example.org");
        assertThat(response.expiresAt()).isAfter(Instant.now().plus(AccountService.TOKEN_LIFETIME).minusSeconds(60));
    }

    @Test
    void wrongPasswordOrUnknownEmailIs401() throws Exception {
        AppUser ada = saved(42, "ada@example.org", passwords.encode("correct horse"));
        when(users.findByEmail("ada@example.org")).thenReturn(Optional.of(ada));
        when(users.findByEmail("bob@example.org")).thenReturn(Optional.empty());
        assertThatThrownBy(() -> accounts.login(new AuthRequest("ada@example.org", "wrong password")))
                .hasMessageContaining("401");
        assertThatThrownBy(() -> accounts.login(new AuthRequest("bob@example.org", "correct horse")))
                .hasMessageContaining("401");
    }

    @Test
    void aTokenSignedWithAnotherKeyIsRejected() throws Exception {
        SecurityConfig other = new SecurityConfig();
        SecretKey otherKey = other.jwtKey("another-secret-of-at-least-32-characters");
        AccountService forged = new AccountService(users, passwords, other.jwtEncoder(otherKey));
        String token = forged.issue(saved(42, "ada@example.org", "x"), Instant.now()).token();
        assertThatThrownBy(() -> decoder.decode(token)).hasMessageContaining("signature");
    }

    @Test
    void aShortSecretStopsTheService() {
        assertThatThrownBy(() -> config.jwtKey("too-short")).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> config.jwtKey("")).hasMessageContaining("JWT_SECRET");
    }
}
