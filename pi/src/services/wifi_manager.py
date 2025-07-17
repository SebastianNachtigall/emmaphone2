"""
WiFi Manager for EmmaPhone2 Pi

Manages WiFi connections and AP mode for setup
"""
import asyncio
import logging
import subprocess
import json
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class WiFiManager:
    """Manages WiFi connections and AP mode"""
    
    def __init__(self):
        self.ap_mode = False
        self.current_ssid = None
        
    async def is_connected(self) -> bool:
        """Check if connected to WiFi"""
        try:
            # Check if we have an IP address
            result = await self._run_command("ip route get 8.8.8.8")
            return "via" in result
        except:
            return False
    
    async def get_current_ssid(self) -> Optional[str]:
        """Get currently connected WiFi SSID"""
        try:
            result = await self._run_command("iwgetid -r")
            return result.strip() if result.strip() else None
        except:
            return None
    
    async def get_signal_strength(self) -> int:
        """Get WiFi signal strength (0-100)"""
        try:
            result = await self._run_command("iwconfig wlan0 | grep 'Signal level'")
            if "Signal level=" in result:
                # Extract signal level (format: Signal level=-50 dBm)
                signal = result.split("Signal level=")[1].split(" ")[0]
                dbm = int(signal)
                
                # Convert dBm to percentage (rough approximation)
                if dbm >= -50:
                    return 100
                elif dbm <= -100:
                    return 0
                else:
                    return int(2 * (dbm + 100))
            
            return 0
        except:
            return 0
    
    async def scan_networks(self) -> List[Dict]:
        """Scan for available WiFi networks"""
        logger.info("🔍 Scanning for WiFi networks...")
        
        try:
            # Trigger scan
            await self._run_command("sudo iwlist wlan0 scan")
            await asyncio.sleep(2)
            
            # Get scan results
            result = await self._run_command("sudo iwlist wlan0 scan | grep -E '(ESSID|Signal|Encryption)'")
            
            networks = []
            current_network = {}
            
            for line in result.split('\n'):
                line = line.strip()
                
                if 'ESSID:' in line:
                    if current_network:
                        networks.append(current_network)
                    
                    ssid = line.split('ESSID:')[1].strip('"')
                    current_network = {'ssid': ssid}
                
                elif 'Signal level=' in line:
                    signal = line.split('Signal level=')[1].split(' ')[0]
                    try:
                        dbm = int(signal)
                        strength = max(0, min(100, 2 * (dbm + 100)))
                        current_network['signal'] = strength
                    except:
                        current_network['signal'] = 0
                
                elif 'Encryption key:' in line:
                    encrypted = 'on' in line
                    current_network['encrypted'] = encrypted
            
            if current_network:
                networks.append(current_network)
            
            # Filter out empty SSIDs and sort by signal strength
            networks = [n for n in networks if n.get('ssid') and n['ssid'] != '']
            networks.sort(key=lambda x: x.get('signal', 0), reverse=True)
            
            logger.info(f"✅ Found {len(networks)} networks")
            return networks
            
        except Exception as e:
            logger.error(f"❌ Failed to scan networks: {e}")
            return []
    
    async def connect_to_network(self, ssid: str, password: str = None) -> bool:
        """Connect to a WiFi network"""
        logger.info(f"🔗 Connecting to network: {ssid}")
        
        try:
            # Create wpa_supplicant configuration
            config = self._create_wpa_config(ssid, password)
            
            # Write temporary config file
            temp_config = "/tmp/wpa_supplicant_temp.conf"
            with open(temp_config, 'w') as f:
                f.write(config)
            
            # Kill any existing wpa_supplicant
            await self._run_command("sudo pkill wpa_supplicant", ignore_error=True)
            await asyncio.sleep(1)
            
            # Start wpa_supplicant
            await self._run_command(f"sudo wpa_supplicant -B -i wlan0 -c {temp_config}")
            await asyncio.sleep(3)
            
            # Get IP address
            await self._run_command("sudo dhclient wlan0")
            await asyncio.sleep(5)
            
            # Check if connected
            if await self.is_connected():
                self.current_ssid = ssid
                
                # Save to permanent config
                await self._save_network_config(ssid, password)
                
                logger.info(f"✅ Connected to {ssid}")
                return True
            else:
                logger.error(f"❌ Failed to connect to {ssid}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error connecting to {ssid}: {e}")
            return False
    
    async def start_ap_mode(self, ssid: str = "EmmaPhone-Setup", password: str = "EmmaPhone2024"):
        """Start WiFi Access Point mode for setup"""
        logger.info(f"📡 Starting AP mode: {ssid}")
        
        try:
            # Stop existing connections
            await self._run_command("sudo pkill wpa_supplicant", ignore_error=True)
            await self._run_command("sudo pkill hostapd", ignore_error=True)
            await self._run_command("sudo pkill dnsmasq", ignore_error=True)
            
            # Configure hostapd
            hostapd_config = f"""
interface=wlan0
driver=nl80211
ssid={ssid}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
            
            with open("/tmp/hostapd.conf", "w") as f:
                f.write(hostapd_config)
            
            # Configure dnsmasq
            dnsmasq_config = """
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
"""
            
            with open("/tmp/dnsmasq.conf", "w") as f:
                f.write(dnsmasq_config)
            
            # Set up network interface
            await self._run_command("sudo ifconfig wlan0 192.168.4.1")
            
            # Start services
            await self._run_command("sudo hostapd /tmp/hostapd.conf &")
            await asyncio.sleep(2)
            
            await self._run_command("sudo dnsmasq -C /tmp/dnsmasq.conf")
            
            self.ap_mode = True
            logger.info("✅ AP mode started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start AP mode: {e}")
            raise
    
    async def stop_ap_mode(self):
        """Stop WiFi Access Point mode"""
        if not self.ap_mode:
            return
        
        logger.info("🛑 Stopping AP mode")
        
        try:
            await self._run_command("sudo pkill hostapd", ignore_error=True)
            await self._run_command("sudo pkill dnsmasq", ignore_error=True)
            
            # Reset interface
            await self._run_command("sudo ifconfig wlan0 down")
            await self._run_command("sudo ifconfig wlan0 up")
            
            self.ap_mode = False
            logger.info("✅ AP mode stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping AP mode: {e}")
    
    def _create_wpa_config(self, ssid: str, password: str = None) -> str:
        """Create wpa_supplicant configuration"""
        config = """
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
    ssid="%s"
""" % ssid
        
        if password:
            config += f'    psk="{password}"\n'
        else:
            config += "    key_mgmt=NONE\n"
        
        config += "}\n"
        
        return config
    
    async def _save_network_config(self, ssid: str, password: str = None):
        """Save network configuration to permanent storage"""
        try:
            config = self._create_wpa_config(ssid, password)
            
            # Backup existing config
            await self._run_command("sudo cp /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf.bak", ignore_error=True)
            
            # Write new config
            with open("/tmp/wpa_supplicant_new.conf", "w") as f:
                f.write(config)
            
            await self._run_command("sudo cp /tmp/wpa_supplicant_new.conf /etc/wpa_supplicant/wpa_supplicant.conf")
            
            logger.info("✅ Network configuration saved")
            
        except Exception as e:
            logger.error(f"❌ Failed to save network config: {e}")
    
    async def _run_command(self, command: str, ignore_error: bool = False) -> str:
        """Run shell command asynchronously"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0 and not ignore_error:
                raise Exception(f"Command failed: {command}\nError: {stderr.decode()}")
            
            return stdout.decode()
            
        except Exception as e:
            if not ignore_error:
                raise e
            return ""