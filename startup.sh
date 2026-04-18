#!/bin/sh

# --- Configuration ---
export USB_DIR="/mnt/usb-ef8d1024"
export SYSTEM_DIR="${USB_DIR}/System"

exec >> "/data/usr/log/startup.log" 2>&1

# --- Start log ---
echo "===== $(date '+%F %T') /data/startup.sh started ====="
mkdir -p "/data/usr/bin" "/data/usr/share"

# --- Set up system settings ---
mkdir -p /etc/profile.d

# --- Function for starting all components ---
do_startup() {
    # Wait for network, external disk, ntp to be ready
    sleep 30

    echo "Run Core script..."
    /data/services/core.sh

    echo "Run AdGuard Home..."
    /data/services/adguardhome.sh

    echo "Run V2rayA (with XRay)..."
    /data/services/v2raya.sh
}

# --- Run in background ---
do_startup &
exit 0
