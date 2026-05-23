"""
将雅思词汇Excel导入到数据库
"""
import sys
sys.path.append('.')

from utils.study_db import import_vocabulary_from_excel, get_vocabulary_stats, get_vocabulary_categories

print("=" * 60)
print("导入雅思词汇到数据库")
print("=" * 60)

# 导入词汇
print("\n正在导入...")
added = import_vocabulary_from_excel("data/IELTS词汇整理.xlsx")
print(f"成功导入 {added} 个新单词")

# 获取统计
print("\n词汇库统计:")
stats = get_vocabulary_stats()
print(f"  单词总数: {stats['total_words']}")
print(f"  已掌握: {stats['mastered']}")
print(f"  学习中: {stats['learning']}")
print(f"  新单词: {stats['new_words']}")

# 获取分类
print("\n词汇分类:")
categories = get_vocabulary_categories()
for i, cat in enumerate(categories[:60], 1):
    print(f"  {i}. {cat}")

if len(categories) > 60:
    print(f"  ... 还有 {len(categories) - 20} 个分类")

print("\n" + "=" * 60)
print("导入完成！")
print("=" * 60)
print("\n现在可以运行: streamlit run app.py")
print("在'单词学习'标签页中开始学习雅思词汇")
