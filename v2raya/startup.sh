#!/bin/sh

# --- Configuration ---
V2RAYA_DIR="${SYSTEM_DIR}/v2raya"
mkdir -p "${V2RAYA_DIR}/etc/v2raya" "${V2RAYA_DIR}/workdir" "${V2RAYA_DIR}/log"

exec >> "${V2RAYA_DIR}/log/startup.log" 2>&1
echo "===== $(date '+%F %T') v2raya startup started ====="

# --- Create soft links ---
LINKS="
/etc/v2ray:${V2RAYA_DIR}/etc/v2ray
/etc/v2raya:${V2RAYA_DIR}/etc/v2raya
/etc/config/v2ray:${V2RAYA_DIR}/etc/config/v2ray
/etc/config/v2raya:${V2RAYA_DIR}/etc/config/v2raya
/etc/init.d/v2ray:${ADGUARD_DIR}/etc/init.d/v2ray
/etc/init.d/v2raya:${ADGUARD_DIR}/etc/init.d/v2raya
/data/usr/share/v2ray:${V2RAYA_DIR}/workdir
/data/usr/bin/v2ray:${V2RAYA_DIR}/usr/bin/v2ray
/data/usr/bin/v2raya:${V2RAYA_DIR}/usr/bin/v2raya
/data/usr/log/v2raya:${V2RAYA_DIR}/log
"

for target in $LINKS; do
    dest="${target%%:*}"
    src="${target##*:}"
    ln -sfn "$src" "$dest"
    echo "Linked $dest -> $src"
done

# --- Disable Enhanced Connection Manager ---
/etc/init.d/qca-nss-ecm stop
/etc/init.d/qca-nss-ecm disable

# --- Start and enable service ---
echo "Enable and start V2ray (core) service..."
/etc/init.d/v2ray start
/etc/init.d/v2ray enable

sleep 5

echo "Enable and start V2rayA (gui) service..."
/etc/init.d/v2raya enable
/etc/init.d/v2raya start
