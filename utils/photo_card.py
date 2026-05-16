#!/usr/bin/env python3
"""照片卡片生成器 - 上部色卡+文字，下部照片"""

import sys
from pathlib import Path
from PIL import Image, ExifTags, ImageDraw, ImageFont
from colorthief import ColorThief

def extract_main_color(image_path):
    """提取主色调"""
    ct = ColorThief(image_path)
    color = ct.get_color(quality=1)
    return color

def get_exif_data(image_path):
    """提取EXIF信息"""
    img = Image.open(image_path)
    exif_data = img._getexif()
    
    if not exif_data:
        return None
    
    exif = {}
    for tag, value in exif_data.items():
        tag_name = ExifTags.TAGS.get(tag, tag)
        exif[tag_name] = value
    
    result = {}
    
    # 拍摄时间
    if 'DateTimeOriginal' in exif:
        dt = exif['DateTimeOriginal']
        # 格式: 2024.03.15 14:32
        result['datetime'] = dt.replace(':', '-', 2).replace(':', '.', 1)
    
    # GPS信息
    if 'GPSInfo' in exif:
        result['gps'] = parse_gps(exif['GPSInfo'])
    
    return result

def parse_gps(gps_info):
    """解析GPS信息为经纬度"""
    def convert_to_degrees(value):
        d, m, s = value
        return float(d) + float(m)/60 + float(s)/3600
    
    try:
        lat = convert_to_degrees(gps_info[2])
        if gps_info[1] == 'S':
            lat = -lat
        
        lon = convert_to_degrees(gps_info[4])
        if gps_info[3] == 'W':
            lon = -lon
        
        return (lat, lon)
    except:
        return None

