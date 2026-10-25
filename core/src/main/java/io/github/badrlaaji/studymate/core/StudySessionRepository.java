package io.github.badrlaaji.studymate.core;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

/** Study sessions in the database. */
public interface StudySessionRepository extends JpaRepository<StudySession, Long> {

    List<StudySession> findAllByUserId(Long userId);
}
