FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -o /out/auth-service .

FROM alpine:3.20
RUN addgroup -S app && adduser -S -G app app
COPY --from=build /out/auth-service /usr/local/bin/auth-service
USER app
EXPOSE 8001
ENTRYPOINT ["auth-service"]
