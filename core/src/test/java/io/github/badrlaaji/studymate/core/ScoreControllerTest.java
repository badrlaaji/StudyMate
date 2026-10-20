package io.github.badrlaaji.studymate.core;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/** One test per endpoint; the service is a mock, no database. */
@WebMvcTest(ScoreController.class)
class ScoreControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private MasteryService service;

    private static final NotionMastery WEAK = new NotionMastery("k_means", 1.5, 2, "WEAK");

    @Test
    void postScoreReturns201AndTheNotionMastery() throws Exception {
        when(service.mastery()).thenReturn(List.of(WEAK));
        mvc.perform(post("/api/scores")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"notionId\":\"k_means\",\"source\":\"QUIZ\",\"score\":2}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.notionId").value("k_means"))
                .andExpect(jsonPath("$.level").value("WEAK"));
        verify(service).record(any(ScoreRequest.class));
    }

    @Test
    void postScoreOutOfRangeIs400() throws Exception {
        mvc.perform(post("/api/scores")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"notionId\":\"k_means\",\"source\":\"QUIZ\",\"score\":7}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void postScoreWithBadNotionIdIs400() throws Exception {
        mvc.perform(post("/api/scores")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"notionId\":\"K Means!\",\"source\":\"FEYNMAN\",\"score\":3}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void weakNotionsUseTheLimit() throws Exception {
        when(service.weak(3)).thenReturn(List.of(WEAK));
        mvc.perform(get("/api/notions/weak").param("limit", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].notionId").value("k_means"))
                .andExpect(jsonPath("$[0].average").value(1.5));
    }

    @Test
    void weakNotionsLimitBelowOneIs400() throws Exception {
        mvc.perform(get("/api/notions/weak").param("limit", "0")).andExpect(status().isBadRequest());
    }

    @Test
    void masteryListsEveryScoredNotion() throws Exception {
        when(service.mastery()).thenReturn(List.of(WEAK));
        mvc.perform(get("/api/mastery"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].level").value("WEAK"));
    }
}
