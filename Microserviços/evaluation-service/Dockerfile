FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -o /out/evaluation-service .

FROM alpine:3.20
RUN addgroup -S app && adduser -S -G app app
COPY --from=build /out/evaluation-service /usr/local/bin/evaluation-service
USER app
EXPOSE 8004
ENTRYPOINT ["evaluation-service"]
