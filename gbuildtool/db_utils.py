
import sqlite3

def clear_build_info(build_db, build_dir):

    c = build_db.cursor()

    c.execute('''delete from last_commands
                       where builddir_path = ?''',
              (build_dir,))

    c.execute('''delete from run_commands
                       where run_id in (select id
                                          from build_runs
                                         where builddir_path = ?)''',
              (build_dir,))

    c.execute('''delete from build_runs
                       where builddir_path = ?''',
              (build_dir,))

    c.execute('''delete from build_dirs
                       where path = ?''',
              (build_dir,))

    build_db.commit()


def compare_builds(build_db, build_dir1, build_dir2):
    
    print("Comparing builds: %s %s" % (build_dir1, build_dir2))
    c = build_db.cursor()
    #cmp_mode = ''
    cmp_mode = '_noincsort'
    c.execute('''select bd.arch, bd.tool, lc.target_path
                      , rc.canonical{cmp_mode}_text, rc.command_text, rc.command_num
                   from last_commands lc
                      , run_commands rc
                      , build_targets bt
                      , build_runs br
                      , build_dirs bd
              where lc.builddir_path = bd.path
                and lc.target_path = bt.path
                and lc.command_id = rc.id
                and rc.run_id = br.id
                and bd.path in (?, ?)
              group by bd.arch, lc.target_path, rc.command_num, rc.canonical{cmp_mode}_text
             having count(*) < 2
              order by bd.arch, lc.target_path, rc.command_num, bd.tool'''
              .format(cmp_mode=cmp_mode),
              (build_dir1, build_dir2))

    last_arch = ''
    last_tgt_path = ''
    last_cmd_num = ''
    inconsistencies_count = 0
    for arch, tool, tgt_path, can_text, cmd_text, cmd_num in c:
        if (arch != last_arch
            or tgt_path != last_tgt_path
            or cmd_num != last_cmd_num):

            print("Inconsistency: %s %s" % (arch, tgt_path))
            inconsistencies_count += 1
            last_arch = arch
            last_tgt_path = tgt_path
            last_cmd_num = cmd_num

        print(" %s can: %s" % (tool.ljust(5), can_text))
        print(" %s org: %s" % (tool.ljust(5), cmd_text))

    if inconsistencies_count == 0:
        print("No inconsistencies.")
    else:
        print("Found %s inconsistencies." % (str(inconsistencies_count)))

    return (inconsistencies_count == 0)
