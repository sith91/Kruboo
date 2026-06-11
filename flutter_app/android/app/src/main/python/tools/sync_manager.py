import os
import secrets
import json
import socket
import io
import base64

try:
    import qrcode
    _QRCODE_AVAILABLE = True
except ImportError:
    _QRCODE_AVAILABLE = False

try:
    from zeroconf import IPVersion, ServiceInfo, Zeroconf
    _ZEROCONF_AVAILABLE = True
except ImportError:
    _ZEROCONF_AVAILABLE = False

class LocalSyncManager:
    def __init__(self, port=8000):
        self.config_path = os.path.join(os.getcwd(), ".sync_config.json")
        self.port = port
        self.sync_token = self._load_or_generate_token()
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only) if _ZEROCONF_AVAILABLE else None
        self.service_info = None

    def _load_or_generate_token(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                config = json.load(f)
                return config.get("sync_token")
        
        # Generate a secure 8-character token
        new_token = secrets.token_hex(4).upper()
        with open(self.config_path, "w") as f:
            json.dump({"sync_token": new_token}, f)
        print(f"--- GENERATED NEW SYNC TOKEN: {new_token} ---")
        return new_token

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def start_discovery(self):
        if not _ZEROCONF_AVAILABLE:
            print("Zeroconf not available, discovery disabled.")
            return
        desc = {'token_required': 'true', 'version': '1.0'}
        local_ip = self.get_local_ip()
        
        self.service_info = ServiceInfo(
            "_ai-assistant._tcp.local.",
            "AI-Assistant-Backend._ai-assistant._tcp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties=desc,
            server="ai-assistant.local.",
        )
        
        print(f"Starting Local Discovery on {local_ip}:{self.port}...")
        self.zeroconf.register_service(self.service_info)

    def stop_discovery(self):
        if not _ZEROCONF_AVAILABLE:
            return
        if self.service_info:
            self.zeroconf.unregister_service(self.service_info)
        if self.zeroconf:
            self.zeroconf.close()

    def verify_token(self, token: str):
        return token == self.sync_token

    def get_pairing_qr_base64(self):
        if not _QRCODE_AVAILABLE:
            return ""
        local_ip = self.get_local_ip()
        payload = {
            "ip": local_ip,
            "port": self.port,
            "token": self.sync_token,
            "name": "AI Assistant Backend"
        }
        
        qr_data = json.dumps(payload)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
