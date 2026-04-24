import streamlit as st
import requests
import json
import time

st.set_page_config(page_title="Máquina de Conversão", layout="wide")

st.title("🎬 Máquina de Conversão - Final MVP")

# --- INICIALIZAÇÃO DO ESTADO ---
if "script_data" not in st.session_state:
    st.session_state.script_data = None
if "video_options" not in st.session_state:
    st.session_state.video_options = {}
if "render_complete" not in st.session_state:
    st.session_state.render_complete = False
if "final_video_path" not in st.session_state:
    st.session_state.final_video_path = None
if "total_time" not in st.session_state:
    st.session_state.total_time = 0
if "is_rendering" not in st.session_state:
    st.session_state.is_rendering = False
if "start_render" not in st.session_state:
    st.session_state.start_render = False
if "was_cancelled" not in st.session_state:
    st.session_state.was_cancelled = False
if "start_time" not in st.session_state:
    st.session_state.start_time = 0

# --- NOVO: POPUP DE CONFIRMAÇÃO ---
@st.dialog("Resumo da Renderização")
def confirm_render_dialog(scenes, eta_seconds):
    st.write(f"⏱️ **Tempo Estimado:** ~{eta_seconds // 60}m {eta_seconds % 60}s")
    st.write("---")
    st.write("**📝 Revisão do Roteiro e Mídia:**")
    
    # Mostra um resumo das cenas
    for i, scene in enumerate(scenes):
        video_status = "✅ Curado manualmente" if scene.get("selected_video_url") else "⚠️ Busca automática"
        st.markdown(f"**Cena {i+1}** ({video_status})\n> _{scene['narration'][:80]}..._")
        
    st.warning("Iniciar a renderização consumirá bastante processamento da sua máquina. Deseja prosseguir?")
    
    col1, col2 = st.columns(2)
    if col1.button("🚀 Iniciar Renderização", use_container_width=True):
        st.session_state.start_render = True
        st.session_state.was_cancelled = False # Limpa o aviso de cancelamento passado, se houver
        st.rerun()
    if col2.button("❌ Voltar e Editar", use_container_width=True):
        st.rerun() # Apenas fecha o modal e não faz nada

# --- CONFIGURAÇÕES E BARRA LATERAL ---
with st.sidebar:
    st.header("Configurações")
    theme = st.text_input("Tema do Vídeo", placeholder="Ex: O futuro da IA", disabled=st.session_state.render_complete)
    lang = st.selectbox("Idioma", ["PT-BR", "EN-US"], disabled=st.session_state.render_complete)
    api_url = "http://localhost:8008" 

    if st.session_state.render_complete:
        st.markdown("---")
        if st.button("🔄 Criar Novo Vídeo (Reset)"):
            st.session_state.script_data = None
            st.session_state.render_complete = False
            st.session_state.final_video_path = None
            st.session_state.video_options = {}
            st.session_state.is_rendering = False
            st.session_state.was_cancelled = False
            st.rerun()

    # BOTÃO DE PÂNICO
    if st.session_state.is_rendering:
        st.markdown("---")
        if st.button("🛑 CANCELAR PROCESSO", type="primary"):
            requests.post(f"{api_url}/v1/video/cancel")
            st.session_state.is_rendering = False
            st.warning("Sinal enviado! Aguardando a máquina abortar a operação atual...")

# --- PASSO 1: GERAÇÃO DO ROTEIRO ---
if st.button("🧠 1. Gerar Roteiro Mestre", disabled=st.session_state.render_complete or st.session_state.is_rendering):
    if theme:
        with st.spinner("A IA está escrevendo..."):
            res = requests.post(f"{api_url}/v1/video/script", json={"theme": theme, "lang": lang})
            if res.status_code == 200:
                st.session_state.script_data = res.json()["data"]["scenes"]
                st.session_state.video_options = {} 
                st.session_state.was_cancelled = False
                st.success("Roteiro pronto!")
    else:
        st.warning("Defina um tema na barra lateral.")

