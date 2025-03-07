import streamlit as st
import pandas as pd
import plotly.express as px
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configurações de estilo Apple
APPLE_COLORS = {
    "primary": "#007AFF",
    "success": "#34C759",
    "warning": "#FF9500",
    "danger": "#FF3B30",
    "background": "#F5F5F7",
    "text": "#1D1D1F"
}

def apply_apple_design():
    """Aplica o design estilo Apple"""
    st.markdown(
        f"""
        <style>
            body {{
                background-color: {APPLE_COLORS['background']};
                color: {APPLE_COLORS['text']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }}
            .stButton>button {{
                background-color: {APPLE_COLORS['primary']};
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 16px;
                border: none;
                transition: all 0.3s ease;
            }}
            .stButton>button:hover {{
                background-color: #005bb5;
            }}
            .success-message {{
                color: {APPLE_COLORS['success']};
                font-weight: bold;
                margin-top: 10px;
            }}
            .error-message {{
                color: {APPLE_COLORS['danger']};
                font-weight: bold;
                margin-top: 10px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

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
            instance = super().__new__(cls)
            creds = service_account.Credentials.from_service_account_info(config.credentials)
            instance.sheets = build('sheets', 'v4', credentials=creds)
            instance.drive = build('drive', 'v3', credentials=creds)
            cls._instances[cls] = instance
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

    def upload_file(self, uploaded_file, name: str) -> Optional[str]:
        """Processa e faz upload do arquivo"""
        if uploaded_file.size > 2 * 1024 * 1024:
            st.error("Arquivo excede 2MB. Por favor, envie um arquivo menor.")
            return None
        try:
            timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
            file_ext = Path(uploaded_file.name).suffix
            filename = f"{timestamp}_{name}{file_ext}"
            file_path = self.upload_dir / filename
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

    def _show_feedback(self, message: str, type: str = "success"):
        """Exibe mensagens de feedback estilizadas"""
        css_class = "success-message" if type == "success" else "error-message"
        st.markdown(f'<div class="{css_class}">{message}</div>', unsafe_allow_html=True)

    def _clear_registration_form(self):
        """Limpa o formulário de cadastro"""
        keys_to_clear = ['name_input', 'phone_input', 'type_input']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

    def _registration_form(self):
        """Formulário de cadastro de novos participantes"""
        with st.form(key="registration_form"):
            st.subheader("🍍 Novo Cadastro")
            cols = st.columns([2, 1])
            name = cols[0].text_input(
                "Nome Completo *",
                key="name_input",
                placeholder="Digite o nome completo"
            )
            phone = cols[1].text_input(
                "Celular *", 
                key="phone_input",
                placeholder="(XX) XXXXX-XXXX"
            )
            participant_type = st.selectbox(
                "Tipo de Participante *",
                ["Membro", "Convidado"],
                key="type_input",
                index=0
            )
            submit_button = st.form_submit_button("Cadastrar", use_container_width=True)

            if submit_button:
                phone_digits = re.sub(r'\D', '', phone)
                if not all([name, phone_digits]):
                    self._show_feedback("❌ Preencha todos os campos obrigatórios", "error")
                    return
                if len(phone_digits) != 11:
                    self._show_feedback("❌ Número de celular inválido", "error")
                    return
                if name.lower() in self.df["Nome"].str.lower().values:
                    self._show_feedback("❌ Nome já cadastrado", "error")
                    return

                new_entry = pd.DataFrame([[
                    name.strip(),
                    phone_digits,
                    participant_type,
                    "Pagamento Pendente"
                ]], columns=self.df.columns)
                self.df = pd.concat([self.df, new_entry], ignore_index=True)
                if self.data_manager.save_data(self.df):
                    self._show_feedback("✅ Cadastro realizado com sucesso!")
                    self._clear_registration_form()
                    st.balloons()  # Animação de sucesso
                    time.sleep(1)
                    st.rerun()

    def _attendance_confirmation(self):
        """Gerencia a confirmação de presença"""
        st.title("🎉 Confirmação de Presença")
        search_term = st.text_input(
            "Buscar participante",
            placeholder="Digite seu nome completo",
            key="search_input"
        ).strip()
        if search_term:
            results = self.df[self.df["Nome"].str.contains(search_term, case=False, regex=False)]
            if not results.empty:
                selected = st.selectbox("Selecione seu nome", results["Nome"])
                current_status = self.df.loc[self.df["Nome"] == selected, "Status"].values[0]
                if current_status != "Pagamento Pendente":
                    self._show_feedback("✅ Você já enviou seu comprovante!", "success")
                    return

                with st.form(key="upload_form"):
                    st.subheader("📤 Envio de Comprovante")
                    uploaded_file = st.file_uploader(
                        "Selecione seu comprovante",
                        type=["pdf", "png", "jpg", "csv"],
                        help="Tamanho máximo: 2MB"
                    )
                    submit_button = st.form_submit_button("Confirmar Presença", use_container_width=True)

                    if submit_button:
                        if uploaded_file:
                            with st.spinner("Processando..."):
                                filename = self.file_handler.upload_file(uploaded_file, selected)
                                if filename:
                                    self.df.loc[self.df["Nome"] == selected, "Status"] = "Pagamento Em Análise"
                                    if self.data_manager.save_data(self.df):
                                        self._show_feedback("✅ Comprovante enviado com sucesso!")
                                        st.balloons()  # Animação de sucesso
                                        time.sleep(1)
                                        st.rerun()
                        else:
                            self._show_feedback("❌ Por favor, selecione um arquivo", "error")
            else:
                self._show_feedback("⚠️ Nenhum participante encontrado", "error")

    def _authenticate_admin(self):
        """Autenticação para acessar o Painel de Administração"""
        st.subheader("🔒 Acesso Restrito")
        password = st.text_input("Digite a senha de administrador:", type="password")
        if st.button("Entrar"):
            if password == st.secrets["admin_password"]:
                st.session_state.authenticated = True
                st.success("✅ Acesso autorizado!")
                time.sleep(1)
                st.rerun()
            else:
                self._show_feedback("❌ Senha incorreta. Tente novamente.", "error")

    def _admin_dashboard(self):
        """Painel de administração com gráfico interativo"""
        st.subheader("📊 Painel de Administração")
        
        # Contagem de registros únicos por status
        status_counts = self.df["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Quantidade"]

        # Gráfico interativo com Plotly
        fig = px.bar(
            status_counts,
            x="Status",
            y="Quantidade",
            title="Quantidade de Registros por Status",
            labels={"Status": "Status", "Quantidade": "Quantidade"},
            color="Status",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig.update_layout(
            plot_bgcolor=APPLE_COLORS["background"],
            paper_bgcolor=APPLE_COLORS["background"],
            font_color=APPLE_COLORS["text"],
            title_font_size=20,
            xaxis_title_font_size=16,
            yaxis_title_font_size=16,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Exibir todos os dados em uma tabela
        st.dataframe(self.df)

    def run(self):
        """Executa o sistema principal"""
        st.sidebar.title("🎉 Abacaxi Friends")
        page = st.sidebar.radio(
            "Navegue pelas opções:",
            ["Confirmação de Presença", "Novo Cadastro", "Painel de Administração"]
        )

        if page == "Confirmação de Presença":
            self._attendance_confirmation()
        elif page == "Novo Cadastro":
            self._registration_form()
        elif page == "Painel de Administração":
            if "authenticated" not in st.session_state or not st.session_state.authenticated:
                self._authenticate_admin()
            else:
                self._admin_dashboard()

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
