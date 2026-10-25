package io.github.badrlaaji.studymate.core;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class QuizServiceTest {

    private static final String QUIZ = "3f2a9c1e-0b7d-4e8a-9c55-1d2e3f4a5b6c";

    @Test
    @SuppressWarnings("unchecked")
    void aSkippedQuestionIsKeptAsSkippedAndCreatesNoScore() {
        QuizAnswerRepository answers = mock(QuizAnswerRepository.class);
        ScoreRepository scores = mock(ScoreRepository.class);
        QuizService service = new QuizService(answers);
        QuizResultRequest request = new QuizResultRequest("data-science", QUIZ, List.of(
                new QuizResultRequest.Item("k_means", AnswerStatus.CORRECT),
                new QuizResultRequest.Item("cnn", AnswerStatus.SKIPPED)));

        QuizSummary summary = service.record(7L, request);

        assertThat(summary).isEqualTo(new QuizSummary(2, 1, 0, 1));
        ArgumentCaptor<List<QuizAnswer>> saved = ArgumentCaptor.forClass(List.class);
        verify(answers).saveAll(saved.capture());
        assertThat(saved.getValue()).extracting(QuizAnswer::getStatus)
                .containsExactly(AnswerStatus.CORRECT, AnswerStatus.SKIPPED);
        assertThat(saved.getValue()).extracting(QuizAnswer::getQuizId).containsOnly(QUIZ);
        assertThat(saved.getValue()).extracting(QuizAnswer::getUserId).containsOnly(7L);
        verifyNoInteractions(scores); // the quiz log never writes a score: mastery and FSRS do not move
    }

    @Test
    void summaryCountsEachStatus() {
        List<QuizAnswer> answers = List.of(
                new QuizAnswer(7L, QUIZ, "c", "a", AnswerStatus.INCORRECT, null),
                new QuizAnswer(7L, QUIZ, "c", "b", AnswerStatus.SKIPPED, null),
                new QuizAnswer(7L, QUIZ, "c", "c", AnswerStatus.SKIPPED, null));
        assertThat(QuizService.summarize(answers)).isEqualTo(new QuizSummary(3, 0, 1, 2));
    }
}
