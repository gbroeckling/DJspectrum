#!/bin/bash
# ============================================================
# LED Panel Controller - Installation Script
# Run on your Raspberry Pi 4/5 (Raspberry Pi OS / Debian)
# ============================================================
set -e

INSTALL_DIR="/opt/ledpanel"
SERVICE_NAME="ledpanel"
VENV_DIR="${INSTALL_DIR}/venv"

echo "╔══════════════════════════════════════════╗"
echo "║   LED Panel Controller - Installer       ║"
echo "║   Colorlight 5A-75B + P1.86 Panels       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root: sudo bash install.sh"
    exit 1
fi

# Check for Raspberry Pi or Linux
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Install with: sudo apt install python3"
    exit 1
fi

echo "[1/7] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3-venv \
    python3-dev \
    python3-pip \
    python3-pyaudio \
    portaudio19-dev \
    fonts-dejavu-core \
    ethtool \
    net-tools

echo "[2/7] Creating install directory..."
mkdir -p "${INSTALL_DIR}"
cp -r ./*.py "${INSTALL_DIR}/"
cp -r ./config.yaml "${INSTALL_DIR}/"
cp -r ./requirements.txt "${INSTALL_DIR}/"
[ -d ./fonts ] && cp -r ./fonts "${INSTALL_DIR}/"

echo "[3/7] Creating Python virtual environment..."
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

echo "[4/7] Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "${INSTALL_DIR}/requirements.txt"

echo "[5/7] Setting raw socket capability on Python..."
# This allows running without sudo after installation
PYTHON_BIN=$(readlink -f "${VENV_DIR}/bin/python3")
setcap cap_net_raw+ep "${PYTHON_BIN}" 2>/dev/null || {
    echo "  WARNING: Could not set CAP_NET_RAW. Service will run as root."
}

echo "[6/7] Detecting Gigabit Ethernet interface..."
# Find the first Gigabit Ethernet interface
GBE_IFACE=""
for iface in $(ls /sys/class/net/ | grep -v lo); do
    speed=$(cat "/sys/class/net/${iface}/speed" 2>/dev/null || echo "0")
    if [ "$speed" -ge 1000 ] 2>/dev/null; then
        GBE_IFACE="$iface"
        break
    fi
done

if [ -z "$GBE_IFACE" ]; then
    echo "  WARNING: No Gigabit Ethernet link detected!"
    echo "  Make sure your Pi is connected to the Colorlight via Gigabit Ethernet."
    echo "  Common interfaces: eth0, end0, enp1s0"
    echo ""
    echo "  Defaulting to: eth0"
    GBE_IFACE="eth0"
else
    echo "  Found Gigabit interface: ${GBE_IFACE} ($(cat /sys/class/net/${GBE_IFACE}/speed)Mbps)"
fi

# Update config with detected interface
sed -i "s/interface: eth0/interface: ${GBE_IFACE}/" "${INSTALL_DIR}/config.yaml"

echo "[7/7] Installing systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << SERVICEEOF
[Unit]
Description=LED Panel Controller (Colorlight 5A-75B)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}
ExecStart=${VENV_DIR}/bin/python3 ${INSTALL_DIR}/main.py --config ${INSTALL_DIR}/config.yaml
Restart=always
RestartSec=5
User=root

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ledpanel

# Security hardening
ProtectHome=read-only
ProtectSystem=strict
ReadWritePaths=${INSTALL_DIR}
NoNewPrivileges=false
AmbientCapabilities=CAP_NET_RAW

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Installation Complete!                  ║"
echo "╠══════════════════════════════════════════╣"
echo "║                                           ║"
echo "║   BEFORE STARTING:                        ║"
echo "║   1. Edit config:                         ║"
echo "║      sudo nano ${INSTALL_DIR}/config.yaml ║"
echo "║      - Set your HA MQTT broker IP         ║"
echo "║      - Set MQTT username/password         ║"
echo "║      - Verify Ethernet interface          ║"
echo "║                                           ║"
echo "║   2. Configure Colorlight 5A-75B:         ║"
echo "║      (One-time setup with LEDVision)      ║"
echo "║      See README for instructions          ║"
echo "║                                           ║"
echo "║   COMMANDS:                                ║"
echo "║   Start:   sudo systemctl start ledpanel  ║"
echo "║   Stop:    sudo systemctl stop ledpanel   ║"
echo "║   Status:  sudo systemctl status ledpanel ║"
echo "║   Logs:    journalctl -u ledpanel -f      ║"
echo "║   Test:    sudo ${VENV_DIR}/bin/python3 \  ║"
echo "║           ${INSTALL_DIR}/main.py --test    ║"
echo "║                                           ║"
echo "╚══════════════════════════════════════════╝"
