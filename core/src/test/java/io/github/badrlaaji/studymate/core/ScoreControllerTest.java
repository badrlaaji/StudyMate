package io.github.badrlaaji.studymate.core;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/** One test per endpoint; the service is a mock, no database. */
@WebMvcTest(controllers = ScoreController.class, properties = TestTokens.SECRET_PROPERTY)
@Import(SecurityConfig.class)
class ScoreControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private MasteryService service;

    private static final NotionMastery WEAK = new NotionMastery("k_means", 1.5, 2, "WEAK");

    @Test
    void postScoreReturns201AndTheNotionMastery() throws Exception {
        when(service.mastery(7L, "data-science")).thenReturn(List.of(WEAK));
        mvc.perform(post("/api/scores").with(TestTokens.as(7))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"courseId\":\"data-science\",\"notionId\":\"k_means\","
                                + "\"source\":\"QUIZ\",\"score\":2}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.notionId").value("k_means"))
                .andExpect(jsonPath("$.level").value("WEAK"));
        verify(service).record(eq(7L), any(ScoreRequest.class));
    }

    @Test
    void postScoreOutOfRangeIs400() throws Exception {
        mvc.perform(post("/api/scores").with(TestTokens.as(7))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"courseId\":\"data-science\",\"notionId\":\"k_means\","
                                + "\"source\":\"QUIZ\",\"score\":7}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void postScoreWithBadNotionIdIs400() throws Exception {
        mvc.perform(post("/api/scores").with(TestTokens.as(7))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"courseId\":\"data-science\",\"notionId\":\"K Means!\","
                                + "\"source\":\"FEYNMAN\",\"score\":3}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void postScoreWithoutCourseIs400() throws Exception {
        mvc.perform(post("/api/scores").with(TestTokens.as(7))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"notionId\":\"k_means\",\"source\":\"QUIZ\",\"score\":2}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void weakNotionsUseTheLimit() throws Exception {
        when(service.weak(7L, "statistics", 3)).thenReturn(List.of(WEAK));
        mvc.perform(get("/api/notions/weak").with(TestTokens.as(7)).param("course", "statistics").param("limit", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].notionId").value("k_means"))
                .andExpect(jsonPath("$[0].average").value(1.5));
    }

    @Test
    void weakNotionsLimitBelowOneIs400() throws Exception {
        mvc.perform(get("/api/notions/weak").with(TestTokens.as(7)).param("course", "statistics").param("limit", "0"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void weakNotionsWithoutOrWithBadCourseIs400() throws Exception {
        mvc.perform(get("/api/notions/weak").with(TestTokens.as(7))).andExpect(status().isBadRequest());
        mvc.perform(get("/api/notions/weak").with(TestTokens.as(7)).param("course", "Bad Course!")).andExpect(status().isBadRequest());
    }

    @Test
    void historyListsScoresWithTheirTime() throws Exception {
        ScoreHistory first = new ScoreHistory("k_means", Source.FEYNMAN, 3, Instant.parse("2026-01-01T09:00:00Z"));
        ScoreHistory second = new ScoreHistory("k_means", Source.QUIZ, 5, Instant.parse("2026-01-03T09:00:00Z"));
        when(service.history(7L, "data-science")).thenReturn(List.of(first, second));
        mvc.perform(get("/api/scores").with(TestTokens.as(7)).param("course", "data-science"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].source").value("FEYNMAN"))
                .andExpect(jsonPath("$[0].createdAt").value("2026-01-01T09:00:00Z"))
                .andExpect(jsonPath("$[1].score").value(5));
    }

    @Test
    void historyWithBadCourseIs400() throws Exception {
        mvc.perform(get("/api/scores").with(TestTokens.as(7)).param("course", "Bad Course!")).andExpect(status().isBadRequest());
    }

    @Test
    void masteryListsEveryScoredNotion() throws Exception {
        when(service.mastery(7L, "data-science")).thenReturn(List.of(WEAK));
        mvc.perform(get("/api/mastery").with(TestTokens.as(7)).param("course", "data-science"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].level").value("WEAK"));
    }

    @Test
    void withoutTokenIs401() throws Exception {
        mvc.perform(get("/api/mastery").param("course", "data-science")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/scores").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void eachUserReadsOnlyTheirOwnScores() throws Exception {
        when(service.mastery(8L, "data-science")).thenReturn(List.of());
        mvc.perform(get("/api/mastery").param("course", "data-science").with(TestTokens.as(8)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isEmpty());
        verify(service).mastery(8L, "data-science");
    }
}
