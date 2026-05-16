import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ExifTags, ImageOps
from colorthief import ColorThief
from pathlib import Path
import io
import tempfile
import os
import requests

try:
    import opencc
    CONVERTER_AVAILABLE = True
except:
    CONVERTER_AVAILABLE = False

# 页面配置
st.set_page_config(
    page_title="照片卡片生成器",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS
st.markdown("""
<style>
    .main .block-container {background: #f6f2eb; padding-top: 20px;}
    header, .stDeployButton {display: none;}
    .main-title {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 48px; font-weight: 300; color: #2c2c2c;
        text-align: center; margin-bottom: 10px; letter-spacing: -0.5px;
    }
    .subtitle {
        font-family: 'Inter', sans-serif; font-size: 14px;
        color: #888; text-align: center; margin-bottom: 20px;
        letter-spacing: 1px; text-transform: uppercase;
    }
    .help-text {
        font-family: 'Inter', sans-serif; font-size: 13px;
        color: #999; text-align: center; margin-bottom: 30px;
        line-height: 1.6;
    }
    .photo-card-container {
        background: white; padding: 30px; border-radius: 24px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.08); margin: 20px 0;
    }
    .stTextInput input {border-radius: 12px; border: 1px solid #e0e0e0; background: white;}
    .stButton button {
        border-radius: 50px; background: #2c2c2c; color: white;
        font-weight: 500; border: none; padding: 12px 40px;
    }
    .stButton button:hover {background: #444;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def extract_main_color(image):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        image.save(tmp.name)
        tmp_path = tmp.name
    try:
        ct = ColorThief(tmp_path)
        color = ct.get_color(quality=1)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return color

def extract_palette(image, num_colors=6):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        image.save(tmp.name)
        tmp_path = tmp.name
    try:
        ct = ColorThief(tmp_path)
        palette = ct.get_palette(color_count=num_colors, quality=1)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return palette

def get_exif_data(image):
    exif_data = image._getexif()
    if not exif_data:
        return None
    exif = {}
    for tag, value in exif_data.items():
        tag_name = ExifTags.TAGS.get(tag, tag)
        exif[tag_name] = value
    result = {}
    if 'DateTimeOriginal' in exif:
        dt = exif['DateTimeOriginal']
        result['datetime'] = dt.replace(':', '-', 2).replace(':', '.', 1)
    return result

def convert_to_traditional(text):
    if CONVERTER_AVAILABLE and text:
        converter = opencc.OpenCC('s2t.json')
        return converter.convert(text)
    return text

def get_weather_by_city(city_name, date_str=""):
    """通过城市名和时间获取天气（使用Open-Meteo API）
    
    Args:
        city_name: 城市名
        date_str: 日期字符串，格式如 "2026.05.16"
    """
    try:
        # 中文城市名映射
        city_map = {
            '杭州': 'Hangzhou', '杭州市': 'Hangzhou',
            '北京': 'Beijing', '北京市': 'Beijing',
            '上海': 'Shanghai', '上海市': 'Shanghai',
            '广州': 'Guangzhou', '广州市': 'Guangzhou',
            '深圳': 'Shenzhen', '深圳市': 'Shenzhen',
            '成都': 'Chengdu', '成都市': 'Chengdu',
            '重庆': 'Chongqing', '重庆市': 'Chongqing',
            '武汉': 'Wuhan', '武汉市': 'Wuhan',
            '西安': 'Xian', '西安市': 'Xian',
            '南京': 'Nanjing', '南京市': 'Nanjing',
            '天津': 'Tianjin', '天津市': 'Tianjin',
            '苏州': 'Suzhou', '苏州市': 'Suzhou',
            '厦门': 'Xiamen', '厦门市': 'Xiamen',
            '青岛': 'Qingdao', '青岛市': 'Qingdao',
            '大连': 'Dalian', '大连市': 'Dalian',
            '宁波': 'Ningbo', '宁波市': 'Ningbo',
        }
        
        # 清理城市名
        city_clean = city_name.replace('，中国', '').replace(', 中国', '').strip()
        city_en = city_map.get(city_clean, city_map.get(city_name, city_name))
        
        # 获取城市坐标
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_en}"
        geo_resp = requests.get(geo_url, timeout=10)
        geo_data = geo_resp.json()
        
        if geo_data.get('results') and len(geo_data['results']) > 0:
            lat = geo_data['results'][0]['latitude']
            lon = geo_data['results'][0]['longitude']
            
            # 判断是历史天气还是当前天气
            if date_str:
                # 解析日期
                try:
                    from datetime import datetime
                    input_date = datetime.strptime(date_str, "%Y.%m.%d")
                    today = datetime.now()
                    
                    # 如果是未来日期，查询预报天气
                    if input_date.date() > today.date():
                        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,weather_code&start_date={input_date.strftime('%Y-%m-%d')}&end_date={input_date.strftime('%Y-%m-%d')}&timezone=auto"
                        weather_resp = requests.get(weather_url, timeout=10)
                        weather_data = weather_resp.json()
                        
                        temp = int(weather_data['daily']['temperature_2m_max'][0])
                        weather_code = weather_data['daily']['weather_code'][0]
                    
                    # 如果是过去日期，查询历史天气
                    else:
                        weather_url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&daily=temperature_2m_max,weather_code&start_date={input_date.strftime('%Y-%m-%d')}&end_date={input_date.strftime('%Y-%m-%d')}&timezone=auto"
                        weather_resp = requests.get(weather_url, timeout=10)
                        weather_data = weather_resp.json()
                        
                        temp = int(weather_data['daily']['temperature_2m_max'][0])
                        weather_code = weather_data['daily']['weather_code'][0]
                
                except Exception as e:
                    # 解析失败，返回当前天气
                    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
                    weather_resp = requests.get(weather_url, timeout=10)
                    weather_data = weather_resp.json()
                    
                    temp = int(weather_data['current']['temperature_2m'])
                    weather_code = weather_data['current']['weather_code']
            
            else:
                # 没有日期，查询当前天气
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
                weather_resp = requests.get(weather_url, timeout=10)
                weather_data = weather_resp.json()
                
                temp = int(weather_data['current']['temperature_2m'])
                weather_code = weather_data['current']['weather_code']
            
            # 天气代码转文字（中英文）
            weather_map = {
                0: '晴', 1: '晴', 2: '多云', 3: '阴天',
                45: '雾', 48: '雾凇',
                51: '小毛毛雨', 53: '毛毛雨', 55: '大毛毛雨',
                61: '小雨', 63: '雨', 65: '大雨',
                71: '小雪', 73: '雪', 75: '大雪',
                80: '阵雨', 81: '阵雨', 82: '大阵雨',
                95: '雷暴'
            }
            weather_desc = weather_map.get(weather_code, '未知')
            
            # 天气图标
            weather_icons = {
                0: '☀️', 1: '☀️', 2: '⛅', 3: '☁️',
                45: '🌫️', 48: '🌫️',
                51: '🌧️', 53: '🌧️', 55: '🌧️',
                61: '🌧️', 63: '🌧️', 65: '🌧️',
                71: '🌨️', 73: '🌨️', 75: '🌨️',
                80: '🌧️', 81: '🌧️', 82: '🌧️',
                95: '⛈️'
            }
            weather_icon = weather_icons.get(weather_code, '🌤️')
            
            return f"{weather_icon} {temp}°C · {weather_desc}"
    except Exception as e:
        st.error(f"天气获取失败: {e}")
    return ""

def create_photo_card(image, location="", custom_time="", weather="", mood="", 
                       use_traditional=False, show_palette=True):
    # 提取主色调和色卡
    palette = extract_palette(image, 6) if show_palette else []
    
    # 时间信息
    if custom_time:
        datetime_str = custom_time
    else:
        exif = get_exif_data(image)
        datetime_str = exif.get('datetime', '') if exif else ''
    
    # 繁简转换
    if use_traditional:
        if location:
            location = convert_to_traditional(location)
        if mood:
            mood = convert_to_traditional(mood)
    
    # 只替换地点中的逗号，心情标签保持原样
    location = location.replace('，', ' · ').replace(',', ' · ')
    
    # 计算尺寸（提高分辨率2倍）
    card_width = 1600  # 原来800
    photo_width = 1400  # 原来700
    photo_height = int(photo_width * image.height / image.width)
    padding = 100
    total_height = padding + photo_height + padding + 400 + padding
    
    # 创建画布
    bg_color = (246, 242, 235)
    output = Image.new('RGB', (card_width, total_height), bg_color)
    
    # 照片（使用高质量重采样）
    photo = image.resize((photo_width, photo_height), Image.Resampling.LANCZOS)
    photo_x = (card_width - photo_width) // 2
    photo_y = padding
    
    # 阴影
    shadow = Image.new('RGBA', (photo_width + 20, photo_height + 20), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle([10, 10, photo_width + 10, photo_height + 10], 
                                   radius=16, fill=(0, 0, 0, 30))
    output.paste(shadow, (photo_x - 10, photo_y - 5), shadow)
    output.paste(photo, (photo_x, photo_y))
    
    # 绘制信息
    draw = ImageDraw.Draw(output)
    text_color = (44, 44, 44)
    
    # 字体（放大2倍）
    try:
        font_dir = Path("fonts")
        font_title = ImageFont.truetype(str(font_dir / "GenWanMin2-EL.ttc"), 64)
        font_text = ImageFont.truetype(str(font_dir / "GenWanMin2-EL.ttc"), 32)
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
    
    info_y = photo_y + photo_height + padding // 2
    
    # 地点
    if location:
        bbox_loc = draw.textbbox((0, 0), location, font=font_title)
        loc_width = bbox_loc[2] - bbox_loc[0]
        x_loc = (card_width - loc_width) // 2
        draw.text((x_loc, info_y), location, fill=text_color, font=font_title)
        info_y += 100
    
    # 天气
    if weather:
        bbox_weather = draw.textbbox((0, 0), weather, font=font_text)
        weather_width = bbox_weather[2] - bbox_weather[0]
        x_weather = (card_width - weather_width) // 2
        draw.text((x_weather, info_y), weather, fill=(136, 136, 136), font=font_text)
        info_y += 60
    
    # 时间
    if datetime_str:
        bbox_time = draw.textbbox((0, 0), datetime_str, font=font_text)
        time_width = bbox_time[2] - bbox_time[0]
        x_time = (card_width - time_width) // 2
        draw.text((x_time, info_y), datetime_str, fill=(136, 136, 136), font=font_text)
        info_y += 70
    
    # 心情（引用样式，居中）
    if mood:
        mood_text = f'"{mood}"'
        bbox_mood = draw.textbbox((0, 0), mood_text, font=font_text)
        mood_width = bbox_mood[2] - bbox_mood[0]
        mood_height = bbox_mood[3] - bbox_mood[1]
        
        quote_width = min(mood_width + 80, card_width - 200)
        line_x = (card_width - quote_width) // 2
        
        draw.line([(line_x, info_y), (line_x, info_y + mood_height + 20)], fill=(200, 200, 200), width=4)
        
        x_mood = line_x + 30
        draw.text((x_mood, info_y + 10), mood_text, fill=(85, 85, 85), font=font_text)
    
    # 色卡
    if show_palette and palette:
        color_y = total_height - padding - 50
        color_start_x = (card_width - len(palette) * 100 - (len(palette) - 1) * 20) // 2
        for i, color in enumerate(palette):
            x = color_start_x + i * 120
            for dx in range(100):
                for dy in range(100):
                    dist = ((dx - 50) ** 2 + (dy - 50) ** 2) ** 0.5
                    if dist <= 50:
                        output.putpixel((x + dx, color_y + dy), color)
    
    return output

# 主界面
st.markdown('<div class="main-title">Photo Card</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Create Beautiful Memories</div>', unsafe_allow_html=True)
st.markdown('<div class="help-text">上传照片，自动提取主色调，添加地点、时间和心情标签</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("", type=['jpg', 'jpeg', 'png'], label_visibility="collapsed")

if uploaded_file:
    image = Image.open(uploaded_file)
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.image(image, use_container_width=True)
        
        location = st.text_input("📍 地点", placeholder="杭州，中国")
        custom_time = st.text_input("🕰 时间", placeholder="2026.05.16")
        
        # 天气选项
        show_weather = st.checkbox("显示天气", value=False)
        
        if show_weather and location:
            col_temp, col_desc, col_btn = st.columns([2, 2, 1])
            
            with col_temp:
                temp_input = st.text_input("🌡️ 温度", value=st.session_state.get("weather_temp", ""), placeholder="14")
            
            with col_desc:
                weather_desc_input = st.text_input("🌤️ 天气", value=st.session_state.get("weather_desc_val", ""), placeholder="多云")
            
            with col_btn:
                st.write("")  # 空行对齐
                if st.button("获取"):
                    city = location.split('·')[0].strip() if '·' in location else location.split('，')[0].strip()
                    date = custom_time.split(' ')[0] if custom_time else ""
                    weather_result = get_weather_by_city(city, date)
                    if weather_result:
                        # 解析天气结果
                        parts = weather_result.split('°C · ')
                        if len(parts) >= 2:
                            # 去掉图标
                            temp = parts[0].split()[-1]
                            desc = parts[1]
                            st.session_state['weather_temp'] = temp
                            st.session_state['weather_desc_val'] = desc
                            st.success(f"✓ {temp}°C · {desc}")
                            st.rerun()
        
        mood = st.text_area("💭 心情和想说的话", placeholder="calm，需要很多阳光", height=100)
        
        with st.expander("⚙️ 高级选项"):
            use_traditional = st.checkbox("转换为繁体字", value=False)
            show_palette = st.checkbox("显示色卡", value=True)
        
        if st.button("✨ 生成卡片", use_container_width=True):
            # 组合天气数据
            final_weather = ""
            if show_weather and location:
                temp_val = st.session_state.get('weather_temp', '')
                desc_val = st.session_state.get('weather_desc_val', '')
                if temp_val and desc_val:
                    final_weather = f"{temp_val}°C · {desc_val}"
            
            st.session_state['generate'] = True
            st.session_state['location'] = location
            st.session_state['custom_time'] = custom_time
            st.session_state['weather'] = final_weather
            st.session_state['mood'] = mood
            st.session_state['use_traditional'] = use_traditional
            st.session_state['show_palette'] = show_palette
    
    with col_right:
        if st.session_state.get('generate'):
            with st.spinner("Creating..."):
                card = create_photo_card(
                    image, 
                    st.session_state.get('location', ''),
                    st.session_state.get('custom_time', ''),
                    st.session_state.get('weather', ''),
                    st.session_state.get('mood', ''),
                    st.session_state.get('use_traditional', False),
                    st.session_state.get('show_palette', True)
                )
                
                st.markdown('<div class="photo-card-container">', unsafe_allow_html=True)
                st.image(card, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                buf = io.BytesIO()
                card.save(buf, format='JPEG', quality=100, dpi=(300, 300))
                buf.seek(0)
                
                st.download_button(
                    label="📥 Download",
                    data=buf,
                    file_name="photo_card.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
