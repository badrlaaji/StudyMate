package io.github.badrlaaji.studymate.core;

/** Mastery of one notion: average of its last scores and the resulting level. */
public record NotionMastery(String notionId, double average, int count, String level) {
}
