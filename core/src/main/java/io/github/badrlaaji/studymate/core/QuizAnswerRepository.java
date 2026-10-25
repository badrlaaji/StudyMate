package io.github.badrlaaji.studymate.core;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

/** Quiz answers in the database. */
public interface QuizAnswerRepository extends JpaRepository<QuizAnswer, Long> {

    /** Every answer of one quiz. */
    List<QuizAnswer> findAllByQuizId(String quizId);

    /** Every answer of one user (the "flawless quiz" trophy). */
    List<QuizAnswer> findAllByUserId(Long userId);
}
