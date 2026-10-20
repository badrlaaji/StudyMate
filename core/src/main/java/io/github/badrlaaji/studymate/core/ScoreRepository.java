package io.github.badrlaaji.studymate.core;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

/** Scores in the database (Spring Data writes the SQL from the method name). */
public interface ScoreRepository extends JpaRepository<Score, Long> {

    /** All scores, newest first (id breaks ties between equal timestamps). */
    List<Score> findAllByOrderByCreatedAtDescIdDesc();
}
