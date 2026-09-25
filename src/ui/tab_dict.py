from pathlib import Path
import streamlit as st
import pandas as pd
from src.core.dict_manager import DictManager, CommonTerm, CharacterTerm

def render_tab_dict(dict_manager: DictManager):
    st.header("📖 Quản lý Từ Điển")

    with st.expander("⚙️ Công cụ Chuẩn hóa & Nạp từ file Scan đã biên tập", expanded=False):
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("##### ✨ Chuẩn hóa toàn bộ từ điển")
            st.caption("Khử trùng lặp từ, chuyển dấu tổ hợp NFD sang NFC, đánh lại số thứ tự ID tuần tự co-1..N và ch-1..N.")
            if st.button("✨ Thực hiện Chuẩn hóa ngay", key="btn_standardize"):
                stats = dict_manager.standardize_dictionaries()
                extra_msg = f", Đã khắc phục {stats.get('conflicts_fixed', 0)} mục xung đột mở rộng" if stats.get('conflicts_fixed', 0) > 0 else ""
                st.success(f"Đã chuẩn hóa thành công! Common: {stats['common_after']} từ (khử {stats['common_deduped']}), Characters: {stats['character_after']} từ (khử {stats['character_deduped']}){extra_msg}.")
                st.rerun()

        with c2:
            st.markdown("##### 📥 Nạp từ file Scan (.json / .txt)")
            uploaded_scan = st.file_uploader("Chọn file scan đã biên tập:", type=["json", "txt"], key="upload_scan_file")
            novel_tag_input = st.text_input("Tag truyện cho nhân vật:", value="Chung", key="scan_import_tag")
            if uploaded_scan and st.button("🚀 Nạp vào từ điển", key="btn_import_scan"):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_scan.name).suffix) as tmp:
                    tmp.write(uploaded_scan.getvalue())
                    tmp_path = Path(tmp.name)
                try:
                    records = dict_manager.parse_scanned_file(tmp_path)
                    res = dict_manager.import_records(records, default_novel_tag=novel_tag_input)
                    st.success(f"Nạp thành công {res['total_records']} mục! Nhân vật: +{res['chars_added']} mới, ~{res['chars_updated']} cập nhật. Từ phổ biến: +{res['common_added']} mới, ~{res['common_updated']} cập nhật.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi nạp file: {e}")
                finally:
                    if tmp_path.exists():
                        tmp_path.unlink()

    subtab1, subtab2 = st.tabs(["Từ điển Từ phổ biến (Global)", "Từ điển Tên nhân vật (Characters)"])
    
    # ---------------- TAB 1: TỪ PHỔ BIẾN ----------------
    with subtab1:
        st.subheader("Danh sách các từ & cụm từ dịch thô phổ biến (ID: co-1, co-2...)")
        common_terms = dict_manager.load_common_dict()
        df_common = pd.DataFrame([t.model_dump() for t in common_terms])
        
        if df_common.empty:
            df_common = pd.DataFrame(columns=["id", "source", "target", "category"])

        # Bộ lọc tìm kiếm
        search_common = st.text_input("🔍 Tìm kiếm từ phổ biến:", key="search_common")
        df_display_common = df_common
        if search_common:
            df_display_common = df_common[
                df_common["source"].str.contains(search_common, case=False, na=False) |
                df_common["target"].str.contains(search_common, case=False, na=False) |
                df_common["id"].str.contains(search_common, case=False, na=False)
            ]

        # Bảng chỉnh sửa tương tác
        edited_common = st.data_editor(
            df_display_common,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_common",
            column_config={
                "id": st.column_config.TextColumn("ID", disabled=True),
                "source": st.column_config.TextColumn("Từ gốc (Bản thô)", required=True),
                "target": st.column_config.TextColumn("Từ thay thế chuẩn", required=True),
                "category": st.column_config.SelectboxColumn("Phân loại", options=["Lỗi dịch máy", "Xưng hô", "Cụm từ Hán Việt", "Thuật ngữ", "Chung"])
            }
        )

        col1, col2 = st.columns([2, 5])
        with col1:
            if st.button("💾 Lưu thay đổi (Từ phổ biến)", type="primary", key="save_common"):
                updated_terms = []
                for idx, (_, row) in enumerate(edited_common.iterrows(), start=1):
                    if pd.notna(row.get("source")) and str(row.get("source")).strip():
                        updated_terms.append(CommonTerm(
                            id=f"co-{idx}",
                            source=str(row.get("source")).strip(),
                            target=str(row.get("target")).strip() if pd.notna(row.get("target")) else "",
                            category=str(row.get("category", "Chung"))
                        ))
                dict_manager.save_common_dict(updated_terms)
                st.success("Đã lưu từ điển từ phổ biến thành công!")
                st.rerun()

    # ---------------- TAB 2: TÊN NHÂN VẬT ----------------
    with subtab2:
        st.subheader("Danh sách Tên nhân vật (ID: ch-1, ch-2...)")
        char_terms = dict_manager.load_character_dict()
        df_char = pd.DataFrame([t.model_dump() for t in char_terms])
        
        if df_char.empty:
            df_char = pd.DataFrame(columns=["id", "source", "target", "novel_tag"])

        # Bộ lọc Tag truyện
        available_tags = ["Tất cả"] + sorted(list(df_char["novel_tag"].dropna().unique()))
        selected_tag = st.selectbox("📚 Lọc theo Bộ truyện:", options=available_tags, key="filter_tag")
        
        df_display_char = df_char
        if selected_tag != "Tất cả":
            df_display_char = df_char[df_char["novel_tag"] == selected_tag]

        # Bảng chỉnh sửa tên nhân vật
        edited_char = st.data_editor(
            df_display_char,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_char",
            column_config={
                "id": st.column_config.TextColumn("ID", disabled=True),
                "source": st.column_config.TextColumn("Tên gốc (Thô)", required=True),
                "target": st.column_config.TextColumn("Tên chuẩn hóa", required=True),
                "novel_tag": st.column_config.TextColumn("Tag truyện", required=True)
            }
        )

        col1, col2 = st.columns([2, 5])
        with col1:
            if st.button("💾 Lưu thay đổi (Tên nhân vật)", type="primary", key="save_char"):
                updated_chars = []
                for idx, (_, row) in enumerate(edited_char.iterrows(), start=1):
                    if pd.notna(row.get("source")) and str(row.get("source")).strip():
                        updated_chars.append(CharacterTerm(
                            id=f"ch-{idx}",
                            source=str(row.get("source")).strip(),
                            target=str(row.get("target")).strip() if pd.notna(row.get("target")) else "",
                            novel_tag=str(row.get("novel_tag", "Chung")).strip()
                        ))
                dict_manager.save_character_dict(updated_chars)
                st.success("Đã lưu từ điển tên nhân vật thành công!")
                st.rerun()
