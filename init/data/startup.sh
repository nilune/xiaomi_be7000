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

# --- Run one service script if present ---
run_service() {
    service_name="$1"
    service_script="$2"

    if [ -x "$service_script" ]; then
        echo "Run ${service_name}..."
        "$service_script"
    else
        echo "Skip ${service_name}: ${service_script} not found or not executable"
    fi
}

# --- Function for starting all components ---
do_startup() {
    # Wait for network, external disk, ntp to be ready
    sleep 30

    run_service "Core" "/data/services/core.sh"
    run_service "AdGuard Home" "/data/services/adguardhome.sh"
    run_service "V2rayA (with XRay)" "/data/services/v2raya.sh"
}

# --- Run in background ---
do_startup &
exit 0
