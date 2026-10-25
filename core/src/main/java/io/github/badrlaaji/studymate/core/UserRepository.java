package io.github.badrlaaji.studymate.core;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/** Accounts in the database. */
public interface UserRepository extends JpaRepository<AppUser, Long> {

    Optional<AppUser> findByEmail(String email);

    boolean existsByEmail(String email);
}
