import logging
import os
import time
import socket
import uuid
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

class SystemLogger:
    def __init__(self, service_name="GLM-OCR", log_dir="logs"):
        self.service_name = service_name
        self.log_dir = log_dir
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Daily rotation at midnight
        log_file = os.path.join(self.log_dir, f"{self.service_name}.log")
        handler = TimedRotatingFileHandler(
            log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        # Custom naming for rotated files: service_name-YYYY-MM-DD.log
        handler.suffix = "%Y-%m-%d"
        
        # Formatter: just the message (we will format the message manually as a tab-separated row)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
            
        self.server_ip = self._get_server_ip()

    def _get_server_ip(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"

    def format_log(self, level, trans_id, endpoint, method, func_name, caller_info, 
                   exec_time_ms, client_ip, trace_id, flag, message, 
                   body="-", result="-", error="-", prev_trans_id="-"):
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Fields mapping per panduan_log.pdf (21 fields)
        fields = [
            timestamp,              # 1
            f"[{level}]",           # 2
            trans_id,               # 3
            self.service_name,      # 4
            endpoint,               # 5
            "REST",                 # 6
            method,                 # 7
            "SYNC",                 # 8
            "application/json",     # 9
            func_name,              # 10
            caller_info,            # 11
            f"{exec_time_ms:.2f} ms" if isinstance(exec_time_ms, (int, float)) else exec_time_ms, # 12
            self.server_ip,         # 13
            client_ip,              # 14
            trace_id,               # 15
            prev_trans_id,          # 16
            str(body).replace("\n", " ").replace("\t", " "),     # 17
            str(result).replace("\n", " ").replace("\t", " "),   # 18
            str(error).replace("\n", " ").replace("\t", " "),    # 19
            f"[{flag}]",            # 20
            message                 # 21
        ]
        
        return "\t".join(fields)

    def info(self, *args, **kwargs):
        self.logger.info(self.format_log("INFO", *args, **kwargs))

    def error(self, *args, **kwargs):
        self.logger.error(self.format_log("ERROR", *args, **kwargs))

    def debug(self, *args, **kwargs):
        self.logger.debug(self.format_log("DEBUG", *args, **kwargs))

# Global instance
sys_logger = SystemLogger()
