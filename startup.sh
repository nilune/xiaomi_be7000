#!/bin/sh

# --- Configuration ---
export USB_DIR="/mnt/usb-ef8d1024"
export SYSTEM_DIR="${USB_DIR}/System"

exec >> "/data/usr/log/startup.log" 2>&1

echo "===== $(date '+%F %T') /data/startup.sh started ====="
mkdir -p "/data/usr/bin" "/data/usr/share"

# --- Set up system settings ---
mkdir -p /etc/profile.d
# Set variables
eval "cat <<EOF
$(cat "${SYSTEM_DIR}/core/etc/profile.d/custom.sh")
EOF
" > /etc/profile.d/custom.sh
# Set nginx config
ln -sfn "${SYSTEM_DIR}/core/etc/nginx/conf.d/router.conf" "/etc/nginx/conf.d/router.conf"

# --- Function for starting all components ---
do_startup() {
    sleep 60

    echo "Run AdGuard Home..."
    /data/services/adguardhome.sh

    echo "Run V2rayA (with XRay)..."
    /data/services/v2raya.sh

    echo "Reload nginx..."
    service nginx reload
}

# --- Run in background ---
do_startup &
exit 0
