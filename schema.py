
import sqlite3

CURRENT_SCHEMA_VERSION=1

def db_check_schema(build_db, required_version):
    c = build_db.cursor()


    c.execute('''SELECT count(*)
                   FROM sqlite_master
                  WHERE type='table'
              ''')
    tables_count = c.fetchone()[0]
    # print('tables_count: %s' % (str(tables_count)))
    tables_exist = (tables_count > 0)


    if not tables_exist:
        return False
    

    c.execute('''SELECT count(*)
                   FROM sqlite_master
                  WHERE type='table' AND name='schema_version'
              ''')
    schema_version_count = c.fetchone()[0]
    # print('schema_version_count: %s' % (str(schema_version_count)))
    schema_version_table_exist = (schema_version_count == 1)

    if (tables_exist and not schema_version_table_exist):
        raise Exception('Database corrupted',
                        'Schema not empty but no schema_version table.')


    c.execute('''SELECT count(*)
                   FROM schema_version
              ''')
    schema_version_rowcount = c.fetchone()[0]
    # print('schema_version_rowcount: %s' % (str(schema_version_rowcount)))
    schema_version_available = (schema_version_rowcount == 1)
    
    if not schema_version_available:
        raise Exception('Database corrupted',
                        'Schema version could not be established')


    c.execute('''SELECT version
                   FROM schema_version
              ''')
    schema_version = c.fetchone()[0]
    # print('schema_version: %s' % (str(schema_version)))
    schema_version_ok = (schema_version_rowcount == required_version)
    
    if not schema_version_ok:
        raise Exception('Database corrupted',
                        'Wrong schema version %s (required %s)'
                        % (str(schema_version), str(required_version)))

    # schema exists
    return True
    

def db_prepare_schema(build_db, schema_version):
    c = build_db.cursor()
    c.execute('''CREATE TABLE build_targets
                 (path TEXT PRIMARY KEY,
                  type TEXT,
                  extension TEXT)
              ''')
    c.execute('''CREATE UNIQUE INDEX build_targets_uk
                 ON build_targets (path)
              ''')

    c.execute('''CREATE TABLE build_dirs
                 (path TEXT PRIMARY KEY,
                  arch TEXT,
                  tool TEXT)
              ''')
    c.execute('''CREATE UNIQUE INDEX build_dirs_uk
                 ON build_dirs (path)
              ''')

    c.execute('''CREATE TABLE build_runs
                 (id INTEGER PRIMARY KEY,
                  builddir_path TEXT,
                  log_file TEXT,
                  run_date DATETIME,
                  run_time NUMERIC,
                  FOREIGN KEY (builddir_path) REFERENCES build_dirs)
              ''')
    c.execute('''CREATE UNIQUE INDEX build_runs_uk
                 ON build_runs (builddir_path, run_date)
              ''')

    c.execute('''CREATE TABLE run_commands
                 (id INTEGER PRIMARY KEY,
                  run_id INTEGER,
                  command_num INTEGER,
                  command_text TEXT,
                  target_path TEXT,
                  canonical_text TEXT,
                  FOREIGN KEY (run_id) REFERENCES build_runs,
                  FOREIGN KEY (target_path) REFERENCES build_targets)
              ''')
    c.execute('''CREATE UNIQUE INDEX run_commands_uk
                 ON run_commands (run_id, target_path)
              ''')

    c.execute('''CREATE TABLE last_commands
                 (target_path TEXT,
                  builddir_path TEXT,
                  command_id INTEGER,
                  PRIMARY KEY (target_path, builddir_path),
                  FOREIGN KEY (target_path) REFERENCES build_targets,
                  FOREIGN KEY (builddir_path) REFERENCES build_dirs,
                  FOREIGN KEY (command_id) REFERENCES run_commands)
              ''')
    c.execute('''CREATE UNIQUE INDEX last_commands_uk
                 ON last_commands (target_path, builddir_path)
              ''')

    c.execute('''CREATE TABLE schema_version
                 (version INTEGER)
              ''')

    c.execute('''INSERT INTO schema_version (version)
                 VALUES (?)
              ''', (schema_version,))

    build_db.commit()
