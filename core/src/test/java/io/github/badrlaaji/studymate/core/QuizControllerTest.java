package io.github.badrlaaji.studymate.core;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

/** POST /api/quiz-answers: validation and the skipped status; the service is a mock. */
@WebMvcTest(controllers = QuizController.class, properties = TestTokens.SECRET_PROPERTY)
@Import(SecurityConfig.class)
class QuizControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private QuizService service;

    private static final String QUIZ = "\"quizId\":\"3f2a9c1e-0b7d-4e8a-9c55-1d2e3f4a5b6c\"";

    private ResultActions send(String answers) throws Exception {
        return mvc.perform(post("/api/quiz-answers")
                .with(TestTokens.as(7))
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"courseId\":\"data-science\"," + QUIZ + ",\"answers\":" + answers + "}"));
    }

    @Test
    void skippedQuestionIsAccepted() throws Exception {
        when(service.record(eq(7L), any(QuizResultRequest.class))).thenReturn(new QuizSummary(2, 1, 0, 1));
        send("[{\"notionId\":\"k_means\",\"status\":\"CORRECT\"},{\"notionId\":\"cnn\",\"status\":\"SKIPPED\"}]")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.skipped").value(1));
    }

    @Test
    void unknownStatusIs400() throws Exception {
        send("[{\"notionId\":\"k_means\",\"status\":\"PASSED\"}]").andExpect(status().isBadRequest());
    }

    @Test
    void emptyQuizIs400() throws Exception {
        send("[]").andExpect(status().isBadRequest());
    }

    @Test
    void badNotionIdIs400() throws Exception {
        send("[{\"notionId\":\"K Means!\",\"status\":\"CORRECT\"}]").andExpect(status().isBadRequest());
    }
}
