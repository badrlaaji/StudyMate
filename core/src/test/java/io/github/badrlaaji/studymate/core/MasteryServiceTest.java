package io.github.badrlaaji.studymate.core;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class MasteryServiceTest {

    private static Score score(String notionId, int value) {
        return new Score("data-science", notionId, Source.QUIZ, value, Instant.EPOCH);
    }

    @Test
    void averageUsesOnlyTheLastThreeScores() {
        // newest first: 5, 4, 3 count; the old 0 is ignored -> (5 + 4 + 3) / 3 = 4.0
        NotionMastery m = MasteryService.summarize("k_means", List.of(5, 4, 3, 0));
        assertThat(m.average()).isEqualTo(4.0);
        assertThat(m.count()).isEqualTo(4);
        assertThat(m.level()).isEqualTo("MASTERED");
    }

    @Test
    void levelBoundaries() {
        assertThat(MasteryService.level(2.99)).isEqualTo("WEAK");
        assertThat(MasteryService.level(3.0)).isEqualTo("LEARNING");
        assertThat(MasteryService.level(3.99)).isEqualTo("LEARNING");
        assertThat(MasteryService.level(4.0)).isEqualTo("MASTERED");
    }

    @Test
    void averageIsRoundedToTwoDecimals() {
        assertThat(MasteryService.summarize("x", List.of(2, 1, 1)).average()).isEqualTo(1.33);
    }

    @Test
    void summarizeAllGroupsByNotionAndSortsWeakestFirst() {
        List<Score> newestFirst = List.of(score("b", 5), score("a", 1), score("b", 4), score("a", 2));
        List<NotionMastery> result = MasteryService.summarizeAll(newestFirst);
        assertThat(result).extracting(NotionMastery::notionId).containsExactly("a", "b");
        assertThat(result.get(0).average()).isEqualTo(1.5);
    }

    @Test
    void weakKeepsOnlyWeakNotionsOfTheCourseWithinTheLimit() {
        ScoreRepository repository = mock(ScoreRepository.class);
        when(repository.findAllByCourseIdOrderByCreatedAtDescIdDesc("data-science"))
                .thenReturn(List.of(score("a", 1), score("b", 2), score("c", 5)));
        MasteryService service = new MasteryService(repository);
        assertThat(service.weak("data-science", 5)).extracting(NotionMastery::notionId).containsExactly("a", "b");
        assertThat(service.weak("data-science", 1)).extracting(NotionMastery::notionId).containsExactly("a");
        assertThat(service.weak("statistics", 5)).isEmpty(); // another course: no scores
    }

    @Test
    void historyKeepsTheTimeAndTheSourceOfEachScore() {
        ScoreRepository repository = mock(ScoreRepository.class);
        Instant time = Instant.parse("2026-01-01T09:00:00Z");
        when(repository.findAllByCourseIdOrderByCreatedAtAscIdAsc("data-science"))
                .thenReturn(List.of(new Score("data-science", "a", Source.FEYNMAN, 4, time)));
        MasteryService service = new MasteryService(repository);
        assertThat(service.history("data-science"))
                .containsExactly(new ScoreHistory("a", Source.FEYNMAN, 4, time));
    }
}
