package io.github.badrlaaji.studymate.core;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.web.server.ResponseStatusException;

/** Public auth routes, and the 401 / 403 rules on the account routes. */
@WebMvcTest(
        controllers = {AuthController.class, UserController.class, HealthController.class},
        properties = TestTokens.SECRET_PROPERTY)
@Import(SecurityConfig.class)
class AuthControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private AccountService accounts;

    @MockitoBean
    private UserRepository users;

    private ResultActions send(String path, String body) throws Exception {
        return mvc.perform(post(path).contentType(MediaType.APPLICATION_JSON).content(body));
    }

    @Test
    void registerWithoutTokenIs201() throws Exception {
        when(accounts.register(any(AuthRequest.class))).thenReturn(new Account(7L, "ada@example.org", Instant.EPOCH));
        send("/api/auth/register", "{\"email\":\"ada@example.org\",\"password\":\"correct horse\"}")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(7))
                .andExpect(jsonPath("$.passwordHash").doesNotExist());
    }

    @Test
    void shortPasswordOrBadEmailIs400() throws Exception {
        send("/api/auth/register", "{\"email\":\"ada@example.org\",\"password\":\"short\"}").andExpect(status().isBadRequest());
        send("/api/auth/register", "{\"email\":\"not an email\",\"password\":\"correct horse\"}").andExpect(status().isBadRequest());
    }

    @Test
    void takenEmailIs409AndWrongPasswordIs401() throws Exception {
        when(accounts.register(any(AuthRequest.class))).thenThrow(new ResponseStatusException(HttpStatus.CONFLICT));
        when(accounts.login(any(AuthRequest.class))).thenThrow(new ResponseStatusException(HttpStatus.UNAUTHORIZED));
        String body = "{\"email\":\"ada@example.org\",\"password\":\"correct horse\"}";
        send("/api/auth/register", body).andExpect(status().isConflict());
        send("/api/auth/login", body).andExpect(status().isUnauthorized());
    }

    @Test
    void loginReturnsAToken() throws Exception {
        when(accounts.login(any(AuthRequest.class)))
                .thenReturn(new TokenResponse("header.payload.signature", Instant.EPOCH, 7L, "ada@example.org"));
        send("/api/auth/login", "{\"email\":\"ada@example.org\",\"password\":\"correct horse\"}")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.token").value("header.payload.signature"));
    }

    @Test
    void healthIsPublic() throws Exception {
        mvc.perform(get("/api/health")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("ok"));
    }

    @Test
    void noTokenIs401() throws Exception {
        mvc.perform(get("/api/me")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/users/7")).andExpect(status().isUnauthorized());
    }

    @Test
    void ownAccountIs200AndAnotherUsersIs403() throws Exception {
        when(users.findById(7L)).thenReturn(Optional.of(new AppUser("ada@example.org", "hash", Instant.EPOCH)));
        mvc.perform(get("/api/users/7").with(TestTokens.as(7))).andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value("ada@example.org"));
        mvc.perform(get("/api/users/7").with(TestTokens.as(8))).andExpect(status().isForbidden());
    }
}
