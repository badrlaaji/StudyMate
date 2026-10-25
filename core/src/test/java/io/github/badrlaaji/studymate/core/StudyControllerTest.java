package io.github.badrlaaji.studymate.core;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
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

/** Study routes: token required, goal limits, session update and trophies. */
@WebMvcTest(controllers = StudyController.class, properties = TestTokens.SECRET_PROPERTY)
@Import(SecurityConfig.class)
class StudyControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private StudyService study;

    @MockitoBean
    private TrophyService trophies;

    private void putGoal(int minutes, int expected) throws Exception {
        mvc.perform(put("/api/study/goal").with(TestTokens.as(7)).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"minutes\":" + minutes + ",\"timezone\":\"Africa/Casablanca\"}"))
                .andExpect(status().is(expected));
    }

    @Test
    void goalMustBeFiveTo480Minutes() throws Exception {
        when(study.setGoal(eq(7L), any())).thenReturn(new StudyGoal(7L, 5, "Africa/Casablanca"));
        putGoal(4, 400);
        putGoal(481, 400);
        putGoal(5, 200);
    }

    @Test
    void withoutTokenIs401() throws Exception {
        mvc.perform(get("/api/study/summary")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/trophies")).andExpect(status().isUnauthorized());
    }

    @Test
    void updateSendsTheTotalOfActiveSeconds() throws Exception {
        when(study.update(eq(7L), eq(3L), eq(120L), any())).thenReturn(new StudyViews.Session(
                3L, "data-science", StudyMode.CAMERA, Instant.EPOCH, 120, List.of("FIRST_STEPS")));
        mvc.perform(patch("/api/study/sessions/3").with(TestTokens.as(7)).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"activeSeconds\":120}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.newTrophies[0]").value("FIRST_STEPS"));
        mvc.perform(patch("/api/study/sessions/3").with(TestTokens.as(7)).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"activeSeconds\":-1}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void trophiesListsAllSix() throws Exception {
        when(trophies.list(7L)).thenReturn(TrophyRules.CODES.stream().map(code -> new TrophyView(code, null)).toList());
        mvc.perform(get("/api/trophies").with(TestTokens.as(7)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(6));
    }
}
