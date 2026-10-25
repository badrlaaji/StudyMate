package io.github.badrlaaji.studymate.core;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Public routes: create an account, get a token. */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AccountService accounts;

    public AuthController(AccountService accounts) {
        this.accounts = accounts;
    }

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    public Account register(@Valid @RequestBody AuthRequest request) {
        return accounts.register(request);
    }

    @PostMapping("/login")
    public TokenResponse login(@Valid @RequestBody AuthRequest request) {
        return accounts.login(request);
    }
}
