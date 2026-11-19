# -*- coding: utf-8 -*-
"""Build the Chicago 18th-edition bibliography (DOCX + Markdown)."""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT_DOCX = "铜镜研究参考书目_Chicago18.docx"
OUT_MD = "铜镜研究参考书目_Chicago18.md"

BODY_FONT = "Times New Roman"
CJK_FONT = "宋体"

# Each entry: list of (text, italic)
SECTIONS = [
    ("一、专著与图录", "Books and Catalogues", [
        [
            ("Cahill, Suzanne E. ", False),
            ("The Lloyd Cotsen Study Collection of Chinese Bronze Mirrors", True),
            (". Vol. 1, ", False),
            ("Catalogue", True),
            (". Edited by Lothar von Falkenhausen. Cotsen Occasional Press; "
             "UCLA Cotsen Institute of Archaeology Press, 2009.", False),
        ],
        [
            ("Falkenhausen, Lothar von, ed. ", False),
            ("The Lloyd Cotsen Study Collection of Chinese Bronze Mirrors", True),
            (". Vol. 2, ", False),
            ("Studies", True),
            (". Cotsen Occasional Press; UCLA Cotsen Institute of Archaeology Press, 2011.", False),
        ],
        [
            ("Loewe, Michael. ", False),
            ("Ways to Paradise: The Chinese Quest for Immortality", True),
            (". George Allen & Unwin, 1979.", False),
        ],
    ]),
    ("二、期刊论文", "Journal Articles", [
        [
            ("Li Xinwei (李新伟). “中国史前陶器图像反映的‘天极’观念”"
             "[The “Celestial Pole” Concept as Reflected in Prehistoric Chinese Pottery Imagery]. ", False),
            ("Zhongyuan wenwu", True),
            (" 中原文物, no. 3 (2020). Reprinted on ", False),
            ("Zhongguo Lishi Yanjiuyuan wang", False),
            (" 中国历史研究院网, February 28, 2025. "
             "http://hrczh.cass.cn/sxqy/kgx/202502/t20250228_5852431.shtml.", False),
        ],
        [
            ("Pan Jing (潘静) and Jing Zhongwei (井中伟). “中国早期铜镜的类型、流布和功能”"
             "[Types, Distribution, and Functions of Early Chinese Bronze Mirrors]. ", False),
            ("Xiyu yanjiu", True),
            (" 西域研究, no. 2 (2020): 37–57, 171. "
             "https://doi.org/10.16363/j.cnki.xyyj.2020.02.004.", False),
        ],
    ]),
    ("三、报刊与网络文章", "Newspapers and Online Essays", [
        [
            ("Chen Yajun (陈亚军). “尕马台发现齐家文化铜镜补论”"
             "[A Supplementary Study of the Qijia Culture Bronze Mirror Found at Gamatai]. ", False),
            ("Qijia Wenhua wang", False),
            (" 齐家文化网, May 28, 2022. "
             "http://www.qijiawenhua.cn/html/2022/hswz_0528/1573.html.", False),
        ],
        [
            ("Zhang Shaoyun (张少昀). “齐家文化铜器铸造技术研究”"
             "[Research on Bronze Casting Technology of the Qijia Culture]. ", False),
            ("Qijia Wenhua wang", False),
            (" 齐家文化网, May 28, 2022. "
             "http://www.qijiawenhua.cn/html/2022/hswz_0528/1572.html.", False),
        ],
        [
            ("Zhao Xin (赵信). “中国最早的铜镜”[China’s Earliest Bronze Mirrors]. ", False),
            ("Qinghai ribao", True),
            (" 青海日报, August 30, 2013. "
             "http://www.qinghai.gov.cn/dmqh/system/2013/08/30/010071712.shtml.", False),
        ],
    ]),
    ("四、博物馆藏品与在线数据库", "Museum Objects and Online Collections", [
        [
            ("British Museum. “Mirror [Bronze Mirror with Handle, Decorated with a Deity "
             "Mounted on a Deer].” ", False),
            ("The British Museum Collection Online", False),
            (", object 1990,0531.8. Accessed November 19, 2026. "
             "https://www.britishmuseum.org/collection/object/A_1990-0531-8.", False),
        ],
        [
            ("Nanjing Museum (南京博物院). “东汉规矩纹铜镜”"
             "[Eastern Han Bronze Mirror with TLV Pattern]. ", False),
            ("Nanjing Bowuyuan", False),
            (" 南京博物院. Accessed November 19, 2026. "
             "https://www.njmuseum.com/zh/collectionDetails?id=10381.", False),
        ],
        [
            ("Palace Museum (故宫博物院). “蓝透明珐琅描金喜字把镜”"
             "[Handled Mirror with Blue Transparent Enamel and Gilt ‘Double Happiness’ Design]. ", False),
            ("Gugong Bowuyuan", False),
            (" 故宫博物院, object 故00180346. Accessed November 19, 2026. "
             "https://www.dpm.org.cn/collection/utensil/230188.html.", False),
        ],
        [
            ("Xi’an Museum (西安博物院). “金背瑞兽葡萄镜”"
             "[Gilt-Backed Mirror with Auspicious Beasts and Grapevine]. ", False),
            ("Xi’an Bowuyuan", False),
            (" 西安博物院, June 6, 2025. "
             "https://www.xabwy.com/showtwo.html?id=719.", False),
        ],
    ]),
]

