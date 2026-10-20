# StudyMate mastery service (Spring Boot). Build from core/: docker build -t studymate-core .
FROM eclipse-temurin:21-jdk AS build
WORKDIR /app
COPY .mvn .mvn
COPY mvnw pom.xml ./
RUN ./mvnw -B -q dependency:go-offline
COPY src src
RUN ./mvnw -B -q package -DskipTests

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/target/core-0.0.1-SNAPSHOT.jar app.jar
RUN useradd --create-home studymate
USER studymate
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
