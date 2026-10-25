package io.github.badrlaaji.studymate.core;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

/** Scores in the database (Spring Data writes the SQL from the method name). */
public interface ScoreRepository extends JpaRepository<Score, Long> {

    /** All scores of one course, newest first (id breaks ties between equal timestamps). */
    List<Score> findAllByCourseIdOrderByCreatedAtDescIdDesc(String courseId);

    /** All scores of one course, oldest first: the review history. */
    List<Score> findAllByCourseIdOrderByCreatedAtAscIdAsc(String courseId);
}
