package io.github.badrlaaji.studymate.core;

/** Counts of one recorded quiz. */
public record QuizSummary(int questions, int correct, int incorrect, int skipped) {
}
