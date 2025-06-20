FROM alpine:latest

# Install SQLite
RUN apk add --no-cache sqlite

# Create data directory with proper permissions
RUN mkdir -p /data && chmod 777 /data

# Copy initialization script if needed
COPY init.sql /docker-entrypoint-initdb.d/

# Create a startup script
RUN echo '#!/bin/sh' > /startup.sh && \
    echo 'if [ ! -f /data/appointments.db ]; then' >> /startup.sh && \
    echo '  sqlite3 /data/appointments.db < /docker-entrypoint-initdb.d/init.sql' >> /startup.sh && \
    echo '  chmod 666 /data/appointments.db' >> /startup.sh && \
    echo 'fi' >> /startup.sh && \
    echo 'tail -f /dev/null' >> /startup.sh && \
    chmod +x /startup.sh

VOLUME ["/data"]

CMD ["/startup.sh"]