package io.github.badrlaaji.studymate.core;

import java.time.Instant;

/** One recorded score with its time: what spaced repetition (FSRS) replays. */
public record ScoreHistory(String notionId, Source source, int score, Instant createdAt) {

    static ScoreHistory of(Score score) {
        return new ScoreHistory(score.getNotionId(), score.getSource(), score.getScore(), score.getCreatedAt());
    }
}
