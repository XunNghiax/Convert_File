import streamlit as st
import pandas as pd
from src.core.dict_manager import DictManager, CommonTerm, CharacterTerm

def render_tab_dict(dict_manager: DictManager):
    st.header("📖 Quản lý Từ Điển")
    
    subtab1, subtab2 = st.tabs(["Từ điển Từ phổ biến (Global)", "Từ điển Tên nhân vật (Characters)"])
    
    # ---------------- TAB 1: TỪ PHỔ BIẾN ----------------
    with subtab1:
        st.subheader("Danh sách các từ & cụm từ dịch thô phổ biến (ID: co-1, co-2...)")
        common_terms = dict_manager.load_common_dict()
        df_common = pd.DataFrame([t.model_dump() for t in common_terms])
        
        if df_common.empty:
            df_common = pd.DataFrame(columns=["id", "source", "target", "category", "notes"])

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
                "category": st.column_config.SelectboxColumn("Phân loại", options=["Lỗi dịch máy", "Xưng hô", "Cụm từ Hán Việt", "Thuật ngữ", "Chung"]),
                "notes": st.column_config.TextColumn("Ghi chú")
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
                            category=str(row.get("category", "Chung")),
                            notes=str(row.get("notes", "")) if pd.notna(row.get("notes")) else ""
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
            df_char = pd.DataFrame(columns=["id", "source", "target", "novel_tag", "gender_role"])

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
                "novel_tag": st.column_config.TextColumn("Tag truyện", required=True),
                "gender_role": st.column_config.TextColumn("Giới tính / Vai vế")
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
                            novel_tag=str(row.get("novel_tag", "Chung")).strip(),
                            gender_role=str(row.get("gender_role", "")) if pd.notna(row.get("gender_role")) else ""
                        ))
                dict_manager.save_character_dict(updated_chars)
                st.success("Đã lưu từ điển tên nhân vật thành công!")
                st.rerun()
