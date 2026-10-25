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

/** One study session (table app.study_session): estimated active seconds, never an image. */
@Entity
@Table(name = "study_session")
public class StudySession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false)
    private String courseId;

    @Column(nullable = false)
    private Instant startedAt;

    @Column(nullable = false)
    private Instant endedAt; // time of the last update

    @Column(nullable = false)
    private long activeSeconds;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private StudyMode mode;

    protected StudySession() {
        // required by JPA
    }

    public StudySession(Long userId, String courseId, StudyMode mode, Instant startedAt) {
        this.userId = userId;
        this.courseId = courseId;
        this.mode = mode;
        this.startedAt = startedAt;
        this.endedAt = startedAt;
        this.activeSeconds = 0;
    }

    /** New total of active seconds, measured at {@code now}. */
    void update(long activeSeconds, Instant now) {
        this.activeSeconds = activeSeconds;
        this.endedAt = now;
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

    public Instant getStartedAt() {
        return startedAt;
    }

    public Instant getEndedAt() {
        return endedAt;
    }

    public long getActiveSeconds() {
        return activeSeconds;
    }

    public StudyMode getMode() {
        return mode;
    }
}
