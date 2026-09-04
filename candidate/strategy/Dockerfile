# Your strategy goes here. Replace this file (and add your source) so that the
# container builds and runs your market maker.
#
# Requirements:
#   - The container must connect to the exchange's NATS at $NATS_URL
#     (inside the compose network that is nats://nats:4222).
#   - It must run your strategy as its CMD/ENTRYPOINT (no host dependencies).
#
# Example skeletons (delete what you don't use):
#
#   # Rust
#   FROM rust:1 AS build
#   WORKDIR /app
#   COPY . .
#   RUN cargo build --release
#   FROM debian:stable-slim
#   COPY --from=build /app/target/release/<your-bin> /usr/local/bin/strategy
#   ENV NATS_URL=nats://nats:4222
#   CMD ["strategy"]
#
#   # Go
#   FROM golang:1 AS build
#   WORKDIR /app
#   COPY . .
#   RUN go build -o /strategy .
#   FROM gcr.io/distroless/base-debian12
#   COPY --from=build /strategy /strategy
#   ENV NATS_URL=nats://nats:4222
#   CMD ["/strategy"]
#
# Placeholder so `docker compose --profile strategy up` works before you start:
FROM alpine
CMD ["sh", "-c", "echo 'Put your strategy in ./strategy/ and replace this Dockerfile.'; sleep infinity"]
