import streamlit as st
import requests

st.set_page_config(page_title="Máquina de Conversão", layout="wide")

st.title("🎬 Máquina de Conversão - Curadoria V2")

# Inicialização do Estado
if "script_data" not in st.session_state:
    st.session_state.script_data = None
if "video_options" not in st.session_state:
    st.session_state.video_options = {}

# Configurações de Entrada
with st.sidebar:
    st.header("Configurações")
    theme = st.text_input("Tema do Vídeo", placeholder="Ex: O futuro da IA")
    lang = st.selectbox("Idioma", ["PT-BR", "EN-US"])
    api_url = "http://localhost:8008" # Ajuste a porta se necessário

# --- PASSO 1: GERAÇÃO DO ROTEIRO ---
if st.button("🧠 1. Gerar Roteiro Mestre"):
    if theme:
        with st.spinner("A IA está escrevendo..."):
            res = requests.post(f"{api_url}/v1/video/script", json={"theme": theme, "lang": lang})
            if res.status_code == 200:
                st.session_state.script_data = res.json()["data"]["scenes"]
                st.session_state.video_options = {} # Limpa buscas antigas
                st.success("Roteiro pronto!")
    else:
        st.warning("Defina um tema.")

# --- PASSO 2: REVISÃO E CURADORIA ---
if st.session_state.script_data:
    st.markdown("---")
    st.subheader("📝 Edição e Escolha de Mídia")
    
    edited_scenes = []

    for i, scene in enumerate(st.session_state.script_data):
        with st.container(border=True):
            st.markdown(f"**Cena {i+1}**")
            col_text, col_media = st.columns([2, 1])
            
            with col_text:
                n_text = st.text_area("Narração", value=scene["narration"], key=f"t_{i}", height=100)
                n_query = st.text_input("Termo de busca", value=scene["search_query"], key=f"q_{i}")
                
                # Botão para buscar vídeos específicos para esta cena
                if st.button(f"🔍 Buscar Opções para Cena {i+1}", key=f"btn_{i}"):
                    with st.spinner("Buscando no Pexels..."):
                        search_res = requests.get(f"{api_url}/v1/media/search?query={n_query}")
                        if search_res.status_code == 200:
                            cands = search_res.json()["candidates"]
                            if len(cands) == 0:
                                st.warning(f"Nenhum vídeo encontrado para '{n_query}'. Tente um termo em inglês mais simples (ex: 'neon city').")
                            st.session_state.video_options[i] = cands

            with col_media:
                # Se houver uma seleção prévia, mostra o status
                selected_url = st.session_state.script_data[i].get("selected_video_url")
                if selected_url:
                    st.info("✅ Vídeo Selecionado!")
                else:
                    st.warning("⚠️ Usando busca automática")

            # Exibe a Galeria se houver resultados para esta cena
            if i in st.session_state.video_options:
                st.markdown("*Escolha o melhor clipe:*")
                cols = st.columns(4)
                for idx, candidate in enumerate(st.session_state.video_options[i]):
                    with cols[idx % 4]:
                        st.image(candidate["preview_img"], use_container_width=True)
                        if st.button("Selecionar", key=f"sel_{i}_{idx}"):
                            st.session_state.script_data[i]["selected_video_url"] = candidate["video_url"]
                            st.rerun()

            edited_scenes.append({
                "id": scene["id"],
                "narration": n_text,
                "search_query": n_query,
                "selected_video_url": st.session_state.script_data[i].get("selected_video_url")
            })

    # --- PASSO 3: RENDERIZAÇÃO FINAL ---
    st.markdown("---")
    cleanup = st.checkbox("Limpar arquivos temporários", value=True)
    
    if st.button("🚀 RENDERIZAR VÍDEO FINAL"):
        with st.spinner("Processando..."):
            payload = {
                "theme": theme,
                "lang": lang,
                "cleanup": cleanup,
                "scenes": edited_scenes
            }
            render_res = requests.post(f"{api_url}/v1/video/render", json=payload)
            
            if render_res.status_code == 200:
                st.balloons()
                video_path = render_res.json()["video_path"]
                st.video(video_path)
            else:
                st.error("Erro na renderização.")