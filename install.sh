# install.sh
#!/bin/bash
# install.sh for T-LeX - Professional installer with progress, structure fix, and auto-launch

# Colors for beauty
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Spinner for progress
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    echo -n "$2 " 
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"${temp}"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Logo
show_logo() {
    echo -e "${MAGENTA}"
    echo "  _______ _      ______ _     _         "
    echo " |__   __| |     |  ____| |   | |        "
    echo "    | |  | |     | |__  | |   | |        "
    echo "    | |  | |     |  __| | |   | |        "
    echo "    | |  | |____ | |____| |___| |        "
    echo "    |_|  |______|______|______| |        "
    echo "                                         "
    echo -e "${GREEN}T-LeX: Super Fast Tunnel Tool 🚀${NC}"
    echo -e "${YELLOW}Author: Amirreza NP${NC}"
    echo -e "${YELLOW}GitHub: https://github.com/amirrezanp/tlex${NC}"
    echo ""
}

# Installation
show_logo
echo -e "${CYAN}Starting T-LeX Installation...${NC}"

sudo apt update -y &> /dev/null &
spinner $! "Updating packages"
echo -e "${GREEN}Done!${NC}"

sudo apt install -y git python3 python3-pip python3-venv certbot wireguard &> /dev/null &
spinner $! "Installing prerequisites"
echo -e "${GREEN}Done!${NC}"

REPO_DIR="/opt/tlex"
sudo mkdir -p $REPO_DIR
if [ -d "$REPO_DIR/.git" ]; then
    sudo git -C $REPO_DIR pull &> /dev/null &
    spinner $! "Pulling latest"
else
    sudo git clone https://github.com/amirrezanp/tlex.git $REPO_DIR &> /dev/null &
    spinner $! "Cloning repo"
fi
echo -e "${GREEN}Done!${NC}"

cd $REPO_DIR

# Fix structure if flat
if [ ! -d "tlex" ]; then
    sudo mkdir tlex
    sudo mv *.py tlex/ 2>/dev/null || true
    echo "__version__ = '1.3.0'" | sudo tee tlex/__init__.py > /dev/null
fi

sudo python3 -m venv venv &> /dev/null &
spinner $! "Creating venv"
echo -e "${GREEN}Done!${NC}"

source venv/bin/activate
pip install . &> /dev/null &
spinner $! "Installing package"
echo -e "${GREEN}Done!${NC}"

cat << EOF | sudo tee /usr/local/bin/tlex > /dev/null
#!/bin/bash
source $REPO_DIR/venv/bin/activate
python -m tlex.main \$@
EOF
sudo chmod +x /usr/local/bin/tlex

export PATH=$PATH:/usr/local/bin

echo -e "${GREEN}T-LeX installed!${NC}"

echo -e "${CYAN}Launching T-LeX...${NC}"
tlex run