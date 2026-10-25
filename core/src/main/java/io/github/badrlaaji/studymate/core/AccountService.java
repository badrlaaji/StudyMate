package io.github.badrlaaji.studymate.core;

import java.time.Duration;
import java.time.Instant;
import java.util.Locale;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

/** Sign-up, login and JWT issuing. */
@Service
public class AccountService {

    static final Duration TOKEN_LIFETIME = Duration.ofDays(7);
    static final String ISSUER = "studymate";

    private final UserRepository users;
    private final PasswordEncoder passwords;
    private final JwtEncoder encoder;

    public AccountService(UserRepository users, PasswordEncoder passwords, JwtEncoder encoder) {
        this.users = users;
        this.passwords = passwords;
        this.encoder = encoder;
    }

    /** Create an account; 409 if the email is taken. */
    public Account register(AuthRequest request) {
        String email = normalize(request.email());
        if (users.existsByEmail(email)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "This email already has an account.");
        }
        AppUser user = users.save(new AppUser(email, passwords.encode(request.password()), Instant.now()));
        return Account.of(user);
    }

    /** Check the password and issue a token; the same 401 whether the email or the password is wrong. */
    public TokenResponse login(AuthRequest request) {
        AppUser user = users.findByEmail(normalize(request.email()))
                .filter(found -> passwords.matches(request.password(), found.getPasswordHash()))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Wrong email or password."));
        return issue(user, Instant.now());
    }

    /** A JWT whose subject is the user id, valid for 7 days. */
    TokenResponse issue(AppUser user, Instant now) {
        Instant expiresAt = now.plus(TOKEN_LIFETIME);
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(ISSUER)
                .subject(String.valueOf(user.getId()))
                .claim("email", user.getEmail())
                .issuedAt(now)
                .expiresAt(expiresAt)
                .build();
        JwsHeader header = JwsHeader.with(MacAlgorithm.HS256).build();
        String token = encoder.encode(JwtEncoderParameters.from(header, claims)).getTokenValue();
        return new TokenResponse(token, expiresAt, user.getId(), user.getEmail());
    }

    static String normalize(String email) {
        return email.trim().toLowerCase(Locale.ROOT);
    }
}
