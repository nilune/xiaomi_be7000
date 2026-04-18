#!/bin/sh

# --- Configuration ---
export USB_DIR="/mnt/usb-ef8d1024"
export SYSTEM_DIR="${USB_DIR}/System"

exec >> "/data/usr/log/startup.log" 2>&1

echo "===== $(date '+%F %T') /data/startup.sh started ====="
mkdir -p "/data/usr/bin" "/data/usr/share"

# --- Set up system path and system settings ---
mkdir -p /etc/profile.d
cat > /etc/profile.d/custom.sh <<EOF
export ROUTER_USB_DIR=${USB_DIR}
export PATH=${USB_DIR}/mi_docker/docker-binaries:/data/usr/bin:${PATH}
EOF

# --- Function for starting all components ---
do_startup() {
    sleep 30

    echo "Run AdGuard Home..."
    /data/services/adguardhome.sh

    echo "Run V2rayA (with XRay)..."
    /data/services/v2raya.sh
}

# --- Run in background ---
do_startup &
exit 0
