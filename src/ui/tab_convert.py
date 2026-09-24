import streamlit as st
import time
from pathlib import Path
from src.config import Config
from src.core.dict_manager import DictManager
from src.core.replacer import ReplacerEngine

def render_tab_convert(dict_manager: DictManager, config: Config):
    st.header("⚡ Convert Truyện & Xem Trước Kết Quả")
    st.write("Áp dụng từ điển để chuẩn hóa bản dịch thô và xuất file hoàn chỉnh bằng engine Longest Match First.")

    col_pick1, col_pick2 = st.columns([2, 1])
    with col_pick1:
        txt_files = list(config.TXT_DIR.glob("*.txt"))
        file_options = ["-- Chọn file từ thư mục txt/ --"] + [f.name for f in txt_files]
        selected_file = st.selectbox("Chọn file truyện cần convert:", options=file_options, key="convert_file_select")
    with col_pick2:
        uploaded_file = st.file_uploader("Hoặc tải lên file .txt mới:", type=["txt"], key="convert_upload")

    input_file_path = None
    input_file_name = ""

    if uploaded_file is not None:
        input_file_name = uploaded_file.name
        temp_input = config.OUTPUT_DIR / f"temp_{uploaded_file.name}"
        with open(temp_input, "wb") as f:
            f.write(uploaded_file.getbuffer())
        input_file_path = temp_input
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.caption(f"📁 Tệp tải lên: `{input_file_name}` | Kích thước: `{file_size_mb:.2f} MB`")
    elif selected_file and selected_file != "-- Chọn file từ thư mục txt/ --":
        input_file_name = selected_file
        input_file_path = config.TXT_DIR / selected_file
        file_size_mb = input_file_path.stat().st_size / (1024 * 1024)
        st.caption(f"📁 Tệp đã chọn: `{selected_file}` | Kích thước: `{file_size_mb:.2f} MB`")

    if not input_file_path:
        st.info("💡 Vui lòng chọn một file truyện có sẵn trong thư mục `txt/` hoặc tải lên file mới để tiếp tục.")
        return

    st.divider()

    # 2. Chọn phạm vi từ điển áp dụng
    st.subheader("📚 Cấu hình từ điển áp dụng")
    char_terms = dict_manager.load_character_dict()
    common_terms = dict_manager.load_common_dict()
    all_tags = sorted(list({c.novel_tag for c in char_terms}))
    
    col1, col2 = st.columns(2)
    with col1:
        apply_common = st.checkbox(f"Áp dụng Từ điển từ phổ biến ({len(common_terms)} từ)", value=True)
    with col2:
        selected_tags = st.multiselect("Lọc Tag nhân vật áp dụng:", options=all_tags, default=all_tags)

    # Xây dựng bảng ánh xạ (mappings)
    common_mappings = {}
    if apply_common:
        for t in common_terms:
            if t.source and t.target:
                common_mappings[t.source] = t.target
            
    character_mappings = {}
    for c in char_terms:
        if c.novel_tag in selected_tags and c.source and c.target:
            character_mappings[c.source] = c.target

    total_terms = len(common_mappings) + len(character_mappings)
    st.info(f"👉 Tổng số cụm từ áp dụng: **{total_terms:,}** (gồm {len(character_mappings)} tên nhân vật [ch-] tự động viết hoa và {len(common_mappings)} từ phổ biến [co-]).")

    if total_terms == 0:
        st.warning("⚠️ Hiện chưa có từ nào trong từ điển được chọn. Hãy thêm từ trước khi convert.")
        return

    engine = ReplacerEngine(common_mappings=common_mappings, character_mappings=character_mappings)

    # 3. Xem trước Diff (Preview)
    st.divider()
    st.subheader("👀 Xem trước (Preview Diff)")
    st.write("Kiểm tra thử độ chính xác trên 30 dòng đầu tiên của truyện:")
    
    try:
        with open(input_file_path, "r", encoding="utf-8", errors="replace") as f:
            sample_preview = "".join([f.readline() for _ in range(30)])
    except Exception as e:
        sample_preview = "Lỗi khi đọc file xem trước."

    if st.button("🔍 Xem trước kết quả thay thế trên đoạn đầu"):
        converted_preview, preview_stats = engine.replace_text(sample_preview)
        
        c_prev1, c_prev2 = st.columns(2)
        with c_prev1:
            st.markdown("**Bản dịch thô ban đầu:**")
            st.text_area("Bản thô", sample_preview, height=300, disabled=True, label_visibility="collapsed")
        with c_prev2:
            st.markdown("**Sau khi chuẩn hóa:**")
            st.text_area("Đã chuẩn hóa", converted_preview, height=300, disabled=True, label_visibility="collapsed")
            
        total_prev_replaced = sum(preview_stats.values())
        st.success(f"Đã thay thế thành công **{total_prev_replaced}** vị trí trong đoạn xem trước!")
        if preview_stats:
            with st.expander("Chi tiết các từ đã thay thế trong đoạn xem trước"):
                st.json(preview_stats)

    # 4. Thực thi Convert toàn bộ
    st.divider()
    st.subheader("🚀 Thực hiện Convert toàn bộ file")
    clean_stem = Path(input_file_name).stem.replace("temp_", "")
    output_filename = f"{clean_stem}_converted.txt"
    output_file_path = config.OUTPUT_DIR / output_filename

    if st.button("⚡ Bắt đầu Convert và Xuất File Hoàn Chỉnh", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Đang xử lý streaming file qua engine Longest Match First...")
        
        start_time = time.time()
        stats = engine.replace_file(input_file_path, output_file_path)
        elapsed = time.time() - start_time
        
        progress_bar.progress(100)
        total_replaced = sum(stats.values())
        status_text.text("Hoàn thành!")

        st.success(f"🎉 **Convert hoàn tất trong {elapsed:.2f} giây!** Tổng cộng đã thay thế **{total_replaced:,}** lượt từ.")
        st.info(f"📂 File kết quả đã được lưu tại: `{output_file_path}`")

        # Nút tải file trực tiếp về máy
        try:
            with open(output_file_path, "r", encoding="utf-8", errors="replace") as f:
                converted_data = f.read()
            st.download_button(
                label=f"📥 Tải xuống `{output_filename}`",
                data=converted_data,
                file_name=output_filename,
                mime="text/plain"
            )
        except Exception as e:
            st.error(f"Không thể đọc file để tải xuống: {e}")
