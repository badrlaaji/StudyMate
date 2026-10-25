package io.github.badrlaaji.studymate.core;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** A user's daily goal in minutes, and the time zone that decides what "today" is. */
@Entity
@Table(name = "study_goal")
public class StudyGoal {

    static final int DEFAULT_MINUTES = 30;
    static final String DEFAULT_ZONE = "UTC";

    @Id
    private Long userId;

    @Column(nullable = false)
    private int minutes;

    @Column(nullable = false)
    private String timezone;

    protected StudyGoal() {
        // required by JPA
    }

    public StudyGoal(Long userId, int minutes, String timezone) {
        this.userId = userId;
        this.minutes = minutes;
        this.timezone = timezone;
    }

    public Long getUserId() {
        return userId;
    }

    public int getMinutes() {
        return minutes;
    }

    public String getTimezone() {
        return timezone;
    }
}