ANNOTATIONS = [
    ("Cahill 2009（卷 1）",
     "罗伊德·扣岑（Lloyd Cotsen）藏镜的完整图录，按纹饰类型编排，每件器物记录年代、尺寸、著录与图版，"
     "是查核实物、建立类型序列的基础工具书。"),
    ("Falkenhausen 2011（卷 2）",
     "十位学者关于早期铜镜的欧亚互动、战国至汉镜纹饰与铭文、铸造技术及社会功能的专题研究，可与卷 1 图录对读。"),
    ("Loewe 1979",
     "以马王堆帛画、TLV 镜与西王母图像为线索，讨论汉代宇宙观与死后信仰；"
     "是解释 TLV 镜图像程序与随葬功能的经典论著。"),
    ("Li 2020",
     "从史前陶器上的八角星纹、纽结纹与鸟兽图像论证“天极”观念的形成，"
     "为理解铜镜上的宇宙图式提供史前图像学背景。"),
    ("Pan and Jing 2020",
     "将早期铜镜分为具钮镜与有柄镜两大类、四期，统计 160 余件标本，提出河西走廊—新疆东部为具钮镜起源的关键区域，"
     "并讨论梳妆、佩饰、法器与身份象征等功能；可作本展类型与年代框架的主要依据。"),
    ("Chen 2022",
     "重新检讨尕马台 M25 七角星纹镜的年代、两阶段使用方式（钮系与木柄绑缚）及装饰来源，"
     "并汇集齐家文化铜镜的比较资料。"),
    ("Zhang 2022",
     "梳理齐家文化铜器的出土情况、合金成分与铸造工艺，说明其处于青铜时代初期，可补铜镜冶铸的技术背景。"),
    ("Zhao 2013",
     "记述尕马台七角星纹镜与齐家坪素面镜的发现、尺寸与铜锡比例，称其为所知中国最早铜镜；"
     "属普及性报道，宜作展览叙事素材。"),
    ("British Museum, 1990,0531.8",
     "宋代带柄铜镜，镜背饰骑鹿仙人，直径 10.3 厘米、连柄长 18.8 厘米；可作唐宋以后带柄镜传统的对照标本。"),
    ("Palace Museum, 故00180346",
     "清晚期广东进呈的蓝透明珐琅描金“囍”字把镜，综合玻璃、珐琅、象牙、珊瑚等材质与多种工艺；"
     "可作清代把镜工艺的延伸案例。"),
    ("Nanjing Museum",
     "东汉规矩纹（TLV）镜，直径 18.3 厘米、厚 0.8 厘米；TLV 纹是汉代宇宙观、式盘与镜铭研究的关键材料。"),
    ("Xi’an Museum",
     "唐代金背瑞兽葡萄镜，2002 年西安灞桥马家沟出土，直径 19.7 厘米、重 0.3 千克；"
     "金背工艺与瑞兽葡萄纹是唐镜的典型面貌。"),
]


