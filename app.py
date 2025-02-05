import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração da interface baseada no design da Apple
st.set_page_config(
    page_title="Gestão de Presenças",
    page_icon="✅",
    layout="centered"
)

# Definir caminho do CSV
CSV_FILE = "registros.csv"

# Criar o CSV se não existir ou corrigir estrutura
def verificar_e_corrigir_csv():
    if not os.path.exists(CSV_FILE) or os.stat(CSV_FILE).st_size == 0:
        df = pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])
        df.to_csv(CSV_FILE, index=False)
    else:
        df = pd.read_csv(CSV_FILE)
        # Verificar se todas as colunas estão presentes
        colunas_necessarias = ["Nome", "Celular", "Tipo", "Status"]
        if not all(col in df.columns for col in colunas_necessarias):
            st.error("🚨 O arquivo CSV está corrompido ou mal formatado. Criando um novo...")
            df = pd.DataFrame(columns=colunas_necessarias)
            df.to_csv(CSV_FILE, index=False)
    return df

# Carregar os registros
df = verificar_e_corrigir_csv()

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

                        df.loc[df["Nome"] == selected_row, "Status"] = "Pagamento Confirmado"
                        df.to_csv(CSV_FILE, index=False)

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
        tipo = "Novo"  # Sempre cadastra como "Novo"
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
                df.to_csv(CSV_FILE, index=False)
                st.success("✅ Cadastro realizado com sucesso!")
                st.balloons()