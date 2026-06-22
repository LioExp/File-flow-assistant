import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict


class VirusScanner:
    def __init__(self, logger=None):
        self.logger = logger
        self.backend = self._detect_backend()

    def _detect_backend(self):
        if sys.platform == 'win32':
            defender = Path(os.environ.get('ProgramFiles', '')) / "Windows Defender" / "MpCmdRun.exe"
            if defender.exists():
                return 'defender'
            if shutil.which('MpCmdRun.exe'):
                return 'defender'
        else:
            if shutil.which('clamscan'):
                return 'clamav'
        return None

    def is_available(self):
        return self.backend is not None

    def get_backend_name(self):
        if self.backend == 'clamav':
            return 'ClamAV'
        elif self.backend == 'defender':
            return 'Windows Defender'
        return 'none'

    def scan_file(self, file_path: str) -> Dict:
        path = Path(file_path)
        if not path.is_file():
            return {'status': 'error', 'message': 'File not found', 'file': file_path}

        if self.backend == 'clamav':
            return self._scan_clamav(str(path))
        elif self.backend == 'defender':
            return self._scan_defender(str(path))
        else:
            return {'status': 'unavailable', 'message': 'No antivirus backend found', 'file': file_path}

    def scan_directory(self, dir_path: str) -> List[Dict]:
        path = Path(dir_path)
        if not path.is_dir():
            return [{'status': 'error', 'message': 'Directory not found', 'file': dir_path}]

        if self.backend == 'clamav':
            return self._scan_clamav_dir(str(path))
        elif self.backend == 'defender':
            return self._scan_defender_dir(str(path))
        else:
            return [{'status': 'unavailable', 'message': 'No antivirus backend found', 'file': dir_path}]

    def _scan_clamav(self, file_path: str) -> Dict:
        try:
            result = subprocess.run(
                ['clamscan', '--no-summary', file_path],
                capture_output=True, text=True, timeout=120
            )
            output = result.stdout.strip()
            if 'OK' in output:
                return {'status': 'clean', 'file': file_path, 'engine': 'ClamAV'}
            elif 'FOUND' in output:
                threat = output.split(':')[1].strip() if ':' in output else 'unknown'
                return {'status': 'infected', 'file': file_path, 'threat': threat, 'engine': 'ClamAV'}
            else:
                return {'status': 'error', 'file': file_path, 'message': output or 'Unknown error', 'engine': 'ClamAV'}
        except subprocess.TimeoutExpired:
            return {'status': 'error', 'file': file_path, 'message': 'Scan timed out', 'engine': 'ClamAV'}
        except FileNotFoundError:
            return {'status': 'unavailable', 'file': file_path, 'message': 'clamscan not found', 'engine': 'ClamAV'}

    def _scan_clamav_dir(self, dir_path: str) -> List[Dict]:
        try:
            result = subprocess.run(
                ['clamscan', '-r', '--no-summary', dir_path],
                capture_output=True, text=True, timeout=600
            )
            results = []
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                if 'OK' in line:
                    fp = line.split(':')[0].strip()
                    results.append({'status': 'clean', 'file': fp, 'engine': 'ClamAV'})
                elif 'FOUND' in line:
                    parts = line.split(':')
                    fp = parts[0].strip()
                    threat = parts[1].strip() if len(parts) > 1 else 'unknown'
                    results.append({'status': 'infected', 'file': fp, 'threat': threat, 'engine': 'ClamAV'})
            return results
        except subprocess.TimeoutExpired:
            return [{'status': 'error', 'file': dir_path, 'message': 'Scan timed out', 'engine': 'ClamAV'}]

    def _scan_defender(self, file_path: str) -> Dict:
        try:
            defender_path = self._get_defender_path()
            result = subprocess.run(
                [defender_path, '-Scan', '-ScanType', '3', '-File', file_path],
                capture_output=True, text=True, timeout=120
            )
            output = result.stdout.strip()
            if 'found no threats' in output.lower() or result.returncode == 0:
                return {'status': 'clean', 'file': file_path, 'engine': 'Windows Defender'}
            elif 'found' in output.lower() and 'threat' in output.lower():
                return {'status': 'infected', 'file': file_path, 'threat': 'detected', 'engine': 'Windows Defender'}
            else:
                return {'status': 'error', 'file': file_path, 'message': output or 'Unknown error', 'engine': 'Windows Defender'}
        except subprocess.TimeoutExpired:
            return {'status': 'error', 'file': file_path, 'message': 'Scan timed out', 'engine': 'Windows Defender'}

    def _scan_defender_dir(self, dir_path: str) -> List[Dict]:
        try:
            defender_path = self._get_defender_path()
            result = subprocess.run(
                [defender_path, '-Scan', '-ScanType', '2', '-ScanPath', dir_path],
                capture_output=True, text=True, timeout=600
            )
            output = result.stdout.strip()
            if 'found no threats' in output.lower():
                return [{'status': 'clean', 'file': dir_path, 'engine': 'Windows Defender'}]
            else:
                return [{'status': 'infected', 'file': dir_path, 'threat': 'detected', 'engine': 'Windows Defender'}]
        except subprocess.TimeoutExpired:
            return [{'status': 'error', 'file': dir_path, 'message': 'Scan timed out', 'engine': 'Windows Defender'}]

    def _get_defender_path(self):
        path = Path(os.environ.get('ProgramFiles', '')) / "Windows Defender" / "MpCmdRun.exe"
        if path.exists():
            return str(path)
        return 'MpCmdRun.exe'


SUSPICIOUS_EXTENSIONS = {
    '.exe', '.scr', '.bat', '.cmd', '.vbs', '.vbe', '.js', '.jse',
    '.wsf', '.wsh', '.ps1', '.msi', '.msp', '.mst', '.pif',
    '.com', '.hta', '.cpl', '.reg', '.rgs', '.sct', '.shb',
}


def is_suspicious(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    return ext in SUSPICIOUS_EXTENSIONS
