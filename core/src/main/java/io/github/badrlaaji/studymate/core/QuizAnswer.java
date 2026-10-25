package io.github.badrlaaji.studymate.core;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/** One answered (or skipped) quiz question (table app.quiz_answer). Scores stay in app.scores. */
@Entity
@Table(name = "quiz_answer")
public class QuizAnswer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String quizId;

    @Column(nullable = false)
    private String courseId;

    @Column(nullable = false)
    private String notionId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private AnswerStatus status;

    @Column(nullable = false)
    private Instant answeredAt;

    protected QuizAnswer() {
        // required by JPA
    }

    public QuizAnswer(String quizId, String courseId, String notionId, AnswerStatus status, Instant answeredAt) {
        this.quizId = quizId;
        this.courseId = courseId;
        this.notionId = notionId;
        this.status = status;
        this.answeredAt = answeredAt;
    }

    public String getQuizId() {
        return quizId;
    }

    public String getCourseId() {
        return courseId;
    }

    public String getNotionId() {
        return notionId;
    }

    public AnswerStatus getStatus() {
        return status;
    }

    public Instant getAnsweredAt() {
        return answeredAt;
    }
}
