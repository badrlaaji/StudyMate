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

/** One 0-5 score for one notion of one course (table app.scores). */
@Entity
@Table(name = "scores")
public class Score {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Nullable in the database: rows saved before accounts have no user (and stay hidden).
    private Long userId;

    // Nullable in the database: rows saved before multi-course support have none.
    private String courseId;

    @Column(nullable = false)
    private String notionId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Source source;

    @Column(nullable = false)
    private int score;

    @Column(nullable = false)
    private Instant createdAt;

    protected Score() {
        // required by JPA
    }

    public Score(Long userId, String courseId, String notionId, Source source, int score, Instant createdAt) {
        this.userId = userId;
        this.courseId = courseId;
        this.notionId = notionId;
        this.source = source;
        this.score = score;
        this.createdAt = createdAt;
    }

    public Long getId() {
        return id;
    }

    public Long getUserId() {
        return userId;
    }

    public String getCourseId() {
        return courseId;
    }

    public String getNotionId() {
        return notionId;
    }

    public Source getSource() {
        return source;
    }

    public int getScore() {
        return score;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
