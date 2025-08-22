# search/migrations/0002_fulltext_mysql.py
from django.db import migrations

APP_LABEL = "search"
TABLE = "search_searchablecontent"
INDEX = "search_ft_idx"
PARSER = ""  # اگر ngram دارید: ' WITH PARSER ngram'

SQL_ENSURE_TABLE_OPTS = f"""
ALTER TABLE `{TABLE}` ENGINE=InnoDB,
  CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"""

SQL_CREATE_GENERATED = f"""
ALTER TABLE `{TABLE}`
    ADD COLUMN `fulltext_all` TEXT
    GENERATED ALWAYS AS (
        CONCAT_WS(
            ' ',
            COALESCE(title,''),
            COALESCE(content,''),
            COALESCE(search_vector,''),
            COALESCE(metadata_text,'')
        )
    ) STORED;
"""

SQL_DROP_GENERATED = f"ALTER TABLE `{TABLE}` DROP COLUMN `fulltext_all`;"

SQL_CONDITIONAL_DROP_INDEX = f"""
SET @idx := (SELECT INDEX_NAME
             FROM information_schema.STATISTICS
             WHERE TABLE_SCHEMA = DATABASE()
               AND TABLE_NAME = '{TABLE}'
               AND INDEX_NAME = '{INDEX}'
             LIMIT 1);
SET @sql := IF(@idx IS NOT NULL, 'ALTER TABLE `{TABLE}` DROP INDEX `{INDEX}`;', 'SELECT 1;');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
""".replace("{TABLE}", TABLE).replace("{INDEX}", INDEX)

SQL_ADD_FULLTEXT = f"""
ALTER TABLE `{TABLE}`
    ADD FULLTEXT INDEX `{INDEX}` (`fulltext_all`){PARSER};
"""

SQL_DROP_FULLTEXT = f"ALTER TABLE `{TABLE}` DROP INDEX `{INDEX}`;"

class Migration(migrations.Migration):
    dependencies = [
        (APP_LABEL, "0001_initial"),
    ]
    operations = [
        migrations.RunSQL(sql=SQL_ENSURE_TABLE_OPTS, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=SQL_CREATE_GENERATED, reverse_sql=SQL_DROP_GENERATED),
        migrations.RunSQL(sql=SQL_CONDITIONAL_DROP_INDEX, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=SQL_ADD_FULLTEXT, reverse_sql=SQL_DROP_FULLTEXT),
    ]