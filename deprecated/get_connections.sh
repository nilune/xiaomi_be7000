#!/bin/sh

get_name() {
    mac="$1"

    name=$(grep -i "^$mac" /etc/ethers 2>/dev/null | awk '{print $2}')
    [ -z "$name" ] && name=$(grep -i "$mac" /tmp/dhcp.leases 2>/dev/null | awk '{print $4}')
    [ -z "$name" ] && name=$(uci show dhcp | grep -i "$mac" -B2 | grep name | cut -d"'" -f2)

    echo "${name:-unknown}"
}

get_ssid() {
    iwinfo "$1" info 2>/dev/null | awk -F'"' '/ESSID/ {print $2}'
}

echo "=== WiFi clients ==="

iw dev | awk '
/Interface/ {iface=$2}
/type AP/ {print iface}
' | while read ifname; do

    ssid=$(get_ssid "$ifname")
    [ -z "$ssid" ] && continue

    echo ""
    echo "--- $ifname ($ssid) ---"
    printf "%-20s %-28s %-8s %-10s\n" "MAC" "NAME" "SIGNAL" "RATE"

    iwinfo "$ifname" assoclist 2>/dev/null \
    | grep -E '([0-9A-F]{2}:){5}[0-9A-F]{2}' \
    | while read line; do

        mac=$(echo "$line" | awk '{print $1}')

        # сигнал
        signal=$(echo "$line" | awk '{
            for(i=1;i<=NF;i++){
                if($i ~ /^-[0-9]+$/ && $(i+1)=="dBm"){
                    print $i
                    break
                }
            }
        }')

        # bitrate (первое число > 0 после сигнала)
        rate=$(echo "$line" | awk '{
            found=0
            for(i=1;i<=NF;i++){
                if($i ~ /^-[0-9]+$/ && $(i+1)=="dBm"){
                    found=1
                    continue
                }
                if(found && $i ~ /^[0-9]+$/){
                    print $i
                    break
                }
            }
        }')

        name=$(get_name "$mac")

        printf "%-20s %-28s %-8s %-10s\n" \
            "$mac" "$name" "${signal:-?}" "${rate:-?}"
    done
done