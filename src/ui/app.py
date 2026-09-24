import streamlit as st
from src.config import Config
from src.core.dict_manager import DictManager
from src.ui.tab_scan import render_tab_scan
from src.ui.tab_dict import render_tab_dict
from src.ui.tab_convert import render_tab_convert

st.set_page_config(
    page_title="Trình Convert & Chuẩn Hóa Truyện",
    page_icon="📚",
    layout="wide"
)

def main():
    st.title("📚 Trình Convert & Chuẩn Hóa Truyện Dịch Thô")
    st.caption("Ứng dụng chuẩn hóa từ ngữ, nhân vật và chuyển đổi truyện convert tiếng Trung sang tiếng Việt mượt mà với engine tốc độ cao.")

    config = Config()
    dict_manager = DictManager(
        common_path=config.COMMON_DICT_PATH,
        character_path=config.CHARACTER_DICT_PATH
    )

    tab1, tab2, tab3 = st.tabs([
        "⚡ 1. Convert Truyện & Xem Trước",
        "📖 2. Quản lý Từ Điển",
        "🔍 3. Quét & Lọc Từ Mới"
    ])

    with tab1:
        render_tab_convert(dict_manager, config)

    with tab2:
        render_tab_dict(dict_manager)

    with tab3:
        render_tab_scan(dict_manager, config)

if __name__ == "__main__":
    main()
