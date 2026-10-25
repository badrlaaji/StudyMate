package io.github.badrlaaji.studymate.core;

import org.springframework.data.jpa.repository.JpaRepository;

/** Daily goals, one per user. */
public interface StudyGoalRepository extends JpaRepository<StudyGoal, Long> {
}
