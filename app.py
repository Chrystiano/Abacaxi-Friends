import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime
import os
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import time
from pathlib import Path

@dataclass
class GoogleConfig:
    """Configuration class for Google API credentials and IDs."""
    sheet_id: str
    folder_id: str
    credentials: Dict[str, Any]

class GoogleServices:
    """Handle Google API services initialization."""
    def __init__(self, config: GoogleConfig):
        self.config = config
        self.creds = service_account.Credentials.from_service_account_info(config.credentials)
        self._sheets_service = None
        self._drive_service = None

    @property
    def sheets(self):
        if not self._sheets_service:
            self._sheets_service = build('sheets', 'v4', credentials=self.creds)
        return self._sheets_service

    @property
    def drive(self):
        if not self._drive_service:
            self._drive_service = build('drive', 'v3', credentials=self.creds)
        return self._drive_service

class DataManager:
    """Handle data operations with Google Sheets."""
    def __init__(self, services: GoogleServices):
        self.services = services
        self.sheet_id = services.config.sheet_id

    def load_data(self) -> pd.DataFrame:
        """Load data from Google Sheets."""
        @st.cache_data(ttl=600)
        def _fetch_sheet_data(_sheet_id: str, _service: Any) -> pd.DataFrame:
            try:
                result = _service.spreadsheets().values().get(
                    spreadsheetId=_sheet_id,
                    range="A:D"
                ).execute()
                
                values = result.get('values', [])
                if not values:
                    return pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])
                
                return pd.DataFrame(values[1:], columns=values[0])
            except Exception as e:
                st.error(f"Erro ao carregar os dados: {str(e)}")
                return pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])
        
        return _fetch_sheet_data(self.sheet_id, self.services.sheets)

    def save_data(self, df: pd.DataFrame) -> bool:
        """Save data to Google Sheets."""
        try:
            values = [df.columns.values.tolist()] + df.values.tolist()
            self.services.sheets.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range="A1",
                valueInputOption="RAW",
                body={'values': values}
            ).execute()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar os dados: {str(e)}")
            return False

class FileHandler:
    """Handle file upload operations."""
    def __init__(self, services: GoogleServices):
        self.services = services
        self.folder_id = services.config.folder_id
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)

    def process_upload(self, uploaded_file, selected_name: str) -> Optional[str]:
        """Process file upload and return the file path if successful."""
        if uploaded_file.size > 2 * 1024 * 1024:
            st.error("❌ O arquivo excede 2MB. Por favor, envie um arquivo menor.")
            return None

        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        file_ext = Path(uploaded_file.name).suffix
        new_filename = f"{timestamp}_{selected_name}{file_ext}"
        file_path = self.upload_dir / new_filename

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"✅ Arquivo salvo como `{new_filename}`!")
        return str(file_path)

    def upload_to_drive(self, file_path: str, filename: str) -> bool:
        """Upload file to Google Drive."""
        try:
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            media = MediaFileUpload(file_path, resumable=True)
            file = self.services.drive.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            st.success(f"Arquivo enviado para o Google Drive com ID: {file.get('id')}")
            return True
        except Exception as e:
            st.error(f"Erro ao fazer upload para o Google Drive: {str(e)}")
            return False

