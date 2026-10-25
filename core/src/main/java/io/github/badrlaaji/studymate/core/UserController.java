package io.github.badrlaaji.studymate.core;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** Account details: a user may only read their own. */
@RestController
@RequestMapping("/api")
public class UserController {

    private final UserRepository users;

    public UserController(UserRepository users) {
        this.users = users;
    }

    @GetMapping("/me")
    public Account me(@AuthenticationPrincipal Jwt jwt) {
        return user(jwt, CurrentUser.id(jwt));
    }

    /** 403 with another user's token, 404 if the account no longer exists. */
    @GetMapping("/users/{id}")
    public Account user(@AuthenticationPrincipal Jwt jwt, @PathVariable Long id) {
        CurrentUser.requireOwner(jwt, id);
        return users.findById(id)
                .map(Account::of)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such account."));
    }
}