# --- PASSO 2: REVISÃO E CURADORIA ---
if st.session_state.script_data:
    st.markdown("---")
    
    expander_label = "✅ Roteiro e Clips Escolhidos (Finalizado)" if st.session_state.render_complete else "📝 Edição e Escolha de Mídia"
    
    with st.expander(expander_label, expanded=not st.session_state.render_complete):
        edited_scenes = []

        for i, scene in enumerate(st.session_state.script_data):
            with st.container(border=True):
                st.markdown(f"**Cena {i+1}**")
                col_text, col_media = st.columns([2, 1])
                
                with col_text:
                    n_text = st.text_area("Narração", value=scene["narration"], key=f"t_{i}", height=100, disabled=st.session_state.render_complete)
                    n_query = st.text_input("Termo de busca", value=scene["search_query"], key=f"q_{i}", disabled=st.session_state.render_complete)
                    
                    if not st.session_state.render_complete:
                        if st.button(f"🔍 Buscar Opções para Cena {i+1}", key=f"btn_{i}"):
                            with st.spinner("Buscando no Pexels..."):
                                search_res = requests.get(f"{api_url}/v1/media/search?query={n_query}")
                                if search_res.status_code == 200:
                                    cands = search_res.json()["candidates"]
                                    if len(cands) == 0:
                                        st.warning(f"Nenhum vídeo encontrado para '{n_query}'. Tente outro termo.")
                                    st.session_state.video_options[i] = cands

                with col_media:
                    selected_url = st.session_state.script_data[i].get("selected_video_url")
                    if selected_url:
                        st.info("✅ Vídeo Selecionado!")
                    else:
                        st.warning("⚠️ Usando busca automática")

                if i in st.session_state.video_options and not st.session_state.render_complete:
                    st.markdown("*Escolha o melhor clipe:*")
                    cols = st.columns(4)
                    for idx, candidate in enumerate(st.session_state.video_options[i]):
                        with cols[idx % 4]:
                            st.image(candidate["preview_img"], width="stretch")
                            
                            if st.session_state.script_data[i].get("selected_video_url") == candidate["video_url"]:
                                st.success("✅ Selecionado")
                            else:
                                if st.button("Escolher este", key=f"sel_{i}_{idx}"):
                                    st.session_state.script_data[i]["selected_video_url"] = candidate["video_url"]
                                    st.rerun()

                edited_scenes.append({
                    "id": scene["id"],
                    "narration": n_text,
                    "search_query": n_query,
                    "selected_video_url": st.session_state.script_data[i].get("selected_video_url")
                })

    # --- PASSO 3: RENDERIZAÇÃO FINAL ---
    if not st.session_state.render_complete:
        st.markdown("---")
        cleanup = st.checkbox("🧹 Limpar arquivos temporários", value=True)
        
        eta_seconds = len(edited_scenes) * 30
        
        # MENSAGEM PÓS-CANCELAMENTO
        if st.session_state.was_cancelled:
            st.info("💡 A renderização anterior foi cancelada com sucesso. A máquina está livre. Você pode fazer suas edições acima e gerar novamente.")

        # O botão agora abre o modal em vez de iniciar o processo
        if st.button("🚀 RENDERIZAR VÍDEO FINAL", disabled=st.session_state.is_rendering):
            confirm_render_dialog(edited_scenes, eta_seconds)

# Gatilho ativado pelo modal de confirmação
if st.session_state.start_render and not st.session_state.is_rendering and not st.session_state.render_complete:
    st.session_state.is_rendering = True
    st.session_state.start_render = False # Reseta a flag
    st.session_state.start_time = time.time()
    st.rerun()

# Bloco de execução do Streaming
if st.session_state.is_rendering and not st.session_state.render_complete:
    with st.status("🎬 Construindo o vídeo... Por favor, não feche a página.", expanded=True) as status:
        payload = {"theme": theme, "lang": lang, "cleanup": cleanup, "scenes": edited_scenes}
        
        try:
            with requests.post(f"{api_url}/v1/video/render", json=payload, stream=True) as render_res:
                for line in render_res.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        
                        if data["status"] == "info":
                            st.write(data["message"]) 
                            
                        elif data["status"] == "success":
                            st.session_state.total_time = round(time.time() - st.session_state.start_time, 2)
                            st.session_state.final_video_path = data["video_path"]
                            st.session_state.render_complete = True
                            status.update(label="✨ Vídeo Renderizado com Sucesso!", state="complete", expanded=False)
                            st.balloons()
                            
                        elif data["status"] == "error":
                            if "abortada" in data["message"].lower() or "cancelado" in data["message"].lower():
                                status.update(label="Processo Abortado", state="error", expanded=True)
                                st.error("🛑 O vídeo foi cancelado.")
                                st.session_state.was_cancelled = True # Sinaliza para mostrar a mensagem verde na tela
                            else:
                                status.update(label="Erro na Renderização!", state="error", expanded=True)
                                st.error(data["message"])
                            break
        finally:
            st.session_state.is_rendering = False
            st.rerun()

# --- PASSO 4: EXIBIÇÃO E DOWNLOAD ---
if st.session_state.render_complete:
    st.markdown("---")
    st.success(f"🎬 Vídeo pronto! Tempo total de processamento: **{st.session_state.total_time} segundos**")
    
    col_v, col_d = st.columns([2, 1])
    
    with col_v:
        st.video(st.session_state.final_video_path)
    
    with col_d:
        st.markdown("### Download")
        try:
            with open(st.session_state.final_video_path, "rb") as file:
                st.download_button(
                    label="💾 Baixar Arquivo MP4",
                    data=file,
                    file_name=f"video_final_{int(time.time())}.mp4",
                    mime="video/mp4",
                    type="primary"
                )
        except Exception as e:
            st.error("Erro ao carregar o arquivo para download.")