class AttendanceUI:
    """Handle UI components and interactions."""
    def __init__(self, data_manager: DataManager, file_handler: FileHandler):
        self.data_manager = data_manager
        self.file_handler = file_handler
        st.set_page_config(
            page_title="Gestão de Presenças",
            page_icon="✅",
            layout="centered"
        )
        self.load_data()

    def load_data(self):
        """Load data with proper state management."""
        if 'df' not in st.session_state:
            st.session_state.df = self.data_manager.load_data()

    def refresh_data(self):
        """Refresh data and clear cache."""
        st.cache_data.clear()
        st.session_state.df = self.data_manager.load_data()

    def search_tab(self):
        """Render search and confirmation tab."""
        st.markdown(
            "<h1 style='text-align: center; color: #1F618D;'>🎉 Confirmação de Presença 🎉</h1>",
            unsafe_allow_html=True
        )

        nome_busca = st.text_input("🔎 Digite seu nome para buscar", "").strip()
        if not nome_busca:
            return

        results = st.session_state.df[
            st.session_state.df["Nome"].str.contains(nome_busca, case=False, na=False)
        ]
        if results.empty:
            st.error("Nenhum registro encontrado. Verifique a grafia do nome.")
            return

        st.write(f"🔍 Encontramos {len(results)} resultado(s):")
        selected_row = st.selectbox("Selecione seu nome:", results["Nome"].tolist())
        
        self.handle_attendance_confirmation(selected_row)

    def handle_attendance_confirmation(self, selected_row: str):
        """Handle attendance confirmation process."""
        status_atual = st.session_state.df[
            st.session_state.df["Nome"] == selected_row
        ]["Status"].values[0]
        
        if status_atual == "Pagamento Confirmado":
            st.warning("✅ Você já confirmou sua presença anteriormente.")
            return

        st.success(f"🔹 {selected_row} encontrado! Envie um arquivo para confirmar sua presença.")
        uploaded_file = st.file_uploader(
            "📁 Envie um comprovante (CSV, PNG, JPG, PDF - máx. 2MB)",
            type=["csv", "png", "jpg", "pdf"]
        )

        if not uploaded_file:
            return

        file_path = self.file_handler.process_upload(uploaded_file, selected_row)
        if not file_path:
            return

        if not self.file_handler.upload_to_drive(file_path, Path(file_path).name):
            return

        st.session_state.df.loc[
            st.session_state.df["Nome"] == selected_row, "Status"
        ] = "Pagamento Confirmado"
        
        if self.data_manager.save_data(st.session_state.df):
            st.balloons()
            st.success("🎉 Presença confirmada com sucesso!")

    def registration_tab(self):
        """Render registration tab."""
        st.markdown(
            "<h1 style='text-align: center; color: #2C3E50;'>📝 Cadastrar Nova Pessoa</h1>",
            unsafe_allow_html=True
        )

        with st.form(key="cadastro_form"):
            nome = st.text_input("🆕 Nome Completo", "").strip()
            celular = st.text_input("📞 Número de Celular", "").strip()
            tipo = st.selectbox("👤 Tipo", ["Membro", "Convidado"])
            cadastrar = st.form_submit_button("📌 Cadastrar")

            if not cadastrar:
                return

            if not all([nome, celular]):
                st.error("❌ Nome e celular são obrigatórios!")
                return

            if st.session_state.df["Nome"].str.lower().str.strip().eq(nome.lower()).any():
                st.error("❌ Já existe um cadastro com esse nome.")
                return

            novo_registro = pd.DataFrame(
                [[nome, celular, tipo, "Pagamento Pendente"]],
                columns=st.session_state.df.columns
            )
            st.session_state.df = pd.concat([st.session_state.df, novo_registro], ignore_index=True)
            
            if self.data_manager.save_data(st.session_state.df):
                st.success("✅ Cadastro realizado com sucesso!")
                st.balloons()
                time.sleep(3)
                self.refresh_data()
                st.experimental_rerun()

def main():
    """Main application entry point."""
    config = GoogleConfig(
        sheet_id=st.secrets["gdrive"]["GOOGLE_SHEET_ID"],
        folder_id=st.secrets["gdrive"]["GDRIVE_FOLDER_ID"],
        credentials=st.secrets["gdrive_credentials"]
    )
    
    services = GoogleServices(config)
    data_manager = DataManager(services)
    file_handler = FileHandler(services)
    ui = AttendanceUI(data_manager, file_handler)

    aba_consulta, aba_cadastro = st.tabs(["🔎 Consultar e Confirmar Presença", "📝 Cadastrar Nova Pessoa"])
    
    with aba_consulta:
        ui.search_tab()
    
    with aba_cadastro:
        ui.registration_tab()

if __name__ == "__main__":
    main()
