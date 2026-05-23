"""
创建单词库Excel模板和示例数据
"""
import pandas as pd

# 示例单词数据
sample_data = [
    {
        "word": "cell",
        "translation": "细胞",
        "category": "生物学",
        "phonetic": "/sel/",
        "example_en": "The cell is the basic unit of life.",
        "example_cn": "细胞是生命的基本单位。",
        "difficulty": 2
    },
    {
        "word": "molecule",
        "translation": "分子",
        "category": "生物学",
        "phonetic": "/ˈmɒlɪkjuːl/",
        "example_en": "Water is a molecule composed of hydrogen and oxygen.",
        "example_cn": "水是由氢和氧组成的分子。",
        "difficulty": 3
    },
    {
        "word": "protein",
        "translation": "蛋白质",
        "category": "生物学",
        "phonetic": "/ˈprəʊtiːn/",
        "example_en": "Proteins are essential for cell structure and function.",
        "example_cn": "蛋白质对细胞结构和功能至关重要。",
        "difficulty": 3
    },
    {
        "word": "DNA",
        "translation": "脱氧核糖核酸",
        "category": "生物学",
        "phonetic": "/ˌdiː en ˈeɪ/",
        "example_en": "DNA carries genetic information in living organisms.",
        "example_cn": "DNA携带生物体的遗传信息。",
        "difficulty": 2
    },
    {
        "word": "enzyme",
        "translation": "酶",
        "category": "生物学",
        "phonetic": "/ˈenzaɪm/",
        "example_en": "Enzymes catalyze biochemical reactions in cells.",
        "example_cn": "酶催化细胞内的生化反应。",
        "difficulty": 4
    },
    {
        "word": "membrane",
        "translation": "膜",
        "category": "生物学",
        "phonetic": "/ˈmembreɪn/",
        "example_en": "The cell membrane controls what enters and exits the cell.",
        "example_cn": "细胞膜控制物质进出细胞。",
        "difficulty": 3
    },
    {
        "word": "chromosome",
        "translation": "染色体",
        "category": "生物学",
        "phonetic": "/ˈkrəʊməsəʊm/",
        "example_en": "Chromosomes contain DNA and proteins.",
        "example_cn": "染色体包含DNA和蛋白质。",
        "difficulty": 4
    },
    {
        "word": "mitochondria",
        "translation": "线粒体",
        "category": "生物学",
        "phonetic": "/ˌmaɪtəˈkɒndriə/",
        "example_en": "Mitochondria are the powerhouse of the cell.",
        "example_cn": "线粒体是细胞的能量工厂。",
        "difficulty": 4
    },
    {
        "word": "nucleus",
        "translation": "细胞核",
        "category": "生物学",
        "phonetic": "/ˈnjuːkliəs/",
        "example_en": "The nucleus contains the cell's genetic material.",
        "example_cn": "细胞核包含细胞的遗传物质。",
        "difficulty": 3
    },
    {
        "word": "photosynthesis",
        "translation": "光合作用",
        "category": "生物学",
        "phonetic": "/ˌfəʊtəʊˈsɪnθəsɪs/",
        "example_en": "Photosynthesis converts light energy into chemical energy.",
        "example_cn": "光合作用将光能转化为化学能。",
        "difficulty": 5
    },
    {
        "word": "geography",
        "translation": "地理学",
        "category": "自然地理",
        "phonetic": "/dʒiˈɒɡrəfi/",
        "example_en": "Geography studies the Earth's physical features.",
        "example_cn": "地理学研究地球的自然特征。",
        "difficulty": 2
    },
    {
        "word": "climate",
        "translation": "气候",
        "category": "自然地理",
        "phonetic": "/ˈklaɪmət/",
        "example_en": "Climate change affects ecosystems worldwide.",
        "example_cn": "气候变化影响全球生态系统。",
        "difficulty": 2
    },
    {
        "word": "ecosystem",
        "translation": "生态系统",
        "category": "自然地理",
        "phonetic": "/ˈiːkəʊˌsɪstəm/",
        "example_en": "An ecosystem includes all living and non-living components.",
        "example_cn": "生态系统包括所有生物和非生物成分。",
        "difficulty": 3
    },
    {
        "word": "biodiversity",
        "translation": "生物多样性",
        "category": "自然地理",
        "phonetic": "/ˌbaɪəʊdaɪˈvɜːsəti/",
        "example_en": "Biodiversity is essential for ecosystem stability.",
        "example_cn": "生物多样性对生态系统稳定性至关重要。",
        "difficulty": 4
    },
    {
        "word": "anatomy",
        "translation": "解剖学",
        "category": "医学",
        "phonetic": "/əˈnætəmi/",
        "example_en": "Anatomy is the study of body structure.",
        "example_cn": "解剖学是研究身体结构的学科。",
        "difficulty": 3
    },
    {
        "word": "diagnosis",
        "translation": "诊断",
        "category": "医学",
        "phonetic": "/ˌdaɪəɡˈnəʊsɪs/",
        "example_en": "Early diagnosis improves treatment outcomes.",
        "example_cn": "早期诊断可以改善治疗效果。",
        "difficulty": 3
    },
    {
        "word": "symptom",
        "translation": "症状",
        "category": "医学",
        "phonetic": "/ˈsɪmptəm/",
        "example_en": "Fever is a common symptom of infection.",
        "example_cn": "发烧是感染的常见症状。",
        "difficulty": 2
    },
    {
        "word": "vaccine",
        "translation": "疫苗",
        "category": "医学",
        "phonetic": "/ˈvæksiːn/",
        "example_en": "Vaccines help prevent infectious diseases.",
        "example_cn": "疫苗有助于预防传染病。",
        "difficulty": 3
    },
    {
        "word": "antibiotic",
        "translation": "抗生素",
        "category": "医学",
        "phonetic": "/ˌæntibaɪˈɒtɪk/",
        "example_en": "Antibiotics are used to treat bacterial infections.",
        "example_cn": "抗生素用于治疗细菌感染。",
        "difficulty": 4
    },
    {
        "word": "immune",
        "translation": "免疫的",
        "category": "医学",
        "phonetic": "/ɪˈmjuːn/",
        "example_en": "The immune system protects the body from disease.",
        "example_cn": "免疫系统保护身体免受疾病侵害。",
        "difficulty": 3
    }
]

# 创建DataFrame
df = pd.DataFrame(sample_data)

# 保存为Excel
output_path = "data/vocabulary_template.xlsx"
df.to_excel(output_path, index=False, sheet_name="单词库")

print(f"单词库模板已创建：{output_path}")
print(f"包含 {len(df)} 个示例单词")
print(f"分类：{', '.join(df['category'].unique())}")
