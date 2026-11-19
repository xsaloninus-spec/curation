# -*- coding: utf-8 -*-
"""Create a copy-paste-friendly, italicized 14-entry bibliography for PPT."""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = "铜镜书目_斜体版_14条.docx"
BODY_FONT = "Times New Roman"
CJK_FONT = "宋体"

ENTRIES = [
    [
        ("[1] Cahill, Suzanne E. ", False),
        ("The Lloyd Cotsen Study Collection of Chinese Bronze Mirrors", True),
        (". Vol. 1, ", False),
        ("Catalogue", True),
        (". Edited by Lothar von Falkenhausen. Cotsen Occasional Press / "
         "UCLA Cotsen Institute of Archaeology Press, 2009.", False),
    ],
    [
        ("[2] Falkenhausen, Lothar von, ed. ", False),
        ("The Lloyd Cotsen Study Collection of Chinese Bronze Mirrors", True),
        (". Vol. 2, ", False),
        ("Studies", True),
        (". Cotsen Occasional Press / UCLA Cotsen Institute of Archaeology Press, 2011.", False),
    ],
    [
        ("[3] Loewe, Michael. ", False),
        ("Ways to Paradise: The Chinese Quest for Immortality", True),
        (". George Allen & Unwin, 1979.", False),
    ],
    [
        ("[4] Li Xinwei (李新伟). “中国史前陶器图像反映的‘天极’观念” "
         "[The “Celestial Pole” Concept as Reflected in Prehistoric Chinese Pottery Imagery]. ", False),
        ("Zhongyuan wenwu", True),
        (" 中原文物, no. 3 (2020). Reprinted on Zhongguo Lishi Yanjiuyuan wang 中国历史研究院网, "
         "February 28, 2025. http://hrczh.cass.cn/sxqy/kgx/202502/t20250228_5852431.shtml.", False),
    ],
    [
        ("[5] Pan Jing (潘静) and Jing Zhongwei (井中伟). “中国早期铜镜的类型、流布和功能” "
         "[Types, Distribution, and Functions of Early Chinese Bronze Mirrors]. ", False),
        ("Xiyu yanjiu", True),
        (" 西域研究, no. 2 (2020): 37–57, 171. "
         "https://doi.org/10.16363/j.cnki.xyyj.2020.02.004.", False),
    ],
    [
        ("[6] Chen Yajun (陈亚军). “尕马台发现齐家文化铜镜补论” "
         "[A Supplementary Study of the Qijia Culture Bronze Mirror Found at Gamatai]. ", False),
        ("Qijia Wenhua wang", False),
        (" 齐家文化网, May 28, 2022. http://www.qijiawenhua.cn/html/2022/hswz_0528/1573.html.", False),
    ],
    [
        ("[7] Zhang Shaoyun (张少昀). “齐家文化铜器铸造技术研究” "
         "[Research on Bronze Casting Technology of the Qijia Culture]. ", False),
        ("Qijia Wenhua wang", False),
        (" 齐家文化网, May 28, 2022. http://www.qijiawenhua.cn/html/2022/hswz_0528/1572.html.", False),
    ],
    [
        ("[8] Zhao Xin (赵信). “中国最早的铜镜” [China’s Earliest Bronze Mirrors]. ", False),
        ("Qinghai ribao", True),
        (" 青海日报, August 30, 2013. "
         "http://www.qinghai.gov.cn/dmqh/system/2013/08/30/010071712.shtml.", False),
    ],
    [
        ("[9] British Museum. “Mirror [Bronze Mirror with Handle, Decorated with a Deity "
         "Mounted on a Deer].” ", False),
        ("The British Museum Collection Online", False),
        (", object 1990,0531.8. Accessed November 19, 2026. "
         "https://www.britishmuseum.org/collection/object/A_1990-0531-8.", False),
    ],
    [
        ("[10] Nanjing Museum (南京博物院). “东汉规矩纹铜镜” "
         "[Eastern Han Bronze Mirror with TLV Pattern]. ", False),
        ("Nanjing Bowuyuan", False),
        (" 南京博物院. Accessed November 19, 2026. "
         "https://www.njmuseum.com/zh/collectionDetails?id=10381.", False),
    ],
    [
        ("[11] Palace Museum (故宫博物院). “蓝透明珐琅描金喜字把镜” "
         "[Handled Mirror with Blue Transparent Enamel and Gilt ‘Double Happiness’ Design]. ", False),
        ("Gugong Bowuyuan", False),
        (" 故宫博物院, object 故00180346. Accessed November 19, 2026. "
         "https://www.dpm.org.cn/collection/utensil/230188.html.", False),
    ],
    [
        ("[12] Xi’an Museum (西安博物院). “金背瑞兽葡萄镜” "
         "[Gilt-Backed Mirror with Auspicious Beasts and Grapevine]. ", False),
        ("Xi’an Bowuyuan", False),
        (" 西安博物院, June 6, 2025. https://www.xabwy.com/showtwo.html?id=719.", False),
    ],
    [
        ("[13] Metropolitan Museum of Art. “Mirror with Interlaced Dragons.” ", False),
        ("The Met Collection", False),
        (", object 23.120.5. Accessed November 19, 2026. "
         "https://www.metmuseum.org/art/collection/search/61403.", False),
    ],
    [
        ("[14] Cleveland Museum of Art. “TLV Mirror with Four Spirits and Companions.” ", False),
        ("Cleveland Museum of Art", False),
        (", object 1995.301. Accessed November 19, 2026. "
         "https://www.clevelandart.org/art/1995.301.", False),
    ],
]


def set_run_font(run, size=10.5, italic=False):
    run.font.name = BODY_FONT
    run.italic = italic
    run.font.size = Pt(size)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), BODY_FONT)
    rFonts.set(qn("w:hAnsi"), BODY_FONT)
    rFonts.set(qn("w:eastAsia"), CJK_FONT)


doc = Document()
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(1.7)
sec.bottom_margin = Cm(1.7)
sec.left_margin = Cm(2.3)
sec.right_margin = Cm(2.3)

normal = doc.styles["Normal"]
normal.font.name = BODY_FONT
normal.font.size = Pt(10.5)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), CJK_FONT)

for parts in ENTRIES:
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.12
    pf.space_after = Pt(7)
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for text, italic in parts:
        set_run_font(p.add_run(text), italic=italic)

cp = doc.core_properties
cp.title = "中国铜镜研究参考书目（斜体版，14 条）"
cp.author = "策展研究"

doc.save(OUT)
print("written", OUT)
