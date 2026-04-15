#!/bin/sh

# --- Configuration ---
ADGUARD_DIR="${SYSTEM_DIR}/adGuardHome"
mkdir -p "${ADGUARD_DIR}/workdir" "${ADGUARD_DIR}/log"
touch "${ADGUARD_DIR}/adguardhome.yaml"

exec >> "${ADGUARD_DIR}/startup.log" 2>&1
echo "===== $(date '+%F %T') adguardhome startup started ====="

# --- Create soft links ---
LINKS="
/etc/init.d/adguardhome:${ADGUARD_DIR}/etc/init.d/adguardhome
/run/adguardhome.pid:${ADGUARD_DIR}/adguardhome.pid
/var/lib/adguardhome:${ADGUARD_DIR}/workdir
/etc/config/adguardhome:${ADGUARD_DIR}/etc/config/adguardhome
/data/usr/bin/AdGuardHome:${ADGUARD_DIR}/usr/bin/AdGuardHome
/etc/adguardhome.yaml:${ADGUARD_DIR}/adguardhome.yaml
"

for target in $LINKS; do
    dest="${target%%:*}"
    src="${target##*:}"
    ln -sfn "$src" "$dest"
    echo "Linked $dest -> $src"
done

# --- Start and enable service ---
echo "Enable AdGuard Home service..."
/etc/init.d/adguardhome enable

echo "Start AdGuard Home service..."
/etc/init.d/adguardhome start
