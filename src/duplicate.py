# duplicate.py
import os
import hashlib
from typing import List, Dict, Optional
from tqdm import tqdm

class DuplicateDetector:
    """Gerencia a detecção e remoção de arquivos duplicados."""
    
    def __init__(self, logger, watch_directories: List[str], hash_algo='md5'):
        """
        :param logger: instância do ColoredLogger para registrar eventos.
        :param watch_directories: lista de diretórios a serem monitorados.
        :param hash_algo: algoritmo de hash ('md5', 'sha1', etc.)
        """
        self.logger = logger
        self.watch_dirs = watch_directories
        self.hash_algo = hash_algo
        self.known_hashes: Dict[str, str] = {}  # hash -> caminho do arquivo mantido
        
        # Faz a varredura inicial
        self._scan_existing_files()
    
    def _scan_existing_files(self):
        """Percorre os diretórios monitorados e registra os hashes dos arquivos existentes."""
        self.logger.info("Scanning existing files for duplicate detection...")
        
        # Primeiro, conta todos os arquivos para a barra de progresso
        total_files = 0
        file_paths = []
        for directory in self.watch_dirs:
            if not os.path.isdir(directory):
                self.logger.warning(f"Directory does not exist, skipping: {directory}")
                continue
            for root, dirs, files in os.walk(directory):
                total_files += len(files)
                for file in files:
                    file_paths.append(os.path.join(root, file))
        
        # Processa com barra de progresso
        with tqdm(total=total_files, desc="Processing files", unit="file", ncols=80) as pbar:
            for path in file_paths:
                self._register_file(path)
                pbar.update(1)
        
        self.logger.info(f"Initial scan complete. {len(self.known_hashes)} unique files registered.")
    
    def _calculate_hash(self, file_path: str) -> Optional[str]:
        """Calcula o hash do arquivo. Retorna None se houver erro."""
        hash_func = hashlib.new(self.hash_algo)
        try:
            with open(file_path, 'rb') as f:
                # Lê em blocos para arquivos grandes
                for chunk in iter(lambda: f.read(65536), b''):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except (IOError, OSError) as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def _register_file(self, file_path: str) -> Optional[str]:
        """
        Registra o arquivo no dicionário de hashes.
        Se o hash já existir, chama _handle_duplicate.
        Retorna o hash se registrado com sucesso, ou None se for duplicata.
        """
        file_hash = self._calculate_hash(file_path)
        if file_hash is None:
            return None
        
        if file_hash in self.known_hashes:
            # Já existe um arquivo com este hash → duplicata
            self._handle_duplicate(file_path, self.known_hashes[file_hash], file_hash)
            return None
        else:
            # Novo hash: armazena
            self.known_hashes[file_hash] = file_path
            # Comente a linha abaixo se não quiser log de cada arquivo
            # self.logger.debug(f"Registered new file: {file_path} (hash: {file_hash[:8]}...)")
            return file_hash
    
    def _handle_duplicate(self, duplicate_path: str, original_path: str, file_hash: str):
        """
        Decide o que fazer com a duplicata.
        Por padrão, remove o arquivo duplicado e mantém o original.
        """
        self.logger.warning(f"Duplicate detected!", path=duplicate_path)
        self.logger.info(f"Original file: {original_path}")
        
        try:
            os.remove(duplicate_path)
            self.logger.info(f"Removed duplicate file: {duplicate_path}")
        except Exception as e:
            self.logger.error(f"Failed to remove duplicate {duplicate_path}: {e}")
    
    def check_new_file(self, file_path: str):
        """Método público para ser chamado quando um novo arquivo é detectado."""
        if not os.path.isfile(file_path):
            return
        self._register_file(file_path)
    
    def check_modified_file(self, file_path: str):
        """Quando um arquivo é modificado, seu hash pode mudar."""
        # Remove hash antigo
        old_hash = None
        for h, path in list(self.known_hashes.items()):
            if path == file_path:
                old_hash = h
                break
        
        if old_hash:
            del self.known_hashes[old_hash]
            self.logger.debug(f"Removed old hash for modified file: {file_path}")
        
        # Registra novamente
        self._register_file(file_path)
    
    def check_deleted_file(self, file_path: str):
        """Remove o hash do arquivo deletado."""
        for h, path in list(self.known_hashes.items()):
            if path == file_path:
                del self.known_hashes[h]
                self.logger.debug(f"Removed hash for deleted file: {file_path}")
                break