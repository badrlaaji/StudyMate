package io.github.badrlaaji.studymate.core;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;

/** A trophy won by a user (table app.trophy): each code at most once per user. */
@Entity
@Table(name = "trophy", uniqueConstraints = @UniqueConstraint(columnNames = {"userId", "code"}))
public class Trophy {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false)
    private String code;

    @Column(nullable = false)
    private Instant obtainedAt;

    protected Trophy() {
        // required by JPA
    }

    public Trophy(Long userId, String code, Instant obtainedAt) {
        this.userId = userId;
        this.code = code;
        this.obtainedAt = obtainedAt;
    }

    public Long getUserId() {
        return userId;
    }

    public String getCode() {
        return code;
    }

    public Instant getObtainedAt() {
        return obtainedAt;
    }
}
