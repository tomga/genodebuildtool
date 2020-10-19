
import os

def store_build_info(build_db, build_info, build_name, build_tool, stamp_dt, arch,
                     log_file, run_time, abs_dir, rel_dir):

    c = build_db.cursor()

    args = (build_name, arch, build_tool)
    c.execute('''REPLACE INTO build_dirs (path, arch, tool)
                 VALUES (?, ?, ?)''', args)

    args = (build_name, log_file, stamp_dt, run_time)
    c.execute('''REPLACE INTO build_runs (builddir_path, log_file, run_date, run_time)
                 VALUES (?, ?, ?, ?)''', args)
    args = (build_name, stamp_dt)
    c.execute('SELECT id FROM build_runs WHERE builddir_path = ? and run_date = ?', args)
    result = c.fetchone()
    build_run_id, = result

    def store_run_command(outputs, sources, command_text, canonical_text):

        output_num = 0
        for output in outputs:
            args = (output, None, None)
            c.execute('''REPLACE INTO build_targets (path, type, extension)
                         VALUES (?, ?, ?)''', args)
            print(str(args))

            args = (build_run_id, output_num, command_text, output, canonical_text)
            c.execute('''REPLACE INTO run_commands (run_id, command_num, command_text,
                                                    target_path, canonical_text)
                         VALUES (?, ?, ?, ?, ?)''', args)
            args = (build_run_id, output)
            print(str(args))
            c.execute('SELECT id FROM run_commands WHERE run_id = ? and target_path = ?', args)
            result = c.fetchone()
            run_command_id, = result

            args = (output, build_name, run_command_id)
            c.execute('''REPLACE INTO last_commands (target_path, builddir_path, command_id)
                         VALUES (?, ?, ?)''', args)
            print(str(args))

    build_info.process(store_run_command, os.getcwd(), abs_dir, rel_dir)

    build_db.commit()
