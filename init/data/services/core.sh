#!/bin/sh

# --- Configuration ---
CORE_DIR="${SYSTEM_DIR}/core"
mkdir -p "${CORE_DIR}/log"

exec >> "${CORE_DIR}/log/startup.log" 2>&1
echo "===== $(date '+%F %T') core script startup started ====="

# --- Create soft links ---
LINKS="
/etc/nginx/conf.d/router.conf:${CORE_DIR}/etc/nginx/conf.d/router.conf
/etc/init.d/core:${CORE_DIR}/etc/init.d/core
/data/usr/bin/core:${CORE_DIR}/usr/bin/core.sh
/data/usr/log/core:${CORE_DIR}/log
"

for target in $LINKS; do
    dest="${target%%:*}"
    src="${target##*:}"
    ln -sfn "$src" "$dest"
    echo "Linked $dest -> $src"
done

# --- Set environment variables ---
echo "Set environment variables..."
eval "cat <<EOF
$(cat "${CORE_DIR}/etc/profile.d/custom.sh")
EOF
" > /etc/profile.d/custom.sh

# --- Start and enable service ---
echo "Enable Core service/script..."
/etc/init.d/core enable

echo "Start Core service/script..."
/etc/init.d/core start
