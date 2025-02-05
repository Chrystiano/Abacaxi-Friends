import streamlit as st
import pandas as pd
import time
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configurações de estilo para seguir o design da Apple
APPLE_COLORS = {
    "primary": "#007AFF",
    "success": "#34C759",
    "warning": "#FF9500",
    "danger": "#FF3B30",
    "background": "#F5F5F7",
    "text": "#1D1D1F"
}

st.set_page_config(
    page_title="Gestão de Presenças",
    page_icon="✅",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def apply_apple_design():
    """Aplica estilos CSS seguindo o design da Apple"""
    st.markdown(f"""
        <style>
            .stApp {{
                background-color: {APPLE_COLORS['background']};
            }}
            .stButton>button {{
                background-color: {APPLE_COLORS['primary']};
                color: white;
                border-radius: 20px;
                padding: 10px 24px;
                font-weight: 500;
                transition: all 0.3s;
            }}
            .stButton>button:hover {{
                opacity: 0.9;
                transform: scale(1.05);
            }}
            .stTextInput>div>div>input {{
                border-radius: 10px;
                padding: 12px;
            }}
            .stSelectbox>div>div>div {{
                border-radius: 10px;
                padding: 8px;
            }}
            .stFileUploader>section {{
                border: 2px dashed {APPLE_COLORS['primary']};
                border-radius: 15px;
                padding: 20px;
            }}
            .success-message {{
                color: {APPLE_COLORS['success']};
                font-weight: 500;
                padding: 15px;
                border-radius: 10px;
                background: rgba(52, 199, 89, 0.1);
            }}
            .error-message {{
                color: {APPLE_COLORS['danger']};
                font-weight: 500;
                padding: 15px;
                border-radius: 10px;
                background: rgba(255, 59, 48, 0.1);
            }}
        </style>
    """, unsafe_allow_html=True)

@dataclass
class GoogleConfig:
    """Configuração para integração com Google APIs"""
    sheet_id: str
    folder_id: str
    credentials: Dict[str, Any]

class GoogleServices:
    """Gerencia conexões com APIs do Google"""
    _instances = {}
    
    def __new__(cls, config: GoogleConfig):
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
            creds = service_account.Credentials.from_service_account_info(config.credentials)
            cls._instances[cls].sheets = build('sheets', 'v4', credentials=creds)
            cls._instances[cls].drive = build('drive', 'v3', credentials=creds)
        return cls._instances[cls]

class DataManager:
    """Gerencia operações de dados com Google Sheets"""
    def __init__(self, config: GoogleConfig):
        self.config = config
        self.service = GoogleServices(config)
        
    @st.cache_data(ttl=300, show_spinner="Carregando dados...")
    def load_data(_self, sheet_id: str) -> pd.DataFrame:
        """Carrega dados da planilha Google"""
        try:
            result = _self.service.sheets.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range="A:D"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])
            
            df = pd.DataFrame(values[1:], columns=values[0])
            df["Celular"] = df["Celular"].apply(lambda x: re.sub(r'\D', '', x))
            return df
        except Exception as e:
            st.error("Erro ao carregar dados. Tente novamente.")
            return pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])

    def save_data(self, df: pd.DataFrame) -> bool:
        """Salva dados na planilha Google"""
        try:
            values = [df.columns.tolist()] + df.values.tolist()
            self.service.sheets.spreadsheets().values().update(
                spreadsheetId=self.config.sheet_id,
                range="A1",
                valueInputOption="USER_ENTERED",
                body={'values': values}
            ).execute()
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar dados: {str(e)}")
            return False

class FileHandler:
    """Gerencia upload de arquivos para o Google Drive"""
    def __init__(self, config: GoogleConfig):
        self.config = config
        self.service = GoogleServices(config)
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)

    def _validate_file(self, file) -> bool:
        """Valida o arquivo antes do upload"""
        if file.size > 2 * 1024 * 1024:
            st.error("Arquivo excede 2MB. Por favor, envie um arquivo menor.")
            return False
        return True

    def upload_file(self, uploaded_file, name: str) -> Optional[str]:
        """Processa e faz upload do arquivo"""
        if not self._validate_file(uploaded_file):
            return None

        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        file_ext = Path(uploaded_file.name).suffix
        filename = f"{timestamp}_{name}{file_ext}"
        file_path = self.upload_dir / filename

        try:
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            file_metadata = {
                'name': filename,
                'parents': [self.config.folder_id]
            }
            media = MediaFileUpload(file_path)
            self.service.drive.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return filename
        except Exception as e:
            st.error(f"Erro no upload: {str(e)}")
            return None

