#!/usr/bin/env bash
TCL_SCRIPT="compile_changed_libs.tcl"

echo "# Auto-generated: only new/updated libs" > "$TCL_SCRIPT"

find memory -type f -name '*.pglib' -print0 \
  | xargs -0 -n1 echo \
  | while IFS= read -r lib; do
    # 1) 提取库名
    name=$(basename "$lib" .pglib)
    # 2) 目标 .db 路径
    dbfile="memory/${name}.db"
    # 3) 只有当 .db 不存在 OR .pglib 比 .db 更新时，才加入编译命令
    if [ ! -f "$dbfile" ] || [ "$lib" -nt "$dbfile" ]; then
      echo "read_lib $lib" >> "$TCL_SCRIPT"
      echo "write_lib $name -format db -output $dbfile" >> "$TCL_SCRIPT"
    fi
done

echo "quit" >> "$TCL_SCRIPT"
