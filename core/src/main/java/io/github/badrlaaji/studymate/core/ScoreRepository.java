package io.github.badrlaaji.studymate.core;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

/** Scores in the database (Spring Data writes the SQL from the method name). */
public interface ScoreRepository extends JpaRepository<Score, Long> {

    /** One user's scores for one course, newest first (id breaks ties between equal timestamps). */
    List<Score> findAllByUserIdAndCourseIdOrderByCreatedAtDescIdDesc(Long userId, String courseId);

    /** One user's scores for one course, oldest first: the review history. */
    List<Score> findAllByUserIdAndCourseIdOrderByCreatedAtAscIdAsc(Long userId, String courseId);
}
