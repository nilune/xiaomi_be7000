#!/bin/sh

LOG_DIR="/data/usr/log/v2raya"
TARGET_DIR="/data/usr/share/v2ray"

exec >> "${LOG_DIR}/update_geo.log" 2>&1
echo "===== $(date '+%F %T') update geo files ====="

# Check directory existence
if [ ! -d "$TARGET_DIR" ]; then
    echo "Dir $TARGET_DIR doesn't exist. Creating..."
    mkdir -p "$TARGET_DIR" || { echo "Cant create $TARGET_DIR."; exit 1; }
fi

# Function for downloading files
download_file() {
    local url=$1
    local output=$2

    echo "Loading file from URL: $url"
    curl -L --fail -A "Mozilla/5.0" -o "$output" "$url"
    if [ $? -eq 0 ]; then
        echo "Success while loading file: $output"
    else
        echo "ERROR while loading file: $url"
        exit 1
    fi
}

# geoip.dat
download_file "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geoip.dat" "$TARGET_DIR/geoip.dat"

# geosite.dat
download_file "https://github.com/runetfreedom/russia-v2ray-rules-dat/releases/latest/download/geosite.dat" "$TARGET_DIR/geosite.dat"

# https://github.com/Chocolate4U/Iran-v2ray-rules
download_file "https://raw.githubusercontent.com/Chocolate4U/Iran-v2ray-rules/release/geoip.dat" "$TARGET_DIR/iranGeoip.dat"