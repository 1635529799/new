import jieba.posseg
import jieba
import warnings
warnings.filterwarnings("ignore")

# 提取实体
def posseg_key(key,file):  # 通过jieba对问题进行词性标注
    jieba.load_userdict(file)  # userdict3中存储了所有头实体的name，用于提取实体
    question_seged = jieba.posseg.cut(str(key).strip())  # jieba.posseg.cut分词获得词性
    result = []
    for w in question_seged:
        word, flag = w.word, w.flag
        if str(flag).strip()=='nm':
            result.append(str(word).strip())

    return result  # 返回result









