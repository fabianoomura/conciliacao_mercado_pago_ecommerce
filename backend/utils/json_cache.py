"""
JSON Cache Utility - Persistência de dados em JSON
Armazena dados processados em JSON para rápido carregamento
"""

import json
import os
from datetime import datetime
from pathlib import Path


class JSONCache:
    """Gerenciador de cache em JSON"""

    def __init__(self, cache_dir='cache'):
        """
        Inicializa o cache

        Args:
            cache_dir: Diretório onde os arquivos de cache serão armazenados
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Subdiretórios por tipo de dados
        self.settlement_dir = self.cache_dir / 'settlement'
        self.releases_dir = self.cache_dir / 'releases'
        self.reconciliation_dir = self.cache_dir / 'reconciliation'
        self.cashflow_dir = self.cache_dir / 'cashflow'

        # Criar subdiretórios
        for dir_path in [self.settlement_dir, self.releases_dir,
                        self.reconciliation_dir, self.cashflow_dir]:
            dir_path.mkdir(exist_ok=True)

        self.metadata_file = self.cache_dir / 'metadata.json'

    def _ensure_serializable(self, obj):
        """
        Converte objetos para estruturas JSON-serializable
        """
        if isinstance(obj, dict):
            return {k: self._ensure_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_serializable(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            # Tentar converter para string para tipos desconhecidos
            return str(obj)

    def save_settlement(self, settlement_data):
        """Salva dados do Settlement"""
        try:
            # Garantir que os dados são serializáveis
            clean_data = self._ensure_serializable(settlement_data)

            file_path = self.settlement_dir / 'settlement_processed.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Settlement salvo em {file_path}")
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao salvar Settlement: {e}")
            return False

    def load_settlement(self):
        """Carrega dados do Settlement"""
        try:
            file_path = self.settlement_dir / 'settlement_processed.json'
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Erro ao carregar Settlement: {e}")
            return None

    def save_releases(self, releases_data):
        """Salva dados de Recebimentos"""
        try:
            clean_data = self._ensure_serializable(releases_data)

            file_path = self.releases_dir / 'releases_processed.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Releases salvo em {file_path}")
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao salvar Releases: {e}")
            return False

    def load_releases(self):
        """Carrega dados de Recebimentos"""
        try:
            file_path = self.releases_dir / 'releases_processed.json'
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Erro ao carregar Releases: {e}")
            return None

    def save_reconciliation(self, reconciliation_data):
        """Salva dados de Conciliação"""
        try:
            clean_data = self._ensure_serializable(reconciliation_data)

            file_path = self.reconciliation_dir / 'reconciliation_processed.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Reconciliation salvo em {file_path}")
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao salvar Reconciliation: {e}")
            return False

    def load_reconciliation(self):
        """Carrega dados de Conciliação"""
        try:
            file_path = self.reconciliation_dir / 'reconciliation_processed.json'
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Erro ao carregar Reconciliation: {e}")
            return None

    def save_cashflow(self, cashflow_data):
        """Salva dados de Fluxo de Caixa"""
        try:
            clean_data = self._ensure_serializable(cashflow_data)

            file_path = self.cashflow_dir / 'cashflow_processed.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Cashflow salvo em {file_path}")
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao salvar Cashflow: {e}")
            return False

    def load_cashflow(self):
        """Carrega dados de Fluxo de Caixa"""
        try:
            file_path = self.cashflow_dir / 'cashflow_processed.json'
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Erro ao carregar Cashflow: {e}")
            return None

    def save_metadata(self, metadata):
        """Salva metadata sobre o processamento"""
        try:
            clean_data = self._ensure_serializable(metadata)

            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Metadata salva")
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao salvar Metadata: {e}")
            return False

    def load_metadata(self):
        """Carrega metadata"""
        try:
            if not self.metadata_file.exists():
                return None

            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Erro ao carregar Metadata: {e}")
            return None

    def clear_all(self):
        """Limpa todo o cache"""
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)

                # Recriar subdiretórios
                for dir_path in [self.settlement_dir, self.releases_dir,
                                self.reconciliation_dir, self.cashflow_dir]:
                    dir_path.mkdir(exist_ok=True)

            print(f"[OK] Cache limpo")
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao limpar cache: {e}")
            return False

    def get_cache_size(self):
        """Retorna o tamanho total do cache em MB"""
        try:
            total_size = 0
            for file_path in self.cache_dir.rglob('*.json'):
                total_size += file_path.stat().st_size

            return round(total_size / (1024 * 1024), 2)  # Converter para MB
        except Exception as e:
            print(f"[ERRO] Erro ao calcular tamanho do cache: {e}")
            return 0

    def get_cache_info(self):
        """Retorna informações sobre o cache"""
        metadata = self.load_metadata()

        return {
            'cache_dir': str(self.cache_dir),
            'cache_size_mb': self.get_cache_size(),
            'metadata': metadata,
            'files': {
                'settlement': self.settlement_dir.exists(),
                'releases': self.releases_dir.exists(),
                'reconciliation': self.reconciliation_dir.exists(),
                'cashflow': self.cashflow_dir.exists()
            }
        }
