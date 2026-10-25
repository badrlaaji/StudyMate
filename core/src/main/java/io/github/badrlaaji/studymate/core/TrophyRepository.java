package io.github.badrlaaji.studymate.core;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

/** Trophies in the database. */
public interface TrophyRepository extends JpaRepository<Trophy, Long> {

    List<Trophy> findAllByUserId(Long userId);
}