def get_brightness(rgb):
    """计算颜色亮度"""
    return (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000

def get_contrast_color(bg_color):
    """根据背景色返回对比色（黑或白）"""
    brightness = get_brightness(bg_color)
    return (255, 255, 255) if brightness < 128 else (0, 0, 0)

def create_photo_card(image_path, location="", custom_time="", output_path=None):
    """生成照片卡片
    
    Args:
        image_path: 照片路径
        location: 地点（可选）
        custom_time: 自定义时间（可选，不填则从EXIF读取）
        output_path: 输出路径（可选）
    """
    print(f"处理图片: {image_path}")
    
    # 提取主色调
    print("提取主色调...")
    main_color = extract_main_color(image_path)
    print(f"主色调: RGB{main_color}")
    
    # 时间信息
    if custom_time:
        datetime_str = custom_time
    else:
        # 提取EXIF
        print("读取EXIF信息...")
        exif = get_exif_data(image_path)
        datetime_str = exif.get('datetime', '未知时间') if exif else '未知时间'
    
    # GPS信息（仅在未手动指定地点时读取）
    if not location:
        exif = get_exif_data(image_path)
        if exif and exif.get('gps'):
            print(f"检测到GPS: {exif['gps']}")
            lat, lon = exif['gps']
            location = f"{lat:.2f}°N, {lon:.2f}°E"
    
    if not location:
        location = "未知地点"
    
    # 打开原图
    img = Image.open(image_path)
    
    # 计算输出尺寸
    card_width = 800
    photo_height = int(card_width * img.height / img.width)
    text_height = photo_height // 2  # 上部区域占1/3
    total_height = photo_height + text_height
    
    # 调整照片尺寸
    img = img.resize((card_width, photo_height), Image.Resampling.LANCZOS)
    
    # 创建输出画布
    output = Image.new('RGB', (card_width, total_height), main_color)
    
    # 粘贴照片到下部
    output.paste(img, (0, text_height))
    
    # 绘制文字
    draw = ImageDraw.Draw(output)
    text_color = get_contrast_color(main_color)
    
    # 尝试加载字体，失败则用默认字体
    # 优先从项目目录读取，再到系统字体目录
    project_dir = Path(__file__).parent
    
    try:
        # 字体路径（优先级从高到低）
        font_paths = [
            # 项目目录字体（推荐）
            project_dir / "GenWanMin2-EL.ttc",  # 源云明体
            project_dir / "GenWanMincho.ttc",
            project_dir / "SourceHanSerifSC-VF.ttf",  # 思源宋体
            project_dir / "SourceHanSerifSC-VF.otf",
            # 系统字体
            Path("C:/Windows/Fonts/SourceHanSerifSC-VF.ttf"),
            Path("C:/Windows/Fonts/SourceHanSerifSC-VF.otf"),
            Path("C:/Windows/Fonts/msyh.ttc"),  # 微软雅黑
            Path("C:/Windows/Fonts/simhei.ttf"),  # 黑体
        ]
        
        # 英文字体路径（项目目录）
        english_font_paths = [
            project_dir / "Inter-ThinItalic.ttf",  # Thin斜体
            project_dir / "Inter.ttc",  # TTC包含所有字重
            project_dir / "Inter-Thin.ttf",
            project_dir / "Inter-Light.ttf",
            project_dir / "Inter-Regular.ttf",
        ]
        
        font_cn = None
        font_en = None
        font_small = None
        
        # 加载中文字体
        for font_path in font_paths:
            if font_path.exists():
                font_cn = ImageFont.truetype(str(font_path), 52)
                font_small = ImageFont.truetype(str(font_path), 20)
                print(f"使用中文字体: {font_path.name}")
                break
        
        # 加载英文字体
        for font_path in english_font_paths:
            if font_path.exists():
                font_en = ImageFont.truetype(str(font_path), 40)
                print(f"使用英文字体: {font_path.name}")
                break
        
        # 如果没有英文字体，用中文字体替代
        if not font_en:
            font_en = font_cn if font_cn else ImageFont.load_default()
        
        # 如果没有中文字体，用默认字体
        if not font_cn:
            font_cn = ImageFont.load_default()
            font_small = ImageFont.load_default()
            print("警告: 未找到字体，使用默认字体")
            
    except Exception as e:
        print(f"字体加载失败: {e}")
        font_cn = ImageFont.load_default()
        font_en = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 计算文字位置（居中）
    # 地点（上）+ 时间（下）
    text_location = location
    text_time = datetime_str
    
    # 获取文字边界框
    bbox_loc = draw.textbbox((0, 0), text_location, font=font_cn)
    bbox_time = draw.textbbox((0, 0), text_time, font=font_small)
    
    text_loc_width = bbox_loc[2] - bbox_loc[0]
    text_time_width = bbox_time[2] - bbox_time[0]
    
    # 地点位置
    x_loc = (card_width - text_loc_width) // 2
    y_loc = text_height // 2 - 30
    
    # 时间位置
    x_time = (card_width - text_time_width) // 2
    y_time = text_height // 2 + 30
    
    # 绘制文字
    draw.text((x_loc, y_loc), text_location, fill=text_color, font=font_cn)
    draw.text((x_time, y_time), text_time, fill=text_color, font=font_small)
    
    # 保存
    if not output_path:
        output_path = Path(image_path).stem + "_card.jpg"
    
    output.save(output_path, quality=95)
    print(f"\n✓ 卡片已保存: {output_path}")
    
    # 打印信息
    print(f"\n📍 地点: {location}")
    print(f"📅 时间: {datetime_str}")
    print(f"🎨 背景色: RGB{main_color}")
    
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python photo_card.py <图片路径> [地点] [时间] [输出路径]")
        print("示例:")
        print("  python photo_card.py photo.jpg")
        print("  python photo_card.py photo.jpg '杭州，中国'")
        print("  python photo_card.py photo.jpg '杭州，中国' '2024.03.15 14:32'")
        sys.exit(1)
    
    image_path = sys.argv[1]
    location = sys.argv[2] if len(sys.argv) > 2 else ""
    custom_time = sys.argv[3] if len(sys.argv) > 3 else ""
    output_path = sys.argv[4] if len(sys.argv) > 4 else None
    
    create_photo_card(image_path, location, custom_time, output_path)