def set_run_font(run, size=None, bold=None, italic=None, color=None):
    run.font.name = BODY_FONT
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), BODY_FONT)
    rFonts.set(qn("w:hAnsi"), BODY_FONT)
    rFonts.set(qn("w:eastAsia"), CJK_FONT)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def add_bottom_border(paragraph, size=6, color="A6A6A6", space=2):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), str(space))
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def add_page_field(paragraph):
    run = paragraph.add_run()
    set_run_font(run, size=8, color=RGBColor(0x80, 0x80, 0x80))
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(text)
    run._r.append(fld_end)


def add_section_heading(doc, zh, en):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(16)
    pf.space_after = Pt(7)
    pf.keep_with_next = True
    r = p.add_run(zh)
    set_run_font(r, size=12.5, bold=True)
    r2 = p.add_run("  " + en)
    set_run_font(r2, size=9, italic=True, color=RGBColor(0x66, 0x66, 0x66))
    add_bottom_border(p, size=4, color="BFBFBF", space=3)


def add_entry(doc, parts):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(0.9)
    pf.first_line_indent = Cm(-0.9)
    pf.line_spacing = 1.3
    pf.space_after = Pt(7)
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for text, italic in parts:
        r = p.add_run(text)
        set_run_font(r, size=10.5, italic=italic)
    return p