class AttendanceSystem:
    """Sistema principal de gestão de presenças"""
    def __init__(self, config: GoogleConfig):
        self.data_manager = DataManager(config)
        self.file_handler = FileHandler(config)
        self.df = self.data_manager.load_data(config.sheet_id)
        apply_apple_design()

    def _format_phone_input(self):
        """Formata o número de celular durante a digitação"""
        if 'phone_input' in st.session_state:
            current_value = st.session_state.phone_input
            digits = re.sub(r'\D', '', current_value)
            
            # Aplica a máscara (XX) XXXXX-XXXX
            formatted = ''
            for i, char in enumerate(digits[:11]):
                if i == 0:
                    formatted += '('
                if i == 2:
                    formatted += ') '
                if i == 7:
                    formatted += '-'
                formatted += char
            
            st.session_state.phone_input = formatted

    def _clear_registration_form(self):
        """Limpa o formulário de cadastro"""
        keys_to_clear = ['name_input', 'phone_input', 'type_input']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

    def _attendance_confirmation(self, selected_name: str):
        """Gerencia a confirmação de presença"""
        current_status = self.df.loc[self.df["Nome"] == selected_name, "Status"].values[0]
        
        if current_status != "Pagamento Pendente":
            self._show_feedback("✅ Você já enviou seu comprovante!", "success")
            return

        with st.form(key="upload_form"):
            uploaded_file = st.file_uploader(
                "📤 Envie seu comprovante (PDF, PNG, JPG, CSV)",
                type=["pdf", "png", "jpg", "csv"],
                help="Tamanho máximo: 2MB",
                key="file_uploader"
            )
            
            if st.form_submit_button("Enviar Comprovante", use_container_width=True):
                if uploaded_file:
                    with st.spinner("Processando..."):
                        filename = self.file_handler.upload_file(uploaded_file, selected_name)
                        if filename:
                            self.df.loc[self.df["Nome"] == selected_name, "Status"] = "Pagamento Em Análise"
                            if self.data_manager.save_data(self.df):
                                # Limpa o uploader e busca
                                st.session_state.uploaded_file = None
                                if 'search_input' in st.session_state:
                                    del st.session_state.search_input
                                self._show_feedback("✅ Comprovante enviado com sucesso!")
                                time.sleep(1)
                                st.rerun()
                else:
                    self._show_feedback("❌ Por favor, selecione um arquivo", "error")

    def _registration_form(self):
        """Formulário de cadastro de novos participantes"""
        with st.form(key="registration_form"):
            cols = st.columns([2, 1])
            name = cols[0].text_input(
                "Nome Completo *",
                key="name_input",
                placeholder="Digite o nome completo"
            )
            
            phone = cols[1].text_input(
                "Celular *", 
                key="phone_input",
                placeholder="(XX) XXXXX-XXXX",
                on_change=self._format_phone_input,
                help="Formato: (XX) XXXXX-XXXX"
            )
            
            st.selectbox(
                "Tipo de Participante *",
                ["Membro", "Convidado"],
                key="type_input",
                index=0
            )
            
            if st.form_submit_button("Cadastrar", use_container_width=True):
                if not all([name, phone]):
                    self._show_feedback("❌ Preencha todos os campos obrigatórios", "error")
                    return
                
                phone_digits = re.sub(r'\D', '', phone)
                if len(phone_digits) != 11:
                    self._show_feedback("❌ Número de celular inválido", "error")
                    return
                
                if name.lower() in self.df["Nome"].str.lower().values:
                    self._show_feedback("❌ Nome já cadastrado", "error")
                    return
                
                new_entry = pd.DataFrame([[
                    name.strip(),
                    phone_digits,
                    st.session_state.type_input,
                    "Pagamento Pendente"
                ]], columns=self.df.columns)
                
                self.df = pd.concat([self.df, new_entry], ignore_index=True)
                if self.data_manager.save_data(self.df):
                    self._show_feedback("✅ Cadastro realizado com sucesso!")
                    self._clear_registration_form()
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

    def run(self):
        """Executa o sistema principal"""
        st.title("🎉 Gestão de Eventos")
        tab1, tab2 = st.tabs(["Confirmação de Presença", "Cadastro de Participantes"])

        with tab1:
            st.subheader("Confirme sua Presença")
            search_term = st.text_input(
                "Buscar por nome",
                key="search_input",
                placeholder="Digite seu nome para buscar"
            ).strip()
            
            if search_term:
                results = self.df[self.df["Nome"].str.contains(search_term, case=False)]
                if not results.empty:
                    selected = st.selectbox("Selecione seu nome", results["Nome"])
                    self._attendance_confirmation(selected)
                else:
                    self._show_feedback("⚠️ Nenhum participante encontrado", "error")

        with tab2:
            st.subheader("Novo Cadastro")
            self._registration_form()

def main():
    """Função principal"""
    config = GoogleConfig(
        sheet_id=st.secrets["gdrive"]["GOOGLE_SHEET_ID"],
        folder_id=st.secrets["gdrive"]["GDRIVE_FOLDER_ID"],
        credentials=st.secrets["gdrive_credentials"]
    )
    
    system = AttendanceSystem(config)
    system.run()

if __name__ == "__main__":
    main()
