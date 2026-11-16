# Production backup image (S3-18): the PostgreSQL client tools plus OpenSSL for
# encrypted off-site copies (scripts/offsite_copy.sh). Same base as development.
FROM postgres:16-alpine
RUN apk add --no-cache openssl
