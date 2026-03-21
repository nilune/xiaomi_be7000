#!/bin/sh

# --- Configuration ---
export USB_DIR="/mnt/usb-1210d517"
export SYSTEM_DIR="${USB_DIR}/System"

exec >> "/data/usr/log/startup.log" 2>&1

echo "===== $(date '+%F %T') /data/startup.sh started ====="
mkdir -p "/data/usr/bin" "/data/usr/share"

# --- Set up system path ---
mkdir -p /etc/profile.d
echo "export PATH=${USB_DIR}/mi_docker/docker-binaries:${PATH}" > /etc/profile.d/custom.sh

# --- Function for starting all components ---
do_startup() {
    sleep 30

    echo "Run AdGuard Home..."
    /data/services/adguardhome.sh

    echo "Run V2ray and V2rayA..."
    /data/services/v2raya.sh
}

# --- Run in background ---
do_startup &
exit 0
