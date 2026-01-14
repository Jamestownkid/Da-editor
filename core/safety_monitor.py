"""
Da Editor - Safety Monitor
============================
keeps an eye on system resources so we dont crash the pc
checks disk, ram, cpu before doing heavy stuff

aint tryna make someones laptop catch fire fr
"""

import os
import sys
from typing import Dict


class SafetyMonitor:
    """
    monitors system resources and reports if safe to continue
    
    1a. checks disk space
    1b. checks memory usage
    1c. checks cpu usage
    1d. checks gpu if available
    """
    
    # minimum free disk space (in GB)
    MIN_DISK_GB = 2.0
    
    # minimum free memory (in GB)
    MIN_MEMORY_GB = 1.0
    
    # max cpu usage to start new tasks
    MAX_CPU_PERCENT = 90.0
    
    def __init__(self):
        # try to import psutil
        try:
            import psutil
            self.psutil = psutil
        except ImportError:
            print("[Safety] psutil not installed - using basic checks only")
            self.psutil = None
    
    def check(self) -> Dict:
        """
        run all checks and return status
        returns dict with safe=True/False and individual statuses
        """
        result = {
            "safe": True,
            "disk": "OK",
            "memory": "OK", 
            "cpu": "OK",
            "gpu": None
        }
        
        # 1a. disk check
        disk_status = self._check_disk()
        result["disk"] = disk_status
        if disk_status == "CRITICAL":
            result["safe"] = False
        
        # 1b. memory check
        mem_status = self._check_memory()
        result["memory"] = mem_status
        if mem_status == "CRITICAL":
            result["safe"] = False
        
        # 1c. cpu check
        cpu_status = self._check_cpu()
        result["cpu"] = cpu_status
        if cpu_status == "CRITICAL":
            result["safe"] = False
        
        # 1d. gpu check (optional)
        gpu_info = self._check_gpu()
        result["gpu"] = gpu_info
        
        return result
    
    def _check_disk(self) -> str:
        """check free disk space"""
        try:
            if self.psutil:
                # check the drive where home directory is
                home = os.path.expanduser("~")
                usage = self.psutil.disk_usage(home)
                free_gb = usage.free / (1024 ** 3)
                
                if free_gb < 1.0:
                    return "CRITICAL"
                elif free_gb < self.MIN_DISK_GB:
                    return "LOW"
                return "OK"
            else:
                # basic check without psutil
                import shutil
                home = os.path.expanduser("~")
                total, used, free = shutil.disk_usage(home)
                free_gb = free / (1024 ** 3)
                
                if free_gb < 1.0:
                    return "CRITICAL"
                elif free_gb < self.MIN_DISK_GB:
                    return "LOW"
                return "OK"
                
        except Exception as e:
            print(f"[Safety] disk check failed: {e}")
            return "OK"  # assume ok if we cant check
    
    def _check_memory(self) -> str:
        """check available memory"""
        try:
            if self.psutil:
                mem = self.psutil.virtual_memory()
                available_gb = mem.available / (1024 ** 3)
                
                if available_gb < 0.5:
                    return "CRITICAL"
                elif available_gb < self.MIN_MEMORY_GB:
                    return "LOW"
                return "OK"
            else:
                # cant check without psutil
                return "OK"
                
        except Exception as e:
            print(f"[Safety] memory check failed: {e}")
            return "OK"
    
    def _check_cpu(self) -> str:
        """check cpu usage"""
        try:
            if self.psutil:
                cpu_percent = self.psutil.cpu_percent(interval=1)
                
                if cpu_percent > 95:
                    return "CRITICAL"
                elif cpu_percent > self.MAX_CPU_PERCENT:
                    return "HIGH"
                return "OK"
            else:
                return "OK"
                
        except Exception as e:
            print(f"[Safety] cpu check failed: {e}")
            return "OK"
    
    def _check_gpu(self) -> Dict:
        """check gpu availability and vram"""
        try:
            import torch
            
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                total_vram = torch.cuda.get_device_properties(0).total_memory
                total_vram_gb = total_vram / (1024 ** 3)
                
                # check free vram
                free_vram = total_vram - torch.cuda.memory_allocated(0)
                free_vram_gb = free_vram / (1024 ** 3)
                
                return {
                    "available": True,
                    "name": name,
                    "total_vram_gb": round(total_vram_gb, 2),
                    "free_vram_gb": round(free_vram_gb, 2)
                }
            else:
                return {"available": False, "name": None}
                
        except ImportError:
            return {"available": False, "name": None, "error": "torch not installed"}
        except Exception as e:
            return {"available": False, "name": None, "error": str(e)}
    
    def get_system_info(self) -> Dict:
        """get detailed system info for debugging"""
        info = {
            "platform": sys.platform,
            "python_version": sys.version
        }
        
        if self.psutil:
            try:
                info["cpu_count"] = self.psutil.cpu_count()
                info["memory_total_gb"] = round(self.psutil.virtual_memory().total / (1024 ** 3), 2)
                info["disk_total_gb"] = round(self.psutil.disk_usage(os.path.expanduser("~")).total / (1024 ** 3), 2)
            except:
                pass
        
        return info


def test_monitor():
    """quick test of the safety monitor"""
    monitor = SafetyMonitor()
    
    print("System Info:")
    print(monitor.get_system_info())
    print()
    
    print("Safety Check:")
    status = monitor.check()
    print(status)
    
    if status["safe"]:
        print("\nAll good - safe to proceed")
    else:
        print("\nWARNING - System resources low!")


if __name__ == "__main__":
    test_monitor()