def build_docx():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.4)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(2.5)

    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), CJK_FONT)

    # header
    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run("中国铜镜研究参考书目 · Chicago 18th ed.")
    set_run_font(hr, size=8, color=RGBColor(0x8C, 0x8C, 0x8C))

    # footer
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = fp.add_run("— ")
    set_run_font(r1, size=8, color=RGBColor(0x80, 0x80, 0x80))
    add_page_field(fp)
    r2 = fp.add_run(" —")
    set_run_font(r2, size=8, color=RGBColor(0x80, 0x80, 0x80))

    # title block
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("中国铜镜研究参考书目")
    set_run_font(r, size=21, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("A Bibliography of Chinese Bronze Mirror Studies")
    set_run_font(r, size=11.5, color=RGBColor(0x40, 0x40, 0x40))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run("The Chicago Manual of Style, 18th Edition (2024) · Notes and Bibliography")
    set_run_font(r, size=9, italic=True, color=RGBColor(0x66, 0x66, 0x66))
    add_bottom_border(p, size=8, color="595959", space=6)

    # explanatory note
    notes = [
        ("体例说明　", "本目收录所提供资料共十一种，其中《The Lloyd Cotsen Study Collection of Chinese Bronze "
                     "Mirrors》二卷因出版年份与编著者不同，分列两条，共十二条。"),
        ("", "编目依据《芝加哥手册》第 18 版（2024，现行最新版）“注释—参考文献”系统：图书不再标注出版地（CMOS 14.30），"
             "文集篇章不列起止页码（14.8），期刊论文不标月份或季节；网络资源视其稳定性标注访问日期。"),
        ("", "中文文献按“拼音（汉字）”著录作者，篇名保留汉字并附英译；期刊、报纸名以拼音（斜体）与汉字并列，"
             "网站名用正体。条目先按文献类型分组，组内按作者字顺（中文按拼音）排列；如须合并为单一字母顺序书目，可按各条首词重排。"),
        ("", "文中访问日期统一为 2026 年 11 月 19 日。"),
    ]
    for label, text in notes:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing = 1.25
        pf.space_after = Pt(3)
        pf.left_indent = Cm(0.0)
        if label:
            lr = p.add_run(label)
            set_run_font(lr, size=9.5, bold=True, color=RGBColor(0x40, 0x40, 0x40))
        r = p.add_run(text)
        set_run_font(r, size=9.5, color=RGBColor(0x40, 0x40, 0x40))

    # entries
    for zh, en, entries in SECTIONS:
        add_section_heading(doc, zh, en)
        for parts in entries:
            add_entry(doc, parts)

    # annotations
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(22)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    r = p.add_run("附录：资料提要")
    set_run_font(r, size=13, bold=True)
    add_bottom_border(p, size=4, color="BFBFBF", space=3)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run("按正文条目顺序，撮述各资料的内容与可用之处，供展览文本与图录写作取资。")
    set_run_font(r, size=9, italic=True, color=RGBColor(0x66, 0x66, 0x66))

    for label, text in ANNOTATIONS:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(0.9)
        pf.first_line_indent = Cm(-0.9)
        pf.line_spacing = 1.25
        pf.space_after = Pt(5)
        lr = p.add_run(label)
        set_run_font(lr, size=9.5, bold=True, color=RGBColor(0x33, 0x33, 0x33))
        sep = p.add_run("　")
        set_run_font(sep, size=9.5)
        tr = p.add_run(text)
        set_run_font(tr, size=9.5, color=RGBColor(0x33, 0x33, 0x33))

    # closing
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("— 书目终 —")
    set_run_font(r, size=8.5, color=RGBColor(0x99, 0x99, 0x99))

    cp = doc.core_properties
    cp.title = "中国铜镜研究参考书目（Chicago 18th ed.）"
    cp.subject = "Chinese bronze mirrors — bibliography"
    cp.author = "策展研究"
    cp.comments = "Chicago Manual of Style, 18th edition (2024), notes-bibliography."

    doc.save(OUT_DOCX)
    return doc


def entry_to_md(parts):
    out = []
    for text, italic in parts:
        out.append(f"*{text}*" if italic else text)
    return "".join(out)


def build_md():
    lines = []
    lines.append("# 中国铜镜研究参考书目")
    lines.append("")
    lines.append("**A Bibliography of Chinese Bronze Mirror Studies**")
    lines.append("")
    lines.append("*The Chicago Manual of Style, 18th Edition (2024) · Notes and Bibliography*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**体例说明**　本目收录所提供资料共十一种，其中《The Lloyd Cotsen Study Collection of Chinese "
                 "Bronze Mirrors》二卷因出版年份与编著者不同，分列两条，共十二条。")
    lines.append("")
    lines.append("编目依据《芝加哥手册》第 18 版（2024，现行最新版）“注释—参考文献”系统：图书不再标注出版地（CMOS 14.30），"
                 "文集篇章不列起止页码（14.8），期刊论文不标月份或季节；网络资源视其稳定性标注访问日期。")
    lines.append("")
    lines.append("中文文献按“拼音（汉字）”著录作者，篇名保留汉字并附英译；期刊、报纸名以拼音（斜体）与汉字并列，"
                 "网站名用正体。条目先按文献类型分组，组内按作者字顺（中文按拼音）排列；如须合并为单一字母顺序书目，可按各条首词重排。"
                 "文中访问日期统一为 2026 年 11 月 19 日。")
    lines.append("")
    for zh, en, entries in SECTIONS:
        lines.append(f"## {zh}")
        lines.append("")
        lines.append(f"*{en}*")
        lines.append("")
        for parts in entries:
            lines.append(entry_to_md(parts))
            lines.append("")
    lines.append("## 附录：资料提要")
    lines.append("")
    lines.append("*按正文条目顺序，撮述各资料的内容与可用之处。*")
    lines.append("")
    for label, text in ANNOTATIONS:
        lines.append(f"**{label}**　{text}")
        lines.append("")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    build_docx()
    build_md()
    print("written", OUT_DOCX, OUT_MD)
