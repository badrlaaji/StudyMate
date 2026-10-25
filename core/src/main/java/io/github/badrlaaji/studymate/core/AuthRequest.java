package io.github.badrlaaji.studymate.core;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** Body of POST /api/auth/register and /api/auth/login. BCrypt reads at most 72 bytes. */
public record AuthRequest(
        @NotBlank @Email @Size(max = 254) String email,
        @NotBlank @Size(min = 8, max = 72) String password) {
}
