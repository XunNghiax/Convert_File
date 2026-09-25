import streamlit as st
import pandas as pd
from pathlib import Path
from src.config import Config
from src.core.dict_manager import DictManager, CommonTerm, CharacterTerm
from src.core.scanner import NovelScanner, ScannedCandidate
from src.core.ai_assistant import AIAssistant
from src.core.scan_exporter import ScanExporter

def render_tab_scan(dict_manager: DictManager, config: Config):
    st.header("🔍 Quét & Lọc Từ Mới Tự Động")
    st.write("Quét file truyện thô để tìm tên riêng, nhân vật và các từ ngữ bất thường chưa có trong từ điển.")

    col1, col2 = st.columns([2, 1])
    with col1:
        txt_files = list(config.TXT_DIR.glob("*.txt"))
        file_options = ["-- Chọn file từ thư mục txt/ --"] + [f.name for f in txt_files]
        selected_file_name = st.selectbox("Chọn file truyện từ thư mục txt/:", options=file_options, key="scan_file_select")
        
    with col2:
        uploaded_file = st.file_uploader("Hoặc tải lên file .txt mới:", type=["txt"], key="scan_file_upload")

    # Đọc nội dung file
    raw_text = ""
    target_novel_tag = "Chung"
    if uploaded_file is not None:
        raw_text = uploaded_file.read().decode("utf-8", errors="replace")
        target_novel_tag = Path(uploaded_file.name).stem[:25]
    elif selected_file_name and selected_file_name != "-- Chọn file từ thư mục txt/ --":
        selected_path = config.TXT_DIR / selected_file_name
        target_novel_tag = selected_path.stem[:25]
        with open(selected_path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read(2000000)  # Đọc mẫu tối đa 2MB để quét từ

    if not raw_text:
        st.info("💡 Vui lòng chọn hoặc tải lên một file truyện để bắt đầu quét tìm từ mới.")
        return

    st.divider()
    st.subheader("⚙️ Tùy chọn quét")
    c1, c2, c3 = st.columns(3)
    with c1:
        scan_mode = st.radio("Phạm vi quét mẫu:", ["Quét mẫu (50,000 ký tự đầu)", "Quét sâu (500,000 ký tự đầu)", "Quét toàn bộ văn bản"])
    with c2:
        min_freq = st.number_input("Tần suất xuất hiện tối thiểu:", min_value=1, max_value=50, value=2)
    with c3:
        has_api_key = bool(config.GEMINI_API_KEY or config.OPENAI_API_KEY)
        use_ai = st.checkbox("Sử dụng AI phân tích & đề xuất", value=has_api_key)
        novel_tag_input = st.text_input("Gán Tag truyện cho nhân vật:", value=target_novel_tag)

    if st.button("🚀 Bắt đầu Quét & Phân tích", type="primary"):
        if "50,000" in scan_mode:
            text_to_scan = raw_text[:50000]
        elif "500,000" in scan_mode:
            text_to_scan = raw_text[:500000]
        else:
            text_to_scan = raw_text
        
        with st.spinner("Đang quét tìm tên riêng và cụm từ bất thường..."):
            # Lấy danh sách từ đã có để loại trừ
            existing_common = {t.source for t in dict_manager.load_common_dict()}
            existing_char = {t.source for t in dict_manager.load_character_dict()}
            existing_all = existing_common.union(existing_char)

            scanner = NovelScanner(existing_words=existing_all)
            candidates = scanner.scan_text(text_to_scan, min_count=min_freq)
            
            if not candidates:
                st.warning("Không tìm thấy cụm từ mới nào thỏa mãn điều kiện quét.")
                return

            results = []
            if use_ai and has_api_key:
                st.info(f"Đang phân tích {len(candidates)} từ ứng viên bằng AI...")
                provider = "gemini" if config.GEMINI_API_KEY else "openai"
                key = config.GEMINI_API_KEY or config.OPENAI_API_KEY
                ai = AIAssistant(api_key=key, provider=provider)
                
                # Xử lý theo batch 30 từ
                for i in range(0, len(candidates), 30):
                    batch = candidates[i:i+30]
                    ai_results = ai.analyze_batch(batch)
                    for c, r in zip(batch, ai_results):
                        c.suggested_target = r.suggested_translation
                        results.append({
                            "selected": True,
                            "source": c.phrase,
                            "target": r.suggested_translation,
                            "is_character": r.is_character,
                            "category": r.category,
                            "count": c.count,
                            "context": c.sample_contexts[0] if c.sample_contexts else ""
                        })
            else:
                for c in candidates:
                    target_val = c.suggested_target if c.suggested_target else c.phrase
                    results.append({
                        "selected": True,
                        "source": c.phrase,
                        "target": target_val,
                        "is_character": (c.candidate_type == "Tên nhân vật"),
                        "category": c.candidate_type,
                        "count": c.count,
                        "context": c.sample_contexts[0] if c.sample_contexts else ""
                    })

            # Tự động xuất kết quả vào thư mục scanned/
            safe_novel_name = novel_tag_input or target_novel_tag
            json_path, txt_path = ScanExporter.auto_export_scanned(candidates, safe_novel_name, config.SCANNED_DIR)

            st.session_state["scan_results"] = results
            st.session_state["scan_novel_tag"] = novel_tag_input
            st.session_state["scan_json_path"] = str(json_path)
            st.session_state["scan_txt_path"] = str(txt_path)
            st.success(f"💾 **Đã tự động lưu kết quả quét vào thư mục scanned/:** `{json_path.name}` và `{txt_path.name}`")

    # Hiển thị nút tải file nếu đã có kết quả scan
    if "scan_json_path" in st.session_state and Path(st.session_state["scan_json_path"]).exists():
        st.divider()
        st.subheader("📥 Tải về kết quả quét")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            with open(st.session_state["scan_json_path"], "r", encoding="utf-8") as f:
                st.download_button(
                    label=f"📥 Tải `{Path(st.session_state['scan_json_path']).name}` (JSON)",
                    data=f.read(),
                    file_name=Path(st.session_state["scan_json_path"]).name,
                    mime="application/json"
                )
        with col_dl2:
            if "scan_txt_path" in st.session_state and Path(st.session_state["scan_txt_path"]).exists():
                with open(st.session_state["scan_txt_path"], "r", encoding="utf-8") as f:
                    st.download_button(
                        label=f"📥 Tải `{Path(st.session_state['scan_txt_path']).name}` (TXT Prompt AI)",
                        data=f.read(),
                        file_name=Path(st.session_state["scan_txt_path"]).name,
                        mime="text/plain"
                    )

    # Hiển thị bảng kết quả để người dùng duyệt
    if "scan_results" in st.session_state and st.session_state["scan_results"]:
        st.divider()
        st.subheader("📋 Bảng duyệt từ ứng viên")
        st.write("Đánh dấu chọn các từ bạn muốn lưu, chỉnh sửa bản dịch đề xuất trực tiếp trên bảng:")
        df_results = pd.DataFrame(st.session_state["scan_results"])
        
        edited_df = st.data_editor(
            df_results,
            use_container_width=True,
            column_config={
                "selected": st.column_config.CheckboxColumn("Chọn", default=True),
                "source": st.column_config.TextColumn("Từ gốc", disabled=True),
                "target": st.column_config.TextColumn("Từ chuẩn đề xuất (Có thể sửa)"),
                "is_character": st.column_config.CheckboxColumn("Là Tên nhân vật?"),
                "category": st.column_config.TextColumn("Phân loại"),
                "count": st.column_config.NumberColumn("Tần suất", disabled=True),
                "context": st.column_config.TextColumn("Ngữ cảnh mẫu", disabled=True)
            },
            key="scan_editor"
        )

        if st.button("➕ Thêm các từ đã chọn vào Từ Điển", type="primary"):
            added_common = 0
            added_char = 0
            novel_tag = st.session_state.get("scan_novel_tag", "Chung")

            for _, row in edited_df.iterrows():
                if row.get("selected") and row.get("source") and row.get("target"):
                    src = str(row["source"]).strip()
                    tgt = str(row["target"]).strip()
                    if row.get("is_character"):
                        try:
                            dict_manager.add_character_term(source=src, target=tgt, novel_tag=novel_tag)
                            added_char += 1
                        except ValueError:
                            pass
                    else:
                        try:
                            dict_manager.add_common_term(source=src, target=tgt, category=str(row.get("category", "Chung")))
                            added_common += 1
                        except ValueError:
                            pass

            st.success(f"🎉 Đã thêm thành công: **{added_char}** tên nhân vật và **{added_common}** từ phổ biến vào từ điển!")
            st.session_state["scan_results"] = []
            st.rerun()
