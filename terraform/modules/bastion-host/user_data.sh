#!/bin/bash

# Update system
yum update -y

# Install required packages
yum install -y postgresql15 postgresql15-server git htop

# Create migration directory
mkdir -p /opt/migration
cd /opt/migration

# Create migration script
cat > /opt/migration/migrate_database.sh << 'EOF'
#!/bin/bash

set -e

DB_HOST="${db_host}"
DB_PORT="${db_port}"
DB_USERNAME="${db_username}"
DB_PASSWORD="${db_password}"
S3_BUCKET="${s3_bucket_name}"

echo "Starting database migration..."

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to execute SQL with error handling
execute_sql() {
    local sql="$1"
    local description="$2"

    log "Executing: $description"
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d postgres -c "$sql"; then
        log "SUCCESS: $description"
    else
        log "ERROR: $description"
        return 1
    fi
}

# Check database connectivity
log "Checking database connectivity..."
if PGPASSWORD="$DB_PASSWORD" pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME"; then
    log "Database is ready"
else
    log "Database connection failed"
    exit 1
fi

# Create databases if they don't exist
databases=("auth_db" "exercises_db" "scores_db")

for db in "${databases[@]}"; do
    log "Creating database: $db"
    PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" "$db" 2>/dev/null || log "Database $db already exists"
done

# Download migration files from S3 (if exists)
if aws s3 ls "s3://$S3_BUCKET/migration/" 2>/dev/null; then
    log "Downloading migration files from S3..."
    aws s3 cp "s3://$S3_BUCKET/migration/" /opt/migration/files/ --recursive --exclude "*" --include "*.sql" || log "No migration files found in S3"
else
    log "No migration files found in S3 bucket"
fi

# Create tables for each database
for db in "${databases[@]}"; do
    log "Setting up database schema for: $db"

    case $db in
        "auth_db")
            # Create users table
            execute_sql "CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                active BOOLEAN DEFAULT true,
                admin BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )" "Create users table in $db"
            ;;

        "exercises_db")
            # Create exercises table
            execute_sql "CREATE TABLE IF NOT EXISTS exercises (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                body TEXT NOT NULL,
                difficulty VARCHAR(20) CHECK (difficulty IN ('easy', 'medium', 'hard')),
                test_cases JSONB,
                solutions JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )" "Create exercises table in $db"
            ;;

        "scores_db")
            # Create scores table
            execute_sql "CREATE TABLE IF NOT EXISTS scores (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                answer TEXT,
                results JSONB,
                user_results JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )" "Create scores table in $db"
            ;;
    esac
done

# Apply any migration files if they exist
if [ -d "/opt/migration/files" ]; then
    for db in "${databases[@]}"; do
        if [ -f "/opt/migration/files/${db}_data.sql" ]; then
            log "Applying data migration for $db..."
            PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USERNAME" -d "$db" -f "/opt/migration/files/${db}_data.sql"
        fi
    done
fi

# Create indexes
log "Creating indexes..."
execute_sql "CREATE INDEX IF NOT EXISTS idx_users_email ON auth_db.users(email)" "Create email index on users"
execute_sql "CREATE INDEX IF NOT EXISTS idx_users_username ON auth_db.users(username)" "Create username index on users"
execute_sql "CREATE INDEX IF NOT EXISTS idx_exercises_difficulty ON exercises_db.exercises(difficulty)" "Create difficulty index on exercises"
execute_sql "CREATE INDEX IF NOT EXISTS idx_scores_user_exercise ON scores_db.scores(user_id, exercise_id)" "Create composite index on scores"

# Create functions for updated_at triggers
for db in "${databases[@]}"; do
    execute_sql "CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql'" "Create updated_at function in $db"
done

# Create triggers
execute_sql "CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON auth_db.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()" "Create users trigger"
execute_sql "CREATE TRIGGER update_exercises_updated_at BEFORE UPDATE ON exercises_db.exercises FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()" "Create exercises trigger"
execute_sql "CREATE TRIGGER update_scores_updated_at BEFORE UPDATE ON scores_db.scores FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()" "Create scores trigger"

# Grant necessary permissions
log "Setting up permissions..."
execute_sql "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres" "Grant permissions on tables"
execute_sql "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres" "Grant permissions on sequences"

# Log completion
log "Database migration completed successfully!"
log "Databases created: ${databases[*]}"
log "Database endpoint: $DB_HOST:$DB_PORT"

# Create status file
echo "MIGRATION_COMPLETED_AT=$(date '+%Y-%m-%d %H:%M:%S')" > /opt/migration/status.txt
echo "DATABASES=${databases[*]}" >> /opt/migration/status.txt
echo "DB_ENDPOINT=$DB_HOST:$DB_PORT" >> /opt/migration/status.txt

EOF

# Make migration script executable
chmod +x /opt/migration/migrate_database.sh

# Create log directory
mkdir -p /var/log/migration

# Create crontab for automated log cleanup
echo "0 2 * * * find /var/log/migration -name '*.log' -mtime +7 -delete" > /etc/cron.d/migration-cleanup

# Create systemd service for migration
cat > /etc/systemd/system/migration.service << 'EOF'
[Unit]
Description=Database Migration Service
After=network.target

[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/opt/migration
ExecStart=/opt/migration/migrate_database.sh
StandardOutput=journal:/var/log/migration/migration.log
StandardError=journal:/var/log/migration/migration.error.log

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the migration service
systemctl daemon-reload
systemctl enable migration.service
systemctl start migration.service

echo "Bastion host setup completed!"
echo "Migration script is available at: /opt/migration/migrate_database.sh"
echo "Run it manually or use: systemctl start migration.service"