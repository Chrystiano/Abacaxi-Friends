import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime
import os

# Configuração da interface
st.set_page_config(
    page_title="Gestão de Presenças",
    page_icon="✅",
    layout="centered"
)

# Carregar IDs e credenciais dos Secrets
GOOGLE_SHEET_ID = st.secrets["gdrive"]["GOOGLE_SHEET_ID"]
GDRIVE_FOLDER_ID = st.secrets["gdrive"]["GDRIVE_FOLDER_ID"]
credentials_dict = st.secrets["gdrive_credentials"]
creds = service_account.Credentials.from_service_account_info(credentials_dict)

# Função para carregar os dados do Google Sheets
@st.cache_data(ttl=600)
def load_data():
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=GOOGLE_SHEET_ID, range="A:D").execute()
        values = result.get('values', [])
        if not values:
            return pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])
        else:
            df = pd.DataFrame(values[1:], columns=values[0])
            return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])

# Função para salvar os dados no Google Sheets
def save_data(df):
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        values = [df.columns.values.tolist()] + df.values.tolist()
        body = {'values': values}
        sheet.values().update(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="A1",
            valueInputOption="RAW",
            body=body
        ).execute()
        st.success("Dados salvos com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar os dados: {e}")

# Função para fazer upload de arquivo no Google Drive
def upload_to_drive(file_path, filename):
    try:
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': filename,
            'parents': [GDRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        st.success(f"Arquivo enviado para o Google Drive com ID: {file.get('id')}")
    except Exception as e:
        st.error(f"Erro ao fazer upload para o Google Drive: {e}")

# Carregar os registros
df = load_data()

# Criar abas
aba_consulta, aba_cadastro = st.tabs(["🔎 Consultar e Confirmar Presença", "📝 Cadastrar Nova Pessoa"])

# === ABA DE CONSULTA ===
with aba_consulta:
    st.markdown(
        "<h1 style='text-align: center; color: #1F618D;'>🎉 Confirmação de Presença 🎉</h1>",
        unsafe_allow_html=True
    )

    nome_busca = st.text_input("🔎 Digite seu nome para buscar", "").strip()

    if nome_busca:
        results = df[df["Nome"].str.contains(nome_busca, case=False, na=False)]
        if not results.empty:
            st.write(f"🔍 Encontramos {len(results)} resultado(s):")
            selected_row = st.selectbox("Selecione seu nome:", results["Nome"].tolist())
        else:
            st.error("Nenhum registro encontrado. Verifique a grafia do nome.")

        if "selected_row" in locals():
            status_atual = df[df["Nome"] == selected_row]["Status"].values[0]
            if status_atual == "Pagamento Confirmado":
                st.warning("✅ Você já confirmou sua presença anteriormente.")
            else:
                st.success(f"🔹 {selected_row} encontrado! Envie um arquivo para confirmar sua presença.")

                uploaded_file = st.file_uploader(
                    "📁 Envie um comprovante (CSV, PNG, JPG, PDF - máx. 2MB)",
                    type=["csv", "png", "jpg", "pdf"]
                )

                if uploaded_file:
                    if uploaded_file.size > 2 * 1024 * 1024:
                        st.error("❌ O arquivo excede 2MB. Por favor, envie um arquivo menor.")
                    else:
                        os.makedirs("uploads", exist_ok=True)
                        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
                        file_ext = os.path.splitext(uploaded_file.name)[1]
                        new_filename = f"{timestamp}_{selected_row}{file_ext}"
                        file_path = os.path.join("uploads", new_filename)

                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        st.success(f"✅ Arquivo salvo como `{new_filename}`!")

                        # Fazer upload para o Google Drive
                        upload_to_drive(file_path, new_filename)

                        df.loc[df["Nome"] == selected_row, "Status"] = "Pagamento Confirmado"
                        save_data(df)

                        st.balloons()
                        st.success("🎉 Presença confirmada com sucesso!")

# === ABA DE CADASTRO ===
with aba_cadastro:
    st.markdown(
        "<h1 style='text-align: center; color: #2C3E50;'>📝 Cadastrar Nova Pessoa</h1>",
        unsafe_allow_html=True
    )

    with st.form(key="cadastro_form"):
        nome = st.text_input("🆕 Nome Completo", "").strip()
        celular = st.text_input("📞 Número de Celular", "").strip()
        tipo = st.selectbox("👤 Tipo", ["Membro", "Convidado"])
        status = "Pagamento Pendente"

        cadastrar = st.form_submit_button("📌 Cadastrar")

        if cadastrar:
            if nome == "" or celular == "":
                st.error("❌ Nome e celular são obrigatórios!")
            elif df["Nome"].str.lower().str.strip().eq(nome.lower()).any():
                st.error("❌ Já existe um cadastro com esse nome.")
            else:
                novo_registro = pd.DataFrame([[nome, celular, tipo, status]], columns=df.columns)
                df = pd.concat([df, novo_registro], ignore_index=True)
                save_data(df)
                st.success("✅ Cadastro realizado com sucesso!")
                st.balloons()
