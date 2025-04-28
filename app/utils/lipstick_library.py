# 定義口紅色號庫
LIPSTICK_COLORS = {
    'MAC': {
        'Ruby Woo': (185, 25, 25),
        'Chili': (180, 50, 35),
        'Velvet Teddy': (174, 108, 108),
        'Diva': (130, 35, 35),
        'Lady Danger': (228, 50, 30),
        'Russian Red': (190, 30, 30),
        'Mehr': (180, 100, 120)
    },
    'YSL': {
        'Rouge Pur': (170, 20, 60),
        'Le Rouge': (190, 25, 45),
        'Rouge Volupté': (200, 40, 80),
        'Tatouage Couture': (185, 35, 55),
        'Rouge Volupté Shine': (210, 50, 90),
        'Rouge Pur Couture': (195, 30, 50)
    },
    'DIOR': {
        '999 Iconic Red': (205, 20, 40),
        'Rouge Trafalgar': (215, 35, 45),
        'Forever Pink': (230, 130, 150),
        'Rosewood': (175, 95, 95),
        'Forever Nude': (200, 140, 130),
        'Rouge Graphist': (190, 40, 60)
    },
    'CHANEL': {
        'Pirate': (195, 25, 35),
        'Rouge Allure': (185, 30, 45),
        'Camelia': (210, 90, 100),
        'Rouge Coco': (180, 35, 50),
        'Rouge Noir': (90, 20, 25),
        'Boy': (170, 110, 110)
    },
    'NARS': {
        'Dragon Girl': (200, 35, 35),
        'Heat Wave': (230, 60, 40),
        'Dolce Vita': (170, 85, 90),
        'Cruella': (180, 30, 40),
        'Red Square': (210, 45, 35),
        'Jungle Red': (195, 40, 45)
    },
    '3CE': {
        'Taupe': (150, 90, 90),
        'Pink Run': (220, 120, 130),
        'Mellow Flower': (200, 100, 110),
        'Brunch Time': (190, 110, 100),
        'Null Set': (180, 95, 85),
        'Simple Stay': (170, 80, 80)
    },
    'Charlotte Tilbury': {
        'Pillow Talk': (190, 120, 120),
        'Walk of Shame': (180, 70, 80),
        'Red Carpet Red': (200, 30, 40),
        'Bond Girl': (160, 80, 85),
        'Very Victoria': (165, 105, 95),
        'Amazing Grace': (210, 110, 120)
    },
    'Armani': {
        'Red 400': (195, 25, 35),
        'Pink 500': (220, 100, 120),
        'Beige 100': (190, 130, 120),
        'Plum 200': (150, 60, 70),
        'Coral 300': (230, 90, 80),
        'Mauve 600': (170, 90, 100)
    }
}

# 預設口紅質地映射
DEFAULT_TEXTURES = {
    'MAC': {
        'Ruby Woo': 'matte',
        'Chili': 'matte',
        'Velvet Teddy': 'matte',
        'Diva': 'matte',
        'Lady Danger': 'matte',
        'Russian Red': 'matte',
        'Mehr': 'matte'
    },
    'YSL': {
        'Rouge Pur': 'matte',
        'Le Rouge': 'matte',
        'Rouge Volupté': 'gloss',
        'Tatouage Couture': 'matte',
        'Rouge Volupté Shine': 'gloss',
        'Rouge Pur Couture': 'velvet'
    },
    'DIOR': {
        '999 Iconic Red': 'matte',
        'Rouge Trafalgar': 'matte',
        'Forever Pink': 'gloss',
        'Rosewood': 'velvet',
        'Forever Nude': 'gloss',
        'Rouge Graphist': 'matte'
    },
    'CHANEL': {
        'Pirate': 'velvet',
        'Rouge Allure': 'velvet',
        'Camelia': 'gloss',
        'Rouge Coco': 'velvet',
        'Rouge Noir': 'matte',
        'Boy': 'velvet'
    },
    'NARS': {
        'Dragon Girl': 'matte',
        'Heat Wave': 'matte',
        'Dolce Vita': 'velvet',
        'Cruella': 'matte',
        'Red Square': 'matte',
        'Jungle Red': 'matte'
    },
    '3CE': {
        'Taupe': 'matte',
        'Pink Run': 'matte',
        'Mellow Flower': 'velvet',
        'Brunch Time': 'matte',
        'Null Set': 'matte',
        'Simple Stay': 'velvet'
    },
    'Charlotte Tilbury': {
        'Pillow Talk': 'matte',
        'Walk of Shame': 'matte',
        'Red Carpet Red': 'matte',
        'Bond Girl': 'matte',
        'Very Victoria': 'matte',
        'Amazing Grace': 'gloss'
    },
    'Armani': {
        'Red 400': 'velvet',
        'Pink 500': 'gloss',
        'Beige 100': 'gloss',
        'Plum 200': 'velvet',
        'Coral 300': 'gloss',
        'Mauve 600': 'velvet'
    }
}

def get_all_brands():
    """獲取所有品牌名稱"""
    return list(LIPSTICK_COLORS.keys())

def get_colors_for_brand(brand):
    """獲取特定品牌的所有色號"""
    if brand in LIPSTICK_COLORS:
        return list(LIPSTICK_COLORS[brand].keys())
    return []

def get_color_rgb(brand, color_name):
    """獲取特定品牌和色號的RGB值"""
    if brand in LIPSTICK_COLORS and color_name in LIPSTICK_COLORS[brand]:
        return LIPSTICK_COLORS[brand][color_name]
    return None

def get_texture(brand, color_name):
    """獲取特定品牌和色號的質地類型"""
    if brand in DEFAULT_TEXTURES and color_name in DEFAULT_TEXTURES[brand]:
        return DEFAULT_TEXTURES[brand][color_name]
    return 'matte'  # 默認霧面質地 